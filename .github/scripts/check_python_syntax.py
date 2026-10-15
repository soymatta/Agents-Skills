"""Fail if any first-party Python file has a syntax error under this interpreter.

CI runs this under every interpreter in the matrix (3.11, 3.12). Syntax that
only parses on a newer version — e.g. PEP 701 nested f-strings, 3.12+ only —
then fails on the version that rejects it, with the exact file and line, before
it can ever ship. This replaces the old setup.py-only check.

Scope: every first-party ``.py`` in the repo. Vendored third-party skills
(impeccable, skill-creator, ai-job-search) are skipped so upstream code never
gates this build, mirroring ``.bandit.toml``.

Exit 1 on any file that does not compile under the running interpreter.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

THIRD_PARTY_SKILLS = {"impeccable", "skill-creator", "ai-job-search"}
SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "node_modules",
    ".archive",
    ".tox",
    ".eggs",
    "clones",
    "dist",
    "build",
}


def _skip(rel: Path) -> bool:
    parts = rel.parts
    if any(p in SKIP_DIR_NAMES or p.endswith(".egg-info") for p in parts):
        return True
    # skills/<third-party>/... — vendored, never gated by this repo
    if len(parts) >= 2 and parts[0] == "skills" and parts[1] in THIRD_PARTY_SKILLS:
        return True
    return False


def python_files(repo: Path) -> Iterator[tuple[Path, str]]:
    """Yield ``(path, posix_relative_path)`` for every first-party Python file."""
    for path in sorted(repo.rglob("*.py")):
        rel = path.relative_to(repo)
        if _skip(rel):
            continue
        yield path, rel.as_posix()


def check(repo: Path) -> list[tuple[str, str]]:
    """Return ``(relative_path, error)`` for every first-party file that won't compile."""
    failures: list[tuple[str, str]] = []
    for path, rel in python_files(repo):
        try:
            compile(path.read_bytes(), rel, "exec")
        except SyntaxError as exc:  # pragma: no cover - message shape varies by version
            where = f"line {exc.lineno}" if exc.lineno else "?"
            failures.append((rel, f"{exc.msg} ({where})"))
    return failures


def main(repo: Path | None = None) -> int:
    repo = repo or Path(__file__).resolve().parents[2]
    version = sys.version.split()[0]
    failures = check(repo)
    if failures:
        print(f"ERROR: {len(failures)} first-party Python file(s) fail to compile on {version}:")
        for rel, err in failures:
            print(f"  - {rel}: {err}")
        return 1
    count = sum(1 for _ in python_files(repo))
    print(f"OK: {count} first-party Python file(s) compile on {version}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
