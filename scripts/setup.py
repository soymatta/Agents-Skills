#!/usr/bin/env python3
"""
Cross-platform installer for AI agents and skills.

Detects your AI agent (OpenCode, Claude Code, VS Code, Kimi),
lets you choose what to install, and copies everything to the
right location — project-wide or globally.

Usage:
    python scripts/setup.py
"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path

# ── ANSI Colors ──────────────────────────────────────────────────────────────

_SUPPORTS_COLOR: bool = (os.name != "nt") or bool(os.environ.get("TERM")) or bool(os.environ.get("WT_SESSION"))
if not _SUPPORTS_COLOR:
    try:
        import colorama
        colorama.init()
        _SUPPORTS_COLOR = True
    except ImportError:
        pass

def _c(code: str) -> str:
    return f"\033[{code}m" if _SUPPORTS_COLOR else ""

C_BOLD   = _c("1")
C_DIM    = _c("2")
C_CYAN   = _c("36")
C_GREEN  = _c("32")
C_YELLOW = _c("33")
C_RED    = _c("31")
C_BLUE   = _c("34")
C_RESET  = _c("0")

BOX_W = 74

# ── Items ────────────────────────────────────────────────────────────────────
# Each entry: type, source path (relative to repo root), name, description,
# limitations, and whether it's a directory (has scripts inside).

ITEMS: list[dict] = [
    {
        "type": "agent",
        "source": "agents/vault-indexer.md",
        "name": "vault-indexer",
        "description": "Lee y responde SOLO del contenido del vault de notas.",
        "limitations": "NO modifica archivos. NO inventa informacion. NO busca en internet.",
        "is_dir": False,
    },
    {
        "type": "agent",
        "source": "agents/vault-researcher.md",
        "name": "vault-researcher",
        "description": "Busca en fuentes externas para verificar conceptos del vault.",
        "limitations": "NO modifica archivos del vault. NO impone cambios. Solo sugiere.",
        "is_dir": False,
    },
    {
        "type": "skill",
        "source": "skills/vault-search.md",
        "name": "vault-search",
        "description": "Busca temas dentro del vault usando glob y grep.",
        "limitations": "NO modifica archivos. Solo busca dentro del proyecto.",
        "is_dir": False,
    },
    {
        "type": "skill",
        "source": "skills/vault-organizer.md",
        "name": "vault-organizer",
        "description": "Sugiere donde colocar informacion en el vault.",
        "limitations": "NO muestra ni edita contenido. Solo sugiere ubicaciones.",
        "is_dir": False,
    },
    {
        "type": "skill",
        "source": "skills/research-pipeline.md",
        "name": "research-pipeline",
        "description": "Pipeline de investigacion cuantitativa para prediction markets.",
        "limitations": "NO pregunta al usuario. NO se detiene por errores.",
        "is_dir": False,
    },
    {
        "type": "skill",
        "source": "skills/goal-pursuit.md",
        "name": "goal-pursuit",
        "description": "Loop autonomo que optimiza hasta alcanzar un target numerico.",
        "limitations": "NO pregunta al usuario. NO se detiene hasta cumplir la meta.",
        "is_dir": False,
    },
    {
        "type": "skill",
        "source": "skills/telegram-notify.md",
        "name": "telegram-notify",
        "description": "Envia notificaciones Telegram para eventos del proyecto.",
        "limitations": "NO pregunta al usuario. NO bloquea la ejecucion si falla.",
        "is_dir": False,
    },
    {
        "type": "skill",
        "source": "skills/backtest-run.md",
        "name": "backtest-run",
        "description": "Ejecuta backtests con configuracion del proyecto.",
        "limitations": "NO pregunta al usuario. NO usa la nube por defecto.",
        "is_dir": False,
    },
    {
        "type": "skill",
        "source": "skills/backtest-validate",
        "name": "backtest-validate",
        "description": "Valida calidad de backtests con scoring 5-dimensional. Incluye script Python.",
        "limitations": "NO ejecuta backtests (usa backtest-run para eso). Solo evalua resultados.",
        "is_dir": True,
    },
    {
        "type": "agent",
        "source": "agents/academic-researcher.md",
        "name": "academic-researcher",
        "description": "Produce trabajos academicos en Markdown (APA/IEEE/Vancouver). Solo fuentes cientificas.",
        "limitations": "NO inventa fuentes. NO usa fuentes no cientificas. NO modifica referencias.",
        "is_dir": False,
    },
    {
        "type": "skill",
        "source": "skills/academic-source-search.md",
        "name": "academic-source-search",
        "description": "Busca fuentes cientificas en bases de datos academicas (Scholar, arXiv, PubMed).",
        "limitations": "NO usa Wikipedia como fuente primaria. Solo fuentes con DOI/URL verificable.",
        "is_dir": False,
    },
    {
        "type": "skill",
        "source": "skills/citation-style-guide.md",
        "name": "citation-style-guide",
        "description": "Referencia de formato APA 7th / IEEE / Vancouver para citas y referencias.",
        "limitations": "NO mezcla normas. NO omite DOI cuando esta disponible.",
        "is_dir": False,
    },
    {
        "type": "skill",
        "source": "skills/content-humanizer",
        "name": "content-humanizer",
        "description": "Pase final anti-deteccion IA. Ajusta estructura, lexico y fluidez. Incluye script detector.",
        "limitations": "NO modifica datos, citas, referencias ni estructura academica.",
        "is_dir": True,
    },
]

# ── Helpers ──────────────────────────────────────────────────────────────────


def repo_root() -> Path:
    """Return the repo root (parent of the scripts/ directory)."""
    return Path(__file__).resolve().parent.parent


def clear_screen() -> None:
    """Cross-platform clear screen."""
    os.system("cls" if os.name == "nt" else "clear")


def println(text: str = "") -> None:
    """Print with reset."""
    print(f"{C_RESET}{text}")


def print_title(text: str) -> None:
    """Print a section title."""
    print(f"\n{C_BOLD}{C_BLUE}┌{'─' * (BOX_W - 2)}┐{C_RESET}")
    print(f"{C_BOLD}{C_BLUE}│{C_RESET}  {C_BOLD}◆  {text}{C_RESET}")
    print(f"{C_BOLD}{C_BLUE}└{'─' * (BOX_W - 2)}┘{C_RESET}\n")


def print_step(text: str) -> None:
    """Print a progress step with checkmark."""
    print(f"  {C_GREEN}✓{C_RESET} {text}")


# ── Input helpers ────────────────────────────────────────────────────────────


def getch() -> str:
    """Read a single keypress (cross-platform, no dependencies)."""
    try:
        import msvcrt
        while True:
            ch = msvcrt.getwch()
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch == "\r":
                return "enter"
            if ch == "\x1b":
                return "esc"
            return ch
    except ImportError:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd, termios.TCSADRAIN)
            ch = sys.stdin.read(1)
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch == "\r":
                return "enter"
            if ch == "\x1b":
                return "esc"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def ask_yesno(prompt: str, default: bool = True) -> bool:
    """Ask a yes/no question and return bool."""
    hint = " [Y/n]" if default else " [y/N]"
    while True:
        answer = input(f"{prompt}{hint}: ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False


def ask_choice(prompt: str, options: list[str]) -> str:
    """Show numbered options and let user pick one."""
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        try:
            choice = input(f"\nOpcion [1-{len(options)}]: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except (ValueError, IndexError):
            pass


# ── OS detection ─────────────────────────────────────────────────────────────


def detect_os() -> str:
    """Return 'linux', 'windows', 'macos', or 'unknown'."""
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform.startswith("darwin"):
        return "macos"
    return "unknown"


# ── Agent detection ──────────────────────────────────────────────────────────


def find_open_code(home: Path, cwd: Path) -> bool:
    """Detect OpenCode by config files."""
    if (cwd / "opencode.json").exists():
        return True
    if (cwd / ".opencode").is_dir():
        return True
    if (home / ".config" / "opencode").is_dir():
        return True
    return False


def find_claude_code(home: Path, cwd: Path) -> bool:
    """Detect Claude Code by config files."""
    if (cwd / "CLAUDE.md").exists():
        return True
    if (home / ".claude").is_dir():
        return True
    return False


def find_vscode(cwd: Path) -> bool:
    """Detect VS Code / Copilot by config files."""
    if (cwd / ".vscode").is_dir():
        return True
    if (cwd / ".github" / "copilot-instructions.md").exists():
        return True
    return False


def find_kimi(home: Path) -> bool:
    """Detect Kimi by config directory."""
    return (home / ".kimi").is_dir()


def detect_agent() -> str:
    """Detect which AI agent is being used. Returns agent id string."""
    home = Path.home()
    cwd = Path.cwd()

    found: list[str] = []
    if find_open_code(home, cwd):
        found.append("opencode")
    if find_claude_code(home, cwd):
        found.append("claude-code")
    if find_vscode(cwd):
        found.append("vscode")
    if find_kimi(home):
        found.append("kimi")

    if len(found) == 1:
        return found[0]

    if len(found) > 1:
        print("\nSe detectaron multiples agentes:")
        return ask_choice("Cual quieres configurar?", found)

    print("\nNo se pudo detectar automaticamente tu agente.")
    return ask_choice("Selecciona tu agente:", [
        "opencode", "claude-code", "vscode", "kimi", "otro"
    ])


# ── Target paths per agent ───────────────────────────────────────────────────


def agent_targets(agent: str, scope: str, base: Path) -> dict:
    """Return {agents_dir, skills_dir} for given agent and scope.

    ``scope`` is 'project' or 'global'. ``base`` is the project root
    (when scope='project') or $HOME (when scope='global').
    """
    if scope == "project":
        if agent == "opencode":
            return {"agents": base / ".opencode" / "agents",
                    "skills": base / ".opencode" / "skills"}
        if agent == "claude-code":
            return {"agents": base / ".claude" / "instructions",
                    "skills": base / ".claude" / "instructions"}
        if agent == "vscode":
            return {"agents": base / ".github" / "instructions",
                    "skills": base / ".github" / "instructions"}
        if agent == "kimi":
            return {"agents": base / ".kimi",
                    "skills": base / ".kimi"}
        return {"agents": base / ".ai" / "instructions",
                "skills": base / ".ai" / "instructions"}
    else:
        home = Path.home()
        if agent == "opencode":
            return {"agents": home / ".config" / "opencode" / "agents",
                    "skills": home / ".config" / "opencode" / "skills"}
        if agent == "claude-code":
            return {"agents": home / ".claude" / "instructions",
                    "skills": home / ".claude" / "instructions"}
        if agent == "vscode":
            return {"agents": home / ".vscode" / "instructions",
                    "skills": home / ".vscode" / "instructions"}
        if agent == "kimi":
            return {"agents": home / ".kimi",
                    "skills": home / ".kimi"}
        return {"agents": home / ".ai" / "instructions",
                "skills": home / ".ai" / "instructions"}


# ── Content adaptation per agent ─────────────────────────────────────────────


def adapt_md_content(content: str, agent: str) -> str:
    """Adapt markdown content for the target agent's format.

    - OpenCode: keeps YAML frontmatter as-is (native format)
    - Others: strips frontmatter, keeps only the markdown body
    """
    if agent == "opencode":
        return content
    # Strip YAML frontmatter for non-OpenCode agents
    lines = content.split("\n")
    if lines and lines[0].strip() == "---":
        end = 1
        while end < len(lines):
            if lines[end].strip() == "---":
                end += 1
                break
            end += 1
        return "\n".join(lines[end:]).strip()
    return content


# ── Toggle menu ──────────────────────────────────────────────────────────────


def _menu_box(items: list[dict], toggled: list[bool]) -> None:
    """Render the toggle menu."""
    inner = BOX_W - 4

    # Header
    print(f"{C_BLUE}┌{'─' * (BOX_W - 2)}┐{C_RESET}")
    title = f"◆  AGENTS-SKILLS  —  Selección de Componentes"
    print(f"{C_BLUE}│{C_RESET}  {C_BOLD}{title}{C_RESET}  {' ' * max(0, inner - len(title) - 2)}{C_BLUE}│{C_RESET}")
    print(f"{C_BLUE}├{'─' * (BOX_W - 2)}┤{C_RESET}")

    # Instructions
    hint = (
        f"  {C_DIM}[{C_RESET}{C_YELLOW}#{C_RESET}{C_DIM}] Alternar{C_RESET}"
        f"   {C_DIM}[{C_RESET}{C_GREEN}d{C_RESET}{C_DIM}] Instalar{C_RESET}"
        f"   {C_DIM}[{C_RESET}{C_RED}q{C_RESET}{C_DIM}] Salir{C_RESET}"
    )
    pad = inner - len(hint) + 4  # +4 because hint doesn't include the leading "│  "
    print(f"{C_BLUE}│{C_RESET}  {hint}{' ' * max(0, pad)}{C_BLUE}│{C_RESET}")

    # Separator
    print(f"{C_BLUE}├{'─' * (BOX_W - 2)}┤{C_RESET}")

    # Items
    for i, item in enumerate(items):
        mark = f"{C_GREEN}●{C_RESET}" if toggled[i] else f"{C_DIM}○{C_RESET}"
        tag = f"{C_CYAN}agent{C_RESET}" if item["type"] == "agent" else f"{C_GREEN}skill{C_RESET}"
        num = f"{i + 1:2d}"
        name = item["name"][:22].ljust(22)
        desc = item["description"]
        content = f"{mark} {num}  {name}  {tag}  {desc}"
        if len(content) > inner:
            content = content[: inner - 1] + "…"
        else:
            content = content.ljust(inner)
        print(f"{C_BLUE}│{C_RESET}  {content}  {C_BLUE}│{C_RESET}")

    # Footer
    print(f"{C_BLUE}├{'─' * (BOX_W - 2)}┤{C_RESET}")
    count = sum(toggled)
    total = len(ITEMS)
    color = C_GREEN if count == total else C_YELLOW if count > 0 else C_RED
    suffix = f"  ({C_DIM}todos{C_RESET})" if count == total else ""
    sel = f"{color}Seleccionados: {count}/{total}{C_RESET}{suffix}"
    print(f"{C_BLUE}│{C_RESET}  {sel}{' ' * max(0, inner - len(sel) + 4)}{C_BLUE}│{C_RESET}")
    print(f"{C_BLUE}└{'─' * (BOX_W - 2)}┘{C_RESET}")


def run_toggle_menu() -> list[dict]:
    """Interactive toggle menu. Returns selected items."""
    toggled = [True] * len(ITEMS)

    while True:
        clear_screen()
        _menu_box(ITEMS, toggled)

        key = getch()

        if key == "q":
            println(f"\n  {C_YELLOW}Instalación cancelada.{C_RESET}")
            sys.exit(0)
        if key in ("d", "enter"):
            if not any(toggled):
                println(f"\n  {C_RED}Selecciona al menos un componente.{C_RESET}")
                input(f"  {C_DIM}Presiona Enter para continuar...{C_RESET}")
                continue
            break
        if key.isdigit():
            idx = int(key) - 1
            if 0 <= idx < len(ITEMS):
                toggled[idx] = not toggled[idx]

    return [ITEMS[i] for i, t in enumerate(toggled) if t]


# ── Installer ────────────────────────────────────────────────────────────────


def _rel_path(path: Path, base: Path) -> str:
    """Return path relative to base, or full path if not under base."""
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def install_items(
    selected: list[dict],
    agent: str,
    targets: dict,
    repo: Path,
    project_root: Path,
) -> None:
    """Copy selected items from repo to target directories."""
    agents_dir = targets["agents"]
    skills_dir = targets["skills"]

    println()
    for item in selected:
        dest_dir = agents_dir if item["type"] == "agent" else skills_dir
        src = repo / item["source"]

        if item["is_dir"]:
            dest = dest_dir / item["name"]
            dest.mkdir(parents=True, exist_ok=True)
            for f in src.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(src)
                    dest_file = dest / rel
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    if f.suffix == ".md":
                        content = f.read_text(encoding="utf-8")
                        content = adapt_md_content(content, agent)
                        dest_file.write_text(content, encoding="utf-8")
                    else:
                        shutil.copy2(f, dest_file)
            print_step(f"{C_BOLD}{item['name']}/{C_RESET}  {C_DIM}→{C_RESET}  {_rel_path(dest, project_root)}")
        else:
            dest = dest_dir / f"{item['name']}.md"
            dest.parent.mkdir(parents=True, exist_ok=True)
            content = src.read_text(encoding="utf-8")
            content = adapt_md_content(content, agent)
            dest.write_text(content, encoding="utf-8")
            print_step(f"{C_BOLD}{item['name']}.md{C_RESET}  {C_DIM}→{C_RESET}  {_rel_path(dest, project_root)}")

    println(f"\n  {C_GREEN}✔ Instalación completada. ({len(selected)} items){C_RESET}")


# ── Repo cleanup ─────────────────────────────────────────────────────────────


def cleanup_repo(repo: Path) -> None:
    """Ask user whether to delete the cloned repo, then do it."""
    if not ask_yesno(f"\n  {C_YELLOW}¿Eliminar el repositorio clonado?{C_RESET}"):
        println(f"  {C_DIM}Repositorio conservado en:{C_RESET} {repo}")
        return

    shutil.rmtree(repo, ignore_errors=True)
    println(f"  {C_DIM}Repositorio eliminado.{C_RESET}")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    try:
        clear_screen()
        print_title("AGENTS-SKILLS  —  Instalador Cross-Platform")

        # 1. OS detection
        platform = detect_os()
        print_step(f"Sistema operativo:  {C_BOLD}{platform}{C_RESET}")

        # 2. Agent detection
        agent = detect_agent()
        print_step(f"Agente detectado:   {C_BOLD}{agent}{C_RESET}")

        # 3. Scope: project or global
        scope = "project"
        if ask_yesno(f"\n  {C_YELLOW}¿Instalar para este proyecto (local)?{C_RESET}"):
            scope = "project"
        else:
            scope = "global"
            if agent == "vscode" and not ask_yesno(
                f"\n  {C_YELLOW}VS Code no tiene una ruta global estándar.{C_RESET}\n"
                f"  ¿Usar ~/.vscode/instructions/ de todas formas?"
            ):
                println(f"  {C_DIM}Se usará instalación local.{C_RESET}")
                scope = "project"

        print_step(f"Alcance:            {C_BOLD}{scope}{C_RESET}")

        # 4. Toggle menu
        selected = run_toggle_menu()

        # 5. Install
        # FIX: target base = CWD (project root), NOT repo_root
        base = Path.cwd() if scope == "project" else Path.home()
        targets = agent_targets(agent, scope, base)
        install_items(selected, agent, targets, repo_root(), base)

        # 6. Cleanup
        cleanup_repo(repo_root())

    except KeyboardInterrupt:
        println(f"\n\n  {C_YELLOW}Instalación cancelada.{C_RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
