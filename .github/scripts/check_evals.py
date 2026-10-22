"""Validate every first-party skill eval set so it can actually be executed.

Running the evals themselves needs ``claude -p`` plus an API key, so that stays a
manual step (see ``skills/skill-creator``). What CI can and must prove is the
shape: every ``evals.json`` loads, is named after its skill, and carries
assertions a run can fail on. An eval with no ``expectations`` is a test that can
never fail — 39 KB of files that only look like coverage.

Rules enforced for ``skills/<name>/evals/evals.json``:
    - top-level object with exactly ``skill_name`` and ``evals``,
    - ``skill_name`` equals the skill directory name,
    - ``evals`` is a non-empty list,
    - each eval has ``id`` (unique), non-empty ``prompt``, non-empty
      ``expected_output``, and a non-empty list of non-empty ``expectations``,
    - ``files``, when present, is a list.

Other ``*.json`` files in an ``evals/`` directory (e.g. ``command_tests.json``)
are only required to be valid, non-empty JSON.

Scope: first-party skills only. Vendored third-party skills are skipped so
upstream content never gates this build, mirroring ``check_python_syntax.py``.

Exit 1 on any violation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

THIRD_PARTY_SKILLS = {"impeccable", "skill-creator", "ai-job-search", "web-design-guidelines"}
REQUIRED_EVAL_FIELDS = ("id", "prompt", "expected_output", "expectations")
ALLOWED_TOP_LEVEL = {"skill_name", "evals"}


def _check_evals_file(rel: str, skill: str, data: object, errors: list[str]) -> None:
    if not isinstance(data, dict):
        errors.append(f"{rel}: top level must be an object, got {type(data).__name__}")
        return
    extra = set(data) - ALLOWED_TOP_LEVEL
    if extra:
        errors.append(f"{rel}: unknown top-level key(s) {sorted(extra)}")
    if data.get("skill_name") != skill:
        errors.append(
            f"{rel}: skill_name is {data.get('skill_name')!r}, expected {skill!r}"
        )
    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        errors.append(f"{rel}: 'evals' must be a non-empty list")
        return

    seen_ids: set[object] = set()
    for index, item in enumerate(evals):
        where = f"{rel}: evals[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: must be an object")
            continue
        missing = [field for field in REQUIRED_EVAL_FIELDS if field not in item]
        if missing:
            errors.append(f"{where}: missing {missing}")
        eval_id = item.get("id")
        if eval_id is None:
            errors.append(f"{where}: 'id' is null")
        elif eval_id in seen_ids:
            errors.append(f"{where}: duplicate id {eval_id!r}")
        else:
            seen_ids.add(eval_id)
        for field in ("prompt", "expected_output"):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{where}: '{field}' must be a non-empty string")
        expectations = item.get("expectations")
        if not isinstance(expectations, list) or not expectations:
            errors.append(f"{where}: 'expectations' must be a non-empty list")
        else:
            for pos, expectation in enumerate(expectations):
                if not isinstance(expectation, str) or not expectation.strip():
                    errors.append(f"{where}: expectations[{pos}] must be a non-empty string")
        if "files" in item and not isinstance(item["files"], list):
            errors.append(f"{where}: 'files' must be a list when present")


def check(repo: Path) -> tuple[list[str], int, int]:
    """Return (errors, files_checked, skills_skipped)."""
    errors: list[str] = []
    checked = 0
    skipped = 0
    for evals_dir in sorted((repo / "skills").glob("*/evals")):
        if not evals_dir.is_dir():
            continue
        skill = evals_dir.parent.name
        if skill in THIRD_PARTY_SKILLS:
            skipped += 1
            continue
        for path in sorted(evals_dir.glob("*.json")):
            rel = path.relative_to(repo).as_posix()
            checked += 1
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{rel}: unreadable JSON ({exc})")
                continue
            if path.name != "evals.json":
                if not data:
                    errors.append(f"{rel}: file is empty")
                continue
            _check_evals_file(rel, skill, data, errors)
    return errors, checked, skipped


def main(repo: Path | None = None) -> int:
    repo = repo or Path(__file__).resolve().parents[2]
    errors, checked, skipped = check(repo)
    if errors:
        print(f"ERROR: {len(errors)} eval-set problem(s):")
        for error in errors:
            print(f"  - {error}")
        return 1
    note = f", {skipped} third-party skill(s) skipped" if skipped else ""
    print(f"OK: {checked} eval file(s) well-formed{note}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
