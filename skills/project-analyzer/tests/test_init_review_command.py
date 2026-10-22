"""Contract tests for the `/init-review` slash command.

The command is prose, but its behavior is checkable: these assertions pin the
two things that used to fail silently.

1. The session cleanup must be **executable**. It used to "suggest" a cleanup that
   nothing ever ran, so the report closed with a paragraph about files that were
   never deleted (and, when only the current session existed, a verbose no-op).
2. The report must **carry the relevant content of previous sessions** (what was
   done, what is pending, decisions, state, next step) before anything is deleted,
   so cleaning up loses nothing.

Each test asserts the wording exists, not that a model chose to follow it: the
regression these guard against is an edit that quietly turns the cleanup back into
a suggestion or drops the inheritance fields from the report.

Run: python -m pytest skills/project-analyzer -q
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

COMMAND = Path(__file__).resolve().parent.parent / "commands" / "init-review.md"
TEXT = COMMAND.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def frontmatter() -> dict:
    return yaml.safe_load(TEXT.split("---", 2)[1])


def test_frontmatter_selects_plan_agent_and_delegates_to_builder(frontmatter):
    """El comando usa `agent: plan` para el escaneo y delega a `builder` en Phase 3."""
    assert frontmatter["agent"] == "plan", "el comando debe usar plan para fases read-only"
    assert isinstance(frontmatter["description"], str)
    assert len(frontmatter["description"]) > 200, "la descripcion explica el comando completo"


def test_read_only_phases_are_a_rule_with_an_approval_gate():
    assert "read-only" in TEXT
    assert "do not edit anything while scanning" in TEXT
    assert "Phase 3" in TEXT and ("this same session" in TEXT or "builder" in TEXT)
    assert re.search(r"(before|once).*(user picks|picks a fix scope)", TEXT), "nada se escribe antes de la respuesta"


def test_uses_the_deterministic_scanner_instead_of_eyeballing():
    assert "scan_project.py" in TEXT
    assert "--format both" in TEXT, "el escaner imprime a stdout, sin escribir archivos"
    assert "no escribe" in TEXT or "writes no files" in TEXT or "writes no files of its own" in TEXT


def test_scan_read_only_claim_is_scoped_to_the_deep_dive_exception():
    """project-analyzer escribe reports/audit-<iso>.json: el comando no puede negarlo."""
    assert "The scan writes no files at all" not in TEXT, "afirmacion falsa al delegar"
    assert "project-analyzer" in TEXT and "reports/audit-" in TEXT


def test_cleanup_is_executable_and_not_a_suggestion():
    assert "Remove-Item" in TEXT, "el comando debe nombrar el borrado real"
    assert "se ejecuta" in TEXT, "la limpieza es un hecho, no una sugerencia"
    assert "se ejecuta aquí" in TEXT or "se ejecuta aqui" in TEXT, "Phase 3 la ejecuta en sesion"
    assert "sugiere" not in TEXT.lower(), "la limpieza ya no es una sugerencia pasiva"


def test_cleanup_asks_once_and_closes_the_loop():
    assert "question" in TEXT, "la confirmacion usa el tool question"
    assert "una sola vez" in TEXT, "no se insiste despues de un no"
    assert re.search(r"borrados? \d+|cuántos archivos", TEXT), "se reporta el conteo real"


def test_current_session_and_tracked_files_are_never_deleted():
    assert "sesión actual nunca se borra" in TEXT
    assert "git ls-files" in TEXT, "la red de seguridad son los archivos versionados"
    for protected in ("AGENTS.md", "roadmap.md", ".roadmap-state"):
        assert protected in TEXT, f"{protected} queda fuera del borrado"


def test_no_previous_sessions_collapses_to_one_line_without_a_question():
    assert "no hay sesiones previas que limpiar" in TEXT
    assert "sin pregunta" in TEXT, "el caso vacio no genera ruido ni pregunta"


def test_report_inherits_the_five_fields_from_previous_sessions():
    for field in ("hecho", "pendiente", "decisiones", "estado", "siguiente paso"):
        assert field in TEXT, f"campo de herencia ausente en el reporte: {field}"
    assert "## Sesiones previas (herencia)" in TEXT


def test_scope_options_and_unconditional_move_to_phase_3_survive():
    for option in ("Aplicar todo", "Solo lo crítico", "Solo estructura", "Solo código", "No hacer nada"):
        assert option in TEXT
    assert "go straight to Phase 3" in TEXT, "tras la respuesta no hay mas escaneo"


def test_only_the_hyphenated_command_name_exists():
    """`init_review.md` era un duplicado obsoleto: una sola variante, con guion.

    Dos archivos con el mismo contenido aterrizan en el mismo sitio al instalar
    (ambos exponen `/init-review` en algunos clientes) y editar uno deja al otro
    desactualizado sin que nadie lo note.
    """
    variants = sorted(p.name for p in COMMAND.parent.glob("init*review.md"))
    assert variants == ["init-review.md"], f"variantes sobrantes: {variants}"
