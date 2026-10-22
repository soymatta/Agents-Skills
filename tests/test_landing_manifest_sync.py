"""Gate: la landing de Astro lista exactamente los items del manifiesto.

Clase de bug que previene: agregar un agente/skill/plugin en `setup.py:ITEMS` y
dejar `web/src/pages/index.astro` atras. La landing es la cara publica del repo:
si omite un agente, el lector cree que no existe y el conteo de la propia pagina
queda mal. Se comparan los nombres (basename del src), no los ids, porque el
manifiesto y la landing usan el nombre visible.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SETUP = REPO / "setup.py"
LANDING = REPO / "web" / "src" / "pages" / "index.astro"

_ARRAY = {
    "agents": re.compile(r"const agents = \[(.*?)\n\];", re.DOTALL),
    "skills": re.compile(r"const skills = \[(.*?)\n\];", re.DOTALL),
    "plugins": re.compile(r"const plugins = \[(.*?)\n\];", re.DOTALL),
}
_NAME = re.compile(r'name:\s*"([^"]+)"')


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


def _landing_names(kind: str) -> list[str]:
    source = LANDING.read_text(encoding="utf-8")
    match = _ARRAY[kind].search(source)
    assert match, f"no se encontro el arreglo '{kind}' en index.astro"
    return _NAME.findall(match.group(1))


def _manifest_names(manifest: dict, kind: str) -> set[str]:
    singular = kind[:-1]
    return {
        Path(item["src"]).name.removesuffix(".md")
        for item in manifest["items"]
        if item["type"] == singular
    }


@pytest.mark.parametrize("kind", ["agents", "skills", "plugins"])
def test_landing_matches_manifest(manifest, kind):
    landing = _landing_names(kind)
    assert len(landing) == len(set(landing)), f"nombres duplicados en la landing: {kind}"
    expected = _manifest_names(manifest, kind)
    assert set(landing) == expected, (
        f"la landing y el manifiesto difieren en {kind}: "
        f"faltan {sorted(expected - set(landing))}, "
        f"sobran {sorted(set(landing) - expected)}"
    )
