import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@pytest.fixture(scope="module")
def collect_module():
    script = Path(__file__).parent.parent / "scripts" / "collect_feedback.py"
    spec = importlib.util.spec_from_file_location("collect_feedback", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def analyze_module():
    script = Path(__file__).parent.parent / "scripts" / "analyze_feedback.py"
    spec = importlib.util.spec_from_file_location("analyze_feedback", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_feedback_json_valid():
    path = Path(__file__).parent.parent / "templates" / "agent-feedback.json"
    data = _load_json(path)
    assert isinstance(data, list)


def test_improvement_log_valid():
    path = Path(__file__).parent.parent / "templates" / "improvement-log.json"
    data = _load_json(path)
    assert isinstance(data, dict)
    assert "total_sessions" in data
    assert "patterns" in data or "summary" in data


def test_session_metrics_valid():
    path = Path(__file__).parent.parent / "templates" / "session-metrics.json"
    data = _load_json(path)
    assert isinstance(data, list)


def test_feedback_roundtrip():
    path = Path(__file__).parent.parent / "templates" / "agent-feedback.json"
    original = _load_json(path)
    entry = {
        "timestamp": "2026-01-01T00:00:00Z",
        "agent": "test-agent",
        "task": "test task",
        "rating": 4,
        "issues": ["minor issue"],
        "suggestions": ["improve x"],
        "tokens_used": 1000,
        "duration_seconds": 30,
    }
    updated = original + [entry]
    _save_json(path, updated)
    loaded = _load_json(path)
    assert len(loaded) == len(original) + 1
    assert loaded[-1]["agent"] == "test-agent"
    _save_json(path, original)


def test_skill_md_exists():
    path = Path(__file__).parent.parent / "SKILL.md"
    assert path.exists()


def test_skill_md_has_frontmatter():
    path = Path(__file__).parent.parent / "SKILL.md"
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "name: agent-self-improver" in content


def test_load_feedback_json_array(collect_module, tmp_path):
    p = tmp_path / "fb.json"
    p.write_text('[{"id": "session-001", "rating": 4}]', encoding="utf-8")
    assert collect_module.load_feedback(p)[0]["id"] == "session-001"


def test_load_feedback_jsonl(collect_module, analyze_module, tmp_path):
    p = tmp_path / "fb.jsonl"
    p.write_text(
        '{"id": "session-001", "rating": 4}\n{"id": "session-002", "rating": 3}\n',
        encoding="utf-8",
    )
    assert len(collect_module.load_feedback(p)) == 2
    assert len(analyze_module.load_feedback(p)) == 2


def test_load_feedback_dict_entries(collect_module, tmp_path):
    p = tmp_path / "fb.json"
    p.write_text('{"entries": [{"id": "session-001"}]}', encoding="utf-8")
    assert collect_module.load_feedback(p)[0]["id"] == "session-001"


def test_collect_output_flag(collect_module, tmp_path):
    out = tmp_path / "custom.json"
    entry = collect_module.create_feedback_entry(
        task="t", rating=3, agent="me", output=out
    )
    assert out.exists()
    assert entry["id"].startswith("session-")
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw[0]["task"] == "t"
    assert raw[0]["id"] == entry["id"]
