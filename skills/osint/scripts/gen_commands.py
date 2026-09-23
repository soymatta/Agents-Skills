#!/usr/bin/env python3
"""Generate investigation commands from a plan."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path


SHELL_TOOLS = {
    "whois", "dig", "nslookup", "host", "curl", "wget",
    "holehe", "sherlock", "maigret", "theHarvester", "nmap",
    "subfinder", "whatweb", "amass", "dnsrecon", "recon-ng", "python",
    "trufflehog", "gitleaks", "exiftool", "openssl",
}

# Tools that may not be installed on every machine. Their shell lines are
# emitted behind a `command -v` guard so the generated script keeps running
# (no hard failure under `set -e`) when the binary is absent.
OPTIONAL_TOOLS = {
    "nmap", "subfinder", "whatweb", "amass", "dnsrecon", "holehe",
    "sherlock", "maigret", "theHarvester", "trufflehog", "gitleaks",
    "exiftool", "recon-ng", "shodan",
}

# Tools that perform ACTIVE scanning/probing against the target. They run only
# against owned/authorized hosts; the generated script keeps them guarded.
ACTIVE_TOOLS = {"nmap", "amass", "dnsrecon", "recon-ng"}

# Pseudo-tools/commands that represent a web search the agent should run with
# its `websearch` tool, NOT something executable in a shell. They are emitted
# as comments so `bash commands.sh` never fails on them.
SEARCH_TOOLS = {"google", "bing", "yandex", "google_scholar", "google_news",
                "linkedin", "github", "gitlab", "stackoverflow", "medium",
                "facebook", "twitter", "reddit", "crunchbase", "glassdoor",
                "indeed", "news", "sec", "archive", "namechk", "lookup"}


def is_shell_step(step: dict) -> bool:
    """Whether a plan step maps to a runnable shell command (vs. a websearch)."""
    tool = (step.get("tool") or "").strip().lower()
    command = (step.get("command") or "").strip()
    if tool in SHELL_TOOLS:
        return True
    if tool in SEARCH_TOOLS:
        return False
    if command.startswith("search ") or command.startswith("curl ") is False and command.split():
        first = command.split()[0]
        return first in SHELL_TOOLS
    return True


def _guard_command(step: dict) -> str:
    """Wrap a shell command in a `command -v` guard when the tool is optional.

    Optional/active-scan tools (nmap, subfinder, ...) that may not be installed
    are emitted guarded, so the generated script degrades gracefully (logs a
    skip line) instead of hard-failing under `set -e`.
    """
    command = step.get("command", "echo 'No command'")
    tool = (step.get("tool") or "").strip().lower()
    if tool not in OPTIONAL_TOOLS:
        return command
    if command.startswith("search "):
        return command
    binary = shlex.split(command)[0] if command.split() else "tool"
    return (f"if command -v {binary} >/dev/null 2>&1; then\n"
            f"    {command}\n"
            f"else\n"
            f"    echo \"[SKIP] {binary} not installed - command skipped: {command}\" >&2\n"
            f"fi")


def generate_commands(plan: dict) -> str:
    """Generate a shell script from an investigation plan.

    Shell steps (whois, dig, curl, nmap, ...) are written as executable lines.
    Web-search steps (google, linkedin, namechk, 'search "..."' pseudo-
    commands, ...) are written as comments prefixed with `[WEBSEARCH]` so the
    script stays runnable; the agent runs those with its `websearch` tool.
    """
    target = plan.get("target_value", "unknown")
    lines = ["#!/bin/bash",
             f"# OSINT Investigation: {shlex.quote(target)}",
             f"# Type: {plan.get('target_type', 'unknown')}",
             f"# Depth: {plan.get('depth', 'standard')}",
             "",
             "# NOTE: lines prefixed with [WEBSEARCH] are run by the agent's",
             "# `websearch` tool, not by this shell script. Only run the rest.",
             "set -e", ""]

    search_count = 0
    for i, phase in enumerate(plan.get("phases", []), 1):
        lines.append(f"# {'='*60}")
        lines.append(f"# PHASE {i}: {phase.get('name', 'Unknown')}")
        lines.append(f"# Estimated time: {phase.get('estimated_time', 'unknown')}")
        lines.append(f"# {'='*60}")
        lines.append("")

        for j, step in enumerate(phase.get("steps", []), 1):
            tool = step.get("tool", "unknown")
            command = step.get("command", "echo 'No command'")
            purpose = step.get("purpose", "")
            condition = step.get("condition", "")

            lines.append(f"# Step {j}: {purpose}")
            if condition:
                lines.append(f"# Condition: {condition}")
            lines.append(f"# Tool: {tool}")

            if is_shell_step(step):
                lines.append(_guard_command(step))
            else:
                lines.append(f"# [WEBSEARCH] {command}")
                search_count += 1
            lines.append("")

        lines.append("")

    lines.append(f"# Investigation complete.")
    lines.append(f"# Total phases: {plan.get('total_phases', 0)}")
    lines.append(f"# Web search steps (run via websearch tool): {search_count}")
    lines.append("echo 'Investigation complete.'")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python gen_commands.py --plan investigation_plan.json [--output commands.sh]")
        sys.exit(1)

    plan_path = Path(sys.argv[1] if sys.argv[1] != "--plan" else sys.argv[2])
    output_path = Path("commands.sh")

    for i, arg in enumerate(sys.argv):
        if arg == "--output" and i + 1 < len(sys.argv):
            output_path = Path(sys.argv[i + 1])

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    commands = generate_commands(plan)

    output_path.write_text(commands, encoding="utf-8")
    search_count = sum(
        1 for phase in plan.get("phases", []) for step in phase.get("steps", [])
        if not is_shell_step(step)
    )
    print(f"  Generated {len(plan.get('phases', []))} phases")
    print(f"  Shell commands: {sum(1 for p in plan.get('phases', []) for s in p.get('steps', []) if is_shell_step(s))}")
    print(f"  Websearch steps (comments, run via agent websearch tool): {search_count}")
    print(f"  Saved to: {output_path}")
    if search_count:
        print(f"\n  NOTE: {search_count} step(s) are web searches (marked [WEBSEARCH]).")
        print(f"  Run the executable commands with: bash {output_path}")
        print(f"  Execute the [WEBSEARCH] steps with your `websearch` tool instead.")
    else:
        print(f"\n  To execute: bash {output_path}")


if __name__ == "__main__":
    main()
