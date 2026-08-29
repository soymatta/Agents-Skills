"""Tests for jobfinder score_match module (5-Dimension Framework)."""

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
# Pre-scoring gates
# ---------------------------------------------------------------------------

class TestEligibilityGate:
    def test_no_requirement_passes(self, score_match_module):
        result = score_match_module.check_eligibility_gate({}, {"title": "Dev", "description": "Python role"})
        assert result["pass"] is True

    def test_citizenship_requirement_fails(self, score_match_module):
        profile = {"nationality": "brazilian"}
        job = {"title": "Dev", "description": "US citizen required"}
        result = score_match_module.check_eligibility_gate(profile, job)
        assert result["pass"] is False

    def test_international_applicants_pass(self, score_match_module):
        job = {"title": "Dev", "description": "We welcome international applicants"}
        result = score_match_module.check_eligibility_gate({}, job)
        assert result["pass"] is True


class TestLanguageGate:
    def test_no_language_requirement_passes(self, score_match_module):
        result = score_match_module.check_language_gate({}, {"title": "Dev", "description": "Python role"})
        assert result["pass"] is True

    def test_undeclared_language_fails(self, score_match_module):
        profile = {"languages": {"spanish": "native"}}
        job = {"title": "Dev", "description": "Fluent English required"}
        result = score_match_module.check_language_gate(profile, job)
        assert result["pass"] is False

    def test_declared_language_passes(self, score_match_module):
        profile = {"languages": {"english": "fluent", "spanish": "native"}}
        job = {"title": "Dev", "description": "Fluent English required"}
        result = score_match_module.check_language_gate(profile, job)
        assert result["pass"] is True

    def test_insufficient_level_flagged(self, score_match_module):
        profile = {"languages": {"english": "beginner"}}
        job = {"title": "Dev", "description": "Fluent English required"}
        result = score_match_module.check_language_gate(profile, job)
        assert result["pass"] is True
        assert result["flag"] is True

    def test_empty_list_languages_does_not_crash(self, score_match_module):
        # Regression: template profile.json ships languages: [], which broke .items().
        profile = {"languages": []}
        job = {"title": "Dev", "description": "Fluent English required"}
        result = score_match_module.check_language_gate(profile, job)
        assert result["pass"] is False

    def test_list_of_strings_languages(self, score_match_module):
        profile = {"languages": ["spanish", "english"]}
        job = {"title": "Dev", "description": "English required"}
        result = score_match_module.check_language_gate(profile, job)
        assert result["pass"] is True

    def test_list_of_objects_languages(self, score_match_module):
        profile = {"languages": [{"language": "English", "level": "Fluent"}]}
        job = {"title": "Dev", "description": "Fluent English required"}
        result = score_match_module.check_language_gate(profile, job)
        assert result["pass"] is True


# ---------------------------------------------------------------------------
# 5D Scoring dimensions
# ---------------------------------------------------------------------------

class TestScoreTechnicalSkills:
    def test_perfect_match(self, score_match_module):
        profile = {"skills": ["python", "react", "docker"]}
        job = {"description": "Python and React developer with Docker experience"}
        score, matched, missing = score_match_module.score_technical_skills(profile, job)
        assert score == 100.0
        assert "python" in matched
        assert "react" in matched

    def test_partial_match(self, score_match_module):
        profile = {"skills": ["python"]}
        job = {"description": "Python and React developer"}
        score, matched, missing = score_match_module.score_technical_skills(profile, job)
        assert 0 < score < 100
        assert "python" in matched
        assert "react" in missing

    def test_no_match(self, score_match_module):
        profile = {"skills": ["cobol"]}
        job = {"description": "Python and React developer"}
        score, matched, missing = score_match_module.score_technical_skills(profile, job)
        assert score == 0.0
        assert matched == []

    def test_empty_job_skills_defaults_to_50(self, score_match_module):
        profile = {"skills": ["python"]}
        job = {"description": "A general management role"}
        score, matched, missing = score_match_module.score_technical_skills(profile, job)
        assert score == 50.0


