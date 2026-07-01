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

# ── ANSI / color support ─────────────────────────────────────────────────────

_HAVE_COLORAMA: bool = False
_SUPPORTS_COLOR: bool = (
    os.name != "nt"
    or bool(os.environ.get("TERM"))
    or bool(os.environ.get("WT_SESSION"))
)
if not _SUPPORTS_COLOR:
    try:
        import colorama  # type: ignore[import-untyped]
        colorama.init()
        _SUPPORTS_COLOR = True
        _HAVE_COLORAMA = True
    except ImportError:
        pass


def _c(code: str) -> str:
    return f"\033[{code}m" if _SUPPORTS_COLOR else ""


RST = _c("0")
BLD = _c("1")
DIM = _c("2")
INV = _c("7")
RED = _c("31")
GRN = _c("32")
YLW = _c("33")
BLU = _c("34")
MAG = _c("35")
CYN = _c("36")

# ── Unicode / fallback glyphs ────────────────────────────────────────────────

_CAN_UTF: bool = False
try:
    "✔".encode(sys.stdout.encoding or "utf-8")
    _CAN_UTF = True
except (UnicodeEncodeError, LookupError):
    pass
if _CAN_UTF:
    CUR = "▸"; CHK = "●"; UNC = "○"; LCK = "◉"; DEP = "⤷"; TIK = "✔"
    TL = "┌"; TR = "┐"; BL = "└"; BR = "┘"; ML = "├"; MR = "┤"; H = "─"; V = "│"
else:
    CUR = ">"; CHK = "+"; UNC = "o"; LCK = "#"; DEP = "->"; TIK = "ok"
    TL = "+"; TR = "+"; BL = "+"; BR = "+"; ML = "+"; MR = "+"; H = "-"; V = "|"

BOX_W = 78

# ── helpers ───────────────────────────────────────────────────────────────────


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _rel_path(p: Path) -> str:
    try:
        return str(p.relative_to(_repo_root()))
    except ValueError:
        return str(p)


def _git(args: list[str], check=True, **kw):
    return subprocess.run(["git", *args], check=check, **kw)


# ── ITEMS definition ──────────────────────────────────────────────────────────

ITEMS: list[dict] = [
    # ── agents ────────────────────────────────────────────────────────────────
    {
        "id": "vault-indexer",
        "dir": "agents/vault-indexer.md",
        "label": "Vault Indexer",
        "type": "agent",
        "dependencies": [],
    },
    {
        "id": "vault-researcher",
        "dir": "agents/vault-researcher.md",
        "label": "Vault Researcher",
        "type": "agent",
        "dependencies": ["vault-indexer", "vault-search", "vault-organizer"],
    },
    {
        "id": "academic-researcher",
        "dir": "agents/academic-researcher.md",
        "label": "Academic Researcher",
        "type": "agent",
        "dependencies": ["academic-source-search", "citation-style-guide"],
    },
    # ── skills ────────────────────────────────────────────────────────────────
    {
        "id": "vault-search",
        "dir": "skills/vault-search.md",
        "label": "Vault Search",
        "type": "skill",
        "dependencies": ["vault-indexer"],
    },
    {
        "id": "vault-organizer",
        "dir": "skills/vault-organizer.md",
        "label": "Vault Organizer",
        "type": "skill",
        "dependencies": ["vault-indexer", "vault-search"],
    },
    {
        "id": "research-pipeline",
        "dir": "skills/research-pipeline.md",
        "label": "Research Pipeline",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "goal-pursuit",
        "dir": "skills/goal-pursuit.md",
        "label": "Goal Pursuit",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "telegram-notify",
        "dir": "skills/telegram-notify.md",
        "label": "Telegram Notify",
        "type": "skill",
        "dependencies": ["roadmaps", "backtest-run", "research-pipeline"],
    },
    {
        "id": "backtest-run",
        "dir": "skills/backtest-run.md",
        "label": "Backtest Run",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "backtest-validate",
        "dir": "skills/backtest-validate",
        "label": "Backtest Validate",
        "type": "skill",
        "dependencies": ["backtest-run"],
    },
    {
        "id": "academic-source-search",
        "dir": "skills/academic-source-search.md",
        "label": "Academic Source Search",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "citation-style-guide",
        "dir": "skills/citation-style-guide.md",
        "label": "Citation Style Guide",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "content-humanizer",
        "dir": "skills/content-humanizer",
        "label": "Content Humanizer",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "roadmaps",
        "dir": "skills/roadmaps",
        "label": "Roadmaps",
        "type": "skill",
        "dependencies": [],
    },
]

