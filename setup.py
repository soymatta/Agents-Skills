"""Interactive setup: toggle skills/agents, install them, and keep repo clean.

Usage:
    python scripts/setup.py              # from repo root
    python setup.py                       # standalone at project root
    git clone ... && python setup.py      # one-liner
    python scripts/setup.py --all        # install all without menu
    python scripts/setup.py --global     # install to user-level config
    python scripts/setup.py --all --platform claude --local
    python scripts/setup.py --check --global --platform opencode   # verify, write nothing
"""

from __future__ import annotations

import hashlib
import json, os, shutil, sys
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
    CUR = "▸"; CHK = "●"; UNC = "○"; LCK = "◉"; DEP = "⤷"; TIK = "✔"; ARR = "→"; X = "✗"
    TL = "┌"; TR = "┐"; BL = "└"; BR = "┘"; ML = "├"; MR = "┤"; H = "─"; V = "│"
else:
    CUR = ">"; CHK = "+"; UNC = "o"; LCK = "#"; DEP = "->"; TIK = "ok"; ARR = "->"; X = "x"
    TL = "+"; TR = "+"; BL = "+"; BR = "+"; ML = "+"; MR = "+"; H = "-"; V = "|"

BOX_W = 78

# ── helpers ───────────────────────────────────────────────────────────────────


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _rel_path(p: Path) -> str:
    try:
        return str(p.relative_to(_repo_root()))
    except ValueError:
        return str(p)


# ── platform / agent detection ────────────────────────────────────────────────

PLATFORMS: dict[str, dict] = {
    "opencode": {
        "label": "OpenCode",
        "config_dir": ".opencode",
        "skills_subdir": "skills",
        "agents_subdir": "agent",
        "plugins_subdir": "plugins",
        "uses_agents_json": False,
        "detect_files": [".opencode"],
        "global_dir": Path.home() / ".config" / "opencode",
    },
    "claude": {
        "label": "Claude Code",
        "config_dir": ".claude",
        "skills_subdir": "skills",
        "agents_subdir": "agents",
        "uses_agents_json": True,
        "detect_files": [".claude"],
        "global_dir": Path.home() / ".claude",
    },
    "cursor": {
        "label": "Cursor",
        "config_dir": ".cursor",
        "skills_subdir": "skills",
        "agents_subdir": "agents",
        "uses_agents_json": True,
        "detect_files": [".cursor"],
        "global_dir": Path.home() / ".cursor",
    },
    "windsurf": {
        "label": "Windsurf",
        "config_dir": ".windsurf",
        "skills_subdir": "skills",
        "agents_subdir": "agents",
        "uses_agents_json": True,
        "detect_files": [".windsurf"],
        "global_dir": Path.home() / ".windsurf",
    },
    "agy": {
        "label": "Agy",
        "config_dir": ".agy",
        "skills_subdir": "skills",
        "agents_subdir": "agents",
        "uses_agents_json": True,
        "detect_files": [".agy"],
        "global_dir": Path.home() / ".agy",
    },
    "codex": {
        "label": "Codex",
        "config_dir": ".codex",
        "skills_subdir": "skills",
        "agents_subdir": "agents",
        "uses_agents_json": True,
        "detect_files": [".codex"],
        "global_dir": Path.home() / ".codex",
    },
}


def _detect_platform() -> str | None:
    """Auto-detect the AI platform from the current project directory."""
    cwd = Path.cwd()
    for platform_id, info in PLATFORMS.items():
        for detect_file in info["detect_files"]:
            if (cwd / detect_file).exists():
                return platform_id
    return None


def _detect_install_mode() -> str:
    """Detect if we're in a project (local) or standalone (global)."""
    cwd = Path.cwd()
    has_git = (cwd / ".git").exists()
    has_package_json = (cwd / "package.json").exists()
    has_pyproject = (cwd / "pyproject.toml").exists()
    has_src = (cwd / "src").is_dir()
    return "local" if any([has_git, has_package_json, has_pyproject, has_src]) else "global"


def _prompt_install_mode() -> str:
    """Ask user: local project or global/machine install."""
    detected = _detect_install_mode()
    print(f"\n  {BLD}Installation mode:{RST}")
    print(f"  {DIM}Detected: {'local project' if detected == 'local' else 'global (no project markers found)'}{RST}\n")
    print(f"  [{CYN}1{RST}] Local project  {DIM}- install to <project>/.opencode/skills/{RST}")
    print(f"  [{CYN}2{RST}] Global (machine) {DIM}- install to ~/.config/opencode/skills/{RST}")
    print()
    while True:
        choice = input(f"  {DIM}Select [1/2] (default: {'1' if detected == 'local' else '2'}): {RST}").strip()
        if choice == "":
            return detected
        if choice in ("1", "local"):
            return "local"
        if choice in ("2", "global"):
            return "global"
        print(f"  {RED}Invalid choice. Enter 1 or 2.{RST}")


