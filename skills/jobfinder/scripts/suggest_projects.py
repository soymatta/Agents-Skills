#!/usr/bin/env python3
"""Suggest 1 GitHub project per vacancy to demonstrate required skills.

The agent can also generate websearch queries for dynamic project discovery:
  python suggest_projects.py --generate-queries --missing-skills "docker,kubernetes"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


# Static project suggestions (fallback when websearch is unavailable)
PROJECT_SUGGESTIONS = {
    "docker": {"name": "docker-curriculum", "url": "https://github.com/prakhar1989/docker-curriculum", "desc": "Practical Docker tutorial", "stars": "4k+"},
    "kubernetes": {"name": "kubernetes-the-hard-way", "url": "https://github.com/kelseyhightower/kubernetes-the-hard-way", "desc": "Learn K8s from scratch", "stars": "14k+"},
    "aws": {"name": "aws-sam-cli", "url": "https://github.com/aws/aws-sam-cli", "desc": "CLI for serverless on AWS", "stars": "9k+"},
    "terraform": {"name": "terraform-best-practices", "url": "https://github.com/antonbabenko/terraform-best-practices", "desc": "Terraform best practices", "stars": "1k+"},
    "machine learning": {"name": "fastai", "url": "https://github.com/fastai/fastai", "desc": "Deep learning made easy", "stars": "20k+"},
    "react": {"name": "next.js", "url": "https://github.com/vercel/next.js", "desc": "React framework for production", "stars": "120k+"},
    "python": {"name": "fastapi", "url": "https://github.com/tiangolo/fastapi", "desc": "Modern Python web framework", "stars": "75k+"},
    "ci/cd": {"name": "awesome-actions", "url": "https://github.com/sdras/awesome-actions", "desc": "GitHub Actions for CI/CD", "stars": "22k+"},
    "postgresql": {"name": "postgres", "url": "https://github.com/docker-library/postgres", "desc": "Official PostgreSQL in Docker", "stars": "10k+"},
    "redis": {"name": "redis", "url": "https://github.com/redis/redis", "desc": "In-memory data store", "stars": "65k+"},
    "graphql": {"name": "strawberry", "url": "https://github.com/strawberry-graphql/strawberry", "desc": "GraphQL for Python", "stars": "4k+"},
    "typescript": {"name": "type-challenges", "url": "https://github.com/type-challenges/type-challenges", "desc": "TypeScript type challenges", "stars": "10k+"},
    "django": {"name": "djangorestframework", "url": "https://github.com/encode/django-rest-framework", "desc": "REST APIs with Django", "stars": "28k+"},
    "flask": {"name": "flask-restful", "url": "https://github.com/flask-restful/flask-restful", "desc": "Simple REST APIs with Flask", "stars": "7k+"},
    "fastapi": {"name": "fastapi-template", "url": "https://github.com/zhanymkanov/fastapi-template", "desc": "Production-ready FastAPI template", "stars": "2k+"},
    "java": {"name": "spring-boot", "url": "https://github.com/spring-projects/spring-boot", "desc": "Java framework for microservices", "stars": "73k+"},
    "node": {"name": "nodebestpractices", "url": "https://github.com/goldbergyoni/nodebestpractices", "desc": "Node.js best practices", "stars": "98k+"},
    "vue": {"name": "vite", "url": "https://github.com/vitejs/vite", "desc": "Next-gen frontend tooling", "stars": "65k+"},
    "angular": {"name": "angular", "url": "https://github.com/angular/angular", "desc": "Angular framework", "stars": "95k+"},
    "rust": {"name": "rustlings", "url": "https://github.com/rust-lang/rustlings", "desc": "Small Rust exercises", "stars": "45k+"},
    "go": {"name": "awesome-go", "url": "https://github.com/avelino/awesome-go", "desc": "Curated Go resources", "stars": "120k+"},
    "cybersecurity": {"name": "owasp-masvs", "url": "https://github.com/OWASP/owasp-masvs", "desc": "Mobile security standards", "stars": "3k+"},
    "flutter": {"name": "flutter-starter", "url": "https://github.com/nicong622/flutter-starter", "desc": "Flutter starter template", "stars": "1k+"},
    "git": {"name": "git-exercises", "url": "https://github.com/pluralsight/git-exercises", "desc": "Practical Git exercises", "stars": "500+"},
    "linux": {"name": "linux-command", "url": "https://github.com/jaywcjlove/linux-command", "desc": "Linux command reference", "stars": "30k+"},
    "sql": {"name": "sqlzoo", "url": "https://github.com/SQLZoo/sqlzoo", "desc": "Interactive SQL tutorials", "stars": "500+"},
    "spark": {"name": "spark", "url": "https://github.com/apache/spark", "desc": "Apache Spark", "stars": "40k+"},
    "airflow": {"name": "airflow", "url": "https://github.com/apache/airflow", "desc": "Apache Airflow", "stars": "35k+"},
    "firebase": {"name": "awesome-firebase", "url": "https://github.com/jthegedberg/awesome-firebase", "desc": "Firebase resources", "stars": "1k+"},
    "supabase": {"name": "supabase", "url": "https://github.com/supabase/supabase", "desc": "Open-source Firebase alternative", "stars": "70k+"},
}


def generate_websearch_queries(missing_skills: list[str], job_title: str = "") -> list[dict]:
    """Generate websearch queries for dynamic project discovery.

    Returns a list of dicts with 'skill', 'query', and 'purpose' keys.
    The agent should run these via the websearch tool and feed results back.
    """
    queries = []
    for skill in missing_skills:
        skill_lower = skill.lower().strip()
        queries.append({
            "skill": skill,
            "query": f'"{skill}" github project tutorial beginner intermediate site:github.com',
            "purpose": f"Find a GitHub project to learn {skill}",
        })
        if job_title:
            queries.append({
                "skill": skill,
                "query": f'"{skill}" portfolio project ideas for {job_title}',
                "purpose": f"Find portfolio-worthy {skill} projects for {job_title} role",
            })
    return queries


def parse_websearch_results(websearch_json: str | list[dict]) -> dict[str, list[dict]]:
    """Parse websearch results and group by skill.

    Returns dict of skill -> list of project dicts.
    """
    if isinstance(websearch_json, str):
        results = json.loads(websearch_json)
    else:
        results = websearch_json

    by_skill: dict[str, list[dict]] = {}
    for r in results:
        skill = r.get("skill", "general")
        if skill not in by_skill:
            by_skill[skill] = []
        by_skill[skill].append({
            "name": r.get("title", ""),
            "url": r.get("url", ""),
            "desc": r.get("snippet", r.get("description", "")),
            "stars": "",
        })
    return by_skill


def suggest_project_for_vacancy(
    missing_skills: list[str],
    job_title: str,
    tech_stack: list[str] | None = None,
    websearch_projects: dict[str, list[dict]] | None = None,
) -> dict | None:
    """Suggest the BEST single project for a specific vacancy."""
    best_match = None
    best_score = 0

    for skill in missing_skills:
        skill_lower = skill.lower().strip()

        # Try websearch results first (dynamic, more relevant)
        if websearch_projects and skill_lower in websearch_projects:
            projects = websearch_projects[skill_lower]
            if projects:
                proj = projects[0]
                score = 3  # Bonus for dynamic results
                if tech_stack:
                    for tech in tech_stack:
                        if tech.lower() in skill_lower or skill_lower in tech.lower():
                            score += 2
                if not best_match or score > best_score:
                    best_match = {
                        "job_title": job_title,
                        "skill": skill,
                        "name": proj["name"],
                        "url": proj["url"],
                        "description": proj["desc"],
                        "stars": proj.get("stars", ""),
                        "reason": f"Demonstrates {skill} skills for {job_title}",
                    }
                    best_score = score
                continue

        # Fallback to static suggestions
        if skill_lower in PROJECT_SUGGESTIONS:
            proj = PROJECT_SUGGESTIONS[skill_lower]
            score = 1
            if tech_stack:
                for tech in tech_stack:
                    if tech.lower() in skill_lower or skill_lower in tech.lower():
                        score += 2
            if not best_match or score > best_score:
                best_match = {
                    "job_title": job_title,
                    "skill": skill,
                    "name": proj["name"],
                    "url": proj["url"],
                    "description": proj["desc"],
                    "stars": proj["stars"],
                    "reason": f"Demonstrates {skill} skills for {job_title}",
                }
                best_score = score

    return best_match


def suggest_projects(
    missing_skills: list[str],
    tech_stack: list[str] | None = None,
    job_title: str = "",
    websearch_projects: dict[str, list[dict]] | None = None,
) -> list[dict]:
    """Suggest 1 project per vacancy based on missing skills."""
    if job_title:
        project = suggest_project_for_vacancy(missing_skills, job_title, tech_stack, websearch_projects)
        return [project] if project else []

    # Fallback: suggest top skill projects
    suggestions = []
    seen = set()
    for skill in missing_skills[:3]:
        skill_lower = skill.lower().strip()
        if skill_lower in seen:
            continue

        proj = None
        # Try websearch first
        if websearch_projects and skill_lower in websearch_projects and websearch_projects[skill_lower]:
            proj = websearch_projects[skill_lower][0]
        elif skill_lower in PROJECT_SUGGESTIONS:
            proj = PROJECT_SUGGESTIONS[skill_lower]

        if proj:
            suggestions.append({
                "job_title": job_title or "General",
                "skill": skill,
                "name": proj["name"],
                "url": proj["url"],
                "description": proj["desc"],
                "stars": proj.get("stars", ""),
                "reason": f"Learn and practice {skill}",
            })
            seen.add(skill_lower)

    return suggestions


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Suggest GitHub projects for job skill gaps")
    parser.add_argument("--missing-skills", "-m", required=True,
                        help="Comma-separated list of missing skills")
    parser.add_argument("--tech-stack", "-t", default="",
                        help="Comma-separated tech stack (optional)")
    parser.add_argument("--job-title", "-j", default="",
                        help="Target job title")
    parser.add_argument("--output", "-o", default="projects.json",
                        help="Output file path")
    parser.add_argument("--generate-queries", action="store_true",
                        help="Generate websearch queries instead of static suggestions")
    parser.add_argument("--websearch-json", default=None,
                        help="Path to JSON file with websearch results")

    args = parser.parse_args()

    missing_skills = [s.strip() for s in args.missing_skills.split(",") if s.strip()]
    tech_stack = [s.strip() for s in args.tech_stack.split(",") if s.strip()] if args.tech_stack else []

    if not missing_skills:
        print("  Error: --missing-skills is required")
        sys.exit(1)

    # Generate websearch queries mode
    if args.generate_queries:
        queries = generate_websearch_queries(missing_skills, args.job_title)
        print(json.dumps(queries, indent=2, ensure_ascii=False))
        return

    # Load websearch results if provided
    websearch_projects = None
    if args.websearch_json:
        ws_path = Path(args.websearch_json)
        if ws_path.exists():
            ws_data = json.loads(ws_path.read_text(encoding="utf-8"))
            websearch_projects = parse_websearch_results(ws_data)

    suggestions = suggest_projects(missing_skills, tech_stack, args.job_title, websearch_projects)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(suggestions, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  Suggested projects: {len(suggestions)}")
    for i, s in enumerate(suggestions, 1):
        stars = f" ({s['stars']})" if s.get("stars") else ""
        print(f"  {i}. [{s['skill']}] {s['name']} — {s['description']}{stars}")
        print(f"     {s['url']}")

    print(f"\n  Saved to: {output_path}")


if __name__ == "__main__":
    main()
