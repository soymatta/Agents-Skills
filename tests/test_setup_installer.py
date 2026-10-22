"""Tests del instalador (setup.py): flag --only, assets de plugins y comandos generados.

Cubre lo que no cubre ningun otro suite: que una instalacion dirigida
(--only) copie solo lo pedido y NUNCA borre items ajenos, que los
archivos auxiliares del plugin (`files`) aterricen en plugins/<id>/, y que
los comandos de una skill third-party sin .md propios (impeccable) se generen
desde su tabla de metadata y se puedan desinstalar.

Ejecutar: python -m pytest tests -q
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_setup():
    spec = importlib.util.spec_from_file_location("_installer", REPO_ROOT / "setup.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["_installer"] = module
    spec.loader.exec_module(module)
    return module


setup = _load_setup()
PLUGIN_ID = "opencode-auto-session"
OTHER_PLUGIN_ID = "opencode-tui-queue"


@pytest.fixture()
def dest(tmp_path: Path) -> dict[str, Path]:
    skills = tmp_path / "skills"
    agents = tmp_path / "agent"
    plugins = tmp_path / "plugins"
    skills.mkdir()
    agents.mkdir()
    plugins.mkdir()
    return {"skills": skills, "agents": agents, "plugins": plugins}


def _run(dest: dict[str, Path], toggled: dict[str, bool], only: set[str] | None) -> None:
    setup.install_items(
        toggled,
        REPO_ROOT,
        dest["skills"],
        dest["agents"],
        plugins_dir=dest["plugins"],
        platform_id="opencode",
        only=only,
    )


def test_manifest_has_three_plugins_and_the_new_item():
    plugins = {it["id"] for it in setup.ITEMS if it["type"] == "plugin"}
    assert plugins == {"opencode-telegram-answers", "opencode-tui-queue", PLUGIN_ID}
    item = setup._item_by_id(PLUGIN_ID)
    assert item is not None
    assert item["entry"] == "autosession.ts"
    assert item.get("commands") == ["autosession.md"], (
        "el comando viaja con el plugin: /autosession solo llega al hook "
        "command.execute.before si el .md esta en el registro de comandos"
    )
    assert (REPO_ROOT / item["dir"] / "commands" / "autosession.md").is_file()
    assert item["files"] == ["limit-notify.ps1", "limit-notify.sh"]
    for asset in item["files"]:
        assert (REPO_ROOT / item["dir"] / asset).is_file(), (
            f"{asset} debe estar en el repo o el instalador avisa 'asset not found'"
        )


def test_only_installs_entry_and_asset(dest):
    toggled = {it["id"]: it["id"] == PLUGIN_ID for it in setup.ITEMS}
    _run(dest, toggled, {PLUGIN_ID})

    entry = dest["plugins"] / f"{PLUGIN_ID}.ts"
    assert entry.is_file(), "el entry .ts debe instalarse"
    assert "notifyScriptFor" in entry.read_text("utf-8")

    ps1 = dest["plugins"] / PLUGIN_ID / "limit-notify.ps1"
    assert ps1.is_file(), "el asset vive en plugins/<id>/"
    assert "LIMITE GRATIS ALCANZADO" in ps1.read_text("utf-8")

    sh = dest["plugins"] / PLUGIN_ID / "limit-notify.sh"
    assert sh.is_file(), "el script de Linux/macOS tambien se instala"
    assert "LIMITE GRATIS ALCANZADO" in sh.read_text("utf-8")


def test_only_never_removes_foreign_items(dest):
    """Regresion: --only no debe borrar plugins/skills de otros items."""
    foreign_plugin = dest["plugins"] / f"{OTHER_PLUGIN_ID}.ts"
    foreign_plugin.write_text("// plugin ajeno", "utf-8")
    foreign_skill = dest["skills"] / "osint"
    foreign_skill.mkdir()
    (foreign_skill / "SKILL.md").write_text("x", "utf-8")

    toggled = {it["id"]: it["id"] == PLUGIN_ID for it in setup.ITEMS}
    _run(dest, toggled, {PLUGIN_ID})

    assert foreign_plugin.is_file(), "plugin ajeno intacto"
    assert foreign_skill.is_dir(), "skill ajena intacta"


def test_without_only_disabled_items_are_removed(dest):
    """Documenta la semantica normal: desactivado = se borra del destino."""
    stale = dest["plugins"] / f"{OTHER_PLUGIN_ID}.ts"
    stale.write_text("// viejo", "utf-8")

    toggled = {it["id"]: it["id"] == PLUGIN_ID for it in setup.ITEMS}
    _run(dest, toggled, None)

    assert not stale.exists(), "sin --only la desactivacion borra"
    assert (dest["plugins"] / f"{PLUGIN_ID}.ts").is_file()


def test_disabling_a_plugin_leaves_nothing_behind(dest):
    """Pinea la semantica: desactivar un plugin limpia entry, assets y comando.

    Los assets de runtime viven en plugins/<id>/ (fuera del autoload de los .ts
    planos); si esa carpeta sobrevive, el usuario ve limit-notify.sh huerfano en
    su config aunque el plugin ya no exista.
    """
    only = {PLUGIN_ID}
    _run(dest, {it["id"]: it["id"] in only for it in setup.ITEMS}, only)
    assert (dest["plugins"] / PLUGIN_ID / "limit-notify.sh").is_file()

    _run(dest, {it["id"]: False for it in setup.ITEMS}, only)

    assert not (dest["plugins"] / f"{PLUGIN_ID}.ts").exists(), "el entry .ts se retira"
    assert not (dest["plugins"] / PLUGIN_ID).exists(), "plugins/<id>/ completo se retira"
    assert not (dest["skills"].parent / "commands" / "autosession.md").exists(), (
        "el comando que viaja con el plugin tambien se retira"
    )


def test_jobfinder_agent_locks_its_skill():
    """El agente jobfinder declara su skill como dependencia (regresion).

    Antes llevaba los archivos del skill solo en `bundles` y con `dependencies`
    vacio: el menu dejaba apagar el skill con el agente encendido (sin lock) y la
    rama de desactivacion del skill borraba los scripts que el agente necesitaba.
    """
    item = setup._item_by_id("jobfinder")
    assert item is not None and item["type"] == "agent"
    assert "jobfinder-skill" in item.get("dependencies", [])

    toggled = {it["id"]: it["id"] in {"jobfinder", "jobfinder-skill"} for it in setup.ITEMS}
    assert setup._is_locked("jobfinder-skill", toggled), "con el agente ON el skill queda bloqueado"

    toggled_off = {it["id"]: it["id"] in {"jobfinder", "jobfinder-skill"} for it in setup.ITEMS}
    setup._propagate_toggle("jobfinder", False, toggled_off)
    assert toggled_off["jobfinder-skill"] is False, "apagar el agente apaga su skill"


def test_only_unknown_id_is_not_silently_installed(dest):
    toggled = {it["id"]: False for it in setup.ITEMS}
    toggled["no-existe"] = True
    _run(dest, toggled, {"no-existe"})
    assert not any(dest["plugins"].iterdir()), "id desconocido no instala nada"


# ── --check: verificación sin escritura ────────────────────────────────────────


def _check(dest: dict[str, Path]) -> int:
    return setup.check_installed(
        REPO_ROOT, dest["skills"], dest["agents"], dest["plugins"], "opencode"
    )


def test_check_is_clean_after_a_full_install(dest):
    _run(dest, {it["id"]: True for it in setup.ITEMS}, None)
    assert _check(dest) == 0, "una instalacion recien hecha no debe tener drift"


def test_check_reports_a_stale_installed_file(dest, capsys):
    """El caso real: el repo avanzo despues de instalar y la copia quedo vieja."""
    _run(dest, {it["id"]: it["id"] == "goal" for it in setup.ITEMS}, {"goal"})
    (dest["skills"] / "goal" / "SKILL.md").write_text("editado a mano", "utf-8")

    assert _check(dest) > 0
    assert "goal: stale SKILL.md" in capsys.readouterr().out


def test_check_reports_missing_items(dest):
    assert _check(dest) > 0, "un destino vacio tiene todo faltante"


def test_check_notes_foreign_skill_without_failing(dest, capsys):
    """Un skill ajeno en el destino se informa, pero no es drift del manifiesto."""
    _run(dest, {it["id"]: True for it in setup.ITEMS}, None)
    (dest["skills"] / "skill-de-otro").mkdir()

    assert _check(dest) == 0
    assert "skill-de-otro" in capsys.readouterr().out


# ── comandos generados (impeccable) ───────────────────────────────────────────

IMPECCABLE_ID = "impeccable"


def _metadata_table(item: dict) -> dict:
    return json.loads(
        (REPO_ROOT / item["dir"] / item["generate_commands"]["metadata"]).read_text("utf-8")
    )


def test_impeccable_generates_one_command_per_vendor_entry():
    item = setup._item_by_id(IMPECCABLE_ID)
    assert item is not None
    table = _metadata_table(item)
    assert len(table) == 23, "la tabla del vendor es la fuente de los 23 comandos"

    prefix = item["generate_commands"]["prefix"]
    generated = setup._generated_commands(REPO_ROOT, item)
    assert [name for name, _ in generated] == [f"{prefix}{cmd}.md" for cmd in table]

    for name, content in generated:
        command = name[len(prefix) : -len(".md")]
        assert content.startswith("---\ndescription: \"")
        assert content.count("\n---\n") == 1, "frontmatter cerrado y sin segundos bloques"
        assert "$ARGUMENTS" in content, "el comando pasa los argumentos al skill"
        assert f"`{command}`" in content, "el template nombra el sub-comando del vendor"


def test_impeccable_commands_do_not_shadow_builtins_or_house_commands():
    item = setup._item_by_id(IMPECCABLE_ID)
    names = set(setup._item_command_names(REPO_ROOT, item))
    reserved = {"init.md", "help.md", "undo.md", "redo.md", "models.md", "editor.md"}
    reserved |= {cmd for other in setup.ITEMS for cmd in other.get("commands", [])}
    assert reserved.isdisjoint(names), f"colision de comandos: {sorted(reserved & names)}"


def test_impeccable_commands_install_and_uninstall(dest):
    cmds = dest["skills"].parent / "commands"
    foreign = cmds / "custom-thing.md"  # not owned by any item in the manifest
    cmds.mkdir()
    foreign.write_text("# ajeno", "utf-8")

    only = {IMPECCABLE_ID}
    toggled = {it["id"]: it["id"] in only for it in setup.ITEMS}
    _run(dest, toggled, only)

    audit = cmds / "impeccable-audit.md"
    assert audit.is_file(), "el comando generado llega a <config>/commands/"
    text = audit.read_text("utf-8")
    assert 'description: "' in text
    assert "`audit`" in text and "$ARGUMENTS" in text
    assert (dest["skills"] / "impeccable" / "SKILL.md").is_file(), "la skill sigue instalada"
    assert foreign.is_file(), "--only no borra comandos ajenos"

    # semantica normal (sin --only): desactivar el item retira sus comandos
    _run(dest, {it["id"]: False for it in setup.ITEMS}, None)
    assert not list(cmds.glob("impeccable-*.md"))
    assert foreign.is_file(), "un comando que no pertenece a ningun item sobrevive"


def test_impeccable_command_frontmatter_is_valid_yaml():
    """opencode parsea el frontmatter de cada comando: debe ser YAML valido."""
    yaml = pytest.importorskip("yaml")
    item = setup._item_by_id(IMPECCABLE_ID)
    table = _metadata_table(item)
    prefix = item["generate_commands"]["prefix"]
    for name, content in setup._generated_commands(REPO_ROOT, item):
        frontmatter, rest = content.split("\n---\n", 1)
        parsed = yaml.safe_load(frontmatter.removeprefix("---\n"))
        command = name[len(prefix) : -len(".md")]
        assert parsed == {"description": table[command]["description"]}
        assert rest.startswith("\n") and "$ARGUMENTS" in rest


def test_impeccable_commands_survive_a_missing_metadata_table(dest, capsys):
    """Un vendor actualizado que se lleve la tabla no rompe la instalacion."""
    item = setup._item_by_id(IMPECCABLE_ID)
    broken = dict(item, generate_commands={"metadata": "scripts/no-existe.json", "prefix": "x-", "template": "{command}"})
    assert setup._generated_commands(REPO_ROOT, broken) == []
    captured = capsys.readouterr()
    assert "command metadata not found" in captured.err
    assert captured.out == "", "el aviso va a stderr: --manifest imprime JSON en stdout"
