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

The weights and the verdict bands are specified by the tables in
skills/jobfinder/SKILL.md. Run `--selftest` to assert both against this script.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Weights documented in SKILL.md "5-Dimension Scoring Framework"; --selftest
# compares them against that table. Location is a pass/fail gate, not a weight.
WEIGHTS = {
    "technical": 0.30,
    "experience": 0.25,
    "behavioral": 0.15,
    "career": 0.30,
}

SKILL_MD = Path(__file__).resolve().parents[1] / "SKILL.md"


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


def _languages_dict(languages) -> dict:
    """Normalize the profile ``languages`` field to {name: level}.

    Accepts a dict ({"English": "Advanced"}), a list of strings
    (["Spanish", "English"]), or a list of objects
    ([{"language": "English", "level": "Native"}, ...]).
    """
    out: dict[str, str] = {}
    if isinstance(languages, dict):
        for lang, level in languages.items():
            out[str(lang).strip().lower()] = str(level or "").strip().lower()
    elif isinstance(languages, list):
        for item in languages:
            if isinstance(item, dict):
                lang = item.get("language") or item.get("name") or item.get("lang")
                level = item.get("level") or item.get("proficiency") or ""
            else:
                lang, level = item, ""
            if lang:
                out[str(lang).strip().lower()] = str(level or "").strip().lower()
    return out


def check_language_gate(profile: dict, job: dict) -> dict:
    """Pre-scoring gate: required vs declared languages."""
    job_text = (job.get("title", "") + " " + job.get("description", "")).lower()
    user_languages = _languages_dict(profile.get("languages", []))

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
            tech_score * WEIGHTS["technical"] +
            exp_score * WEIGHTS["experience"] +
            behav_score * WEIGHTS["behavioral"] +
            career_score * WEIGHTS["career"]
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


def fit_verdict(total: float) -> str:
    """Map a 0-100 total to the documented fit band."""
    if total >= 75:
        return "Strong Fit"
    if total >= 60:
        return "Good Fit"
    if total >= 45:
        return "Moderate Fit"
    if total >= 30:
        return "Weak Fit"
    return "Poor Fit"


def _generate_analysis_5d(total, tech, exp, behav, career, matched, missing,
                          loc_result, loc_note, lang_flag, lang_note):
    verdict = fit_verdict(total)

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


# ---------------------------------------------------------------------------
# Self-test: the SKILL.md weight table and fit bands are the spec
# ---------------------------------------------------------------------------

_LABEL_TO_KEY = {
    "Technical Skills Match": "technical",
    "Experience Match": "experience",
    "Behavioral/Culture Fit": "behavioral",
    "Career Alignment": "career",
}
_BAND_RE = re.compile(r"^-\s+\*\*(?P<label>[^*]+)\*\*\s+\((?P<range>[^)]+)\)")


def _parse_weight_rows(text: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("| Dimension | Weight"):
            in_table = True
            continue
        if not in_table:
            continue
        if not stripped.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2 or not cells[0] or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append((cells[0], cells[1], cells[2] if len(cells) > 2 else ""))
    return rows


def _parse_fit_bands(text: str) -> list[tuple[int, str]]:
    bands: list[tuple[int, str]] = []
    for line in text.splitlines():
        match = _BAND_RE.match(line.strip())
        if not match:
            continue
        rng = match.group("range").strip()
        if rng.startswith("<"):
            bands.append((0, match.group("label").strip()))
            continue
        digits = re.match(r"\d+", rng)
        if digits:
            bands.append((int(digits.group(0)), match.group("label").strip()))
    return bands


def run_selftest() -> int:
    """Assert the documented weights and fit bands against the code."""
    text = SKILL_MD.read_text(encoding="utf-8")
    failures: list[str] = []

    rows = _parse_weight_rows(text)
    if not rows:
        raise SystemExit(f"selftest: no weight table found in {SKILL_MD}")
    documented: dict[str, float] = {}
    for label, weight, _range in rows:
        if label in _LABEL_TO_KEY:
            match = re.search(r"(\d+(?:\.\d+)?)\s*%", weight)
            if not match:
                raise SystemExit(f"selftest: unparseable weight {weight!r} for {label}")
            documented[_LABEL_TO_KEY[label]] = float(match.group(1)) / 100.0
        elif label == "Location & Logistics":
            if "Pass/Fail" not in weight:
                failures.append(f"{label}: doc says {weight!r}, expected Pass/Fail")
        else:
            raise SystemExit(f"selftest: unknown dimension {label!r} in {SKILL_MD}")

    missing = set(_LABEL_TO_KEY.values()) - set(documented)
    if missing:
        raise SystemExit(f"selftest: weight table missing {sorted(missing)}")
    for key, expected in documented.items():
        if abs(WEIGHTS[key] - expected) > 1e-9:
            failures.append(f"{key}: code {WEIGHTS[key]:.2f}, doc {expected:.2f}")
    if abs(sum(documented.values()) - 1.0) > 1e-9:
        failures.append(f"documented weights sum to {sum(documented.values()):.3f}, not 1.0")

    bands = _parse_fit_bands(text)
    if len(bands) < 2:
        raise SystemExit(f"selftest: fewer than 2 fit bands found in {SKILL_MD}")
    bands.sort(key=lambda band: band[0])
    for index, (lower, label) in enumerate(bands):
        actual = fit_verdict(lower)
        if actual != label:
            failures.append(f"fit_verdict({lower}) -> {actual!r}, doc says {label!r}")
        if index:
            below = fit_verdict(lower - 1)
            if below != bands[index - 1][1]:
                failures.append(
                    f"fit_verdict({lower - 1}) -> {below!r}, doc says {bands[index - 1][1]!r}"
                )

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        print(f"selftest: {len(failures)} mismatch(es) with {SKILL_MD}")
        return 1
    print(
        f"selftest: {len(documented)} weight(s) and {len(bands)} fit band(s) "
        f"match {SKILL_MD}"
    )
    return 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Score job matches (5D framework)")
    parser.add_argument("--profile", "-p", help="Path to profile.json")
    parser.add_argument("--jobs", "-j", help="Path to results.json")
    parser.add_argument("--output", "-o", default="scored.json", help="Output path")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Verify the SKILL.md weight table and fit bands against this script, "
        "then exit.",
    )
    args = parser.parse_args()

    if args.selftest:
        raise SystemExit(run_selftest())
    if not args.profile or not args.jobs:
        parser.error("--profile and --jobs are required (or use --selftest)")

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
    raise SystemExit(main())
