#!/usr/bin/env python3
"""Score match between user profile and job listings using 5-Dimension Framework.

Dimensions:
  1. Technical Skills Match (30%)
  2. Experience Match (25%)
  3. Behavioral/Culture Fit (15%)
  4. Location & Logistics (Pass/Fail gate)
  5. Career Alignment & Motivation (30%)

Pre-scoring gates:
  - Eligibility Gate (citizenship/visa)
  - Language Gate (required vs declared languages)
"""

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
        "js": "javascript", "ts": "typescript", "py": "python",
        "k8s": "kubernetes", "tf": "terraform", "gcp": "google cloud",
        "react.js": "react", "reactjs": "react", "vue.js": "vue",
        "vuejs": "vue", "next.js": "nextjs", "node.js": "node",
        "nodejs": "node", "c plus plus": "c++", "c sharp": "c#",
        "postgres": "postgresql", "mongo": "mongodb", "ci cd": "ci/cd",
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
        "git", "github", "gitlab", "linux", "bash",
        "machine learning", "deep learning", "tensorflow", "pytorch", "scikit",
        "pandas", "numpy", "data science",
        "rest api", "graphql", "grpc", "ci/cd", "jenkins", "github actions",
        "agile", "scrum", "jira", "figma",
        "sql", "nosql", "etl", "airflow", "spark",
        "blockchain", "solidity", "web3",
        "cybersecurity", "penetration testing",
        "communication", "leadership", "teamwork", "problem solving",
        "project management", "time management",
        "spanish", "english", "portuguese", "french", "german",
    ]
    return [s for s in skill_keywords if re.search(rf"\b{re.escape(s)}\b", description_lower)]


def check_eligibility_gate(profile: dict, job: dict) -> dict:
    """Pre-scoring gate: citizenship/visa requirements."""
    job_text = (job.get("title", "") + " " + job.get("description", "")).lower()
    user_nationality = profile.get("nationality", "").lower()

    citizenship_kw = ["citizen", "permanent resident", "pr required", "full working rights",
                       "security clearance", "clearance required"]
    for kw in citizenship_kw:
        if kw in job_text:
            if user_nationality and user_nationality not in job_text:
                return {"pass": False, "reason": f"Requires {kw}"}

    international_kw = ["international applicants", "visa holders", "we sponsor"]
    for kw in international_kw:
        if kw in job_text:
            return {"pass": True, "reason": "Accepts international applicants"}

    return {"pass": True, "reason": "No explicit citizenship requirement"}


def check_language_gate(profile: dict, job: dict) -> dict:
    """Pre-scoring gate: required vs declared languages."""
    job_text = (job.get("title", "") + " " + job.get("description", "")).lower()
    user_languages = {lang.lower(): level.lower()
                      for lang, level in profile.get("languages", {}).items()}

    required_langs = []
    lang_pattern = re.compile(r"((?:fluent|native|bilingual|proficient|conversational)?)\s*"
                              r"(spanish|english|portuguese|french|german|chinese|japanese|"
                              r"korean|arabic|russian|hindi|italian|dutch)", re.IGNORECASE)
    for match in lang_pattern.finditer(job.get("description", "")):
        lang = match.group(2).lower()
        qualifier = (match.group(1) or "").strip().lower()
        required_langs.append({"language": lang, "qualifier": qualifier})

    for req in required_langs:
        lang = req["language"]
        if lang not in user_languages:
            return {"pass": False, "flag": False,
                    "reason": f"Requires {lang} (not declared)"}
        user_level = user_languages[lang]
        qualifier = req["qualifier"]
        if qualifier in ("fluent", "native", "bilingual") and user_level in ("beginner", "basic"):
            return {"pass": True, "flag": True,
                    "reason": f"Requires {qualifier} {lang}, you declared {user_level}"}

    return {"pass": True, "flag": False, "reason": "Language requirements met"}


def score_technical_skills(profile: dict, job: dict) -> tuple[float, list, list]:
    """Dimension 1: Technical Skills Match (0-100)."""
    profile_skills = set(normalize_skill(s) for s in profile.get("skills", []))
    job_skills = set(normalize_skill(s) for s in extract_skills_from_description(
        job.get("description", "")))

    if not job_skills:
        return 50.0, [], []

    matched = sorted(profile_skills & job_skills)
    missing = sorted(job_skills - profile_skills)
    score = len(matched) / len(job_skills) * 100
    return round(score, 1), matched, missing


def score_experience(profile: dict, job: dict) -> float:
    """Dimension 2: Experience Match (0-100)."""
    user_years = profile.get("experience", {}).get("years")
    desc_text = job.get("description", "").lower()
    exp_match = re.search(r"(\d+)\+?\s*years?", desc_text)
    job_years = int(exp_match.group(1)) if exp_match else None

    if user_years and job_years:
        if user_years >= job_years:
            return 100.0
        elif user_years >= job_years * 0.7:
            return 70.0
        else:
            return max(0.0, 100 - (job_years - user_years) * 20)
    return 50.0


def score_behavioral_fit(profile: dict, job: dict) -> float:
    """Dimension 3: Behavioral/Culture Fit (0-100)."""
    job_text = (job.get("title", "") + " " + job.get("description", "")).lower()
    user_industries = set(i.lower().strip() for i in profile.get("industries", [])
                          if isinstance(i, str))

    culture_keywords = {
        "fast-paced": 0, "startup": 0, "agile": 0, "collaborative": 0,
        "independent": 0, "remote": 0, "innovative": 0,
    }
    culture_matches = sum(1 for kw in culture_keywords if kw in job_text)

    if user_industries:
        industry_overlap = sum(1 for ind in user_industries if ind in job_text)
        return min(100.0, 50 + culture_matches * 8 + industry_overlap * 10)

    return min(100.0, 50 + culture_matches * 10)


