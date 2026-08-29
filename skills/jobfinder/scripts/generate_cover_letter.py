#!/usr/bin/env python3
"""Generate a tailored cover letter in Markdown format."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def generate_cover_letter(profile: dict, job: dict, matched_skills: list[str]) -> str:
    """Generate a cover letter based on profile and job posting."""
    name = profile.get("name", "Candidate")
    role = job.get("title", "the position")
    company = job.get("company", "your company")
    desc = job.get("description", "")

    # Extract key requirements from description
    requirements = []
    for skill in matched_skills[:5]:
        requirements.append(skill)

    # Build cover letter
    lines = [
        f"# Cover Letter: {role} at {company}",
        "",
        f"Dear Hiring Team,",
        "",
        f"I am writing to express my interest in the {role} position at {company}. "
        f"With my background in {', '.join(requirements[:3]) if requirements else 'software development'}, "
        f"I am confident I can contribute meaningfully to your team.",
        "",
        "## Why I Am a Strong Fit",
        "",
    ]

    if matched_skills:
        lines.append("My relevant skills include:")
        for skill in matched_skills[:5]:
            lines.append(f"- **{skill.title()}**")
        lines.append("")

    # Add experience section
    roles = profile.get("experience", {}).get("roles", [])
    if roles:
        lines.append("## Relevant Experience")
        lines.append("")
        for role_entry in roles[:2]:
            if isinstance(role_entry, dict):
                lines.append(f"**{role_entry.get('role', 'Role')}** at {role_entry.get('company', 'Company')}")
                bullets = role_entry.get("bullets", [])
                for bullet in bullets[:3]:
                    lines.append(f"- {bullet}")
                lines.append("")

    # Closing
    lines.extend([
        "## Closing",
        "",
        f"I am excited about the opportunity to contribute to {company}'s goals. "
        f"I look forward to discussing how my experience aligns with your needs.",
        "",
        f"Best regards,",
        f"{name}",
    ])

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate cover letter")
    parser.add_argument("--profile", "-p", required=True, help="Path to profile.json")
    parser.add_argument("--job", "-j", required=True, help="Path to single job JSON")
    parser.add_argument("--skills", "-s", default="", help="Comma-separated matched skills")
    parser.add_argument("--output", "-o", default="cover_letter.md", help="Output path")
    args = parser.parse_args()

    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    job = json.loads(Path(args.job).read_text(encoding="utf-8"))
    skills = [s.strip() for s in args.skills.split(",") if s.strip()]

    letter = generate_cover_letter(profile, job, skills)
    Path(args.output).write_text(letter, encoding="utf-8")
    print(f"  Cover letter saved to: {args.output}")


if __name__ == "__main__":
    main()
