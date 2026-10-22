"""Regression tests for the doc-vs-code coherence gate.

Guards a false positive: `_resolve` compared basenames against first-party
scripts only, so a doc that pointed at a vendored third-party script by its
real path was reported as unresolved drift even though the file exists.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
GATE = REPO / ".github" / "scripts" / "check_doc_code_coherence.py"


@pytest.fixture(scope="module")
def gate():
    spec = importlib.util.spec_from_file_location("coherence_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_accepts_existing_third_party_path(gate):
    """A precise repo-relative path to a vendored script is not drift."""
    token = "skills/impeccable/scripts/detect.mjs"
    assert (REPO / token).is_file(), "fixture path moved; update the test"
    assert gate._resolve(REPO, token) is True


def test_resolve_accepts_first_party_basename(gate):
    assert gate._resolve(REPO, "skills/roadmaps/scripts/validate_roadmap.py") is True


def test_resolve_rejects_unknown_script(gate):
    assert gate._resolve(REPO, "scripts/definitely-not-a-real-script.py") is False


def test_gate_is_green_on_this_repo(gate):
    assert gate.main() == 0


# ── regla del prefijo skills/ ─────────────────────────────────────────────────


def _fake_repo(tmp_path: Path, doc_text: str) -> Path:
    """Repo minimo con un skill dueño de `scripts/references.py` y su doc."""
    scripts = tmp_path / "skills" / "citation-formatter" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "references.py").write_text("", "utf-8")
    skill = tmp_path / "skills" / "citador"
    skill.mkdir()
    (skill / "SKILL.md").write_text(doc_text, "utf-8")
    (tmp_path / "agents").mkdir()
    return tmp_path


def test_unprefixed_skill_path_is_reported(gate, tmp_path):
    """`citation-formatter/scripts/x.py` se lee desde la raiz: debe llevar skills/."""
    repo = _fake_repo(tmp_path, "Corre `citation-formatter/scripts/references.py`.\n")
    found = gate._missing_skills_prefix(repo)
    assert found, "la ruta sin prefijo debe reportarse"
    assert found[0][0] == "citation-formatter/scripts/references.py"


def test_prefixed_skill_path_is_accepted(gate, tmp_path):
    repo = _fake_repo(tmp_path, "Corre `skills/citation-formatter/scripts/references.py`.\n")
    assert gate._missing_skills_prefix(repo) == []


def test_this_repo_has_no_unprefixed_script_paths(gate):
    """Regresion: academic-source-search citaba el script sin el prefijo skills/."""
    assert gate._missing_skills_prefix(REPO) == []


# ── rutas .md en docs y docstrings de scripts ─────────────────────────────────


def test_missing_md_path_in_docstring_is_reported(gate, tmp_path):
    """El bug real: un docstring citaba skills/backtest-expert/references/*.md."""
    repo = _fake_repo(tmp_path, "# Doc\n")
    scripts = repo / "skills" / "backtest-validate" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "evaluate_backtest.py").write_text(
        '"""Methodology from skills/backtest-expert/references/methodology.md."""\n',
        "utf-8",
    )
    found = gate._missing_md_paths(repo)
    assert found, "una ruta .md inexistente en un docstring debe reportarse"
    assert found[0][0] == "skills/backtest-expert/references/methodology.md"


def test_existing_md_path_in_docstring_is_accepted(gate, tmp_path):
    repo = _fake_repo(tmp_path, "# Doc\n")
    target = repo / "skills" / "backtest-validate" / "SKILL.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Skill\n", "utf-8")
    scripts = target.parent / "scripts"
    scripts.mkdir()
    (scripts / "run.py").write_text(
        '"""Thresholds are specified in skills/backtest-validate/SKILL.md."""\n',
        "utf-8",
    )
    assert gate._missing_md_paths(repo) == []


def test_missing_md_path_in_markdown_is_reported(gate, tmp_path):
    repo = _fake_repo(tmp_path, "Lee `skills/ghost/references/guide.md` antes de seguir.\n")
    found = gate._missing_md_paths(repo)
    assert found and found[0][0] == "skills/ghost/references/guide.md"


def test_user_project_md_paths_are_ignored(gate, tmp_path):
    """Ejemplos del proyecto del usuario no son promesas de este repo."""
    repo = _fake_repo(
        tmp_path,
        "Guarda en `path/to/note.md` y lee `research/YYYY-MM-DD-topic.md`.\n",
    )
    assert gate._missing_md_paths(repo) == []


def test_single_letter_segments_are_placeholders(gate, tmp_path):
    """`a/b.py` es un ejemplo de JSON, no una ruta del repo."""
    repo = _fake_repo(tmp_path, "Ejemplo: `a/b.py`.\n")
    assert gate._prose_script_tokens(repo) == []


def test_this_repo_has_no_missing_md_paths(gate):
    assert gate._missing_md_paths(REPO) == []
