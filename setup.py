"""Interactive setup: toggle skills/agents, install them, and keep repo clean.

Usage:
    python scripts/setup.py              # from repo root
    python setup.py                       # standalone at project root
    git clone ... && python setup.py      # one-liner
    python scripts/setup.py --all        # install all without menu
    python scripts/setup.py --global     # install to user-level config
    python scripts/setup.py --all --platform claude --local
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


def _git(args: list[str], check=True, **kw):
    return subprocess.run(["git", *args], check=check, **kw)


# ── platform / agent detection ────────────────────────────────────────────────

PLATFORMS: dict[str, dict] = {
    "opencode": {
        "label": "OpenCode",
        "config_dir": ".opencode",
        "skills_subdir": "skills",
        "agents_file": "agents.json",
        "detect_files": [".opencode"],
        "global_dir": Path.home() / ".config" / "opencode",
    },
    "claude": {
        "label": "Claude Code",
        "config_dir": ".claude",
        "skills_subdir": "skills",
        "agents_file": "agents.json",
        "detect_files": [".claude"],
        "global_dir": Path.home() / ".claude",
    },
    "cursor": {
        "label": "Cursor",
        "config_dir": ".cursor",
        "skills_subdir": "skills",
        "agents_file": "agents.json",
        "detect_files": [".cursor"],
        "global_dir": Path.home() / ".cursor",
    },
    "windsurf": {
        "label": "Windsurf",
        "config_dir": ".windsurf",
        "skills_subdir": "skills",
        "agents_file": "agents.json",
        "detect_files": [".windsurf"],
        "global_dir": Path.home() / ".windsurf",
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


def _get_install_paths(platform_id: str, mode: str) -> tuple[Path, Path]:
    """Return (skills_dir, agents_file) based on platform and mode."""
    info = PLATFORMS[platform_id]
    if mode == "global":
        base = info["global_dir"]
    else:
        base = Path.cwd() / info["config_dir"]
    skills_dir = base / info["skills_subdir"]
    agents_file = base / info["agents_file"]
    return skills_dir, agents_file


# ── ITEMS definition ──────────────────────────────────────────────────────────

ITEMS: list[dict] = [
    # ── agents ────────────────────────────────────────────────────────────────
    {
        "id": "vault-indexer",
        "dir": "agents/vault-indexer.md",
        "label": "Vault Indexer",
        "type": "agent",
        "dependencies": [],
        "bundles": ["agents/vault-researcher.md"],
    },
    {
        "id": "paper-researcher",
        "dir": "agents/paper-researcher.md",
        "label": "Paper Researcher",
        "type": "agent",
        "dependencies": ["academic-source-search", "citation-formatter"],
    },
    {
        "id": "vault-search",
        "dir": "agents/vault-search.md",
        "label": "Vault Search",
        "type": "agent",
        "dependencies": ["vault-indexer"],
    },
    {
        "id": "vault-organizer",
        "dir": "agents/vault-organizer.md",
        "label": "Vault Organizer",
        "type": "agent",
        "dependencies": ["vault-indexer", "vault-search"],
    },
    {
        "id": "roadmaps",
        "dir": "agents/roadmaps.md",
        "label": "Roadmaps",
        "type": "agent",
        "dependencies": ["telegram-notify"],
        "bundles": ["skills/roadmaps/scripts", "skills/roadmaps/templates", "skills/roadmaps/evals"],
    },
    {
        "id": "jobfinder",
        "dir": "agents/jobfinder.md",
        "label": "Job Finder",
        "type": "agent",
        "dependencies": [],
        "bundles": ["skills/jobfinder/scripts", "skills/jobfinder/templates"],
    },
    {
        "id": "metric-optimizer",
        "dir": "agents/metric-optimizer.md",
        "label": "Metric Optimizer",
        "type": "agent",
        "dependencies": [],
        "bundles": ["skills/metric-optimizer/templates"],
    },
    # ── skills ────────────────────────────────────────────────────────────────
    {
        "id": "research-pipeline",
        "dir": "skills/research-pipeline",
        "label": "Research Pipeline",
        "type": "skill",
        "dependencies": ["telegram-notify"],
    },
    {
        "id": "telegram-notify",
        "dir": "skills/telegram-notify",
        "label": "Telegram Notify",
        "type": "skill",
        "dependencies": [],
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
    },
    {
        "id": "skill-creator",
        "dir": "skills/skill-creator",
        "label": "Skill Creator",
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
        "id": "osint",
        "dir": "skills/osint",
        "label": "OSINT Investigator",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "impeccable",
        "dir": "skills/impeccable",
        "label": "Impeccable (third-party)",
        "type": "skill",
        "dependencies": [],
    },
    {
        "id": "project-analyzer",
        "dir": "skills/project-analyzer",
        "label": "Project Analyzer",
        "type": "skill",
        "dependencies": [],
        "commands": ["commands/init_review.md"],
    },
]

_TYPE_ORDER = {"agent": 0, "skill": 1}
_TYPE_LABEL = {"agent": "Agents", "skill": "Skills"}

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
    """Copy a single file or directory from src to dst."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
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


