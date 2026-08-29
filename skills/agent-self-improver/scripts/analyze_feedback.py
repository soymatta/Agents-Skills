#!/usr/bin/env python3
"""
analyze_feedback.py — Analyze accumulated agent feedback for recurring patterns.

Usage:
    python analyze_feedback.py
    python analyze_feedback.py --input feedback.json --output improvement-log.json
    python analyze_feedback.py --threshold 0.2 --min-sessions 2
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone


SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_INPUT = SKILL_DIR / "templates" / "agent-feedback.json"
DEFAULT_OUTPUT = SKILL_DIR / "templates" / "improvement-log.json"


def load_feedback(path: Path) -> list:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    return []


def save_output(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def analyze_patterns(entries: list, threshold: float = 0.2, min_sessions: int = 2) -> dict:
    """Analyze feedback entries for recurring patterns."""
    
    total_sessions = len(entries)
    if total_sessions == 0:
        return {"error": "No feedback entries found", "total_sessions": 0}

    # ── Overall Metrics ───────────────────────────────────────────────────
    ratings = [e.get("rating", 0) for e in entries]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    total_retries = sum(e.get("retry_count", 0) for e in entries)
    total_tokens = sum(e.get("tokens_used", 0) for e in entries)
    total_duration = sum(e.get("duration_seconds", 0) for e in entries)
    total_tool_calls = sum(e.get("tool_calls", 0) for e in entries)

    retry_rate = total_retries / total_sessions if total_sessions else 0
    avg_tokens_per_session = total_tokens / total_sessions if total_sessions else 0

    # ── Issue Analysis ────────────────────────────────────────────────────
    all_issues = []
    for e in entries:
        for issue in e.get("issues", []):
            issue_copy = dict(issue)
            issue_copy["session_id"] = e.get("id", "unknown")
            issue_copy["session_rating"] = e.get("rating", 0)
            all_issues.append(issue_copy)

    total_issues = len(all_issues)
    issue_density = total_issues / total_tool_calls if total_tool_calls else 0

    # Count by type
    type_counter = Counter(i.get("type", "unknown") for i in all_issues)
    severity_counter = Counter(i.get("severity", "unknown") for i in all_issues)

    # Issues per session
    issues_per_session = defaultdict(int)
    for i in all_issues:
        issues_per_session[i.get("session_id", "unknown")] += 1

    # ── Pattern Detection ─────────────────────────────────────────────────
    patterns = []

    # Pattern 1: Issue types that appear in >threshold of sessions
    sessions_with_issue_type = defaultdict(set)
    for i in all_issues:
        session_id = i.get("session_id", "unknown")
        issue_type = i.get("type", "unknown")
        sessions_with_issue_type[issue_type].add(session_id)

    for issue_type, session_ids in sessions_with_issue_type.items():
        freq = len(session_ids) / total_sessions
        if freq >= threshold and len(session_ids) >= min_sessions:
            # Get the most common fix for this type
            fixes = [i.get("fix_applied", "") for i in all_issues if i.get("type") == issue_type and i.get("fix_applied")]
            most_common_fix = Counter(fixes).most_common(1)[0][0] if fixes else "No fix recorded"
            
            causes = [i.get("root_cause", "") for i in all_issues if i.get("type") == issue_type and i.get("root_cause")]
            most_common_cause = Counter(causes).most_common(1)[0][0] if causes else "Unknown"

            patterns.append({
                "id": f"pattern-{len(patterns)+1:03d}",
                "type": "recurring_issue_type",
                "issue_type": issue_type,
                "frequency": round(freq, 3),
                "affected_sessions": sorted(session_ids),
                "count": len(session_ids),
                "most_common_fix": most_common_fix,
                "most_common_root_cause": most_common_cause,
                "severity": "high" if freq >= 0.5 else "medium",
            })

    # Pattern 2: Specific issues that repeat
    issue_descriptions = Counter(i.get("description", "") for i in all_issues)
    for desc, count in issue_descriptions.items():
        if count >= 2:
            freq = count / total_sessions
            sessions = [i.get("session_id", "") for i in all_issues if i.get("description") == desc]
            patterns.append({
                "id": f"pattern-{len(patterns)+1:03d}",
                "type": "recurring_specific_issue",
                "description": desc,
                "frequency": round(freq, 3),
                "count": count,
                "affected_sessions": sorted(set(sessions)),
                "severity": "high" if count >= 3 else "medium",
            })

    # Pattern 3: Low-rated sessions
    low_rated = [e for e in entries if e.get("rating", 5) <= 2]
    if low_rated:
        low_rated_ids = [e.get("id", "") for e in low_rated]
        patterns.append({
            "id": f"pattern-{len(patterns)+1:03d}",
            "type": "low_satisfaction",
            "description": f"{len(low_rated)} sessions rated 2 or below",
            "frequency": round(len(low_rated) / total_sessions, 3),
            "affected_sessions": low_rated_ids,
            "severity": "high",
        })

    # Pattern 4: High retry rate
    high_retry_sessions = [e for e in entries if e.get("retry_count", 0) >= 3]
    if high_retry_sessions:
        patterns.append({
            "id": f"pattern-{len(patterns)+1:03d}",
            "type": "high_retry_rate",
            "description": f"{len(high_retry_sessions)} sessions with 3+ retries",
            "frequency": round(len(high_retry_sessions) / total_sessions, 3),
            "affected_sessions": [e.get("id", "") for e in high_retry_sessions],
            "severity": "high" if len(high_retry_sessions) / total_sessions >= 0.3 else "medium",
        })

    # ── Improvement Suggestions ───────────────────────────────────────────
    suggestions = []
    for pattern in patterns:
        if pattern["severity"] == "high":
            suggestion = {
                "pattern_id": pattern["id"],
                "pattern_type": pattern["type"],
                "issue_type": pattern.get("issue_type", pattern.get("type", "")),
                "frequency": pattern["frequency"],
                "severity": pattern["severity"],
                "suggested_action": _generate_suggestion(pattern),
                "confidence": min(0.95, 0.5 + pattern["frequency"] * 0.5),
                "requires_human_approval": True,
            }
            suggestions.append(suggestion)

    # ── Build Output ──────────────────────────────────────────────────────
    analysis = {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "total_sessions": total_sessions,
        "summary": {
            "avg_rating": round(avg_rating, 2),
            "total_issues": total_issues,
            "issue_density": round(issue_density, 4),
            "retry_rate": round(retry_rate, 2),
            "avg_tokens_per_session": int(avg_tokens_per_session),
            "total_duration_seconds": total_duration,
        },
        "issue_breakdown": {
            "by_type": dict(type_counter.most_common()),
            "by_severity": dict(severity_counter.most_common()),
        },
        "patterns_detected": patterns,
        "suggestions": suggestions,
        "top_improvements": [s["suggested_action"] for s in suggestions[:5]],
    }

    return analysis


def _generate_suggestion(pattern: dict) -> str:
    """Generate a concrete suggestion based on pattern."""
    ptype = pattern.get("type", "")
    issue_type = pattern.get("issue_type", "")
    freq = pattern.get("frequency", 0)

    suggestions_map = {
        "format-compliance": (
            "Add a FORMAT_SPEC dictionary at the top of every document generator "
            "with all standard values (font, size, spacing, margins) pre-defined. "
            "Cross-reference against the actual standard before generating."
        ),
        "xml-structure": (
            "Always use qn('w:tagname') for XML elements. For internal hyperlinks, "
            "use w:anchor attribute (not r:id). Add bookmark AFTER all runs."
        ),
        "i18n-support": (
            "Add regex patterns for all expected languages (English, Spanish, French, etc.) "
            "when detecting section headings. Use re.IGNORECASE."
        ),
        "script-bug": (
            "Verify enum values against the library API docs before using. "
            "Common python-docx: JUSTIFY not JUSTIFIED, CENTER not CENTRE."
        ),
        "logic": (
            "Add validation checks after each major step. "
            "Log intermediate results for debugging."
        ),
    }

    if ptype == "recurring_issue_type":
        return suggestions_map.get(issue_type, f"Review and fix recurring {issue_type} issues (appeared in {freq:.0%} of sessions)")
    elif ptype == "recurring_specific_issue":
        return f"Prevent: {pattern.get('description', 'Unknown issue')} — appeared {pattern.get('count', 0)} times"
    elif ptype == "low_satisfaction":
        return "Investigate root causes of low-rated sessions. Check if issues are from the same category."
    elif ptype == "high_retry_rate":
        return "Improve first-attempt success rate. Add pre-flight checks before generating output."
    return "Review pattern and implement fix"


def print_report(analysis: dict):
    """Print a human-readable report."""
    print("=" * 60)
    print("AGENT SELF-IMPROVER — Feedback Analysis Report")
    print("=" * 60)
    print(f"Analyzed at: {analysis.get('analyzed_at', 'N/A')}")
    print(f"Total sessions: {analysis['total_sessions']}")
    print()

    s = analysis.get("summary", {})
    print("SUMMARY")
    print("-" * 40)
    print(f"  Average rating:     {s.get('avg_rating', 0)}/5")
    print(f"  Total issues:       {s.get('total_issues', 0)}")
    print(f"  Issue density:      {s.get('issue_density', 0):.4f} per tool call")
    print(f"  Retry rate:         {s.get('retry_rate', 0):.1f} per session")
    print(f"  Avg tokens/session: {s.get('avg_tokens_per_session', 0):,}")
    print()

    # Issue breakdown
    bd = analysis.get("issue_breakdown", {})
    if bd.get("by_type"):
        print("ISSUES BY TYPE")
        print("-" * 40)
        for t, c in bd["by_type"].items():
            print(f"  {t:25s} {c:3d}")
        print()

    if bd.get("by_severity"):
        print("ISSUES BY SEVERITY")
        print("-" * 40)
        for sev, c in bd["by_severity"].items():
            print(f"  {sev:25s} {c:3d}")
        print()

    # Patterns
    patterns = analysis.get("patterns_detected", [])
    if patterns:
        print(f"PATTERNS DETECTED ({len(patterns)})")
        print("-" * 40)
        for p in patterns:
            print(f"  [{p['severity'].upper():8s}] {p.get('issue_type', p.get('type', ''))}")
            print(f"            Frequency: {p['frequency']:.0%} ({p.get('count', '?')} occurrences)")
            if p.get("most_common_fix"):
                print(f"            Fix: {p['most_common_fix'][:70]}")
            print()

    # Suggestions
    suggestions = analysis.get("suggestions", [])
    if suggestions:
        print(f"IMPROVEMENT SUGGESTIONS ({len(suggestions)})")
        print("-" * 40)
        for i, sug in enumerate(suggestions, 1):
            print(f"  #{i} [{sug['severity'].upper()}] Confidence: {sug['confidence']:.0%}")
            print(f"     {sug['suggested_action'][:80]}")
            print()

    # Top improvements
    top = analysis.get("top_improvements", [])
    if top:
        print("TOP IMPROVEMENTS")
        print("-" * 40)
        for i, imp in enumerate(top, 1):
            print(f"  {i}. {imp[:75]}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Analyze agent feedback patterns")
    parser.add_argument("--input", "-i", default=str(DEFAULT_INPUT), help="Input feedback JSON")
    parser.add_argument("--output", "-o", default=str(DEFAULT_OUTPUT), help="Output analysis JSON")
    parser.add_argument("--threshold", "-t", type=float, default=0.2, help="Frequency threshold (default: 0.2)")
    parser.add_argument("--min-sessions", "-m", type=int, default=2, help="Min sessions for pattern")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only, no report")
    args = parser.parse_args()

    entries = load_feedback(Path(args.input))
    if not entries:
        print(f"No feedback entries found in {args.input}", file=sys.stderr)
        sys.exit(1)

    analysis = analyze_patterns(entries, threshold=args.threshold, min_sessions=args.min_sessions)
    save_output(analysis, Path(args.output))

    if not args.json_only:
        print_report(analysis)

    print(f"\nAnalysis saved to: {args.output}")


if __name__ == "__main__":
    main()