def _prompt_platform() -> str:
    """Ask user which AI platform to install for, or auto-detect."""
    detected = _detect_platform()
    platform_list = list(PLATFORMS.keys())

    print(f"\n  {BLD}Target platform:{RST}")
    if detected:
        print(f"  {DIM}Detected: {PLATFORMS[detected]['label']}{RST}\n")
    else:
        print(f"  {DIM}No platform detected in current directory.{RST}\n")

    for i, pid in enumerate(platform_list, 1):
        label = PLATFORMS[pid]["label"]
        marker = f" {GRN}(detected){RST}" if pid == detected else ""
        print(f"  [{CYN}{i}{RST}] {label}{marker}")
    print()
    while True:
        default = str(platform_list.index(detected) + 1) if detected else ""
        choice = input(f"  {DIM}Select [1-{len(platform_list)}] (default: {default or '1'}): {RST}").strip()
        if choice == "":
            idx = int(default) - 1 if default else 0
            return platform_list[idx]
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(platform_list):
                return platform_list[idx]
        except ValueError:
            pass
        print(f"  {RED}Invalid choice. Enter a number 1-{len(platform_list)}.{RST}")


def _get_install_paths(platform_id: str, mode: str) -> dict:
    """Return install paths for the platform and mode.

    Returns dict with keys: skills_dir, agents_file, agents_dir, plugins_dir,
    uses_agents_json. plugins_dir is None for platforms without plugin support.
    """
    info = PLATFORMS[platform_id]
    if mode == "global":
        base = info["global_dir"]
    else:
        base = Path.cwd() / info["config_dir"]
    skills_dir = base / info["skills_subdir"]
    agents_dir = base / info["agents_subdir"]
    agents_file = base / f"{info['agents_subdir']}.json"
    plugins_dir = base / info["plugins_subdir"] if info.get("plugins_subdir") else None
    return {
        "skills_dir": skills_dir,
        "agents_file": agents_file,
        "agents_dir": agents_dir,
        "plugins_dir": plugins_dir,
        "uses_agents_json": info["uses_agents_json"],
    }


def _normalize_dest(prefix: str) -> str:
    """Strip the leading 'skills/' portion of a source path.

    Item dirs/bundles live under ``skills/`` in the repo, but the install
    destination root is already the platform's ``skills`` directory, so the
    prefix must be removed to avoid double-nesting (``skills/skills/...``).
    """
    if prefix.startswith("skills/"):
        return prefix[len("skills/"):]
    return prefix


# ── ITEMS definition ──────────────────────────────────────────────────────────

