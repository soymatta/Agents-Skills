#!/usr/bin/env python3
"""Score match between user profile and job listings."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def normalize_skill(skill: str) -> str:
    """Normalize a skill name for comparison."""
    s = skill.lower().strip()
    s = re.sub(r"[\s\-_]+", " ", s)
    aliases = {
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
        "k8s": "kubernetes",
        "tf": "terraform",
        "gcp": "google cloud",
        "react.js": "react",
        "reactjs": "react",
        "vue.js": "vue",
        "vuejs": "vue",
        "next.js": "nextjs",
        "node.js": "node",
        "nodejs": "node",
        "c plus plus": "c++",
        "c sharp": "c#",
        "postgres": "postgresql",
        "mongo": "mongodb",
        "ci cd": "ci/cd",
        "machine-learning": "machine learning",
        "deep-learning": "deep learning",
    }
    return aliases.get(s, s)


def extract_skills_from_description(description: str) -> list[str]:
    """Extract mentioned skills from a job description."""
    description_lower = description.lower()
    skill_keywords = [
        "python", "javascript", "typescript", "java", "c++", "c#", "ruby",
        "go", "golang", "rust", "php", "swift", "kotlin", "scala", "r",
        "html", "css", "scss", "sass",
        "react", "vue", "angular", "svelte", "nextjs", "nuxt",
        "node", "express", "fastapi", "django", "flask", "spring", "rails",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
        "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
        "git", "github", "gitlab",
        "linux", "bash",
        "machine learning", "deep learning", "tensorflow", "pytorch", "scikit",
        "pandas", "numpy", "data science",
        "rest api", "graphql", "grpc",
        "ci/cd", "jenkins", "github actions",
        "agile", "scrum", "jira",
        "figma",
        "sql", "nosql", "etl", "airflow", "spark",
        "blockchain", "solidity", "web3",
        "cybersecurity", "penetration testing",
        "communication", "leadership", "teamwork", "problem solving",
        "project management", "time management",
        "spanish", "english", "portuguese", "french", "german",
    ]

    found = []
    for skill in skill_keywords:
        if re.search(rf"\b{re.escape(skill)}\b", description_lower):
            found.append(skill)
    return found


def score_job_match(profile: dict, job: dict) -> dict:
    """Calculate match score between profile and job."""
    profile_skills = set(normalize_skill(s) for s in profile.get("skills", []))
    job_skills_raw = extract_skills_from_description(job.get("description", ""))
    job_skills = set(normalize_skill(s) for s in job_skills_raw)

    # Skills match (35%)
    if job_skills:
        matched = profile_skills & job_skills
        missing = job_skills - profile_skills
        skills_score = len(matched) / len(job_skills) * 100
    else:
        matched = set()
        missing = set()
        skills_score = 50  # No skills listed, assume partial match

    # Experience match (20%)
    user_years = profile.get("experience", {}).get("years")
    desc_text = job.get("description", "").lower()
    exp_match = re.search(r"(\d+)\+?\s*years?", desc_text)
    job_years = int(exp_match.group(1)) if exp_match else None

    if user_years and job_years:
        if user_years >= job_years:
            exp_score = 100
        elif user_years >= job_years * 0.7:
            exp_score = 70
        else:
            exp_score = max(0, 100 - (job_years - user_years) * 20)
    else:
        exp_score = 50

    # Salary match (15%)
    user_salary = profile.get("salary_expected")
    if isinstance(user_salary, str):
        # Parse salary range string like "2000000-4000000 COP"
        nums = re.findall(r"\d+", user_salary)
        if nums:
            user_salary = int(nums[0])  # Use lower bound
        else:
            user_salary = None
    job_min = job.get("salary_min")
    job_max = job.get("salary_max")

    if user_salary and job_min:
        if job_max and job_min <= user_salary <= job_max:
            salary_score = 100
        elif user_salary <= job_min:
            salary_score = 80  # Under budget, good
        else:
            over_pct = (user_salary - job_min) / job_min * 100 if job_min else 0
            salary_score = max(0, 100 - over_pct)
    else:
        salary_score = 50

    # Location match (15%)
    user_remote = profile.get("remote_preference", "no-preference")
    job_remote = job.get("is_remote", False)
    job_location = job.get("location", "").lower()

    if user_remote == "remote-only":
        location_score = 100 if job_remote else 10
    elif user_remote == "no-preference":
        location_score = 100
    elif user_remote in ("hybrid", "on-site"):
        location_score = 90 if not job_remote else 60
    else:
        location_score = 50

    # Education match (10%)
    user_edu = profile.get("education", "Not specified")
    if isinstance(user_edu, list):
        # Extract highest degree from list of education entries
        edu_degrees = [e.get("degree", "") for e in user_edu if isinstance(e, dict)]
        user_edu = " ".join(edu_degrees) if edu_degrees else "Not specified"
    edu_levels = {
        "PhD/Doctorate": 5, "Master's Degree": 4, "Bachelor's Degree": 3,
        "Bootcamp/Certification": 2, "Technical Degree": 2, "Not specified": 1,
    }
    user_edu_level = edu_levels.get(user_edu, 1)

    edu_keywords = ["phd", "master", "bachelor", "degree", "university", "bootcamp"]
    edu_mentioned = any(k in desc_text for k in edu_keywords)
    edu_score = 100 if (not edu_mentioned or user_edu_level >= 3) else 60

    # Industry match (5%)
    user_industries = set(
        i.lower().strip() for i in profile.get("industries", []) if isinstance(i, str)
    )
    industry_keywords = {
        "fintech", "healthcare", "education", "ecommerce", "e-commerce",
        "gaming", "saas", "ai", "machine learning", "blockchain",
        "cybersecurity", "logistics", "manufacturing", "real estate",
        "media", "telecommunications", "energy", "agriculture",
        "automotive", "aerospace", "retail", "travel", "insurance",
        "banking", "consulting", "nonprofit", "government",
    }
    # Extract industry hints from job title + description
    job_text = (job.get("title", "") + " " + job.get("description", "")).lower()
    job_industries = set()
    for kw in industry_keywords:
        if kw in job_text:
            job_industries.add(kw)

    if user_industries and job_industries:
        overlap = user_industries & job_industries
        industry_score = min(100, 50 + len(overlap) * 25) if overlap else 40
    else:
        industry_score = 60  # Unknown, assume moderate

    # Weighted total
    total = (
        skills_score * 0.35 +
        exp_score * 0.20 +
        salary_score * 0.15 +
        location_score * 0.15 +
        edu_score * 0.10 +
        industry_score * 0.05
    )

    return {
        "total_score": round(total, 1),
        "skills_score": round(skills_score, 1),
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "nice_to_have": sorted(profile_skills - job_skills),
        "experience_score": round(exp_score, 1),
        "salary_score": round(salary_score, 1),
        "location_score": round(location_score, 1),
        "education_score": round(edu_score, 1),
        "industry_score": round(industry_score, 1),
        "analysis": _generate_analysis(total, matched, missing, exp_score, salary_score),
    }


def _generate_analysis(total, matched, missing, exp_score, salary_score):
    """Generate a human-readable analysis."""
    if total >= 85:
        strength = "excellent"
    elif total >= 70:
        strength = "strong"
    elif total >= 50:
        strength = "moderate"
    else:
        strength = "low"

    parts = [f"This is a {strength} match ({total:.0f}%)."]

    if matched:
        parts.append(f"Your skills in {', '.join(sorted(matched)[:3])} align well with this role.")
    if missing:
        top_missing = sorted(missing)[:3]
        parts.append(f"Key gaps: {', '.join(top_missing)} — consider developing these.")
    if exp_score < 50:
        parts.append("You may need more experience for this position.")
    if salary_score < 50:
        parts.append("Salary expectations may be higher than the listed range.")

    return " ".join(parts)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Score job matches against a user profile")
    parser.add_argument("--profile", "-p", required=True, help="Path to profile.json")
    parser.add_argument("--jobs", "-j", required=True, help="Path to results.json")
    parser.add_argument("--output", "-o", default="scored.json", help="Output path (default: scored.json)")
    args = parser.parse_args()

    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    jobs = json.loads(Path(args.jobs).read_text(encoding="utf-8"))

    scored = []
    for job in jobs:
        result = score_job_match(profile, job)
        scored.append({**job, **result})

    scored.sort(key=lambda x: x["total_score"], reverse=True)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(scored, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  Scored {len(scored)} jobs. Top 5:")
    for i, job in enumerate(scored[:5], 1):
        print(f"  {i}. [{job['total_score']:.0f}%] {job['title']} @ {job['company']}")
        if job['missing_skills']:
            print(f"     Missing: {', '.join(job['missing_skills'][:3])}")

    print(f"\n  Saved to: {output_path}")


if __name__ == "__main__":
    main()
