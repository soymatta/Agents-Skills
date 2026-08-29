#!/usr/bin/env python3
"""
collect_feedback.py — Structured feedback collection for agent self-improvement.

Usage:
    python collect_feedback.py --task "Task description" --rating 3 \
        --issues "format_wrong,bookmark_order" --fixes "use_justify,w_anchor" \
        --category document-generation --tokens 50000 --duration 1200

    python collect_feedback.py --interactive  # prompts for each field

    python collect_feedback.py --output custom-feedback.json  # custom path

Appends to: templates/agent-feedback.json (or the --output path)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
FEEDBACK_FILE = SCRIPT_DIR.parent / "templates" / "agent-feedback.json"


def load_feedback(path: Path | None = None) -> list:
    """Load existing feedback entries.

    Accepts either a JSON array file, a JSON object with an ``entries`` list, or
    a JSON-lines (ndjson) file where each line is one feedback record.
    """
    path = path or FEEDBACK_FILE
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        entries = []
        for line in raw.splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        entries = data.get("entries")
        return entries if isinstance(entries, list) else []
    return []


def save_feedback(entries: list, path: Path | None = None) -> None:
    """Save feedback entries to JSON."""
    path = path or FEEDBACK_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def generate_session_id(entries: list) -> str:
    """Generate next session ID."""
    existing_ids = [e.get("id", "") for e in entries]
    nums = []
    for eid in existing_ids:
        if eid.startswith("session-"):
            try:
                nums.append(int(eid.split("-")[1]))
            except ValueError:
                pass
    next_num = max(nums, default=0) + 1
    return f"session-{next_num:03d}"


def create_feedback_entry(
    task: str,
    rating: int,
    issues: list[dict] = None,
    suggestions: list[str] = None,
    category: str = "general",
    tokens_used: int = 0,
    duration_seconds: int = 0,
    retry_count: int = 0,
    tool_calls: int = 0,
    files_modified: list[str] = None,
    files_created: list[str] = None,
    agent: str = "unknown",
    output: Path | None = None,
) -> dict:
    """Create a structured feedback entry."""
    entries = load_feedback(output)
    session_id = generate_session_id(entries)

    entry = {
        "id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "task": task,
        "category": category,
        "rating": max(1, min(5, rating)),
        "issues": issues or [],
        "suggestions": suggestions or [],
        "tokens_used": tokens_used,
        "duration_seconds": duration_seconds,
        "retry_count": retry_count,
        "tool_calls": tool_calls,
        "files_modified": files_modified or [],
        "files_created": files_created or [],
    }

    entries.append(entry)
    save_feedback(entries, output)
    return entry


def interactive_collect() -> dict:
    """Interactively collect feedback from the user."""
    print("=" * 60)
    print("AGENT SELF-IMPROVER — Feedback Collection")
    print("=" * 60)

    task = input("\nTask description: ").strip()
    agent = input("Agent name [paper-researcher]: ").strip() or "paper-researcher"
    category = input("Category [document-generation/code/research]: ").strip() or "document-generation"

    while True:
        try:
            rating = int(input("Rating (1-5): ").strip())
            if 1 <= rating <= 5:
                break
            print("  Must be 1-5")
        except ValueError:
            print("  Enter a number")

    # Collect issues
    issues = []
    print("\n--- Issues (empty line to stop) ---")
    while True:
        desc = input("Issue description: ").strip()
        if not desc:
            break
        severity = input("  Severity (critical/high/medium/low) [high]: ").strip() or "high"
        issue_type = input("  Type (format/bug/xml/i18n/logic/performance) [format]: ").strip() or "format"
        root_cause = input("  Root cause: ").strip()
        fix = input("  Fix applied: ").strip()
        issues.append({
            "type": issue_type,
            "description": desc,
            "severity": severity,
            "fix_applied": fix,
            "root_cause": root_cause,
        })

    # Collect suggestions
    suggestions = []
    print("\n--- Suggestions (empty line to stop) ---")
    while True:
        s = input("Suggestion: ").strip()
        if not s:
            break
        suggestions.append(s)

    tokens = int(input("\nTokens used [0]: ").strip() or "0")
    duration = int(input("Duration in seconds [0]: ").strip() or "0")
    retries = int(input("Retry count [0]: ").strip() or "0")
    tool_calls_count = int(input("Tool calls [0]: ").strip() or "0")

    files_mod = input("Files modified (comma-separated): ").strip()
    files_cr = input("Files created (comma-separated): ").strip()

    entry = create_feedback_entry(
        task=task,
        rating=rating,
        issues=issues,
        suggestions=suggestions,
        category=category,
        tokens_used=tokens,
        duration_seconds=duration,
        retry_count=retries,
        tool_calls=tool_calls_count,
        files_modified=[f.strip() for f in files_mod.split(",") if f.strip()],
        files_created=[f.strip() for f in files_cr.split(",") if f.strip()],
        agent=agent,
    )

    print(f"\nFeedback saved: {entry['id']}")
    print(json.dumps(entry, indent=2, ensure_ascii=False))
    return entry


def main():
    parser = argparse.ArgumentParser(description="Collect agent feedback")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--task", "-t", help="Task description")
    parser.add_argument("--agent", "-a", default="paper-researcher", help="Agent name")
    parser.add_argument("--category", "-c", default="document-generation", help="Category")
    parser.add_argument("--rating", "-r", type=int, help="Rating 1-5")
    parser.add_argument("--issues", help="Comma-separated issue descriptions")
    parser.add_argument("--issue-types", help="Comma-separated issue types (format,bug,xml,i18n,logic)")
    parser.add_argument("--issue-severities", help="Comma-separated severities")
    parser.add_argument("--fixes", help="Comma-separated fixes applied")
    parser.add_argument("--root-causes", help="Comma-separated root causes")
    parser.add_argument("--suggestions", help="Comma-separated suggestions")
    parser.add_argument("--tokens", type=int, default=0, help="Tokens used")
    parser.add_argument("--duration", type=int, default=0, help="Duration in seconds")
    parser.add_argument("--retries", type=int, default=0, help="Retry count")
    parser.add_argument("--tool-calls", type=int, default=0, help="Tool calls count")
    parser.add_argument("--files-modified", help="Comma-separated files modified")
    parser.add_argument("--files-created", help="Comma-separated files created")
    parser.add_argument("--output", "-o", default=str(FEEDBACK_FILE), help="Output feedback JSON path")
    args = parser.parse_args()

    output = Path(args.output)

    if args.interactive:
        interactive_collect()
        return

    if not args.task or not args.rating:
        print("Error: --task and --rating are required", file=sys.stderr)
        sys.exit(1)

    # Parse issues
    issues = []
    if args.issues:
        descs = [d.strip() for d in args.issues.split(",")]
        types = [t.strip() for t in args.issue_types.split(",")] if args.issue_types else ["format"] * len(descs)
        sevs = [s.strip() for s in args.issue_severities.split(",")] if args.issue_severities else ["high"] * len(descs)
        fixes = [f.strip() for f in args.fixes.split(",")] if args.fixes else [""] * len(descs)
        causes = [c.strip() for c in args.root_causes.split(",")] if args.root_causes else [""] * len(descs)

        for i, desc in enumerate(descs):
            issues.append({
                "type": types[i] if i < len(types) else "format",
                "description": desc,
                "severity": sevs[i] if i < len(sevs) else "high",
                "fix_applied": fixes[i] if i < len(fixes) else "",
                "root_cause": causes[i] if i < len(causes) else "",
            })

    suggestions = [s.strip() for s in args.suggestions.split(",")] if args.suggestions else []

    entry = create_feedback_entry(
        task=args.task,
        rating=args.rating,
        issues=issues,
        suggestions=suggestions,
        category=args.category,
        tokens_used=args.tokens,
        duration_seconds=args.duration,
        retry_count=args.retries,
        tool_calls=args.tool_calls,
        files_modified=[f.strip() for f in (args.files_modified or "").split(",") if f.strip()],
        files_created=[f.strip() for f in (args.files_created or "").split(",") if f.strip()],
        agent=args.agent,
        output=output,
    )

    print(f"Feedback saved: {entry['id']}")


if __name__ == "__main__":
    main()