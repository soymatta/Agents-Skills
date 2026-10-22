#!/usr/bin/env python3
"""Generate OSINT investigation reports."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OSINT Report: {target}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0e17; color: #c9d1d9; line-height: 1.6; padding: 2rem; }}
.container {{ max-width: 900px; margin: 0 auto; }}
h1 {{ color: #58a6ff; font-size: 1.8rem; margin-bottom: 0.3rem; }}
h2 {{ color: #79c0ff; font-size: 1.3rem; margin: 2rem 0 1rem; border-bottom: 1px solid #21262d; padding-bottom: 0.5rem; }}
h3 {{ color: #a5d6ff; font-size: 1rem; margin: 1rem 0 0.5rem; }}
.meta {{ color: #8b949e; font-size: 0.85rem; margin-bottom: 2rem; }}
.summary {{ background: #161b22; border-radius: 8px; padding: 1.2rem; border-left: 4px solid #58a6ff; margin: 1rem 0; }}
.finding {{ background: #161b22; border-radius: 8px; padding: 1.2rem; margin: 1rem 0; border-left: 3px solid #238636; }}
.finding.warning {{ border-left-color: #d29922; }}
.finding.danger {{ border-left-color: #f85149; }}
table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
th {{ background: #161b22; padding: 0.6rem; text-align: left; color: #58a6ff; border-bottom: 2px solid #30363d; }}
td {{ padding: 0.6rem; border-bottom: 1px solid #21262d; }}
.tag {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 12px; font-size: 0.75rem; margin: 0.15rem; }}
.tag-high {{ background: #f85149; color: #fff; }}
.tag-medium {{ background: #d29922; color: #000; }}
.tag-low {{ background: #238636; color: #fff; }}
.tag-info {{ background: #1f6feb; color: #fff; }}
.tool {{ background: #1c2128; padding: 0.5rem; border-radius: 4px; margin: 0.3rem 0; font-family: monospace; font-size: 0.85rem; }}
pre {{ background: #161b22; padding: 1rem; border-radius: 8px; overflow-x: auto; font-size: 0.85rem; }}
a {{ color: #58a6ff; }}
.risk-meter {{ height: 20px; background: #21262d; border-radius: 10px; overflow: hidden; margin: 0.5rem 0; }}
.risk-fill {{ height: 100%; border-radius: 10px; transition: width 0.3s; }}
.risk-high {{ background: #f85149; }}
.risk-medium {{ background: #d29922; }}
.risk-low {{ background: #238636; }}
</style>
</head>
<body>
<div class="container">
<h1>OSINT Report: {target}</h1>
<div class="meta">Generated: {date} | Depth: {depth} | Type: {target_type}</div>

<div class="summary">
<h3 style="margin-top:0">Executive Summary</h3>
<p>{summary}</p>
</div>

<h2>Target Profile</h2>
<table>
<tr><th>Field</th><th>Value</th></tr>
<tr><td>Target</td><td>{target}</td></tr>
<tr><td>Type</td><td>{target_type}</td></tr>
<tr><td>Investigation Date</td><td>{date}</td></tr>
<tr><td>Confidence Level</td><td><span class="tag tag-info">{confidence}</span></td></tr>
<tr><td>Sources Checked</td><td>{sources_count}</td></tr>
</table>

<h2>Findings</h2>
{findings_html}

<h2>Risk Assessment</h2>
{risk_html}

<h2>Tools Used</h2>
<table>
<tr><th>Tool</th><th>Purpose</th><th>Source</th></tr>
{tools_html}
</table>

<h2>Recommendations</h2>
{recommendations_html}

<h2>Methodology</h2>
<table>
<tr><td>Investigation Depth</td><td>{depth}</td></tr>
<tr><td>Tools Used</td><td>{tools_count}</td></tr>
<tr><td>Sources Checked</td><td>{sources_count}</td></tr>
</table>

<div style="margin-top:2rem;padding:1rem;background:#161b22;border-radius:8px;font-size:0.85rem;color:#8b949e">
<strong>Disclaimer:</strong> This report was generated using publicly available information (OSINT).
Findings should be verified through additional sources before making decisions.
This investigation was conducted legally and ethically using only public data.
</div>
</div>
</body>
</html>"""


