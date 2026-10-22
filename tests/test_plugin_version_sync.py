"""Gate: la version de cada plugin es una sola, no dos.

Clase de bug que previene: `package.json` y `package-lock.json` declaran la
version del paquete en dos sitios. Cuando divergen (paso de verdad:
`opencode-auto-session` decia 1.0.0 en package.json y 2.0.0 en el lock), el
paquete publicado y el lock que instala CI no son el mismo artefacto, y el
numero que ve el usuario deja de ser cierto.

El repo no tiene 13 puntos de version como el caso que inspiro esta regla: tiene
los que existan por plugin. El gate cubre todos los que encuentre, sin lista
hardcodeada.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PLUGIN_LOCKS = sorted(REPO.glob("plugins/*/package-lock.json"))


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_at_least_one_plugin_lock_is_covered():
    """Si el glob deja de encontrar locks, el gate no debe pasar en silencio."""
    assert PLUGIN_LOCKS, "no se encontro ningun plugins/*/package-lock.json"


@pytest.mark.parametrize("lock_path", PLUGIN_LOCKS, ids=lambda p: p.parent.name)
def test_package_json_and_lock_agree(lock_path: Path):
    manifest_path = lock_path.parent / "package.json"
    assert manifest_path.is_file(), f"falta {manifest_path} junto al lock"
    manifest = _load(manifest_path)
    lock = _load(lock_path)

    root = lock.get("packages", {}).get("")
    assert root is not None, f"{lock_path} no tiene la entrada packages['']"

    assert manifest["version"] == root.get("version"), (
        f"{manifest_path.name} dice {manifest['version']!r} y {lock_path.name} "
        f"dice {root.get('version')!r}"
    )
    assert manifest.get("name") == lock.get("name"), (
        f"{manifest_path.name} y {lock_path.name} declaran nombres distintos"
    )
