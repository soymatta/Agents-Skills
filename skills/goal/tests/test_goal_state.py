"""Tests for the goal skill: goal-state schema and direction-aware logic.

The skill ships no script, so these tests pin the two things it does define:
the schema of ``templates/goal_state_template.json`` and the direction rules in
``SKILL.md`` (success, best_metric, degradation -> revert, budget stop). The
rule checks re-read ``SKILL.md`` so a drift between the doc and this encoding
fails the suite instead of silently diverging.

Run: python -m pytest skills/goal -v
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_DIR / "SKILL.md"
TEMPLATE = SKILL_DIR / "templates" / "goal_state_template.json"

# Schema named in SKILL.md "State file" (the JSON block) and mirrored by the template.
DOCUMENTED_FIELDS = {
    "goal",
    "mode",
    "target",
    "current_metric",
    "best_metric",
    "iterations",
    "achieved",
    "budget",
    "measure_cmd",
    "history",
    "blockers",
    "last_action",
    "approach_tried",
    "approach_ceiling",
}
BUDGET_FIELDS = {"max_iterations", "max_cost", "deadline", "budget_exhausted"}
MODES = {"maximize", "minimize", "exact"}
DEFAULT_MAX_ITERATIONS = 20  # SKILL.md: "default to `max_iterations: 20`"
EXACT_TOLERANCE_FRACTION = 0.01  # SKILL.md: "default tolerance = 1% of target"


def skill_text() -> str:
    """SKILL.md with whitespace collapsed, so line wrapping never breaks a check."""
    return re.sub(r"\s+", " ", SKILL_MD.read_text(encoding="utf-8"))


def load_template() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def succeeded(mode: str, current: float, target: float, tolerance: float | None = None) -> bool:
    """Success rule from SKILL.md 'Direction-aware logic'."""
    if mode == "maximize":
        return current >= target
    if mode == "minimize":
        return current <= target
    if mode == "exact":
        tol = target * EXACT_TOLERANCE_FRACTION if tolerance is None else tolerance
        return abs(current - target) <= tol
    raise ValueError(f"unknown mode: {mode}")


def best_metric(mode: str, best: float | None, current: float, target: float) -> float:
    """best_metric update rule from SKILL.md 'Direction-aware logic'."""
    if best is None:
        return current
    if mode == "maximize":
        return max(best, current)
    if mode == "minimize":
        return min(best, current)
    if mode == "exact":
        return min(best, current, key=lambda value: abs(value - target))
    raise ValueError(f"unknown mode: {mode}")


def degraded(mode: str, current: float, best: float, target: float) -> bool:
    """'Degraded' rule from SKILL.md: moving away from the target vs best_metric."""
    if mode == "maximize":
        return current < best
    if mode == "minimize":
        return current > best
    if mode == "exact":
        return abs(current - target) > abs(best - target)
    raise ValueError(f"unknown mode: {mode}")


def should_revert(mode: str, current: float, best: float, target: float) -> bool:
    """Revert rule: a degraded metric reverts to the last checkpoint."""
    return degraded(mode, current, best, target)


def budget_exhausted(state: dict) -> bool:
    """Budget stop from SKILL.md step 3: flag set, or iterations at the cap."""
    budget = state["budget"]
    return bool(budget["budget_exhausted"]) or state["iterations"] >= budget["max_iterations"]


# --------------------------------------------------------------------------
# Template schema
# --------------------------------------------------------------------------


class TestTemplateSchema:
    def test_template_exists_and_is_valid_json(self) -> None:
        assert TEMPLATE.is_file()
        assert isinstance(load_template(), dict)

    def test_template_has_exactly_the_documented_fields(self) -> None:
        assert set(load_template()) == DOCUMENTED_FIELDS

    def test_budget_has_exactly_the_documented_fields(self) -> None:
        assert set(load_template()["budget"]) == BUDGET_FIELDS

    def test_template_defaults(self) -> None:
        state = load_template()
        assert state["mode"] in MODES
        assert isinstance(state["target"], (int, float))
        assert state["iterations"] == 0
        assert state["achieved"] is False
        assert state["budget"]["budget_exhausted"] is False

    def test_template_default_budget_matches_documented_default(self) -> None:
        assert load_template()["budget"]["max_iterations"] == DEFAULT_MAX_ITERATIONS

    def test_list_fields_default_to_empty(self) -> None:
        state = load_template()
        assert state["history"] == []
        assert state["blockers"] == []
        assert state["approach_tried"] == []


# --------------------------------------------------------------------------
# Invariants the SKILL.md must keep stating
# --------------------------------------------------------------------------


class TestDocumentedInvariants:
    def test_state_file_path_is_documented(self) -> None:
        assert ".opencode/decisions/goal_state.json" in skill_text()

    def test_default_budget_is_documented(self) -> None:
        assert f"max_iterations: {DEFAULT_MAX_ITERATIONS}" in skill_text()

    def test_default_budget_is_only_used_when_the_user_has_no_preference(self) -> None:
        text = skill_text()
        assert "If the user has no preference, default to" in text
        assert "max_iterations: 20" in text

    def test_maximize_rule_is_documented(self) -> None:
        text = skill_text()
        assert "success when `current >= target`" in text
        assert "`best_metric = max(best, current)`" in text

    def test_minimize_rule_is_documented(self) -> None:
        text = skill_text()
        assert "success when `current <= target`" in text
        assert "`best_metric = min(best, current)`" in text

    def test_exact_rule_and_default_tolerance_are_documented(self) -> None:
        text = skill_text()
        assert "within tolerance of `target`" in text
        assert "default tolerance = 1% of target" in text

    def test_degradation_rule_is_documented(self) -> None:
        text = skill_text()
        assert "maximize → current < best" in text
        assert "minimize → current > best" in text
        assert "exact → |current - target| > |best - target|" in text

    def test_revert_and_checkpoint_rules_are_documented(self) -> None:
        text = skill_text()
        assert "revert to last checkpoint" in text
        assert "record a revert checkpoint before each change" in text

    def test_budget_stop_is_documented(self) -> None:
        text = skill_text()
        assert "iterations >= budget.max_iterations" in text
        assert "budget_exhausted=true" in text

    def test_plateau_constant_is_documented(self) -> None:
        assert "3 consecutive flat or failed iterations on the same approach" in skill_text()

    def test_single_scoping_question_rule_is_documented(self) -> None:
        assert "Ask one scoping question up front" in skill_text()


# --------------------------------------------------------------------------
# Direction logic: success
# --------------------------------------------------------------------------


class TestSuccessRule:
    @pytest.mark.parametrize(
        "current, expected",
        [(89.0, False), (90.0, True), (91.0, True)],
    )
    def test_maximize_reaches_upward(self, current: float, expected: bool) -> None:
        assert succeeded("maximize", current, 90.0) is expected

    @pytest.mark.parametrize(
        "current, expected",
        [(121.0, False), (120.0, True), (119.0, True)],
    )
    def test_minimize_reaches_downward(self, current: float, expected: bool) -> None:
        assert succeeded("minimize", current, 120.0) is expected

    def test_exact_uses_default_tolerance(self) -> None:
        target = 1024.0
        tol = target * EXACT_TOLERANCE_FRACTION
        assert succeeded("exact", target, target) is True
        assert succeeded("exact", target + tol - 0.01, target) is True
        assert succeeded("exact", target + tol + 0.01, target) is False

    def test_exact_does_not_accept_arbitrary_offsets(self) -> None:
        assert succeeded("exact", 1100.0, 1024.0) is False

    def test_unknown_mode_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            succeeded("sideways", 1.0, 1.0)


# --------------------------------------------------------------------------
# Direction logic: best_metric
# --------------------------------------------------------------------------


class TestBestMetricRule:
    def test_maximize_keeps_the_maximum(self) -> None:
        assert best_metric("maximize", 87.0, 85.0, 90.0) == 87.0
        assert best_metric("maximize", 87.0, 88.0, 90.0) == 88.0

    def test_minimize_keeps_the_minimum(self) -> None:
        assert best_metric("minimize", 130.0, 135.0, 120.0) == 130.0
        assert best_metric("minimize", 130.0, 125.0, 120.0) == 125.0

    def test_exact_keeps_the_value_closest_to_target(self) -> None:
        # 95 is closer to 100 than 110, so best stays 95 (not max nor min of the two).
        assert best_metric("exact", 95.0, 110.0, 100.0) == 95.0
        assert best_metric("exact", 110.0, 102.0, 100.0) == 102.0

    def test_first_measurement_seeds_best(self) -> None:
        assert best_metric("maximize", None, 84.0, 90.0) == 84.0


# --------------------------------------------------------------------------
# Direction logic: degradation -> revert
# --------------------------------------------------------------------------


class TestDegradationRule:
    def test_maximize_degrades_when_below_best(self) -> None:
        assert degraded("maximize", 81.0, 87.0, 90.0) is True
        assert degraded("maximize", 88.0, 87.0, 90.0) is False

    def test_minimize_degrades_when_above_best(self) -> None:
        assert degraded("minimize", 140.0, 130.0, 120.0) is True
        assert degraded("minimize", 125.0, 130.0, 120.0) is False

    def test_exact_degrades_when_further_from_target(self) -> None:
        assert degraded("exact", 110.0, 95.0, 100.0) is True
        assert degraded("exact", 102.0, 110.0, 100.0) is False

    def test_degradation_triggers_revert(self) -> None:
        assert should_revert("maximize", 81.0, 87.0, 90.0) is True
        assert should_revert("minimize", 125.0, 130.0, 120.0) is False
        assert should_revert("exact", 110.0, 95.0, 100.0) is True


# --------------------------------------------------------------------------
# Budget stop
# --------------------------------------------------------------------------


class TestBudgetStop:
    def test_not_exhausted_under_the_cap(self) -> None:
        state = load_template()
        state["iterations"] = DEFAULT_MAX_ITERATIONS - 1
        assert budget_exhausted(state) is False

    def test_exhausted_at_the_iteration_cap(self) -> None:
        state = load_template()
        state["iterations"] = DEFAULT_MAX_ITERATIONS
        assert budget_exhausted(state) is True

    def test_explicit_flag_short_circuits(self) -> None:
        state = load_template()
        state["iterations"] = 1
        state["budget"]["budget_exhausted"] = True
        assert budget_exhausted(state) is True
