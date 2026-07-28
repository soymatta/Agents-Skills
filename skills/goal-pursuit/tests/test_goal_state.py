"""Tests for goal-pursuit goal_state_template.json schema."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "goal_state_template.json"


class TestGoalStateTemplateExists:
    def test_template_file_exists(self):
        assert TEMPLATE_PATH.exists(), f"Template not found at {TEMPLATE_PATH}"

    def test_template_is_valid_json(self):
        content = TEMPLATE_PATH.read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, dict)


class TestGoalStateRequiredKeys:
    def test_all_required_keys_present(self, goal_state_template, goal_state_schema):
        for key in goal_state_schema["required_keys"]:
            assert key in goal_state_template, f"Missing required key: {key}"

    def test_no_extra_keys_beyond_expected(self, goal_state_template, goal_state_schema):
        unexpected = set(goal_state_template.keys()) - goal_state_schema["required_keys"]
        assert not unexpected, f"Unexpected keys: {unexpected}"

    def test_goal_is_string(self, goal_state_template):
        assert isinstance(goal_state_template["goal"], str)

    def test_goal_not_empty(self, goal_state_template):
        assert len(goal_state_template["goal"]) > 0


class TestGoalStateFieldTypes:
    def test_target_is_numeric(self, goal_state_template, goal_state_schema):
        assert goal_state_template["target"] is None or isinstance(
            goal_state_template["target"], (int, float)
        )

    def test_current_metric_is_none_or_number(self, goal_state_template):
        val = goal_state_template["current_metric"]
        assert val is None or isinstance(val, (int, float))

    def test_best_metric_is_none_or_number(self, goal_state_template):
        val = goal_state_template["best_metric"]
        assert val is None or isinstance(val, (int, float))

    def test_iterations_is_int(self, goal_state_template):
        assert isinstance(goal_state_template["iterations"], int)

    def test_iterations_non_negative(self, goal_state_template):
        assert goal_state_template["iterations"] >= 0

    def test_achieved_is_boolean(self, goal_state_template):
        assert isinstance(goal_state_template["achieved"], bool)

    def test_history_is_list(self, goal_state_template):
        assert isinstance(goal_state_template["history"], list)

    def test_blockers_is_list(self, goal_state_template):
        assert isinstance(goal_state_template["blockers"], list)

    def test_last_action_is_none_or_string(self, goal_state_template):
        val = goal_state_template["last_action"]
        assert val is None or isinstance(val, str)

    def test_approach_tried_is_list(self, goal_state_template):
        assert isinstance(goal_state_template["approach_tried"], list)

    def test_approach_ceiling_is_none_or_number(self, goal_state_template):
        val = goal_state_template["approach_ceiling"]
        assert val is None or isinstance(val, (int, float))


class TestGoalStateDefaults:
    def test_achieved_defaults_false(self, goal_state_template):
        assert goal_state_template["achieved"] is False

    def test_iterations_starts_at_zero(self, goal_state_template):
        assert goal_state_template["iterations"] == 0

    def test_history_starts_empty(self, goal_state_template):
        assert goal_state_template["history"] == []

    def test_blockers_starts_empty(self, goal_state_template):
        assert goal_state_template["blockers"] == []

    def test_approach_tried_starts_empty(self, goal_state_template):
        assert goal_state_template["approach_tried"] == []

    def test_current_metric_starts_none(self, goal_state_template):
        assert goal_state_template["current_metric"] is None

    def test_best_metric_starts_none(self, goal_state_template):
        assert goal_state_template["best_metric"] is None

    def test_last_action_starts_none(self, goal_state_template):
        assert goal_state_template["last_action"] is None

    def test_approach_ceiling_starts_none(self, goal_state_template):
        assert goal_state_template["approach_ceiling"] is None


class TestGoalStateMutation:
    def test_template_can_be_deep_copied(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        assert copy == goal_state_template
        copy["achieved"] = True
        assert goal_state_template["achieved"] is False

    def test_increment_iterations(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        copy["iterations"] += 1
        assert copy["iterations"] == 1

    def test_append_to_history(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        copy["history"].append({"iteration": 1, "metric": 0.85})
        assert len(copy["history"]) == 1
        assert copy["history"][0]["iteration"] == 1

    def test_update_current_metric(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        copy["current_metric"] = 0.85
        copy["best_metric"] = 0.85
        assert copy["current_metric"] == 0.85
        assert copy["best_metric"] == 0.85

    def test_add_blocker(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        copy["blockers"].append("Overfitting on validation set")
        assert len(copy["blockers"]) == 1

    def test_set_achieved(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        copy["achieved"] = True
        assert copy["achieved"] is True

    def test_serialize_roundtrip(self, goal_state_template):
        serialized = json.dumps(goal_state_template, ensure_ascii=False)
        deserialized = json.loads(serialized)
        assert deserialized == goal_state_template


class TestGoalStateEdgeCases:
    def test_negative_target(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        copy["target"] = -10.0
        assert copy["target"] == -10.0

    def test_zero_target(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        copy["target"] = 0
        assert copy["target"] == 0

    def test_very_large_iterations(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        copy["iterations"] = 1000000
        assert copy["iterations"] == 1000000

    def test_unicode_goal_text(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        copy["goal"] = "Alcanzar 92% de precision en validacion"
        assert "precision" in copy["goal"]

    def test_many_blockers(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        copy["blockers"] = [f"blocker_{i}" for i in range(50)]
        assert len(copy["blockers"]) == 50

    def test_many_approaches_tried(self, goal_state_template):
        copy = deepcopy(goal_state_template)
        copy["approach_tried"] = [f"approach_{i}" for i in range(20)]
        assert len(copy["approach_tried"]) == 20
