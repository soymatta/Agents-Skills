"""Gate: las tablas del README y los conteos de INSTALL.md reflejan el manifiesto.

Clase de bug que previene: agregar/quitar un item en `setup.py:ITEMS` y dejar el
README (tabla de skills/agentes) o el conteo de INSTALL.md desincronizados. El
lector ve una lista incompleta y los numeros dejan de ser ciertos.

Los ids del manifiesto no siempre coinciden con el nombre visible del item
(`jobfinder-skill` se llama `jobfinder` en el README), asi que la comparacion es
por nombre de carpeta/archivo del item, no por id.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SETUP = REPO / "setup.py"

_ROW_NAME = re.compile(r"^\| `([^`]+)`")


@pytest.fixture(scope="module")
def manifest() -> dict:
    out = subprocess.run(
        [sys.executable, str(SETUP), "--manifest"],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(out.stdout)


def _visible_name(item: dict) -> str:
    """Nombre que el README usa para el item: basename de su dir sin extension."""
    return Path(item["src"]).name.removesuffix(".md")


def _table_rows(header_prefix: str) -> list[str]:
    lines = (REPO / "README.md").read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(header_prefix))
    rows: list[str] = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        m = _ROW_NAME.match(line)
        if m:
            rows.append(m.group(1))
    return rows


def test_readme_skills_table_lists_every_skill(manifest):
    rows = set(_table_rows("| Skill | Description | Dependencies"))
    expected = {_visible_name(it) for it in manifest["items"] if it["type"] == "skill"}
    assert rows == expected, f"faltan: {sorted(expected - rows)} | sobran: {sorted(rows - expected)}"


def test_readme_agents_table_lists_every_agent(manifest):
    rows = set(_table_rows("| Agent | Description | Permissions"))
    expected = {_visible_name(it) for it in manifest["items"] if it["type"] == "agent"}
    assert rows == expected, f"faltan: {sorted(expected - rows)} | sobran: {sorted(rows - expected)}"


def test_install_md_counts_match_the_manifest(manifest):
    text = (REPO / "INSTALL.md").read_text(encoding="utf-8")
    counts = manifest["count"]
    m = re.search(
        r"(\d+)\s+agents,\s*(\d+)\s+skills,\s*(\d+)\s+plugins[^,]*,\s*(\d+)\s+slash commands",
        text,
    )
    assert m, "INSTALL.md ya no declara el resumen 'N agents, N skills, ...'"
    agents, skills, plugins, commands = (int(g) for g in m.groups())
    assert (agents, skills, plugins) == (counts["agents"], counts["skills"], counts["plugins"])
    total_commands = sum(len(it["commands"]) for it in manifest["items"])
    assert commands == total_commands, f"INSTALL.md dice {commands}, el manifiesto genera {total_commands}"


def test_readme_names_every_generated_command(manifest):
    """Cada comando que genera setup.py debe nombrarse en el README."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    generated = sorted(
        {Path(cmd).stem for it in manifest["items"] for cmd in it.get("commands", [])}
    )
    missing = [name for name in generated if f"/{name}" not in readme and f"`{name}`" not in readme]
    assert not missing, f"comandos sin nombrar en el README: {missing}"