_TYPE_ORDER = {"agent": 0, "skill": 1}
_TYPE_LABEL = {"agent": "Agents", "skill": "Skills"}

# ── dependency propagation ────────────────────────────────────────────────────


def _item_by_id(item_id: str) -> dict | None:
    return next((it for it in ITEMS if it["id"] == item_id), None)


def _propagate_toggle(item_id: str, new_state: bool, toggled: dict[str, bool]) -> None:
    """ON enables dependencies; OFF disables them (unless shared with another ON item).
    Never auto-toggles agents — only skills can be auto-managed."""
    toggled[item_id] = new_state
    item = _item_by_id(item_id)
    if not item:
        return
    if new_state:
        for dep_id in item.get("dependencies", []):
            dep = _item_by_id(dep_id)
            if dep and dep["type"] == "agent":
                # Agents are never auto-enabled — user must toggle them
                continue
            if not toggled.get(dep_id, False):
                toggled[dep_id] = True
                _propagate_toggle(dep_id, True, toggled)
    else:
        for dep_id in item.get("dependencies", []):
            dep = _item_by_id(dep_id)
            if dep and dep["type"] == "agent":
                # Never auto-disable agents
                continue
            still_needed = any(
                other["id"] != item_id
                and dep_id in other.get("dependencies", [])
                and toggled.get(other["id"], False)
                for other in ITEMS
            )
            if not still_needed:
                toggled[dep_id] = False
                _propagate_toggle(dep_id, False, toggled)


def _is_locked(item_id: str, toggled: dict[str, bool]) -> bool:
    """A skill is locked if it's ON and required by any currently ON agent."""
    item = _item_by_id(item_id)
    if not item or item["type"] == "agent":
        return False
    if not toggled.get(item_id, False):
        return False
    return any(
        it["type"] == "agent"
        and toggled.get(it["id"], False)
        and item_id in it.get("dependencies", [])
        for it in ITEMS
    )


def _build_display_order() -> list[dict]:
    """Return items sorted: agents first, then skills."""
    return sorted(ITEMS, key=lambda x: (_TYPE_ORDER.get(x["type"], 99), x["label"]))


# ── input ─────────────────────────────────────────────────────────────────────


def getch() -> str:
    """Read a single keypress. Returns named keys or the char."""
    try:
        import msvcrt

        ch = msvcrt.getwch()
        if ch == "\x03":
            raise KeyboardInterrupt
        if ch == "\r":
            return "enter"
        if ch == " ":
            return "space"
        if ch in ("q", "Q"):
            return "q"
        if ch in ("r", "R"):
            return "r"
        if ch in ("\xe0", "\x00"):
            ch2 = msvcrt.getwch()
            if ch2 == "H":
                return "up"
            if ch2 == "P":
                return "down"
            return "unknown"
        return "unknown"
    except ImportError:
        import tty, termios  # type: ignore[import-untyped]
        import select

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd, termios.TCSADRAIN)
            ch = sys.stdin.read(1)
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch == "\r":
                return "enter"
            if ch == " ":
                return "space"
            if ch in ("q", "Q"):
                return "q"
            if ch in ("r", "R"):
                return "r"
            if ch == "\x1b":
                if select.select([sys.stdin], [], [], 0.05)[0]:
                    seq = sys.stdin.read(2)
                    if seq == "[A":
                        return "up"
                    if seq == "[B":
                        return "down"
                return "esc"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ── menu rendering ────────────────────────────────────────────────────────────


