import json
import os
from pathlib import Path


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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