class TestScoreExperience:
    def test_exact_match(self, score_match_module):
        profile = {"experience": {"years": 5}}
        job = {"description": "5+ years experience required"}
        assert score_match_module.score_experience(profile, job) == 100.0

    def test_near_match(self, score_match_module):
        profile = {"experience": {"years": 4}}
        job = {"description": "5+ years experience required"}
        assert score_match_module.score_experience(profile, job) == 70.0

    def test_far_below(self, score_match_module):
        profile = {"experience": {"years": 1}}
        job = {"description": "5+ years experience required"}
        assert score_match_module.score_experience(profile, job) < 50.0

    def test_not_mentioned_defaults_to_50(self, score_match_module):
        profile = {"experience": {"years": 5}}
        job = {"description": "Some role"}
        assert score_match_module.score_experience(profile, job) == 50.0


class TestScoreLocation:
    def test_remote_only_matches_remote(self, score_match_module):
        profile = {"remote_preference": "remote-only"}
        job = {"is_remote": True}
        result, note = score_match_module.score_location(profile, job)
        assert result == "PASS"

    def test_remote_only_fails_onsite(self, score_match_module):
        profile = {"remote_preference": "remote-only"}
        job = {"is_remote": False}
        result, note = score_match_module.score_location(profile, job)
        assert result == "FAIL"

    def test_no_preference_always_passes(self, score_match_module):
        profile = {"remote_preference": "no-preference"}
        job = {"is_remote": True}
        result, note = score_match_module.score_location(profile, job)
        assert result == "PASS"

    def test_onsite_pref_favours_onsite(self, score_match_module):
        profile = {"remote_preference": "on-site"}
        job = {"is_remote": False}
        result, note = score_match_module.score_location(profile, job)
        assert result == "PASS"

    def test_onsite_pref_flags_remote(self, score_match_module):
        profile = {"remote_preference": "on-site"}
        job = {"is_remote": True}
        result, note = score_match_module.score_location(profile, job)
        assert result == "FLAG"


# ---------------------------------------------------------------------------
# score_job_match (full pipeline)
# ---------------------------------------------------------------------------

