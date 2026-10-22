#!/usr/bin/env python3
"""Check which OSINT tools are installed and available."""

from __future__ import annotations

import shutil
import subprocess
import sys


TOOLS = [
    {"name": "whois", "check": "whois --version", "install": "apt install whois / brew install whois", "category": "domain"},
    {"name": "dig", "check": "dig -v", "install": "apt install dnsutils / brew install bind", "category": "domain"},
    {"name": "nmap", "check": "nmap --version", "install": "apt install nmap / brew install nmap", "category": "domain"},
    {"name": "curl", "check": "curl --version", "install": "apt install curl / brew install curl", "category": "http"},
    {"name": "sherlock", "check": "sherlock --version", "install": "pip install sherlock-project", "category": "username"},
    {"name": "maigret", "check": "maigret --version", "install": "pip install maigret", "category": "username"},
    {"name": "holehe", "check": "holehe --version", "install": "pip install holehe", "category": "email"},
    {"name": "theHarvester", "check": "theHarvester -h", "install": "pip install theHarvester", "category": "email"},
    {"name": "subfinder", "check": "subfinder -version", "install": "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest", "category": "domain"},
    {"name": "whatweb", "check": "whatweb --version", "install": "apt install whatweb / gem install whatweb", "category": "domain"},
    {"name": "python3", "check": "python3 --version", "install": "apt install python3", "category": "core"},
]


def check_tools():
    """Check which tools are available."""
    results = []
    for tool in TOOLS:
        name = tool["name"]
        available = shutil.which(name) is not None
        if available and tool["check"]:
            try:
                result = subprocess.run(
                    tool["check"].split()[:3],
                    capture_output=True, text=True, timeout=5
                )
                version = result.stdout.strip()[:100] if result.returncode == 0 else "installed"
            except Exception:
                version = "installed"
        else:
            version = "not found"

        results.append({
            "name": name,
            "available": available,
            "version": version,
            "install": tool["install"],
            "category": tool["category"],
        })

    return results


def main():
    print("  OSINT Tools Check\n")
    results = check_tools()

    available = [r for r in results if r["available"]]
    missing = [r for r in results if not r["available"]]

    print(f"  Available: {len(available)}/{len(results)}")
    for r in available:
        print(f"    [OK] {r['name']:<15} {r['version'][:40]}")

    if missing:
        print(f"\n  Missing: {len(missing)}")
        for r in missing:
            print(f"    [--] {r['name']:<15} Install: {r['install']}")

    # Category summary
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"available": 0, "total": 0}
        categories[cat]["total"] += 1
        if r["available"]:
            categories[cat]["available"] += 1

    print(f"\n  By Category:")
    for cat, counts in sorted(categories.items()):
        status = "OK" if counts["available"] == counts["total"] else "PARTIAL"
        print(f"    {cat:<12} {counts['available']}/{counts['total']} [{status}]")


if __name__ == "__main__":
    main()
