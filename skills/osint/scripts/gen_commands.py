#!/usr/bin/env python3
"""Generate investigation commands from a plan."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def generate_commands(plan: dict) -> str:
    """Generate a shell script from an investigation plan."""
    lines = ["#!/bin/bash", f"# OSINT Investigation: {plan.get('target_value', 'unknown')}", f"# Type: {plan.get('target_type', 'unknown')}", f"# Depth: {plan.get('depth', 'standard')}", "", "set -e", ""]

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
            lines.append(command)
            lines.append("")

        lines.append("")

    lines.append(f"# Investigation complete.")
    lines.append(f"# Total phases: {plan.get('total_phases', 0)}")
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
    print(f"  Generated {len(plan.get('phases', []))} phases")
    print(f"  Saved to: {output_path}")
    print(f"\n  To execute: bash {output_path}")


if __name__ == "__main__":
    main()
