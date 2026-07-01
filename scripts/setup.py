# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Interactive setup: toggle skills/agents, install them, and keep repo clean.

Usage:
    python scripts/setup.py              # from repo root
    python setup.py                       # standalone at project root
    git clone ... && python setup.py      # one-liner
"""

from __future__ import annotations

import json, os, shutil, subprocess, sys
from pathlib import Path

# ── ANSI helpers ──────────────────────────────────────────────────────────────

_USE_ANSI = os.environ.get("TERM", "") not in ("", "dumb") and hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

def _ansi(code: str) -> str:
    return f"\033[{code}m" if _USE_ANSI else ""

RST = _ansi("0"); BLD = _ansi("1"); DIM = _ansi("2"); INV = _ansi("7")
RED = _ansi("31"); GRN = _ansi("32"); YLW = _ansi("33")
BLU = _ansi("34"); MAG = _ansi("35"); CYN = _ansi("36")

# ── box-drawing glyphs ────────────────────────────────────────────────────────

_GLYPH = {
    "tl": "┌", "tr": "┐", "bl": "└", "br": "┘",
    "h": "─", "v": "│",
    "on": "◉", "off": "○", "lock": "🔒",
} if _USE_ANSI else {
    "tl": "+", "tr": "+", "bl": "+", "br": "+",
    "h": "-", "v": "|",
    "on": "[x]", "off": "[ ]", "lock": "[L]",
}

# ── helpers ───────────────────────────────────────────────────────────────────

def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent

def _rel_path(p: Path) -> str:
    try:
        return str(p.relative_to(_repo_root()))
    except ValueError:
        return str(p)

def clear_screen() -> None:
    if _USE_ANSI:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
    else:
        os.system("cls" if os.name == "nt" else "clear")

def _git(args: list[str], check=True, **kw):
    return subprocess.run(["git", *args], check=check, **kw)

# ── ITEMS definition ──────────────────────────────────────────────────────────

ITEMS: list[dict] = [
    # ── agents ────────────────────────────────────────────────────────────────
    {"id": "vault-indexer",    "dir": "agents/vault-indexer.md",        "label": "Vault Indexer",        "type": "agent", "dependencies": []},
    {"id": "vault-researcher", "dir": "agents/vault-researcher.md",     "label": "Vault Researcher",     "type": "agent",
     "dependencies": ["vault-indexer", "vault-search", "vault-organizer"]},
    {"id": "academic-researcher", "dir": "agents/academic-researcher.md", "label": "Academic Researcher", "type": "agent",
     "dependencies": ["academic-source-search", "citation-style-guide"]},
    # ── skills ────────────────────────────────────────────────────────────────
    {"id": "vault-search",         "dir": "skills/vault-search.md",         "label": "Vault Search",         "type": "skill",
     "dependencies": ["vault-indexer"]},
    {"id": "vault-organizer",      "dir": "skills/vault-organizer.md",      "label": "Vault Organizer",      "type": "skill",
     "dependencies": ["vault-indexer", "vault-search"]},
    {"id": "research-pipeline",    "dir": "skills/research-pipeline.md",    "label": "Research Pipeline",    "type": "skill", "dependencies": []},
    {"id": "goal-pursuit",         "dir": "skills/goal-pursuit.md",         "label": "Goal Pursuit",         "type": "skill", "dependencies": []},
    {"id": "telegram-notify",      "dir": "skills/telegram-notify.md",      "label": "Telegram Notify",      "type": "skill",
     "dependencies": ["roadmaps", "backtest-run", "research-pipeline"]},
    {"id": "backtest-run",         "dir": "skills/backtest-run.md",         "label": "Backtest Run",         "type": "skill", "dependencies": []},
    {"id": "backtest-validate",    "dir": "skills/backtest-validate",       "label": "Backtest Validate",    "type": "skill",
     "dependencies": ["backtest-run"]},
    {"id": "academic-source-search","dir": "skills/academic-source-search.md","label": "Academic Source Search","type": "skill", "dependencies": []},
    {"id": "citation-style-guide",  "dir": "skills/citation-style-guide.md", "label": "Citation Style Guide", "type": "skill", "dependencies": []},
    {"id": "content-humanizer",    "dir": "skills/content-humanizer",        "label": "Content Humanizer",    "type": "skill", "dependencies": []},
    {"id": "roadmaps",             "dir": "skills/roadmaps",                 "label": "Roadmaps",             "type": "skill", "dependencies": []},
]

_TYPE_ORDER = {"agent": 0, "skill": 1}
_TYPE_LABEL = {"agent": "🤖  Agents", "skill": "🛠   Skills"}

# ── dependency propagation ────────────────────────────────────────────────────

def _item_by_id(item_id: str) -> dict | None:
    return next((it for it in ITEMS if it["id"] == item_id), None)

def _propagate_toggle(item_id: str, new_state: bool, toggled: dict[str, bool]) -> None:
    """BFS propagation: ON→enable dependencies, OFF→disable dependents."""
    toggled[item_id] = new_state
    if new_state:
        item = _item_by_id(item_id)
        if item:
            for dep_id in item.get("dependencies", []):
                if not toggled.get(dep_id, False):
                    toggled[dep_id] = True
                    _propagate_toggle(dep_id, True, toggled)
    else:
        for it in ITEMS:
            dep_ids = it.get("dependencies", [])
            if item_id in dep_ids and toggled.get(it["id"], False):
                toggled[it["id"]] = False
                _propagate_toggle(it["id"], False, toggled)

def _locked_ids() -> set[str]:
    """Items required by at least one agent cannot be toggled off."""
    locked: set[str] = set()
    for it in ITEMS:
        if it["type"] == "agent":
            for dep_id in it.get("dependencies", []):
                locked.add(dep_id)
    return locked

def _build_display_order() -> list[dict]:
    """Return items in display order: agents first, then skills."""
    return sorted(ITEMS, key=lambda x: (_TYPE_ORDER.get(x["type"], 99), x["label"]))

def _item_line_content(it: dict, toggled: dict[str, bool]) -> str:
    status = "on" if toggled.get(it["id"], False) else "off"
    glyph = _GLYPH["on"] if status == "on" else _GLYPH["off"]
    label = f"{glyph} {it['label']}"
    deps = it.get("dependencies", [])
    if deps:
        dep_labels = []
        for d_id in deps:
            d_it = _item_by_id(d_id)
            dep_labels.append(d_it["label"] if d_it else d_id)
        label += f" {DIM}(requires: {', '.join(dep_labels)}){RST}"
    return label

def _render_menu_box(lines: list[str], title: str | None = None, selected: int = 0, show_help: bool = True) -> None:
    if not _USE_ANSI:
        if title:
            print(f"\n--- {title} ---")
        for i, line in enumerate(lines):
            marker = ">" if i == selected else " "
            print(f"{marker} {line}")
        if show_help:
            print("  [↑↓] navigate  [Space] toggle  [Enter] confirm  [q] quit")
        return

    max_len = max(len(line) for line in lines) if lines else 0
    if title:
        max_len = max(max_len, len(title) + 4)
    width = max_len + 4

    title_str = f" {title} " if title else ""
    print(f"{_GLYPH['tl']}{_GLYPH['h']}{title_str}{_GLYPH['h'] * (width - len(title_str) - 2)}{_GLYPH['tr']}")

    for i, line in enumerate(lines):
        marker = f"{CYN}{'▸'}{RST}" if i == selected else " "
        padded = f"{marker} {line}{' ' * (width - len(line) - 3)}"
        print(f"{_GLYPH['v']}{padded}{_GLYPH['v']}")

    print(f"{_GLYPH['bl']}{_GLYPH['h'] * width}{_GLYPH['br']}")
    if show_help:
        help_text = f"{DIM}[↑↓] nav  [Space] toggle  [Enter] confirm  [q] quit{RST}"
        print(f"  {help_text}")

def run_toggle_menu() -> dict[str, bool]:
    """Interactive menu: arrow-key navigation with dependency propagation."""
    import msvcrt

    display_items = _build_display_order()
    toggled: dict[str, bool] = {}
    locked = _locked_ids()

    for it in ITEMS:
        if it["type"] == "agent":
            toggled[it["id"]] = True

    selected = 0
    while True:
        clear_screen()

        current_type = None
        box_lines: list[str] = []
        box_title = None
        for idx, it in enumerate(display_items):
            if it["type"] != current_type:
                if box_lines:
                    _render_menu_box(box_lines, title=box_title, selected=-1, show_help=False)
                current_type = it["type"]
                box_title = _TYPE_LABEL[current_type]
                box_lines = []

            prefix = ""
            if it["id"] in locked and not toggled.get(it["id"], False):
                prefix = f"{_GLYPH['lock']} "
            elif toggled.get(it["id"], False):
                prefix = f"{_GLYPH['on']} "
            else:
                prefix = f"{_GLYPH['off']} "

            label = f"{prefix}{it['label']}"
            deps = it.get("dependencies", [])
            if deps:
                dep_labels = []
                for d_id in deps:
                    d_it = _item_by_id(d_id)
                    dep_labels.append(d_it["label"] if d_it else d_id)
                label += f" {DIM}(needs: {', '.join(dep_labels)}){RST}"

            box_lines.append(label)

        if box_lines:
            _render_menu_box(box_lines, title=box_title, show_help=False)

        print(f"\n  {DIM}[↑↓] nav  [Space] toggle  [Enter] confirm  [r] reset  [q] quit{RST}")

        key = msvcrt.getch()
        if key in (b"\xe0", b"\x00"):
            key = msvcrt.getch()
            if key == b"H":
                selected = max(0, selected - 1)
            elif key == b"P":
                selected = min(len(display_items) - 1, selected + 1)
        elif key == b" ":
            it = display_items[selected]
            new_state = not toggled.get(it["id"], False)
            if new_state is False and it["id"] in locked:
                continue
            toggled[it["id"]] = new_state
            _propagate_toggle(it["id"], new_state, toggled)
        elif key in (b"\r", b"\n"):
            break
        elif key in (b"q", b"Q"):
            sys.exit(0)
        elif key in (b"r", b"R"):
            for it in ITEMS:
                toggled[it["id"]] = it["type"] == "agent"
            selected = 0

    return toggled

# ── install / file operations ─────────────────────────────────────────────────

def install_items(toggled: dict[str, bool], project_root: Path) -> None:
    """Copy enabled skill directories into the project."""
    skills_root = project_root / ".opencode" / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)

    for it in ITEMS:
        src = project_root / it["dir"]
        dst = skills_root / it["dir"]
        if toggled.get(it["id"], False):
            if src.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dst, dirs_exist_ok=True)
                print(f"  {GRN}✓{RST} {it['label']}  →  {_rel_path(dst)}")
            else:
                print(f"  {YLW}⚠{RST} {it['label']}  source not found: {_rel_path(src)}")
        else:
            if dst.exists():
                shutil.rmtree(dst)
                print(f"  {DIM}✗ removed {it['label']}{RST}")

def cleanup_repo() -> None:
    """Remove .opencode/skills to trigger reinstall on next run."""
    skills_dir = _repo_root() / ".opencode" / "skills"
    if skills_dir.exists():
        shutil.rmtree(skills_dir)
        print("  ✓ Cleared .opencode/skills/")
    else:
        print("  — Nothing to clean.")

# ── adapt / push / pull ───────────────────────────────────────────────────────

def adapt_md_content(content: str, item_id: str) -> str:
    """Replace placeholders in skill files."""
    return content.replace("{{AGENT_ID}}", item_id)

def agent_targets(dest: Path | None = None) -> None:
    """Generate .opencode/agents.json from skill dirs."""
    d = dest or (_repo_root() / ".opencode")
    agents = []
    agents_file = d / "agents.json"
    existing: list = json.loads(agents_file.read_text("utf-8")) if agents_file.exists() else []
    existing_ids = {a.get("name") or a.get("id") for a in existing}
    for it in ITEMS:
        if it["type"] == "agent":
            if it["label"] not in existing_ids:
                agents.append({"id": it["id"], "dir": it["dir"], "name": it["label"]})
    if agents:
        agents_file.parent.mkdir(parents=True, exist_ok=True)
        existing.extend(agents)
        agents_file.write_text(json.dumps(existing, indent=2, ensure_ascii=False), "utf-8")
        print(f"  ✓ Appended {len(agents)} agent(s) to {_rel_path(agents_file)}")
    else:
        print("  — All agents already registered.")

def push_changes() -> None:
    """Commit and push local skill changes."""
    result = _git(["status", "--porcelain"], capture_output=True, text=True)
    if not result.stdout.strip():
        print("  — Nothing to commit.")
        return
    print(f"  {BLU}i{RST} Changes detected.  Commit message:")
    msg = input(f"  {DIM}> {RST}").strip() or "Update skills"
    _git(["add", "-A"])
    _git(["commit", "-m", msg])
    _git(["push"])
    print(f"  {GRN}✓{RST} Pushed.")

def pull_changes() -> None:
    """Pull latest from remote."""
    _git(["pull"])
    print(f"  {GRN}✓{RST} Pulled latest.")

# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    base = Path.cwd()
    print(f"\n  {BLD}{MAG}OpenCode Skill Installer{RST}  {DIM}{base}{RST}\n")

    print(f"  {BLD}Select skills/agents to install:{RST}\n")
    toggled = run_toggle_menu()

    print(f"\n  {BLD}Installing…{RST}\n")
    install_items(toggled, base)
    agent_targets()

    print(f"\n  {GRN}{BLD}✔ Done.{RST}\n")

if __name__ == "__main__":
    main()