def generate_markdown(target: str, target_type: str, findings: dict, depth: str) -> str:
    """Generate a Markdown OSINT report."""
    lines = []
    lines.append(f"# OSINT Report: {target}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Depth: {depth} | Type: {target_type}\n")

    lines.append("## Executive Summary")
    lines.append(findings.get("summary", "Investigation completed. See findings below.\n"))

    lines.append("## Target Profile")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| Target | {target} |")
    lines.append(f"| Type | {target_type} |")
    lines.append(f"| Date | {datetime.now().strftime('%Y-%m-%d')} |")
    lines.append(f"| Confidence | {findings.get('confidence', 'Medium')} |")
    lines.append(f"| Sources | {findings.get('sources_count', 0)} |\n")

    lines.append("## Findings")
    for finding in findings.get("findings", []):
        risk_cls = "warning" if finding.get("risk") == "medium" else "danger" if finding.get("risk") == "high" else ""
        lines.append(f"### {finding.get('title', 'Finding')}")
        if finding.get("risk"):
            lines.append(f"**Risk**: {finding['risk'].upper()}")
        lines.append(f"{finding.get('description', '')}\n")
        for detail in finding.get("details", []):
            lines.append(f"- {detail}")
        lines.append("")

    lines.append("## Risk Assessment")
    for risk in findings.get("risks", []):
        lines.append(f"- **{risk.get('factor', 'Unknown')}**: {risk.get('level', 'Unknown')} — {risk.get('evidence', '')}")

    lines.append("\n## Recommendations")
    for i, rec in enumerate(findings.get("recommendations", []), 1):
        lines.append(f"{i}. {rec}")

    lines.append("\n## Tools Used")
    lines.append("| Tool | Purpose | Source |")
    lines.append("|------|---------|--------|")
    for tool in findings.get("tools_used", []):
        lines.append(f"| {tool.get('name', 'N/A')} | {tool.get('purpose', 'N/A')} | {tool.get('source', 'N/A')} |")

    lines.append(f"\n## Methodology")
    lines.append(f"- Depth: {depth}")
    lines.append(f"- Tools: {findings.get('tools_count', 0)}")
    lines.append(f"- Sources: {findings.get('sources_count', 0)}")

    lines.append("\n---")
    lines.append("*This report uses publicly available information (OSINT). Verify findings independently.*")
    return "\n".join(lines)


def generate_html(target: str, target_type: str, findings: dict, depth: str) -> str:
    """Generate an HTML OSINT report."""
    findings_html = ""
    for finding in findings.get("findings", []):
        cls = "warning" if finding.get("risk") == "medium" else "danger" if finding.get("risk") == "high" else ""
        details = "".join(f"<li>{d}</li>" for d in finding.get("details", []))
        findings_html += f"""
<div class="finding {cls}">
<h3>{finding.get('title', 'Finding')}</h3>
{f'<span class="tag tag-{finding.get("risk", "low")}">{finding.get("risk", "").upper()}</span>' if finding.get('risk') else ''}
<p>{finding.get('description', '')}</p>
{f'<ul>{details}</ul>' if details else ''}
</div>"""

    risk_html = ""
    for risk in findings.get("risks", []):
        level = risk.get("level", "low").lower()
        risk_html += f"""
<div style="margin:0.5rem 0">
<strong>{risk.get('factor', 'Unknown')}</strong>: {risk.get('evidence', '')}
<div class="risk-meter"><div class="risk-fill risk-{level}" style="width:{'80' if level == 'high' else '50' if level == 'medium' else '20'}%"></div></div>
</div>"""

    tools_html = ""
    for tool in findings.get("tools_used", []):
        tools_html += f"<tr><td>{tool.get('name', 'N/A')}</td><td>{tool.get('purpose', 'N/A')}</td><td>{tool.get('source', 'N/A')}</td></tr>"

    recommendations_html = "<ul>"
    for rec in findings.get("recommendations", []):
        recommendations_html += f"<li>{rec}</li>"
    recommendations_html += "</ul>"

    return HTML_TEMPLATE.format(
        target=target,
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        depth=depth,
        target_type=target_type,
        summary=findings.get("summary", "Investigation completed."),
        confidence=findings.get("confidence", "Medium"),
        sources_count=findings.get("sources_count", 0),
        findings_html=findings_html,
        risk_html=risk_html,
        tools_html=tools_html,
        recommendations_html=recommendations_html,
        tools_count=findings.get("tools_count", 0),
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate OSINT report")
    parser.add_argument("--target", required=True, help="Target value")
    parser.add_argument("--target-type", required=True, help="Target type")
    parser.add_argument("--findings", default="findings.json", help="Findings file")
    parser.add_argument("--depth", default="standard", help="Investigation depth")
    parser.add_argument("--output", default="osint_report", help="Output base name")
    parser.add_argument("--format", default="both", choices=["markdown", "html", "both"])

    args = parser.parse_args()

    findings_path = Path(args.findings)
    findings = json.loads(findings_path.read_text(encoding="utf-8")) if findings_path.exists() else {
        "summary": "Investigation completed.",
        "findings": [],
        "risks": [],
        "recommendations": [],
        "tools_used": [],
        "confidence": "Medium",
        "sources_count": 0,
        "tools_count": 0,
    }

    if args.format in ("markdown", "both"):
        md = generate_markdown(args.target, args.target_type, findings, args.depth)
        md_path = Path(f"{args.output}.md")
        md_path.write_text(md, encoding="utf-8")
        print(f"  Markdown: {md_path}")

    if args.format in ("html", "both"):
        html = generate_html(args.target, args.target_type, findings, args.depth)
        html_path = Path(f"{args.output}.html")
        html_path.write_text(html, encoding="utf-8")
        print(f"  HTML: {html_path}")


if __name__ == "__main__":
    main()
