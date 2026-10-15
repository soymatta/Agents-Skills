"""Tests for check_python_syntax.py — run on every matrix interpreter in CI."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_python_syntax as mod  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_flags_first_party_syntax_error(tmp_path: Path) -> None:
    _write(tmp_path / "setup.py", "x = 1\n")
    _write(tmp_path / "skills" / "good" / "a.py", "def f():\n    return 1\n")
    _write(tmp_path / "skills" / "bad" / "b.py", "def f(:\n")

    failures = mod.check(tmp_path)

    assert [rel for rel, _ in failures] == ["skills/bad/b.py"]


def test_skips_third_party_skills_and_caches(tmp_path: Path) -> None:
    for third_party in ("impeccable", "skill-creator", "ai-job-search"):
        _write(tmp_path / "skills" / third_party / "bad.py", "def f(:\n")
    _write(tmp_path / "__pycache__" / "bad.py", "def f(:\n")
    _write(tmp_path / "node_modules" / "bad.py", "def f(:\n")
    _write(tmp_path / "good.py", "x = 1\n")

    assert mod.check(tmp_path) == []


def test_python_files_excludes_third_party(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "x = 1\n")
    _write(tmp_path / "skills" / "ai-job-search" / "b.py", "x = 1\n")
    _write(tmp_path / "skills" / "commit" / "c.py", "x = 1\n")

    rels = sorted(rel for _, rel in mod.python_files(tmp_path))

    assert rels == ["a.py", "skills/commit/c.py"]


def test_main_returns_zero_when_clean(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "a.py", "x = 1\n")

    assert mod.main(repo=tmp_path) == 0
    assert "OK:" in capsys.readouterr().out


def test_main_returns_one_and_names_the_file(tmp_path: Path, capsys) -> None:
    _write(tmp_path / "broken.py", "def f(:\n")

    assert mod.main(repo=tmp_path) == 1
    out = capsys.readouterr().out
    assert "broken.py" in out
    assert "ERROR" in out
