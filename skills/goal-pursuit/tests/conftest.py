"""Test fixtures for goal-pursuit goal state schema."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def goal_state_template():
    """Load goal_state_template.json as a dict."""
    template_path = (
        Path(__file__).resolve().parents[1] / "templates" / "goal_state_template.json"
    )
    return json.loads(template_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def goal_state_schema():
    """Return the expected field definitions for goal state validation."""
    return {
        "required_keys": {
            "goal",
            "target",
            "current_metric",
            "best_metric",
            "iterations",
            "achieved",
            "history",
            "blockers",
            "last_action",
            "approach_tried",
            "approach_ceiling",
        },
        "boolean_fields": {"achieved"},
        "list_fields": {"history", "blockers", "approach_tried"},
        "numeric_fields": {"target", "iterations", "approach_ceiling"},
    }
