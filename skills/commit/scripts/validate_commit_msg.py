#!/usr/bin/env python3
"""Validate (and install) the repository's commit-message convention.

Convention::

    {Type}: {explanation}

where ``{Type}`` is one of the capitalized types below and ``{explanation}`` is a
short, non-empty, English phrase (no trailing period, subject line <= 72 chars).

Usage
-----
    # check a message directly
    python validate_commit_msg.py --message "Fix: correct login timeout"

    # what a git commit-msg hook calls (a file path)
    python validate_commit_msg.py .git/COMMIT_EDITMSG

    # install the hook
    python validate_commit_msg.py --install            # native .git/hooks/commit-msg
    python validate_commit_msg.py --install --husky    # .husky/commit-msg

Exit codes: 0 = valid, 1 = invalid, 2 = usage/setup error.
Stdlib only.
"""

from __future__ import annotations

import argparse
import re
import stat
import subprocess
import sys
from pathlib import Path

TYPES = (
    "Fix", "Feature", "Docs", "Refactor", "Test",
    "Chore", "Perf", "Build", "CI", "Style", "Revert",
)

SUBJECT_RE = re.compile(
    r"^(?P<type>" + "|".join(TYPES) + r")(?P<bang>!?): (?P<explanation>\S.*)$"
)
_LOWERCASE_TYPES = {t.lower() for t in TYPES}
MAX_SUBJECT = 72

# git-generated subjects we must never reject (merge/revert commits).
_ALLOW_SUBJECT_RE = re.compile(r'^(Merge (branch|pull request|remote-tracking|commit)\b|Revert ")')

HOOK_TEMPLATE = """#!/usr/bin/env sh
# Installed by the commit skill. Validates the commit message convention.
# Points at the validator that installed this hook (absolute path).
validator="{validator}"
[ -f "$validator" ] || exit 0
python "$validator" "$1"
"""


def _subject(message: str) -> str:
    """First meaningful line: skip blank lines and ``#`` comment lines."""
    for line in message.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return line.rstrip()
    return ""


def validate(message: str) -> tuple[bool, str]:
    """Return ``(ok, reason)`` for a full commit message."""
    subject = _subject(message)
    if not subject:
        return False, "empty commit message"
    if _ALLOW_SUBJECT_RE.match(subject):
        return True, "git-generated subject (merge/revert) — allowed"
    if len(subject) > MAX_SUBJECT:
        return False, f"subject is {len(subject)} chars (max {MAX_SUBJECT})"
    m = SUBJECT_RE.match(subject)
    if not m:
        # Give a targeted hint when the only problem is casing.
        head = subject.split(":", 1)[0].strip()
        if head.lower() in _LOWERCASE_TYPES:
            return False, f"type `{head}` must be capitalized, e.g. `{head.capitalize()}: …`"
        return False, (
            f"must match `{{Type}}: {{explanation}}` with Type in "
            f"{', '.join(TYPES)}; got: {subject!r}"
        )
    if m.group("explanation").strip() == "":
        return False, "explanation after the colon is empty"
    if subject.endswith("."):
        return False, "subject must not end with a period"
    return True, "ok"


def _git_toplevel() -> Path | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def install(husky: bool) -> int:
    root = _git_toplevel()
    if root is None:
        print("error: not inside a git repository", file=sys.stderr)
        return 2
    if husky:
        target = root / ".husky" / "commit-msg"
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        target = root / ".git" / "hooks" / "commit-msg"
        target.parent.mkdir(parents=True, exist_ok=True)
    hook = HOOK_TEMPLATE.format(validator=str(Path(__file__).resolve()).replace("\\", "/"))
    target.write_text(hook, encoding="utf-8")
    target.chmod(target.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"installed commit-msg hook: {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Validate the commit-message convention.")
    ap.add_argument("path", nargs="?", help="commit message file (hook form)")
    ap.add_argument("--message", "-m", help="validate this message string")
    ap.add_argument("--install", action="store_true", help="install the commit-msg hook")
    ap.add_argument("--husky", action="store_true", help="install into .husky/ (with --install)")
    args = ap.parse_args(argv)

    if args.install:
        return install(husky=args.husky)

    if args.message is not None:
        message = args.message
    elif args.path:
        try:
            message = Path(args.path).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"error: cannot read {args.path}: {e}", file=sys.stderr)
            return 2
    else:
        ap.error("provide --message, a path, or --install")

    ok, reason = validate(message)
    if ok:
        return 0
    print(f"invalid commit message: {reason}", file=sys.stderr)
    print(f'  expected: {{Type}}: {{explanation}}  (e.g. "Fix: correct login timeout")',
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
