"""Doc-vs-code coherence check for Agents-Skills CI.

Verifies that file paths referenced in first-party documentation actually exist
in the repository. This catches "over-promises" — places where a doc tells the
model to run a script or read a reference file that was never implemented.

Scope: first-party skills and the first-party agents directory. Documentation is
both the skill/agent Markdown AND the module docstrings of first-party skill
scripts: a docstring pointing at ``skills/<removed>/references/x.md`` misleads
the model exactly like a SKILL.md would. Third-party skills (impeccable,
skill-creator, ai-job-search, ...) are excluded so we never grep inside vendored
external content.

Out of scope by design:
    - references inside fenced code blocks (``` ... ```) — these are example
      commands / sample diffs, not the skill promising a shipped file,
    - external/URL-like tokens and library names (Next.js, Three.js, ...),
    - path-like tokens whose first segment is not a repo root we own
      (user-project examples such as ``path/to/note.md``).

Exit code 1 on any missing reference so CI fails.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

THIRD_PARTY = {"impeccable", "skill-creator", "ai-job-search", "web-design-guidelines"}
SKILLS_DIR = "skills"
AGENTS_DIR = "agents"

# First path segments that belong to this repo, so a reference starting with one
# is a promise about a shipped file. Anything else is a user-project example.
OWNED_ROOTS = {SKILLS_DIR, AGENTS_DIR, ".github", "web", "tests", "plugins", "docs", "scripts"}

# Tokens made of path-ish chars ending in a known script extension.
_SCRIPT_RE = re.compile(r"[\w./\\-]+\.(?:py|mjs|sh)\b", re.IGNORECASE)
# Backticked script paths: the shape a doc promises the agent can run as-is.
_BACKTICK_PATH_RE = re.compile(r"`([A-Za-z0-9_][\w./\\-]*\.(?:py|mjs|sh))`", re.IGNORECASE)
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
# Markdown files referenced by a path with at least one directory component.
_MD_PATH_RE = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.md\b", re.IGNORECASE)


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
    return names


def _is_placeholder(token: str) -> bool:
    """Single-letter segments are example placeholders (``a/b.py``), not paths."""
    return any(len(part) == 1 for part in token.replace("\\", "/").split("/"))


def _prose_script_tokens(repo: Path) -> list[tuple[str, str]]:
    """Return (reference, doc_path) for every first-party doc that references it."""
    found: list[tuple[str, str]] = []
    for label, body in _first_party_texts(repo):
        for m in _SCRIPT_RE.finditer(body):
            tok = m.group(0)
            base = tok.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
            if base in _SKIP_BASENAMES or tok.startswith(tuple(_SKIP_STARTS)):
                continue
            if _is_placeholder(tok):
                continue
            found.append((tok, label))
    return found


def _resolve(repo: Path, token: str) -> bool:
    """Does 'token' resolve to an existing repo-relative file, or a script anywhere?"""
    tok = token.replace("\\", "/")
    # A precise path that exists is never drift, even when it points into a
    # vendored third-party skill (those are tracked code too).
    if "/" in tok and (repo / tok).is_file():
        return True
    available = _script_files(repo)
    base = tok.rsplit("/", 1)[-1].lower()
    return base in available


def _first_party_docs(repo: Path) -> list[Path]:
    """Skill SKILL.md files (first-party only) plus agent definitions."""
    docs: list[Path] = []
    for skill_dir in (repo / SKILLS_DIR).iterdir():
        if skill_dir.is_dir() and skill_dir.name not in THIRD_PARTY:
            docs.extend(sorted(skill_dir.glob("*.md")))
    docs.extend(sorted((repo / AGENTS_DIR).glob("*.md")))
    return docs


def _first_party_docstrings(repo: Path) -> list[tuple[str, str]]:
    """Module docstrings of first-party skill scripts, as (label, prose)."""
    found: list[tuple[str, str]] = []
    for skill_dir in (repo / SKILLS_DIR).iterdir():
        if not skill_dir.is_dir() or skill_dir.name in THIRD_PARTY:
            continue
        for path in sorted((skill_dir / "scripts").glob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            except SyntaxError:
                continue
            doc = ast.get_docstring(tree)
            if doc:
                found.append((str(path.relative_to(repo)), _strip_code_blocks(doc)))
    return found


def _first_party_texts(repo: Path) -> list[tuple[str, str]]:
    """(label, prose) for every first-party doc: Markdown plus script docstrings.

    A docstring that points at a removed skill path misleads the model exactly
    like a SKILL.md would, so both feed the same checks.
    """
    texts: list[tuple[str, str]] = [
        (
            str(md.relative_to(repo)),
            _strip_code_blocks(md.read_text(encoding="utf-8", errors="ignore")),
        )
        for md in _first_party_docs(repo)
    ]
    texts.extend(_first_party_docstrings(repo))
    return texts


def _md_path_tokens(repo: Path) -> list[tuple[str, str]]:
    """Markdown paths in docs whose first segment is a root this repo owns."""
    tokens: list[tuple[str, str]] = []
    for label, body in _first_party_texts(repo):
        for token in sorted(set(_MD_PATH_RE.findall(body))):
            normalized = token.replace("\\", "/")
            if _is_placeholder(normalized):
                continue
            if normalized.split("/", 1)[0] in OWNED_ROOTS:
                tokens.append((normalized, label))
    return tokens


def _missing_md_paths(repo: Path) -> list[tuple[str, str]]:
    """Repo-root-relative ``.md`` paths in docs that do not exist."""
    return [(token, doc) for token, doc in _md_path_tokens(repo) if not (repo / token).is_file()]


def _missing_skills_prefix(repo: Path) -> list[tuple[str, str]]:
    """Backticked paths that read repo-root-relative but only exist under skills/.

    ``citation-formatter/scripts/references.py`` no existe en la raiz del repo: el
    archivo vive en ``skills/citation-formatter/scripts/references.py``. El
    fallback por basename de :func:`_resolve` no lo detecta, asi que la regla se
    chequea aparte: la forma prefijada es la unica que resuelve desde cualquier cwd.
    """
    skill_names = {d.name for d in (repo / SKILLS_DIR).iterdir() if d.is_dir()}
    refs: list[tuple[str, str]] = []
    for label, body in _first_party_texts(repo):
        for token in sorted(set(_BACKTICK_PATH_RE.findall(body))):
            parts = token.replace("\\", "/").split("/")
            if len(parts) < 2 or parts[0] not in skill_names:
                continue
            if (repo / token).is_file():
                continue
            if (repo / SKILLS_DIR / token).is_file():
                refs.append((token, label))
    return refs


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

    unprefixed = _missing_skills_prefix(repo)
    if unprefixed:
        print(f"ERROR: {len(unprefixed)} path(s) missing the {SKILLS_DIR}/ prefix:")
        for token, doc in sorted(set(unprefixed)):
            print(f"  - {token!r} (referenced in {doc}) -> use {SKILLS_DIR}/{token}")
        return 1

    missing_md = _missing_md_paths(repo)
    if missing_md:
        print(f"ERROR: {len(missing_md)} Markdown path(s) referenced by docs do not exist:")
        for token, doc in sorted(set(missing_md)):
            print(f"  - {token} (referenced in {doc})")
        return 1

    print(
        f"OK: {len(refs)} script reference(s) and {len(_md_path_tokens(repo))} "
        "Markdown path(s) verified against repo source."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