def _stripped_len(s: str) -> int:
    """Length of string with ANSI codes removed."""
    import re
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def _item_line(
    item: dict,
    idx: int,
    toggled: dict[str, bool],
    is_cursor: bool,
    all_items: list[dict],
) -> str:
    """Build a single item row (without box borders)."""
    ptr = f"{CYN}{CUR}{RST}" if is_cursor else " "

    locked = _is_locked(item["id"], toggled)
    if locked:
        mark = f"{CYN}{LCK}{RST}"
    elif toggled.get(item["id"], False):
        mark = f"{GRN}{CHK}{RST}"
    else:
        mark = f"{DIM}{UNC}{RST}"

    label = item["label"]
    tag = f"{CYN}agent{RST}" if item["type"] == "agent" else f"{GRN}skill{RST}"

    deps = item.get("dependencies", [])
    if deps:
        dep_labels = []
        for d_id in deps:
            d_it = _item_by_id(d_id)
            dep_labels.append(d_it["label"] if d_it else d_id)
        dep_str = f"{DIM}{DEP} {dep_labels[0]}{RST}"
        if len(deps) > 1:
            dep_str += f"{DIM} +{len(deps)-1}{RST}"
    else:
        dep_str = ""

    return f"{ptr} {mark}  {label:<22s}  {tag}  {dep_str}"


def _render_menu(items: list[dict], toggled: dict[str, bool], cursor: int) -> int:
    """Render the full toggle menu inside a box with agent/skill sections. Returns line count."""
    inner = BOX_W - 4
    lines: list[str] = []

    # header
    lines.append(f"{BLU}{TL}{H * (BOX_W - 2)}{TR}{RST}")
    lines.append(f"{BLU}{V}{RST}  {BLD}AGENTS-SKILLS -- Installer{RST}{' ' * (inner - 28)}{BLU}{V}{RST}")
    lines.append(f"{BLU}{ML}{H * (BOX_W - 2)}{MR}{RST}")

    arrows = "↑↓" if _CAN_UTF else "^v"
    hint = (
        f"{DIM}[{RST}{CYN}{arrows}{RST}{DIM}] nav{RST}"
        f"  {DIM}[{RST}{GRN}Space{RST}{DIM}] toggle{RST}"
        f"  {DIM}[{RST}{GRN}Enter{RST}{DIM}] install{RST}"
        f"  {DIM}[{RST}q{RST}{DIM}] quit{RST}"
        f"  {DIM}[{RST}r{RST}{DIM}] reset{RST}"
    )
    lines.append(f"{BLU}{V}{RST}  {hint}{' ' * (inner - _stripped_len(hint))}{BLU}{V}{RST}")
    lines.append(f"{BLU}{ML}{H * (BOX_W - 2)}{MR}{RST}")

    current_type = None
    for it in items:
        if it["type"] != current_type:
            current_type = it["type"]
            section_title = f"  {_TYPE_LABEL[current_type]}"
            lines.append(f"{BLU}{V}{RST}  {BLD}{MAG if current_type == 'agent' else GRN}{section_title}{RST}{' ' * (inner - _stripped_len(section_title))}{BLU}{V}{RST}")
        idx = items.index(it)
        c = idx == cursor
        content = _item_line(it, idx, toggled, c, items)
        style = INV if c else ""
        padded = f"{style}{content}{RST}" if style else content
        visible_len = _stripped_len(padded)
        pad = inner - visible_len
        lines.append(f"{BLU}{V}{RST}  {padded}{' ' * pad}{BLU}{V}{RST}")

    # footer with counts
    selected_count = sum(1 for it in items if toggled.get(it["id"], False))
    total_count = len(items)
    color = GRN if selected_count == total_count else YLW if selected_count > 0 else RED
    suffix = f"  ({DIM}all{RST})" if selected_count == total_count else ""
    sel = f"{color}Selected: {selected_count}/{total_count}{RST}{suffix}"

    lines.append(f"{BLU}{ML}{H * (BOX_W - 2)}{MR}{RST}")
    lines.append(f"{BLU}{V}{RST}  {sel}{' ' * (inner - _stripped_len(sel))}{BLU}{V}{RST}")
    lines.append(f"{BLU}{BL}{H * (BOX_W - 2)}{BR}{RST}")

    for l in lines:
        print(l)
    return len(lines)