ITEMS: list[dict] = [
    # ── agents ────────────────────────────────────────────────────────────────
    {
        "id": "vault",
        "dir": "agents/vault.md",
        "label": "Vault (Obsidian Manager)",
        "type": "agent",
        "dependencies": [],
    },
    {
        "id": "paper-researcher",
        "dir": "agents/paper-researcher.md",
        "label": "Paper Researcher",
        "type": "agent",
        "dependencies": ["academic-source-search", "citation-formatter"],
    },
    {
        "id": "jobfinder",
        "dir": "agents/jobfinder.md",
        "label": "Job Finder",
        "type": "agent",
        # El skill se declara como dependencia para que el menu bloquee apagarlo
        # con el agente encendido; los bundles siguen ahi porque `--only jobfinder`
        # no propaga dependencias y necesita los scripts del skill.
        "dependencies": ["jobfinder-skill"],
        "bundles": [
            "skills/jobfinder/SKILL.md",
            "skills/jobfinder/scripts",
            "skills/jobfinder/templates",
        ],
    },
    {
        "id": "builder",
        "dir": "agents/builder.md",
        "label": "Builder (Build Mod)",
        "type": "agent",
        "dependencies": ["agent-self-improver", "skill-creator", "goal", "roadmaps"],
    },
    {
        "id": "reverse-engineer",
        "dir": "agents/reverse-engineer.md",
        "label": "Reverse Engineer",
        "type": "agent",
        "dependencies": [],
    },
    {
        "id": "fitness-coach",
        "dir": "agents/fitness-coach.md",
        "label": "Fitness Coach (Evidence-Based)",
        "type": "agent",
        # Read-only by design (edit/bash deny): it searches and cites, it never touches code.
        # The two skills are declared so the menu blocks turning them off under the agent.
        "dependencies": ["academic-source-search", "citation-formatter"],
    },
    # ── skills ────────────────────────────────────────────────────────────────
    {
        "id": "telegram-notify",
        "dir": "skills/telegram-notify",
        "label": "Telegram Notify",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "research-pipeline",
        "dir": "skills/research-pipeline",
        "label": "Research Pipeline",
        "type": "skill",
        "dependencies": ["telegram-notify"],
    },
    {
        "id": "backtest-run",
        "dir": "skills/backtest-run",
        "label": "Backtest Run",
        "type": "skill",
        "dependencies": ["telegram-notify"],
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
        "dir": "skills/academic-source-search",
        "label": "Academic Source Search",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "citation-formatter",
        "dir": "skills/citation-formatter",
        "label": "Citation Formatter",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "math-notation",
        "dir": "skills/math-notation",
        "label": "Math Notation",
        "type": "skill",
        "dependencies": ["citation-formatter"],
        "bundles": ["skills/citation-formatter/scripts/generate_outputs.py"],
    },
    {
        "id": "content-humanizer",
        "dir": "skills/content-humanizer",
        "label": "Content Humanizer",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "osint",
        "dir": "skills/osint",
        "label": "OSINT Investigator",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "goal",
        "dir": "skills/goal",
        "label": "Goal",
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
    {
        "id": "project-analyzer",
        "dir": "skills/project-analyzer",
        "label": "Project Analyzer",
        "type": "skill",
        "dependencies": [],
        "commands": ["init-review.md"],
    },
    {
        "id": "agent-self-improver",
        "dir": "skills/agent-self-improver",
        "label": "Agent Self-Improver",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "code-review",
        "dir": "skills/code-review",
        "label": "Code Review",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "debug",
        "dir": "skills/debug",
        "label": "Debug",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "git-workflow",
        "dir": "skills/git-workflow",
        "label": "Git Workflow",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "commit",
        "dir": "skills/commit",
        "label": "Commit",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "project-memory",
        "dir": "skills/project-memory",
        "label": "Project Memory",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "refactor",
        "dir": "skills/refactor",
        "label": "Refactor",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "skill-creator",
        "dir": "skills/skill-creator",
        "label": "Skill Creator",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "impeccable",
        "dir": "skills/impeccable",
        "label": "Impeccable (third-party)",
        "type": "skill",
        "dependencies": [],
        # The vendored tree is read-only and lists its 23 sub-commands in a JSON
        # table (no .md file per command), so the installer generates the slash
        # commands from that table: hand-written copies would drift on every
        # upstream update. The `impeccable-` prefix keeps `/impeccable-init` and
        # friends from shadowing opencode's built-in `/init`.
        "generate_commands": {
            "metadata": "scripts/command-metadata.json",
            "prefix": "impeccable-",
            "template": (
                "Run the `impeccable` skill's `{command}` workflow.\n\n"
                "Arguments: $ARGUMENTS\n\n"
                "Load the `impeccable` skill, follow the playbook its Commands table "
                "maps to `{command}` for this request, and carry it out end to end on "
                "the current project. With no arguments, work on what is in front of "
                "you and ask only if the target is genuinely ambiguous."
            ),
        },
    },
    {
        "id": "qa-tester",
        "dir": "skills/qa-tester",
        "label": "QA Tester",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "ai-job-search",
        "dir": "skills/ai-job-search",
        "label": "AI Job Search (third-party)",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "web-cloner",
        "dir": "skills/web-cloner",
        "label": "Web Cloner",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "ui-ux-pro-max",
        "dir": "skills/ui-ux-pro-max",
        "label": "UI UX Pro Max (third-party)",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "web-esenciales",
        "dir": "skills/web-esenciales",
        "label": "Web Esenciales",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "web-design-guidelines",
        "dir": "skills/web-design-guidelines",
        "label": "Web Design Guidelines (third-party)",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "ui-ux-orchestrator",
        "dir": "skills/ui-ux-orchestrator",
        "label": "UI UX Orchestrator",
        "type": "skill",
        "dependencies": ["ui-ux-pro-max", "impeccable", "web-design-guidelines", "web-esenciales"],
        "commands": ["init-ui-ux.md"],
    },
    {
        "id": "jobfinder-skill",
        "dir": "skills/jobfinder",
        "label": "Job Finder (skill)",
        "type": "skill",
        "dependencies": ["ai-job-search"],
    },
    # ── plugins (opencode-only — not portable to other agents) ──────────────
    {
        "id": "opencode-telegram-answers",
        "dir": "plugins/opencode-telegram-answers",
        "label": "OpenCode Telegram Answers (plugin)",
        "type": "plugin",
        "platforms": ["opencode"],
        "dependencies": [],
        "entry": "notification.ts",
    },
    {
        "id": "opencode-tui-queue",
        "dir": "plugins/opencode-tui-queue",
        "label": "OpenCode TUI Queue (plugin)",
        "type": "plugin",
        "platforms": ["opencode"],
        "dependencies": [],
        "entry": "queue.ts",
        "commands": ["queue.md"],
    },
    {
        "id": "opencode-auto-session",
        "dir": "plugins/opencode-auto-session",
        "label": "OpenCode Auto Session (plugin)",
        "type": "plugin",
        "platforms": ["opencode"],
        "dependencies": [],
        "entry": "autosession.ts",
        "files": ["limit-notify.ps1", "limit-notify.sh"],
        "commands": ["autosession.md"],
    },
]

_TYPE_ORDER = {"agent": 0, "skill": 1, "plugin": 2}
_TYPE_LABEL = {"agent": "Agents", "skill": "Skills", "plugin": "Plugins"}

# ── dependency propagation ────────────────────────────────────────────────────


def _item_by_id(item_id: str) -> dict | None:
    return next((it for it in ITEMS if it["id"] == item_id), None)


def _propagate_toggle(item_id: str, new_state: bool, toggled: dict[str, bool]) -> None:
    """ON enables all dependencies (including agents). OFF disables skill dependencies
    unless shared with another ON item. Never auto-disables agents."""
    toggled[item_id] = new_state
    item = _item_by_id(item_id)
    if not item:
        return
    if new_state:
        for dep_id in item.get("dependencies", []):
            if not toggled.get(dep_id, False):
                toggled[dep_id] = True
                _propagate_toggle(dep_id, True, toggled)
    else:
        for dep_id in item.get("dependencies", []):
            dep = _item_by_id(dep_id)
            if dep and dep["type"] == "agent":
                # Never auto-disable agents — user must toggle them off
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


def _copy_one(src: Path, dst: Path) -> None:
    """Copy a single file or directory from src to dst.

    Directory copies skip bytecode caches (``__pycache__``, ``*.pyc``) so a local
    pytest run never leaks compiled artifacts into the installed config.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(
            src,
            dst,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    else:
        shutil.copy2(src, dst)


def _remove_one(dst: Path) -> None:
    """Remove a single file or directory."""
    if not dst.exists():
        return
    if dst.is_dir():
        shutil.rmtree(dst)
    else:
        dst.unlink()


def _commands_root(skills_root: Path) -> Path:
    """Return the commands directory (sibling to skills/)."""
    return skills_root.parent / "commands"


def _generated_commands(project_root: Path, item: dict) -> list[tuple[str, str]]:
    """Build ``(filename, content)`` pairs for an item declaring ``generate_commands``.

    Some third-party skills (``impeccable``) ship their sub-commands as a JSON
    metadata table instead of one markdown file per command. Generating the
    slash commands from that table keeps the installed set in sync with the
    vendor's own inventory, and needs no writes inside the vendored tree.

    Diagnostics go to stderr: ``--manifest`` prints JSON on stdout and must stay
    parseable for the AI agents that consume it.
    """
    spec = item.get("generate_commands")
    if not spec:
        return []
    meta_path = project_root / item["dir"] / spec["metadata"]
    if not meta_path.is_file():
        print(
            f"  {YLW}..{RST} {item['label']}  command metadata not found: {_rel_path(meta_path)}",
            file=sys.stderr,
        )
        return []
    try:
        table = json.loads(meta_path.read_text("utf-8"))
    except (OSError, ValueError) as exc:
        print(
            f"  {YLW}..{RST} {item['label']}  command metadata unreadable: {exc}",
            file=sys.stderr,
        )
        return []
    prefix = spec.get("prefix", "")
    generated: list[tuple[str, str]] = []
    for name, entry in table.items():
        description = (entry or {}).get("description") or f"{name} ({item['label']})"
        body = spec["template"].replace("{command}", name)
        content = (
            "---\n"
            f"description: {json.dumps(description, ensure_ascii=False)}\n"
            "---\n\n"
            f"{body}\n"
        )
        generated.append((f"{prefix}{name}.md", content))
    return generated


def _item_command_names(project_root: Path, item: dict) -> list[str]:
    """Every command file name an item installs: declared in-repo plus generated."""
    names = list(item.get("commands", []))
    names.extend(name for name, _ in _generated_commands(project_root, item))
    return names


def install_items(
    toggled: dict[str, bool],
    project_root: Path,
    skills_root: Path,
    agents_dir: Path,
    plugins_dir: Path | None = None,
    platform_id: str | None = None,
    only: set[str] | None = None,
) -> None:
    """Copy enabled items into the project (files or directories).

    ``skills_root`` is the platform's skills directory (e.g. ``.opencode/skills``);
    agents are installed to ``agents_dir`` (e.g. ``.opencode/agent``) so the
    platform can discover them. ``plugins_dir`` (e.g. ``.opencode/plugins``) is
    only set for platforms that support plugins; plugin items are additionally
    gated by their ``platforms`` list so they never install on other agents.

    ``only`` restricts the run to a set of item ids and skips the removal branch
    for everything else, so a targeted install never deletes unrelated items.
    """
    skills_root.mkdir(parents=True, exist_ok=True)
    cmds_root = _commands_root(skills_root)
    if plugins_dir:
        plugins_dir.mkdir(parents=True, exist_ok=True)

    for it in ITEMS:
        if only is not None and it["id"] not in only:
            continue
        src = project_root / it["dir"]
        enabled = toggled.get(it["id"], False)
        applies = it.get("platforms", None) is None or platform_id in it.get("platforms", [])
        if it["type"] == "plugin":
            if not applies:
                # Plugin not intended for this platform — never install nor remove.
                continue
            if enabled:
                if not src.exists():
                    print(f"  {YLW}..{RST} {it['label']}  source not found: {_rel_path(src)}")
                else:
                    entry = src / it.get("entry", "notification.ts")
                    stale_dir = plugins_dir / Path(it["dir"]).name
                    if stale_dir.exists():
                        # Modelo antiguo (carpetas): OpenCode solo autoload .ts planos
                        _remove_one(stale_dir)
                    if entry.exists():
                        dst_ts = plugins_dir / f"{it['id']}.ts"
                        _copy_one(entry, dst_ts)
                        print(f"  {GRN}{TIK}{RST} {it['label']}  {DIM}{ARR}{RST}  {_rel_path(dst_ts)}")
                    else:
                        print(f"  {YLW}..{RST} {it['label']}  entry not found: {it.get('entry', 'notification.ts')}")
                # command files del plugin (registrados como slash commands)
                for cmd_src in it.get("commands", []):
                    cmd_path = src / "commands" / cmd_src
                    cmd_dst = cmds_root / cmd_src
                    if cmd_path.exists():
                        cmd_dst.parent.mkdir(parents=True, exist_ok=True)
                        _copy_one(cmd_path, cmd_dst)
                        print(f"  {GRN}{TIK}{RST} command/{cmd_src}  {DIM}{ARR}{RST}  {_rel_path(cmd_dst)}")
                # archivos auxiliares del plugin (assets en runtime, no .ts):
                # viven en plugins/<id>/ para que el autoload de OpenCode no los toque
                files_root = plugins_dir / it["id"]
                for fname in it.get("files", []):
                    f_src = src / fname
                    if f_src.exists():
                        f_dst = files_root / fname
                        _copy_one(f_src, f_dst)
                        print(f"  {GRN}{TIK}{RST} {fname}  {DIM}{ARR}{RST}  {_rel_path(f_dst)}")
                    else:
                        print(f"  {YLW}..{RST} {it['label']}  asset not found: {fname}")
            else:
                _remove_one(plugins_dir / f"{it['id']}.ts")
                # carpeta del plugin en la config: el .ts se autoload desde
                # plugins/ plano, pero los assets de runtime (files) y el modelo
                # antiguo (carpeta con el nombre del dir) viven dentro, y se
                # retiran juntos para no dejar restos al desinstalar.
                _remove_one(plugins_dir / Path(it["dir"]).name)
                _remove_one(plugins_dir / it["id"])
                for cmd_src in it.get("commands", []):
                    _remove_one(cmds_root / cmd_src)
            continue

        dst = _item_dest(it, skills_root, agents_dir)
        if enabled:
            if not src.exists():
                print(f"  {YLW}..{RST} {it['label']}  source not found: {_rel_path(src)}")
            else:
                _copy_one(src, dst)
                print(f"  {GRN}{TIK}{RST} {it['label']}  {DIM}{ARR}{RST}  {_rel_path(dst)}")
            # bundled files (sub-agents, cross-skill scripts, etc.)
            for bundle_src in it.get("bundles", []):
                bundle_path = project_root / bundle_src
                bundle_dst = skills_root / _normalize_dest(bundle_src)
                if bundle_path.exists():
                    _copy_one(bundle_path, bundle_dst)
                    print(f"  {GRN}{TIK}{RST} {bundle_src}  {DIM}{ARR}{RST}  {_rel_path(bundle_dst)}")
            # command files (installed to <config>/commands/)
            for cmd_src in it.get("commands", []):
                cmd_path = project_root / it["dir"] / "commands" / cmd_src
                cmd_dst = cmds_root / cmd_src
                if cmd_path.exists():
                    cmd_dst.parent.mkdir(parents=True, exist_ok=True)
                    _copy_one(cmd_path, cmd_dst)
                    print(f"  {GRN}{TIK}{RST} command/{cmd_src}  {DIM}{ARR}{RST}  {_rel_path(cmd_dst)}")
            # commands generated from the vendor's metadata table (never vendored)
            for cmd_name, cmd_content in _generated_commands(project_root, it):
                cmd_dst = cmds_root / cmd_name
                cmd_dst.parent.mkdir(parents=True, exist_ok=True)
                cmd_dst.write_text(cmd_content, "utf-8", newline="\n")
                print(f"  {GRN}{TIK}{RST} command/{cmd_name}  {DIM}{ARR}{RST}  {_rel_path(cmd_dst)}")
        else:
            _remove_one(dst)
            # also remove bundled files
            for bundle_src in it.get("bundles", []):
                bundle_dst = skills_root / _normalize_dest(bundle_src)
                _remove_one(bundle_dst)
            # also remove command files
            for cmd_src in it.get("commands", []):
                cmd_dst = cmds_root / cmd_src
                _remove_one(cmd_dst)
            for cmd_name, _ in _generated_commands(project_root, it):
                _remove_one(cmds_root / cmd_name)


def _item_dest(item: dict, skills_root: Path, agents_dir: Path) -> Path:
    """Compute the install destination for a single item."""
    if item["type"] == "agent":
        return agents_dir / Path(item["dir"]).name
    return skills_root / _normalize_dest(item["dir"])


# ── verify an installed config ────────────────────────────────────────────────


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_digests(root: Path) -> dict[str, str]:
    """relative path -> sha256 for every file under root (skips bytecode caches)."""
    out: dict[str, str] = {}
    for f in root.rglob("*"):
        if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc":
            out[str(f.relative_to(root)).replace("\\", "/")] = _digest(f)
    return out


def _tree_drift(src: Path, dst: Path) -> list[str]:
    """Differences between a repo source (file or dir) and its installed copy.

    ``copy2``/``copytree`` are byte-exact, so any hash difference is real drift:
    either the source moved ahead of the install or the installed file was edited.
    """
    if src.is_file():
        if not dst.is_file():
            return [f"missing {dst.name}"]
        return [] if _digest(src) == _digest(dst) else [f"stale {dst.name}"]
    if not dst.is_dir():
        return ["not installed"]
    expected, actual = _tree_digests(src), _tree_digests(dst)
    problems = [f"missing {k}" for k in sorted(set(expected) - set(actual))]
    problems += [f"stale {k}" for k in sorted(set(expected) & set(actual)) if expected[k] != actual[k]]
    problems += [f"extra {k}" for k in sorted(set(actual) - set(expected))]
    return problems


def check_installed(
    project_root: Path,
    skills_root: Path,
    agents_dir: Path,
    plugins_dir: Path | None,
    platform_id: str,
) -> int:
    """Report drift between the manifest and an installed config.

    Returns the number of problems (missing or stale items/commands). Unrelated
    entries living in the destination are listed as notes, not problems: another
    tool can legitimately drop skills or plugins in the same config directory.
    """
    cmds_root = _commands_root(skills_root)
    problems: list[str] = []
    notes: list[str] = []
    checked = 0

    for it in ITEMS:
        applies = it.get("platforms") is None or platform_id in it.get("platforms", [])
        if not applies:
            continue
        src = project_root / it["dir"]

        if it["type"] == "plugin":
            if not plugins_dir:
                continue
            entry = plugins_dir / f"{it['id']}.ts"
            if not entry.is_file():
                notes.append(f"{it['id']}: not installed (plugin)")
                continue
            checked += 1
            problems += [
                f"{it['id']}: {p}"
                for p in _tree_drift(src / it.get("entry", "notification.ts"), entry)
            ]
            for fname in it.get("files", []):
                problems += [
                    f"{it['id']}: asset {p}"
                    for p in _tree_drift(src / fname, plugins_dir / it["id"] / fname)
                ]
        else:
            checked += 1
            problems += [f"{it['id']}: {p}" for p in _tree_drift(src, _item_dest(it, skills_root, agents_dir))]

        for cmd_name, cmd_content in _generated_commands(project_root, it):
            cmd_dst = cmds_root / cmd_name
            if not cmd_dst.is_file():
                problems.append(f"{it['id']}: command {cmd_name} missing")
            elif cmd_dst.read_text("utf-8", errors="ignore") != cmd_content:
                problems.append(f"{it['id']}: command {cmd_name} stale")
        for cmd_src in it.get("commands", []):
            src_cmd = project_root / it["dir"] / "commands" / cmd_src
            if not src_cmd.is_file():
                continue
            dst_cmd = cmds_root / cmd_src
            if not dst_cmd.is_file():
                problems.append(f"{it['id']}: command {cmd_src} missing")
            elif _digest(src_cmd) != _digest(dst_cmd):
                problems.append(f"{it['id']}: command {cmd_src} stale")

    if skills_root.is_dir():
        known = {_normalize_dest(i["dir"]) for i in ITEMS if i["type"] == "skill"}
        for entry in sorted(skills_root.iterdir()):
            if entry.is_dir() and entry.name not in known:
                notes.append(f"{entry.name}: extra skill in the destination")

    if problems:
        print(f"  {RED}{BLD}DRIFT:{RST} {len(problems)} problem(s) against the manifest")
        for p in problems:
            print(f"  {RED}x{RST} {p}")
    for n in notes:
        print(f"  {DIM}- {n}{RST}")
    if problems:
        print(f"  {DIM}fix: python setup.py --only <ids> --global --platform {platform_id}{RST}")
        return len(problems)
    print(f"  {GRN}{TIK}{RST} In sync: {checked} item(s) verified against the manifest.")
    return 0


def cleanup_orphaned_mds(skills_dir: Path) -> None:
    """Remove stale leftovers from previous (double-nested) installs.

    Older installs placed items under ``<skills>/skills/`` and agents under
    ``<skills>/agents/``. New installs put skills directly in ``skills_dir``
    and agents in the platform's ``agent``/``agents`` directory, so any
    nested ``skills/`` or ``agents/`` dir inside the skills root is stale.
    """
    if not skills_dir.exists():
        return
    for stale in ("skills", "agents"):
        nested = skills_dir / stale
        if nested.exists():
            shutil.rmtree(nested)
            print(f"  {YLW}{X}{RST} Removed stale nested dir: {_rel_path(nested)}")


# ── agent registration ────────────────────────────────────────────────────────


def agent_targets(dest: Path | None = None, agents_file: Path | None = None) -> None:
    """Generate agents JSON file from skill dirs."""
    d = dest or (_repo_root() / ".opencode")
    agents = []
    af = agents_file or (d / "agents.json")
    existing: list = json.loads(af.read_text("utf-8")) if af.exists() else []
    existing_ids = {a.get("name") or a.get("id") for a in existing}
    for it in ITEMS:
        if it["type"] == "agent":
            if it["label"] not in existing_ids:
                agents.append({"id": it["id"], "dir": it["dir"], "name": it["label"]})
    if agents:
        af.parent.mkdir(parents=True, exist_ok=True)
        existing.extend(agents)
        af.write_text(json.dumps(existing, indent=2, ensure_ascii=False), "utf-8")
        print(f"  {GRN}{TIK}{RST} Appended {len(agents)} agent(s) to {_rel_path(af)}")
    else:
        print("  -- All agents already registered.")


# ── main ──────────────────────────────────────────────────────────────────────


def _parse_args() -> dict[str, str | bool | None]:
    """Parse CLI arguments using argparse."""
    import argparse as _ap
    parser = _ap.ArgumentParser(description="Toggle skills/agents and install them.")
    parser.add_argument("-a", "--all", action="store_true", help="Install all items")
    parser.add_argument("-g", "--global", action="store_true", dest="global_", help="Install globally")
    parser.add_argument("--local", action="store_true", help="Install locally")
    parser.add_argument("--platform", default=None, help="Target platform")
    parser.add_argument("--manifest", action="store_true", help="Print JSON inventory and exit (for AI agents)")
    parser.add_argument("--only", nargs="+", default=None, metavar="ID",
                        help="Install just these item ids (never removes anything else)")
    parser.add_argument("--check", action="store_true",
                        help="Verify the installed config against the manifest, write nothing, exit 1 on drift")
    parsed = parser.parse_args()
    return {"all": parsed.all, "global": parsed.global_, "local": parsed.local,
            "platform": parsed.platform, "manifest": parsed.manifest, "only": parsed.only,
            "check": parsed.check}


def print_manifest() -> None:
    """Print a machine-readable inventory of every installable item."""
    from collections import Counter

    counts = Counter(it["type"] for it in ITEMS)
    root = _repo_root()
    sys.stdout.write(
        json.dumps(
            {
                "repo_root": str(root),
                "count": {
                    "agents": counts.get("agent", 0),
                    "skills": counts.get("skill", 0),
                    "plugins": counts.get("plugin", 0),
                },
                "items": [
                    {
                        "id": it["id"],
                        "type": it["type"],
                        "label": it["label"],
                        "src": it["dir"],
                        "dependencies": it.get("dependencies", []),
                        "commands": _item_command_names(root, it),
                        "platforms": it.get("platforms"),
                    }
                    for it in ITEMS
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    sys.stdout.write("\n")


def main() -> None:
    base = Path.cwd()
    cli = _parse_args()

    if cli["manifest"]:
        print_manifest()
        sys.exit(0)

    # ── --check: verify an installed config, write nothing ──
    if cli["check"]:
        if not cli["platform"]:
            print(f"  {RED}--check needs --platform <id>{RST}")
            sys.exit(2)
        if not (cli["global"] or cli["local"]):
            print(f"  {RED}--check needs --global or --local{RST}")
            sys.exit(2)
        if cli["platform"] not in PLATFORMS:
            print(f"  {RED}Unknown platform: {cli['platform']}{RST}")
            sys.exit(1)
        check_mode = "global" if cli["global"] else "local"
        check_paths = _get_install_paths(cli["platform"], check_mode)
        label = PLATFORMS[cli["platform"]]["label"]
        print(f"  {GRN}{TIK}{RST} Checking {label} ({check_mode}): {check_paths['skills_dir']}")
        drift = check_installed(
            base,
            check_paths["skills_dir"],
            check_paths["agents_dir"],
            check_paths["plugins_dir"],
            cli["platform"],
        )
        sys.exit(1 if drift else 0)

    # ── Platform selection ──
    if cli["platform"]:
        if cli["platform"] not in PLATFORMS:
            print(f"  {RED}Unknown platform: {cli['platform']}{RST}")
            print(f"  {DIM}Available: {', '.join(PLATFORMS.keys())}{RST}")
            sys.exit(1)
        platform_id = cli["platform"]
        print(f"  {GRN}{TIK}{RST} Platform: {PLATFORMS[platform_id]['label']} (via --platform)")
    else:
        platform_id = _prompt_platform()
        print(f"  {GRN}{TIK}{RST} Platform: {PLATFORMS[platform_id]['label']}")

    # ── Install mode ──
    if cli["global"]:
        mode = "global"
        print(f"  {GRN}{TIK}{RST} Mode: Global (via --global)")
    elif cli["local"]:
        mode = "local"
        print(f"  {GRN}{TIK}{RST} Mode: Local project (via --local)")
    else:
        mode = _prompt_install_mode()
        print(f"  {GRN}{TIK}{RST} Mode: {'Global (machine)' if mode == 'global' else 'Local project'}")

    # ── Resolve paths ──
    paths = _get_install_paths(platform_id, mode)
    skills_dir = paths["skills_dir"]
    agents_file = paths["agents_file"]
    agents_dir = paths["agents_dir"]
    plugins_dir = paths["plugins_dir"]
    uses_agents_json = paths["uses_agents_json"]
    print(f"  {DIM}Skills dir: {skills_dir}{RST}")
    print(f"  {DIM}Agents dir: {agents_dir}{RST}")
    if plugins_dir:
        print(f"  {DIM}Plugins dir: {plugins_dir}{RST}")
    if uses_agents_json:
        print(f"  {DIM}Agents file: {agents_file}{RST}")

    # ── Toggle menu or --all / --only ──
    only = set(cli["only"]) if cli["only"] else None
    if cli["all"]:
        toggled = {it["id"]: True for it in ITEMS}
    elif only is not None:
        unknown = sorted(only - {it["id"] for it in ITEMS})
        if unknown:
            print(f"  {RED}Unknown item id(s): {', '.join(unknown)}{RST}")
            sys.exit(1)
        toggled = {it["id"]: it["id"] in only for it in ITEMS}
    else:
        toggled = run_toggle_menu()

    print(f"\n  {BLD}Installing to {PLATFORMS[platform_id]['label']} ({mode})...{RST}\n")
    install_items(toggled, base, skills_dir, agents_dir, plugins_dir=plugins_dir, platform_id=platform_id, only=only)
    if uses_agents_json:
        agent_targets(agents_file=agents_file)
    cleanup_orphaned_mds(skills_dir)

    print(f"\n  {GRN}{BLD}{TIK} Done.{RST}")
    print(f"  {DIM}Installed {sum(1 for v in toggled.values() if v)} items to {skills_dir}{RST}\n")


if __name__ == "__main__":
    main()
