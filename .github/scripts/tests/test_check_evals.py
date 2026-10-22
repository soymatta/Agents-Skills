"""Regression tests for the eval-set schema gate.

The gate exists because the LLM eval run cannot happen in CI (it needs
``claude -p`` and a key). The failure mode it prevents is silent: an
``evals.json`` with empty expectations validates as JSON and can never fail.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
GATE = REPO / ".github" / "scripts" / "check_evals.py"


@pytest.fixture(scope="module")
def gate():
    spec = importlib.util.spec_from_file_location("evals_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_evals(tmp_path: Path, data, skill: str = "demo", name: str = "evals.json") -> Path:
    target = tmp_path / "skills" / skill / "evals" / name
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


def _valid() -> dict:
    return {
        "skill_name": "demo",
        "evals": [
            {
                "id": 0,
                "prompt": "do the thing",
                "expected_output": "the thing is done",
                "expectations": ["it is done correctly"],
            }
        ],
    }


def test_gate_is_green_on_this_repo(gate):
    assert gate.main() == 0


def test_valid_minimal_set_passes(gate, tmp_path: Path):
    assert gate.main(_write_evals(tmp_path, _valid())) == 0


def test_missing_expectations_fails(gate, tmp_path: Path):
    data = _valid()
    del data["evals"][0]["expectations"]
    assert gate.main(_write_evals(tmp_path, data)) == 1


def test_empty_expectations_fails(gate, tmp_path: Path):
    data = _valid()
    data["evals"][0]["expectations"] = []
    assert gate.main(_write_evals(tmp_path, data)) == 1


def test_blank_expectation_fails(gate, tmp_path: Path):
    data = _valid()
    data["evals"][0]["expectations"] = ["   "]
    assert gate.main(_write_evals(tmp_path, data)) == 1


def test_skill_name_mismatch_fails(gate, tmp_path: Path):
    data = _valid()
    data["skill_name"] = "other-skill"
    assert gate.main(_write_evals(tmp_path, data)) == 1


def test_empty_evals_list_fails(gate, tmp_path: Path):
    data = _valid()
    data["evals"] = []
    assert gate.main(_write_evals(tmp_path, data)) == 1


def test_duplicate_id_fails(gate, tmp_path: Path):
    data = _valid()
    data["evals"].append(dict(data["evals"][0]))
    assert gate.main(_write_evals(tmp_path, data)) == 1


def test_unknown_top_level_key_fails(gate, tmp_path: Path):
    data = _valid()
    data["expectations"] = ["typo at the wrong level"]
    assert gate.main(_write_evals(tmp_path, data)) == 1


def test_malformed_json_fails(gate, tmp_path: Path):
    target = tmp_path / "skills" / "demo" / "evals" / "evals.json"
    target.parent.mkdir(parents=True)
    target.write_text("{not json", encoding="utf-8")
    assert gate.main(tmp_path) == 1


def test_other_eval_json_only_needs_to_parse(gate, tmp_path: Path):
    # Valid list-shaped sidecar (e.g. ui-ux-orchestrator's command_tests.json).
    assert gate.main(_write_evals(tmp_path, [{"prompt": "x"}], name="command_tests.json")) == 0


def test_sidecar_empty_fails(gate, tmp_path: Path):
    assert gate.main(_write_evals(tmp_path, [], name="command_tests.json")) == 1


def test_third_party_skill_is_skipped(gate, tmp_path: Path):
    # Broken JSON in a vendored skill must not gate this build.
    target = tmp_path / "skills" / "skill-creator" / "evals" / "evals.json"
    target.parent.mkdir(parents=True)
    target.write_text("{broken", encoding="utf-8")
    assert gate.main(tmp_path) == 0


def test_check_counts_skipped_skills(gate, tmp_path: Path):
    _write_evals(tmp_path, _valid())
    _write_evals(tmp_path, _valid(), skill="skill-creator")
    errors, checked, skipped = gate.check(tmp_path)
    assert errors == []
    assert checked == 1
    assert skipped == 1