def score_location(profile: dict, job: dict) -> tuple[str, str]:
    """Dimension 4: Location & Logistics (Pass/Fail)."""
    user_remote = profile.get("remote_preference", "no-preference")
    job_remote = job.get("is_remote", False)

    if user_remote == "remote-only":
        return ("PASS", "Remote position") if job_remote else ("FAIL", "Not remote")
    elif user_remote == "no-preference":
        return "PASS", "No location preference"
    elif user_remote in ("hybrid", "on-site"):
        if job_remote:
            return "FLAG", "Remote but you prefer on-site"
        return "PASS", "On-site position"
    return "PASS", "Location unspecified"


def score_career_alignment(profile: dict, job: dict) -> float:
    """Dimension 5: Career Alignment & Motivation (0-100)."""
    job_text = (job.get("title", "") + " " + job.get("description", "")).lower()
    user_goals = profile.get("career_goals", [])
    goal_keywords = {"growth", "leadership", "senior", "architect", "lead",
                     "management", "principal", "staff", "director"}

    alignment = 0
    for goal in user_goals:
        if goal.lower() in job_text:
            alignment += 20

    for kw in goal_keywords:
        if kw in job_text:
            alignment += 5

    return min(100.0, 50 + alignment)


def score_job_match(profile: dict, job: dict) -> dict:
    """Calculate 5-dimension match score with pre-scoring gates."""
    eligibility = check_eligibility_gate(profile, job)
    if not eligibility["pass"]:
        return _gate_fail("eligibility", eligibility["reason"], job)

    language = check_language_gate(profile, job)
    if not language["pass"]:
        return _gate_fail("language", language["reason"], job)

    tech_score, matched, missing = score_technical_skills(profile, job)
    exp_score = score_experience(profile, job)
    behav_score = score_behavioral_fit(profile, job)
    location_result, location_note = score_location(profile, job)
    career_score = score_career_alignment(profile, job)

    if location_result == "FAIL":
        total = 0
        analysis = f"Location gate failed: {location_note}"
    else:
        total = (
            tech_score * 0.30 +
            exp_score * 0.25 +
            behav_score * 0.15 +
            career_score * 0.30
        )
        analysis = _generate_analysis_5d(
            total, tech_score, exp_score, behav_score, career_score,
            matched, missing, location_result, location_note,
            language.get("flag", False), language.get("reason", "")
        )

    return {
        "total_score": round(total, 1),
        "technical_score": tech_score,
        "experience_score": exp_score,
        "behavioral_score": behav_score,
        "career_score": career_score,
        "location_result": location_result,
        "location_note": location_note,
        "eligibility_gate": eligibility["reason"],
        "language_gate": language["reason"],
        "language_flag": language.get("flag", False),
        "matched_skills": matched,
        "missing_skills": missing,
        "nice_to_have": sorted(set(normalize_skill(s) for s in profile.get("skills", []))
                               - set(extract_skills_from_description(job.get("description", "")))),
        "analysis": analysis,
    }


def _gate_fail(gate: str, reason: str, job: dict) -> dict:
    return {
        "total_score": 0,
        "technical_score": 0, "experience_score": 0,
        "behavioral_score": 0, "career_score": 0,
        "location_result": "N/A", "location_note": "",
        "eligibility_gate": reason if gate == "eligibility" else "PASS",
        "language_gate": reason if gate == "language" else "PASS",
        "language_flag": False,
        "matched_skills": [], "missing_skills": [], "nice_to_have": [],
        "analysis": f"GATE FAILED ({gate}): {reason}",
    }


def _generate_analysis_5d(total, tech, exp, behav, career, matched, missing,
                          loc_result, loc_note, lang_flag, lang_note):
    if total >= 75:
        verdict = "Strong Fit"
    elif total >= 60:
        verdict = "Good Fit"
    elif total >= 45:
        verdict = "Moderate Fit"
    elif total >= 30:
        verdict = "Weak Fit"
    else:
        verdict = "Poor Fit"

    parts = [f"{verdict} ({total:.0f}/100)."]

    if matched:
        parts.append(f"Strong skills: {', '.join(matched[:3])}.")
    if missing:
        parts.append(f"Gaps: {', '.join(missing[:3])}.")
    if loc_result == "FLAG":
        parts.append(f"Location note: {loc_note}.")
    if lang_flag:
        parts.append(f"Language note: {lang_note}.")
    if exp < 50:
        parts.append("Experience may be insufficient.")
    if career < 50:
        parts.append("Limited career alignment.")

    return " ".join(parts)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Score job matches (5D framework)")
    parser.add_argument("--profile", "-p", required=True, help="Path to profile.json")
    parser.add_argument("--jobs", "-j", required=True, help="Path to results.json")
    parser.add_argument("--output", "-o", default="scored.json", help="Output path")
    args = parser.parse_args()

    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    jobs = json.loads(Path(args.jobs).read_text(encoding="utf-8"))

    scored = [dict(job, **score_job_match(profile, job)) for job in jobs]
    scored.sort(key=lambda x: x["total_score"], reverse=True)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(scored, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  Scored {len(scored)} jobs. Top 5:")
    for i, job in enumerate(scored[:5], 1):
        loc = job.get("location_result", "")
        flag = " [LANG FLAG]" if job.get("language_flag") else ""
        print(f"  {i}. [{job['total_score']:.0f}%] {job['title']} @ {job['company']} ({loc}){flag}")
        if job.get("missing_skills"):
            print(f"     Missing: {', '.join(job['missing_skills'][:3])}")

    print(f"\n  Saved to: {output_path}")


if __name__ == "__main__":
    main()
