"""Tests for the commit-message validator (commit skill)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from validate_commit_msg import MAX_SUBJECT, TYPES, validate  # noqa: E402


def test_all_capitalized_types_are_accepted() -> None:
    for t in TYPES:
        ok, reason = validate(f"{t}: do the thing")
        assert ok, f"{t} rejected: {reason}"


def test_canonical_example_passes() -> None:
    assert validate("Fix: correct login timeout") == (True, "ok")


def test_subject_only_message_passes() -> None:
    assert validate("Feature: add scanner\n")[0] is True


def test_body_after_blank_line_is_ignored_by_validation() -> None:
    msg = "Refactor: extract helper\n\nWhy: it was duplicated three times.\n"
    assert validate(msg)[0] is True


def test_lowercase_type_rejected_with_hint() -> None:
    ok, reason = validate("fix: correct login timeout")
    assert ok is False
    assert "capitalized" in reason


def test_unknown_type_rejected() -> None:
    ok, reason = validate("Update: something")
    assert ok is False
    assert "must match" in reason


def test_missing_colon_rejected() -> None:
    assert validate("Fix correct login timeout")[0] is False


def test_empty_explanation_rejected() -> None:
    assert validate("Fix: ")[0] is False


def test_trailing_period_rejected() -> None:
    ok, reason = validate("Fix: correct login timeout.")
    assert ok is False
    assert "period" in reason


def test_overlong_subject_rejected() -> None:
    ok, reason = validate("Docs: " + ("x" * MAX_SUBJECT))
    assert ok is False
    assert "max" in reason


def test_empty_message_rejected() -> None:
    ok, reason = validate("\n\n# only comments\n# more\n")
    assert ok is False
    assert "empty" in reason


def test_git_generated_merge_subject_allowed() -> None:
    assert validate('Merge branch "main" into "feature"')[0] is True


def test_git_generated_revert_subject_allowed() -> None:
    assert validate('Revert "Fix: correct login timeout"')[0] is True


def test_comment_lines_are_skipped(tmp_path: Path) -> None:
    msg = "# Please enter the commit message\nFix: real subject\n"
    assert validate(msg)[0] is True


def test_husky_hook_template_embeds_absolute_validator() -> None:
    from validate_commit_msg import HOOK_TEMPLATE, install  # noqa: F401

    rendered = HOOK_TEMPLATE.format(validator="/abs/path/validate_commit_msg.py")
    assert "/abs/path/validate_commit_msg.py" in rendered
    assert "python " in rendered