# ── toggle menu ───────────────────────────────────────────────────────────────


def run_toggle_menu() -> dict[str, bool]:
    """Interactive arrow-key menu with dependency propagation."""
    display_items = _build_display_order()
    toggled: dict[str, bool] = {}

    cursor = 0
    rendered_lines = 0
    first = True

    while True:
        if _SUPPORTS_COLOR and not first:
            sys.stdout.write(f"\033[{rendered_lines}A")
            sys.stdout.flush()

        rendered_lines = _render_menu(display_items, toggled, cursor)
        first = False

        key = getch()

        if key == "q":
            print(f"\n  {YLW}Cancelled.{RST}")
            sys.exit(0)
        elif key == "enter":
            if not any(toggled.get(it["id"], False) for it in display_items):
                print(f"\n  {RED}Select at least one component.{RST}")
                input(f"  {DIM}Press Enter to continue...{RST}")
                continue
            break
        elif key == "up":
            cursor = max(0, cursor - 1)
        elif key == "down":
            cursor = min(len(display_items) - 1, cursor + 1)
        elif key == "space":
            it = display_items[cursor]
            new_state = not toggled.get(it["id"], False)
            if new_state is False and _is_locked(it["id"], toggled):
                continue
            toggled[it["id"]] = new_state
            _propagate_toggle(it["id"], new_state, toggled)
        elif key == "r":
            toggled.clear()
            cursor = 0

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
                print(f"  {GRN}{TIK}{RST} {it['label']}  {DIM}→{RST}  {_rel_path(dst)}")
            else:
                print(f"  {YLW}..{RST} {it['label']}  source not found: {_rel_path(src)}")
        else:
            if dst.exists():
                shutil.rmtree(dst)
                print(f"  {DIM}✗ removed {it['label']}{RST}")


def cleanup_repo() -> None:
    """Remove .opencode/skills to trigger reinstall on next run."""
    skills_dir = _repo_root() / ".opencode" / "skills"
    if skills_dir.exists():
        shutil.rmtree(skills_dir)
        print(f"  {GRN}{TIK}{RST} Cleared .opencode/skills/")
    else:
        print("  -- Nothing to clean.")


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
        print(f"  {GRN}{TIK}{RST} Appended {len(agents)} agent(s) to {_rel_path(agents_file)}")
    else:
        print("  -- All agents already registered.")


def push_changes() -> None:
    """Commit and push local skill changes."""
    result = _git(["status", "--porcelain"], capture_output=True, text=True)
    if not result.stdout.strip():
        print("  -- Nothing to commit.")
        return
    print(f"  {BLU}i{RST} Changes detected.  Commit message:")
    msg = input(f"  {DIM}> {RST}").strip() or "Update skills"
    _git(["add", "-A"])
    _git(["commit", "-m", msg])
    _git(["push"])
    print(f"  {GRN}{TIK}{RST} Pushed.")


def pull_changes() -> None:
    """Pull latest from remote."""
    _git(["pull"])
    print(f"  {GRN}{TIK}{RST} Pulled latest.")


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    base = Path.cwd()

    icon = "◆" if _CAN_UTF else "#"
    print(f"\n  {BLD}{MAG}{icon}{RST}  {BLD}AGENTS-SKILLS -- Installer{RST}  {DIM}{base}{RST}\n")

    print(f"  {BLD}Select components to install:{RST}\n")
    toggled = run_toggle_menu()

    print(f"\n  {BLD}Installing...{RST}\n")
    install_items(toggled, base)
    agent_targets()

    print(f"\n  {GRN}{BLD}{TIK} Done.{RST}\n")


if __name__ == "__main__":
    main()
