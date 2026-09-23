"""Doc-vs-code coherence check for Agents-Skills CI.

Verifies that script filenames referenced in first-party documentation
(SKILL.md files and agent markdown) actually exist in the repository. This
catches "over-promises" — places where a doc tells the model to run a script
that was never implemented.

Scope: first-party skills and the first-party agents directory. Third-party
skills (impeccable, skill-creator, ai-job-search, ...) are excluded so we never
grep inside vendored external content.

Out of scope by design:
    - references inside fenced code blocks (``` ... ```) — these are example
      commands / sample diffs, not the skill promising a shipped script,
    - external/URL-like tokens and library names (Next.js, Three.js, ...).

Exit code 1 on any missing reference so CI fails.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

THIRD_PARTY = {"impeccable", "skill-creator", "ai-job-search"}
SKILLS_DIR = "skills"
AGENTS_DIR = "agents"

# Tokens made of path-ish chars ending in a known script extension.
_SCRIPT_RE = re.compile(r"[\w./\\-]+\.(?:py|mjs|sh)\b", re.IGNORECASE)
# Things that look like scripts but aren't repo promises.
_SKIP_BASENAMES = {
    "crt.sh",  # external OSINT service (crt.sh), not a script
    "skills.sh",  # open agent skills registry domain (skills.sh), not a script
    "next.js",  # framework
    "three.js",  # library
    "commands.sh",  # OSINT generated runtime artifact (gen_commands.py --output), not shipped
}
_SKIP_STARTS = {
    "//",  # protocol-relative-ish or comment markers
    ".client.",  # framework helper
    ".server.",
}


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks so their contents aren't treated as promises."""
    lines = text.splitlines()
    out: list[str] = []
    in_block = False
    for line in lines:
        if line.strip().startswith("```"):
            in_block = not in_block
            continue
        if not in_block:
            out.append(line)
    return "\n".join(out)


def _script_files(repo: Path) -> set[str]:
    """Every script basename present in first-party scripts/ and skill dirs."""
    names: set[str] = set()
    for skill_dir in (repo / SKILLS_DIR).iterdir():
        if not skill_dir.is_dir() or skill_dir.name in THIRD_PARTY:
            continue
        for f in skill_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in {".py", ".mjs", ".sh"}:
                names.add(f.name.lower())
    for agent_file in (repo / AGENTS_DIR).rglob("*.md"):
        pass  # agents don't ship scripts themselves
    return names


def _prose_script_tokens(repo: Path) -> list[tuple[str, str]]:
    """Return (reference, doc_path) for every first-party doc that references it."""
    found: list[tuple[str, str]] = []
    doc_roots: list[tuple[Path, ...]] = []
    skills_root = repo / SKILLS_DIR
    for skill_dir in skills_root.iterdir():
        if not skill_dir.is_dir() or skill_dir.name in THIRD_PARTY:
            continue
        doc_roots.append(tuple(skill_dir.glob("*.md")))
    agents_root = repo / AGENTS_DIR
    doc_roots.append(tuple(agents_root.glob("*.md")))

    for group in doc_roots:
        for md in group:
            body = _strip_code_blocks(md.read_text(encoding="utf-8", errors="ignore"))
            for m in _SCRIPT_RE.finditer(body):
                tok = m.group(0)
                base = tok.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
                if base in _SKIP_BASENAMES or tok.startswith(tuple(_SKIP_STARTS)):
                    continue
                found.append((tok, str(md.relative_to(repo))))
    return found


def _resolve(repo: Path, token: str) -> bool:
    """Does 'token' resolve to an existing repo-relative file, or a script anywhere?"""
    # Try repo-root-relative and doc-adjacent resolutions lazily via basename search.
    available = _script_files(repo)
    base = token.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
    return base in available


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    refs = _prose_script_tokens(repo)
    missing: list[tuple[str, str]] = []
    for token, doc in refs:
        if not _resolve(repo, token):
            missing.append((token, doc))

    if missing:
        print(f"ERROR: {len(missing)} doc-vs-code script reference(s) unresolved:")
        for token, doc in sorted(set(missing)):
            print(f"  - {token!r} (referenced in {doc})")
        return 1

    print(f"OK: {len(refs)} script reference(s) verified against first-party source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