class TestScoreJobMatch:
    @pytest.fixture
    def full_profile(self):
        return {
            "skills": ["python", "react", "typescript", "docker", "aws"],
            "experience": {"years": 5},
            "remote_preference": "remote-only",
            "languages": {"english": "fluent", "spanish": "native"},
            "career_goals": ["senior", "growth"],
        }

    @pytest.fixture
    def full_job(self):
        return {
            "title": "Senior Python Developer",
            "description": "Looking for a Python developer with React and AWS experience. 3+ years experience required. Fast-paced startup environment.",
            "company": "TechCorp",
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
        assert result["technical_score"] == 0.0

    def test_experience_exact_match(self, score_match_module):
        profile = {"skills": ["python"], "experience": {"years": 5}}
        job = {"title": "Dev", "description": "5+ years experience", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["experience_score"] == 100.0

    def test_experience_near_match_70pct(self, score_match_module):
        profile = {"skills": ["python"], "experience": {"years": 4}}
        job = {"title": "Dev", "description": "5+ years experience", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["experience_score"] == 70.0

    def test_experience_far_below(self, score_match_module):
        profile = {"skills": ["python"], "experience": {"years": 1}}
        job = {"title": "Dev", "description": "5+ years experience", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["experience_score"] < 50.0

    def test_experience_not_mentioned_defaults_to_50(self, score_match_module):
        profile = {"skills": ["python"], "experience": {"years": 5}}
        job = {"title": "Dev", "description": "Some role", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["experience_score"] == 50.0

    def test_location_gate_fail(self, score_match_module):
        profile = {"skills": ["python"], "remote_preference": "remote-only"}
        job = {"title": "Dev", "description": "On-site role", "is_remote": False}
        result = score_match_module.score_job_match(profile, job)
        assert result["location_result"] == "FAIL"
        assert result["total_score"] == 0

    def test_location_gate_pass(self, score_match_module):
        profile = {"skills": ["python"], "remote_preference": "remote-only"}
        job = {"title": "Dev", "description": "Remote role", "is_remote": True}
        result = score_match_module.score_job_match(profile, job)
        assert result["location_result"] == "PASS"
        assert result["total_score"] > 0

    def test_result_keys_present(self, score_match_module, full_profile, full_job):
        result = score_match_module.score_job_match(full_profile, full_job)
        required_keys = {
            "total_score", "technical_score", "experience_score",
            "behavioral_score", "career_score", "location_result",
            "location_note", "eligibility_gate", "language_gate",
            "language_flag", "matched_skills", "missing_skills",
            "nice_to_have", "analysis",
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

    def test_analysis_contains_fit_verdict(self, score_match_module, full_profile, full_job):
        result = score_match_module.score_job_match(full_profile, full_job)
        assert "fit" in result["analysis"].lower()

    def test_eligibility_gate_failure(self, score_match_module):
        profile = {"nationality": "brazilian", "skills": ["python"]}
        job = {"title": "Dev", "description": "US citizen required", "is_remote": True}
        result = score_match_module.score_job_match(profile, job)
        assert result["total_score"] == 0
        assert "eligibility" in result["analysis"].lower()

    def test_language_gate_failure(self, score_match_module):
        profile = {"skills": ["python"], "languages": {"spanish": "native"}}
        job = {"title": "Dev", "description": "Fluent English required", "is_remote": True}
        result = score_match_module.score_job_match(profile, job)
        assert result["total_score"] == 0
        assert "language" in result["analysis"].lower()


# ---------------------------------------------------------------------------
# _generate_analysis_5d
# ---------------------------------------------------------------------------

class TestGenerateAnalysis5D:
    def test_strong_fit_for_high_score(self, score_match_module):
        analysis = score_match_module._generate_analysis_5d(
            85, 100, 100, 80, 90, ["python"], [], "PASS", "", False, "")
        assert "strong fit" in analysis.lower()

    def test_good_fit_for_medium_high(self, score_match_module):
        analysis = score_match_module._generate_analysis_5d(
            65, 70, 80, 60, 70, ["python"], ["react"], "PASS", "", False, "")
        assert "good fit" in analysis.lower()

    def test_moderate_fit_for_medium(self, score_match_module):
        analysis = score_match_module._generate_analysis_5d(
            50, 50, 50, 50, 50, [], ["react", "docker"], "PASS", "", False, "")
        assert "moderate fit" in analysis.lower()

    def test_weak_fit_for_low_score(self, score_match_module):
        analysis = score_match_module._generate_analysis_5d(
            35, 30, 40, 30, 40, [], ["python", "react"], "PASS", "", False, "")
        assert "weak fit" in analysis.lower()

    def test_poor_fit_for_very_low(self, score_match_module):
        analysis = score_match_module._generate_analysis_5d(
            10, 0, 20, 10, 20, [], ["python", "react", "docker"], "PASS", "", False, "")
        assert "poor fit" in analysis.lower()

    def test_missing_skills_mentioned(self, score_match_module):
        analysis = score_match_module._generate_analysis_5d(
            50, 50, 50, 50, 50, ["python"], ["react", "typescript"], "PASS", "", False, "")
        assert "react" in analysis or "typescript" in analysis

    def test_low_experience_mentioned(self, score_match_module):
        analysis = score_match_module._generate_analysis_5d(
            50, 50, 30, 50, 50, [], [], "PASS", "", False, "")
        assert "experience" in analysis.lower()

    def test_location_flag_mentioned(self, score_match_module):
        analysis = score_match_module._generate_analysis_5d(
            70, 80, 80, 70, 80, ["python"], [], "FLAG", "Remote but you prefer on-site", False, "")
        assert "location" in analysis.lower()

    def test_language_flag_mentioned(self, score_match_module):
        analysis = score_match_module._generate_analysis_5d(
            70, 80, 80, 70, 80, ["python"], [], "PASS", "", True, "Requires fluent english")
        assert "language" in analysis.lower()
