#!/usr/bin/env python3
"""Execute OSINT investigation pipeline.

Runs commands from a plan, collects results, and generates findings.json.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


def run_command(cmd: str, timeout: int = 30) -> dict:
    """Execute a command and capture output."""
    start = time.time()
    try:
        result = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = round(time.time() - start, 2)
        return {
            "command": cmd,
            "returncode": result.returncode,
            "stdout": result.stdout[:5000] if result.stdout else "",
            "stderr": result.stderr[:2000] if result.stderr else "",
            "elapsed_seconds": elapsed,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "command": cmd,
            "returncode": -1,
            "stdout": "",
            "stderr": "Command timed out",
            "elapsed_seconds": timeout,
            "success": False,
        }
    except Exception as e:
        return {
            "command": cmd,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "elapsed_seconds": 0,
            "success": False,
        }


def execute_plan(plan: dict, interactive: bool = False) -> dict:
    """Execute an investigation plan and collect results."""
    results = {
        "target": plan.get("target_value", "unknown"),
        "target_type": plan.get("target_type", "unknown"),
        "depth": plan.get("depth", "standard"),
        "started_at": datetime.now().isoformat(),
        "phases": [],
        "summary": {
            "total_steps": 0,
            "successful": 0,
            "failed": 0,
            "total_time_seconds": 0,
        },
    }

    phases = plan.get("phases", [])

    for i, phase in enumerate(phases, 1):
        print(f"\n{'='*60}")
        print(f"PHASE {i}/{len(phases)}: {phase.get('name', 'Unknown')}")
        print(f"Estimated: {phase.get('estimated_time', 'unknown')}")
        print(f"{'='*60}")

        phase_result = {
            "name": phase.get("name", "Unknown"),
            "steps": [],
            "start_time": datetime.now().isoformat(),
        }

        for j, step in enumerate(phase.get("steps", []), 1):
            tool = step.get("tool", "unknown")
            command = step.get("command", "echo 'No command'")
            purpose = step.get("purpose", "")
            condition = step.get("condition", "")

            # Check if step should be skipped
            if condition and "if" in condition.lower():
                # Simple condition check - skip if not met
                print(f"  [{j}] {tool}: {purpose} [SKIPPED - condition not met]")
                continue

            print(f"  [{j}] {tool}: {purpose}")
            print(f"      Command: {command[:80]}...")

            if interactive:
                response = input("      Execute? [y/N]: ").strip().lower()
                if response != "y":
                    print(f"      [SKIPPED by user]")
                    continue

            result = run_command(command, timeout=30)
            result["tool"] = tool
            result["purpose"] = purpose

            status = "OK" if result["success"] else "FAIL"
            print(f"      Result: {status} ({result['elapsed_seconds']}s)")

            if result["stderr"] and not result["success"]:
                print(f"      Error: {result['stderr'][:100]}")

            phase_result["steps"].append(result)
            results["summary"]["total_steps"] += 1
            if result["success"]:
                results["summary"]["successful"] += 1
            else:
                results["summary"]["failed"] += 1
            results["summary"]["total_time_seconds"] += result["elapsed_seconds"]

        phase_result["end_time"] = datetime.now().isoformat()
        results["phases"].append(phase_result)

    results["ended_at"] = datetime.now().isoformat()
    return results


def generate_findings(results: dict, extra_data: Optional[dict] = None) -> dict:
    """Generate findings.json from results."""
    findings = {
        "summary": f"Investigation of {results['target']} ({results['target_type']}) completed.",
        "target": results["target"],
        "target_type": results["target_type"],
        "depth": results["depth"],
        "investigation_date": results["started_at"],
        "confidence": "Medium",
        "findings": [],
        "risks": [],
        "recommendations": [],
        "tools_used": [],
        "sources_count": 0,
        "tools_count": 0,
    }

    # Process results into findings
    for phase in results["phases"]:
        for step in phase.get("steps", []):
            if step.get("success") and step.get("stdout"):
                finding = {
                    "title": f"{step.get('tool', 'Unknown')} - {step.get('purpose', '')}",
                    "description": step["stdout"][:500],
                    "source": step.get("tool", "unknown"),
                    "risk": "low",
                    "details": [],
                }
                findings["findings"].append(finding)
                findings["sources_count"] += 1

            findings["tools_used"].append({
                "name": step.get("tool", "unknown"),
                "purpose": step.get("purpose", ""),
                "source": "free" if step.get("success") else "failed",
            })
            findings["tools_count"] += 1

    # Merge extra data if provided
    if extra_data:
        for item in extra_data.get("findings", []):
            findings["findings"].append(item)
        if "summary" in extra_data:
            findings["summary"] = extra_data["summary"]

    # Add recommendations based on findings
    findings["recommendations"] = [
        "Verify all findings through additional sources",
        "Cross-reference with social media profiles",
        "Consider using paid APIs for deeper investigation",
    ]

    return findings


def save_results(results: dict, findings: dict, output_dir: str = ".") -> dict:
    """Save results and findings to files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save raw results
    results_file = output_path / "investigation_results.json"
    results_file.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    # Save findings
    findings_file = output_path / "findings.json"
    findings_file.write_text(json.dumps(findings, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    return {
        "results_file": str(results_file),
        "findings_file": str(findings_file),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run OSINT investigation pipeline")
    parser.add_argument("--plan", required=True, help="Path to investigation_plan.json")
    parser.add_argument("--output", default="osint_output", help="Output directory")
    parser.add_argument("--interactive", action="store_true", help="Ask before each step")
    parser.add_argument("--extra-data", help="Path to extra findings JSON to merge")

    args = parser.parse_args()

    # Load plan
    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"Error: Plan file not found: {plan_path}")
        sys.exit(1)

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    print(f"\n  OSINT Investigation Pipeline")
    print(f"{'='*50}")
    print(f"  Target:  {plan.get('target_value', 'unknown')}")
    print(f"  Type:    {plan.get('target_type', 'unknown')}")
    print(f"  Depth:   {plan.get('depth', 'standard')}")
    print(f"  Phases:  {len(plan.get('phases', []))}")

    # Execute
    results = execute_plan(plan, args.interactive)

    # Load extra data if provided
    extra_data = None
    if args.extra_data:
        extra_path = Path(args.extra_data)
        if extra_path.exists():
            extra_data = json.loads(extra_path.read_text(encoding="utf-8"))

    # Generate findings
    findings = generate_findings(results, extra_data)

    # Save
    files = save_results(results, findings, args.output)

    # Summary
    print(f"\n{'='*50}")
    print(f"  Investigation Complete")
    print(f"{'='*50}")
    print(f"  Total steps:    {results['summary']['total_steps']}")
    print(f"  Successful:     {results['summary']['successful']}")
    print(f"  Failed:         {results['summary']['failed']}")
    print(f"  Total time:     {results['summary']['total_time_seconds']:.1f}s")
    print(f"\n  Output files:")
    print(f"    Results:  {files['results_file']}")
    print(f"    Findings: {files['findings_file']}")


if __name__ == "__main__":
    main()
