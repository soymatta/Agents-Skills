"""Tests for skill-creator quick_validate module."""

from __future__ import annotations

from pathlib import Path

import pytest


def _write_skill(tmp_path, name="test-skill", desc="A test skill", extra_fm="", content="# Test"):
    """Helper to create a temp skill directory with SKILL.md."""
    skill_dir = tmp_path / name
    skill_dir.mkdir()
    fm_lines = ["---", f"name: {name}", f"description: {desc}"]
    if extra_fm:
        fm_lines.append(extra_fm)
    fm_lines.append("---")
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("\n".join(fm_lines) + f"\n{content}", encoding="utf-8")
    return skill_dir


class TestValidateSkill:
    def test_valid_skill(self, quick_validate_module, tmp_path):
        skill_dir = _write_skill(tmp_path)
        valid, msg = quick_validate_module.validate_skill(skill_dir)
        assert valid is True

    def test_missing_skill_md(self, quick_validate_module, tmp_path):
        skill_dir = tmp_path / "empty-skill"
        skill_dir.mkdir()
        valid, msg = quick_validate_module.validate_skill(skill_dir)
        assert valid is False
        assert "SKILL.md not found" in msg

    def test_no_frontmatter(self, quick_validate_module, tmp_path):
        skill_dir = tmp_path / "no-fm"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Just a heading\nNo frontmatter.", encoding="utf-8")
        valid, msg = quick_validate_module.validate_skill(skill_dir)
        assert valid is False
        assert "No YAML frontmatter" in msg

    def test_missing_name(self, quick_validate_module, tmp_path):
        skill_dir = tmp_path / "no-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\ndescription: test\n---\n# Test", encoding="utf-8")
        valid, msg = quick_validate_module.validate_skill(skill_dir)
        assert valid is False
        assert "name" in msg.lower()

    def test_missing_description(self, quick_validate_module, tmp_path):
        skill_dir = tmp_path / "no-desc"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: test-skill\n---\n# Test", encoding="utf-8")
        valid, msg = quick_validate_module.validate_skill(skill_dir)
        assert valid is False
        assert "description" in msg.lower()

    def test_name_not_kebab_case(self, quick_validate_module, tmp_path):
        valid, msg = quick_validate_module.validate_skill(_write_skill(tmp_path, name="Not Valid"))
        assert valid is False
        assert "kebab-case" in msg

    def test_name_with_double_hyphens(self, quick_validate_module, tmp_path):
        valid, msg = quick_validate_module.validate_skill(_write_skill(tmp_path, name="bad--name"))
        assert valid is False
        assert "hyphen" in msg.lower()

    def test_name_too_long(self, quick_validate_module, tmp_path):
        valid, msg = quick_validate_module.validate_skill(_write_skill(tmp_path, name="a" * 65))
        assert valid is False
        assert "too long" in msg.lower()

    def test_description_with_angle_brackets(self, quick_validate_module, tmp_path):
        valid, msg = quick_validate_module.validate_skill(
            _write_skill(tmp_path, desc="Use <div> tags")
        )
        assert valid is False
        assert "angle brackets" in msg

    def test_description_too_long(self, quick_validate_module, tmp_path):
        valid, msg = quick_validate_module.validate_skill(
            _write_skill(tmp_path, desc="x" * 1025)
        )
        assert valid is False
        assert "too long" in msg.lower()

    def test_unexpected_frontmatter_key(self, quick_validate_module, tmp_path):
        valid, msg = quick_validate_module.validate_skill(
            _write_skill(tmp_path, extra_fm="unexpected_key: value")
        )
        assert valid is False
        assert "Unexpected" in msg

    def test_valid_with_compatibility(self, quick_validate_module, tmp_path):
        valid, msg = quick_validate_module.validate_skill(
            _write_skill(tmp_path, extra_fm="compatibility: depends on other-skill")
        )
        assert valid is True

    def test_valid_with_metadata(self, quick_validate_module, tmp_path):
        valid, msg = quick_validate_module.validate_skill(
            _write_skill(tmp_path, extra_fm="metadata:\n  version: 1.0")
        )
        assert valid is True


class TestAggregateBenchmark:
    def test_calculate_stats_empty(self, aggregate_benchmark_module):
        result = aggregate_benchmark_module.calculate_stats([])
        assert result == {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}

    def test_calculate_stats_single(self, aggregate_benchmark_module):
        result = aggregate_benchmark_module.calculate_stats([5.0])
        assert result["mean"] == 5.0
        assert result["stddev"] == 0.0
        assert result["min"] == 5.0
        assert result["max"] == 5.0

    def test_calculate_stats_multiple(self, aggregate_benchmark_module):
        result = aggregate_benchmark_module.calculate_stats([1.0, 2.0, 3.0, 4.0, 5.0])
        assert result["mean"] == 3.0
        assert result["min"] == 1.0
        assert result["max"] == 5.0
        assert result["stddev"] > 0

    def test_calculate_stats_identical(self, aggregate_benchmark_module):
        result = aggregate_benchmark_module.calculate_stats([7.0, 7.0, 7.0])
        assert result["mean"] == 7.0
        assert result["stddev"] == 0.0

    def test_generate_benchmark_empty_dir(self, aggregate_benchmark_module, tmp_path):
        benchmark = aggregate_benchmark_module.generate_benchmark(tmp_path)
        assert "metadata" in benchmark
        assert "runs" in benchmark
        assert "run_summary" in benchmark
        assert benchmark["runs"] == []

    def test_generate_markdown(self, aggregate_benchmark_module):
        benchmark = {
            "metadata": {
                "skill_name": "test-skill",
                "executor_model": "gpt-4",
                "timestamp": "2026-01-01T00:00:00Z",
                "evals_run": [1, 2],
                "runs_per_configuration": 3,
            },
            "runs": [],
            "run_summary": {
                "with_skill": {
                    "pass_rate": {"mean": 0.85, "stddev": 0.05, "min": 0.8, "max": 0.9},
                    "time_seconds": {"mean": 10.0, "stddev": 2.0, "min": 8.0, "max": 12.0},
                    "tokens": {"mean": 500, "stddev": 50, "min": 450, "max": 550},
                },
                "without_skill": {
                    "pass_rate": {"mean": 0.60, "stddev": 0.10, "min": 0.5, "max": 0.7},
                    "time_seconds": {"mean": 15.0, "stddev": 3.0, "min": 12.0, "max": 18.0},
                    "tokens": {"mean": 800, "stddev": 100, "min": 700, "max": 900},
                },
                "delta": {"pass_rate": "+0.25", "time_seconds": "-5.0", "tokens": "-300"},
            },
            "notes": [],
        }
        md = aggregate_benchmark_module.generate_markdown(benchmark)
        assert "test-skill" in md
        assert "85%" in md
        assert "60%" in md
        assert "+0.25" in md
