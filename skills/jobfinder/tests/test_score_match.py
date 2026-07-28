"""Tests for jobfinder score_match module."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# normalize_skill
# ---------------------------------------------------------------------------

class TestNormalizeSkill:
    def test_lowercase_and_strip(self, score_match_module):
        assert score_match_module.normalize_skill("  Python  ") == "python"

    def test_whitespace_and_dashes_collapsed(self, score_match_module):
        assert score_match_module.normalize_skill("machine-learning") == "machine learning"
        assert score_match_module.normalize_skill("machine   learning") == "machine learning"
        assert score_match_module.normalize_skill("ci - cd") == "ci/cd"

    def test_alias_js(self, score_match_module):
        assert score_match_module.normalize_skill("js") == "javascript"

    def test_alias_ts(self, score_match_module):
        assert score_match_module.normalize_skill("ts") == "typescript"

    def test_alias_py(self, score_match_module):
        assert score_match_module.normalize_skill("py") == "python"

    def test_alias_k8s(self, score_match_module):
        assert score_match_module.normalize_skill("k8s") == "kubernetes"

    def test_alias_tf(self, score_match_module):
        assert score_match_module.normalize_skill("tf") == "terraform"

    def test_alias_reactjs(self, score_match_module):
        assert score_match_module.normalize_skill("reactjs") == "react"
        assert score_match_module.normalize_skill("react.js") == "react"

    def test_alias_vuejs(self, score_match_module):
        assert score_match_module.normalize_skill("vuejs") == "vue"
        assert score_match_module.normalize_skill("vue.js") == "vue"

    def test_alias_nodejs(self, score_match_module):
        assert score_match_module.normalize_skill("nodejs") == "node"
        assert score_match_module.normalize_skill("node.js") == "node"

    def test_alias_cplusplus(self, score_match_module):
        assert score_match_module.normalize_skill("c plus plus") == "c++"

    def test_alias_csharp(self, score_match_module):
        assert score_match_module.normalize_skill("c sharp") == "c#"

    def test_alias_postgres(self, score_match_module):
        assert score_match_module.normalize_skill("postgres") == "postgresql"

    def test_alias_mongo(self, score_match_module):
        assert score_match_module.normalize_skill("mongo") == "mongodb"

    def test_unknown_skill_passes_through(self, score_match_module):
        assert score_match_module.normalize_skill("rust") == "rust"

    def test_empty_string(self, score_match_module):
        assert score_match_module.normalize_skill("") == ""


# ---------------------------------------------------------------------------
# extract_skills_from_description
# ---------------------------------------------------------------------------

class TestExtractSkillsFromDescription:
    def test_finds_python(self, score_match_module):
        result = score_match_module.extract_skills_from_description("We need a Python developer")
        assert "python" in result

    def test_finds_multiple_skills(self, score_match_module):
        text = "Looking for React and TypeScript developer with Node experience"
        result = score_match_module.extract_skills_from_description(text)
        assert "react" in result
        assert "typescript" in result
        assert "node" in result

    def test_case_insensitive(self, score_match_module):
        result = score_match_module.extract_skills_from_description("PYTHON expert needed")
        assert "python" in result

    def test_no_skills_found(self, score_match_module):
        result = score_match_module.extract_skills_from_description("Hello world foo bar baz")
        assert result == []

    def test_aws_azure_gcp(self, score_match_module):
        text = "Experience with AWS, Azure, and GCP cloud platforms"
        result = score_match_module.extract_skills_from_description(text)
        assert "aws" in result
        assert "azure" in result
        assert "gcp" in result

    def test_sql_found(self, score_match_module):
        result = score_match_module.extract_skills_from_description("Strong SQL skills required")
        assert "sql" in result

    def test_docker_kubernetes(self, score_match_module):
        text = "Docker and Kubernetes experience preferred"
        result = score_match_module.extract_skills_from_description(text)
        assert "docker" in result
        assert "kubernetes" in result

    def test_soft_skills(self, score_match_module):
        text = "Communication and leadership skills are important"
        result = score_match_module.extract_skills_from_description(text)
        assert "communication" in result
        assert "leadership" in result


# ---------------------------------------------------------------------------
# score_job_match
# ---------------------------------------------------------------------------

class TestScoreJobMatch:
    @pytest.fixture
    def full_profile(self):
        return {
            "skills": ["python", "react", "typescript", "docker", "aws"],
            "experience": {"years": 5},
            "salary_expected": 80000,
            "remote_preference": "remote-only",
            "education": "Bachelor's Degree",
        }

    @pytest.fixture
    def full_job(self):
        return {
            "title": "Senior Python Developer",
            "description": "Looking for a Python developer with React and AWS experience. 3+ years experience required.",
            "company": "TechCorp",
            "salary_min": 70000,
            "salary_max": 100000,
            "is_remote": True,
        }

    def test_perfect_match_scores_high(self, score_match_module, full_profile, full_job):
        result = score_match_module.score_job_match(full_profile, full_job)
        assert result["total_score"] >= 70

    def test_matched_skills_populated(self, score_match_module, full_profile, full_job):
        result = score_match_module.score_job_match(full_profile, full_job)
        assert len(result["matched_skills"]) > 0
        assert "python" in result["matched_skills"]

    def test_total_score_between_0_and_100(self, score_match_module, full_profile, full_job):
        result = score_match_module.score_job_match(full_profile, full_job)
        assert 0 <= result["total_score"] <= 100

    def test_no_matching_skills(self, score_match_module, full_job):
        profile = {"skills": ["cobol", "fortran"], "experience": {"years": 20}}
        result = score_match_module.score_job_match(profile, full_job)
        assert result["skills_score"] == 0

    def test_empty_job_skills_defaults_to_50(self, score_match_module):
        profile = {"skills": ["python"]}
        job = {"title": "Manager", "description": "A general management role with no tech stack"}
        result = score_match_module.score_job_match(profile, job)
        assert result["skills_score"] == 50

    def test_experience_exact_match(self, score_match_module):
        profile = {"skills": ["python"], "experience": {"years": 5}}
        job = {"title": "Dev", "description": "5+ years experience", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["experience_score"] == 100

    def test_experience_near_match_70pct(self, score_match_module):
        profile = {"skills": ["python"], "experience": {"years": 4}}
        job = {"title": "Dev", "description": "5+ years experience", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["experience_score"] == 70

    def test_experience_far_below(self, score_match_module):
        profile = {"skills": ["python"], "experience": {"years": 1}}
        job = {"title": "Dev", "description": "5+ years experience", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["experience_score"] < 50

    def test_experience_not_mentioned_defaults_to_50(self, score_match_module):
        profile = {"skills": ["python"], "experience": {"years": 5}}
        job = {"title": "Dev", "description": "Some role", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["experience_score"] == 50

    def test_salary_in_range(self, score_match_module):
        profile = {"skills": ["python"], "salary_expected": 80000}
        job = {"title": "Dev", "description": "Dev role", "salary_min": 70000, "salary_max": 100000, "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["salary_score"] == 100

    def test_salary_below_minimum(self, score_match_module):
        profile = {"skills": ["python"], "salary_expected": 50000}
        job = {"title": "Dev", "description": "Dev role", "salary_min": 70000, "salary_max": 100000, "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["salary_score"] == 80

    def test_salary_above_max(self, score_match_module):
        profile = {"skills": ["python"], "salary_expected": 150000}
        job = {"title": "Dev", "description": "Dev role", "salary_min": 70000, "salary_max": 100000, "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["salary_score"] < 50

    def test_salary_string_parsing(self, score_match_module):
        profile = {"skills": ["python"], "salary_expected": "$80000"}
        job = {"title": "Dev", "description": "Dev role", "salary_min": 70000, "salary_max": 100000, "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["salary_score"] == 100

    def test_remote_only_matches_remote_job(self, score_match_module):
        profile = {"skills": ["python"], "remote_preference": "remote-only"}
        job = {"title": "Dev", "description": "Dev role", "is_remote": True}
        result = score_match_module.score_job_match(profile, job)
        assert result["location_score"] == 100

    def test_remote_only_penalized_for_onsite(self, score_match_module):
        profile = {"skills": ["python"], "remote_preference": "remote-only"}
        job = {"title": "Dev", "description": "Dev role", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["location_score"] == 10

    def test_no_preference_always_100(self, score_match_module):
        profile = {"skills": ["python"], "remote_preference": "no-preference"}
        job = {"title": "Dev", "description": "Dev role", "is_remote": True}
        result = score_match_module.score_job_match(profile, job)
        assert result["location_score"] == 100

    def test_onsite_pref_favours_onsite(self, score_match_module):
        profile = {"skills": ["python"], "remote_preference": "on-site"}
        job = {"title": "Dev", "description": "Dev role", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["location_score"] == 90

    def test_onsite_pref_penalty_for_remote(self, score_match_module):
        profile = {"skills": ["python"], "remote_preference": "on-site"}
        job = {"title": "Dev", "description": "Dev role", "is_remote": True}
        result = score_match_module.score_job_match(profile, job)
        assert result["location_score"] == 60

    def test_education_bachelors_passes(self, score_match_module):
        profile = {"skills": ["python"], "education": "Bachelor's Degree"}
        job = {"title": "Dev", "description": "Requires university degree", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["education_score"] == 100

    def test_education_not_specified_passes_when_no_requirement(self, score_match_module):
        profile = {"skills": ["python"], "education": "Not specified"}
        job = {"title": "Dev", "description": "General role", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["education_score"] == 100

    def test_education_list_format(self, score_match_module):
        profile = {
            "skills": ["python"],
            "education": [{"degree": "Master's Degree"}, {"degree": "Bachelor's Degree"}],
        }
        job = {"title": "Dev", "description": "General role", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["education_score"] == 100

    def test_weighted_total_is_correct(self, score_match_module, full_profile, full_job):
        result = score_match_module.score_job_match(full_profile, full_job)
        expected = (
            result["skills_score"] * 0.35
            + result["experience_score"] * 0.20
            + result["salary_score"] * 0.15
            + result["location_score"] * 0.15
            + result["education_score"] * 0.10
            + result["industry_score"] * 0.05
        )
        assert abs(result["total_score"] - round(expected, 1)) < 0.2

    def test_result_keys_present(self, score_match_module, full_profile, full_job):
        result = score_match_module.score_job_match(full_profile, full_job)
        required_keys = {
            "total_score", "skills_score", "matched_skills", "missing_skills",
            "experience_score", "salary_score", "location_score", "education_score",
            "industry_score", "nice_to_have", "analysis",
        }
        assert required_keys.issubset(result.keys())

    def test_missing_skills_populated(self, score_match_module):
        profile = {"skills": ["python"], "experience": {"years": 3}}
        job = {"title": "Dev", "description": "Python and React developer", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert "react" in result["missing_skills"]

    def test_empty_profile(self, score_match_module):
        profile = {}
        job = {"title": "Dev", "description": "Python developer", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert 0 <= result["total_score"] <= 100

    def test_analysis_contains_match_info(self, score_match_module, full_profile, full_job):
        result = score_match_module.score_job_match(full_profile, full_job)
        assert "match" in result["analysis"].lower()


# ---------------------------------------------------------------------------
# _generate_analysis
# ---------------------------------------------------------------------------

class TestGenerateAnalysis:
    def test_excellent_for_high_score(self, score_match_module):
        analysis = score_match_module._generate_analysis(90, {"python"}, set(), 100, 100)
        assert "excellent" in analysis

    def test_strong_for_medium_high(self, score_match_module):
        analysis = score_match_module._generate_analysis(75, {"python"}, set(), 100, 100)
        assert "strong" in analysis

    def test_moderate_for_medium(self, score_match_module):
        analysis = score_match_module._generate_analysis(55, set(), set(), 50, 50)
        assert "moderate" in analysis

    def test_low_for_low_score(self, score_match_module):
        analysis = score_match_module._generate_analysis(30, set(), set(), 30, 30)
        assert "low" in analysis

    def test_missing_skills_mentioned(self, score_match_module):
        analysis = score_match_module._generate_analysis(50, {"python"}, {"react", "typescript"}, 50, 50)
        assert "react" in analysis or "typescript" in analysis

    def test_low_experience_mentioned(self, score_match_module):
        analysis = score_match_module._generate_analysis(50, set(), set(), 30, 50)
        assert "experience" in analysis

    def test_high_salary_mentioned(self, score_match_module):
        analysis = score_match_module._generate_analysis(50, set(), set(), 50, 30)
        assert "salary" in analysis.lower()