def install_items(toggled: dict[str, bool], project_root: Path, skills_root: Path) -> None:
    """Copy enabled items into the project (files or directories)."""
    skills_root.mkdir(parents=True, exist_ok=True)
    cmds_root = _commands_root(skills_root)

    for it in ITEMS:
        src = project_root / it["dir"]
        dst = skills_root / it["dir"]
        enabled = toggled.get(it["id"], False)

        if enabled:
            if not src.exists():
                print(f"  {YLW}..{RST} {it['label']}  source not found: {_rel_path(src)}")
            else:
                _copy_one(src, dst)
                print(f"  {GRN}{TIK}{RST} {it['label']}  {DIM}{ARR}{RST}  {_rel_path(dst)}")
            # bundled files (sub-agents, etc.)
            for bundle_src in it.get("bundles", []):
                bundle_path = project_root / bundle_src
                bundle_dst = skills_root / bundle_src
                if bundle_path.exists():
                    _copy_one(bundle_path, bundle_dst)
                    print(f"  {GRN}{TIK}{RST} {bundle_src}  {DIM}{ARR}{RST}  {_rel_path(bundle_dst)}")
            # command files (installed to <config>/commands/)
            for cmd_src in it.get("commands", []):
                cmd_path = project_root / it["dir"] / cmd_src
                cmd_dst = cmds_root / cmd_src
                if cmd_path.exists():
                    cmd_dst.parent.mkdir(parents=True, exist_ok=True)
                    _copy_one(cmd_path, cmd_dst)
                    print(f"  {GRN}{TIK}{RST} command/{cmd_src}  {DIM}{ARR}{RST}  {_rel_path(cmd_dst)}")
        else:
            _remove_one(dst)
            # also remove bundled files
            for bundle_src in it.get("bundles", []):
                bundle_dst = skills_root / bundle_src
                _remove_one(bundle_dst)
            # also remove command files
            for cmd_src in it.get("commands", []):
                cmd_dst = cmds_root / cmd_src
                _remove_one(cmd_dst)


def cleanup_repo(skills_dir: Path | None = None) -> None:
    """Remove skills directory to trigger reinstall on next run."""
    d = skills_dir or (_repo_root() / ".opencode" / "skills")
    if d.exists():
        shutil.rmtree(d)
        print(f"  {GRN}{TIK}{RST} Cleared {_rel_path(d)}")
    else:
        print("  -- Nothing to clean.")


def cleanup_orphaned_mds(skills_dir: Path) -> None:
    """Remove standalone .md files in skills dir that are leftovers from old installs."""
    if not skills_dir.exists():
        return
    for md_file in skills_dir.rglob("*.md"):
        # Only remove .md files directly in skills/skills/ (not SKILL.md inside subdirs)
        if md_file.parent == skills_dir / "skills" and md_file.name != "SKILL.md":
            md_file.unlink()
            print(f"  {YLW}{X}{RST} Removed orphaned: {_rel_path(md_file)}")


# ── adapt / push / pull ───────────────────────────────────────────────────────


def adapt_md_content(content: str, item_id: str) -> str:
    """Replace placeholders in skill files."""
    return content.replace("{{AGENT_ID}}", item_id)


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


def _parse_args() -> dict[str, str | bool]:
    """Parse CLI arguments using argparse."""
    import argparse as _ap
    parser = _ap.ArgumentParser(description="Toggle skills/agents and install them.")
    parser.add_argument("-a", "--all", action="store_true", help="Install all items")
    parser.add_argument("-g", "--global", action="store_true", dest="global_", help="Install globally")
    parser.add_argument("--local", action="store_true", help="Install locally")
    parser.add_argument("--platform", default=None, help="Target platform")
    parsed = parser.parse_args()
    return {"all": parsed.all, "global": parsed.global_, "local": parsed.local, "platform": parsed.platform}


def main() -> None:
    base = Path.cwd()
    cli = _parse_args()

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
    skills_dir, agents_file = _get_install_paths(platform_id, mode)
    print(f"  {DIM}Skills dir: {skills_dir}{RST}")
    print(f"  {DIM}Agents file: {agents_file}{RST}")

    # ── Toggle menu or --all ──
    if cli["all"]:
        toggled = {it["id"]: True for it in ITEMS}
    else:
        toggled = run_toggle_menu()

    print(f"\n  {BLD}Installing to {PLATFORMS[platform_id]['label']} ({mode})...{RST}\n")
    install_items(toggled, base, skills_dir)
    agent_targets(agents_file=agents_file)
    cleanup_orphaned_mds(skills_dir)

    print(f"\n  {GRN}{BLD}{TIK} Done.{RST}")
    print(f"  {DIM}Installed {sum(1 for v in toggled.values() if v)} items to {skills_dir}{RST}\n")


if __name__ == "__main__":
    main()
