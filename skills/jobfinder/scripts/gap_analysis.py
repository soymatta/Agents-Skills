#!/usr/bin/env python3
"""Analyze skill gaps between profile and job requirements."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def analyze_gaps(profile: dict, scored_jobs: list[dict]) -> dict:
    """Analyze skill gaps across all scored jobs."""
    user_skills = set(s.lower() for s in profile.get("skills", []))

    skill_freq = {}
    for job in scored_jobs:
        for skill in job.get("missing_skills", []):
            skill_freq[skill] = skill_freq.get(skill, 0) + 1

    total_jobs = len(scored_jobs) if scored_jobs else 1
    gaps = []
    for skill, count in sorted(skill_freq.items(), key=lambda x: -x[1]):
        pct = count / total_jobs * 100
        gaps.append({
            "skill": skill,
            "frequency": count,
            "percentage": round(pct, 1),
            "priority": "high" if pct > 30 else "medium" if pct > 15 else "low",
            "has_skill": skill in user_skills,
        })

    return {
        "total_jobs_analyzed": len(scored_jobs),
        "unique_gaps": len(gaps),
        "gaps": gaps,
        "top_3": [g["skill"] for g in gaps[:3]],
    }


def suggest_learning(skill: str) -> str:
    """Suggest learning resources for a skill."""
    suggestions = {
        "kubernetes": "Kubernetes official docs (kubernetes.io), killer.sh labs",
        "docker": "Docker getting started guide, Play with Docker labs",
        "aws": "AWS Free Tier + AWS Skill Builder",
        "terraform": "HashiCorp Learn tutorials",
        "react": "React official tutorial (react.dev)",
        "vue": "Vue.js official guide (vuejs.org)",
        "angular": "Angular tutorial (angular.dev)",
        "python": "Python.org tutorial, Real Python",
        "machine learning": "Andrew Ng's ML course (Coursera)",
        "graphql": "GraphQL official tutorial (graphql.org)",
        "ci/cd": "GitHub Actions documentation",
        "agile": "Scrum.org learning path",
    }
    return suggestions.get(skill, f"Search for '{skill} tutorial' on YouTube or freeCodeCamp")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze skill gaps")
    parser.add_argument("--profile", "-p", required=True, help="Path to profile.json")
    parser.add_argument("--scored", "-s", required=True, help="Path to scored.json")
    parser.add_argument("--output", "-o", default="gap_analysis.json", help="Output path")
    args = parser.parse_args()

    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    scored = json.loads(Path(args.scored).read_text(encoding="utf-8"))

    analysis = analyze_gaps(profile, scored)

    # Add learning suggestions
    for gap in analysis["gaps"]:
        gap["learning_suggestion"] = suggest_learning(gap["skill"])

    output_path = Path(args.output)
    output_path.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  Gap Analysis ({analysis['total_jobs_analyzed']} jobs analyzed)")
    print(f"  Unique skill gaps: {analysis['unique_gaps']}")
    if analysis["top_3"]:
        print(f"  Top 3 gaps: {', '.join(analysis['top_3'])}")
    for gap in analysis["gaps"][:5]:
        marker = "HAS" if gap["has_skill"] else "MISSING"
        print(f"  [{gap['priority'].upper()}] {gap['skill']} ({gap['percentage']:.0f}%) [{marker}]")
        print(f"       -> {gap['learning_suggestion']}")
    print(f"\n  Saved to: {output_path}")


if __name__ == "__main__":
    main()
