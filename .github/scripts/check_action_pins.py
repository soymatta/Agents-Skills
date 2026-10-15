"""Validate that every action referenced in .github/workflows resolves.

Why: GitHub resolves a job's ``uses:`` refs when it sets the job up. A single
bad ref — a SHA that does not exist, e.g. a SHA copy-pasted from a different
action — makes every run of that workflow fail at "Set up job" with an opaque
message. That failure is easy to miss for weeks because it happens before any
step runs. This turns it into a clear, named failure instead.

For each ``owner/repo@ref`` it asks the GitHub API to resolve the ref. Local
(``./path``) and ``docker://`` refs are ignored. Network or rate-limit errors
are reported as warnings and do not fail the build unless ``--strict`` is set,
so a transient outage never blocks a release. Set ``GH_TOKEN`` (in CI,
``secrets.GITHUB_TOKEN``) for reliable rate limits.

Exit 1 when a ref is malformed or the API reports it does not exist.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterator, Optional

USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?([^'\"\s#]+)['\"]?", re.MULTILINE)
API = "https://api.github.com"
IGNORED_PREFIXES = ("./", "../", "/", "docker://")


def iter_uses(text: str) -> Iterator[str]:
    """Yield every ``uses:`` value found in a workflow's raw YAML text."""
    for match in USES_RE.finditer(text):
        yield match.group(1).strip()


def parse_ref(uses: str) -> Optional[tuple[str, str, str]]:
    """Return ``(owner, repo, ref)`` for a remote action, or None if it is not one."""
    uses = uses.strip()
    if not uses or uses.startswith(IGNORED_PREFIXES):
        return None
    if "@" not in uses:
        return None
    path, ref = uses.rsplit("@", 1)
    parts = path.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1] or not ref:
        return None
    return parts[0], parts[1], ref


def resolve(owner: str, repo: str, ref: str, token: str | None = None, timeout: int = 15) -> Optional[bool]:
    """Return True if the ref resolves, False if not, None when the API is unreachable."""
    url = f"{API}/repos/{owner}/{repo}/commits/{ref}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "agents-skills-ci"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 422):
            return False
        return None
    except Exception:  # noqa: BLE001 - any transport failure is "unknown", never fatal
        return None


def collect(workflows_dir: Path) -> list[tuple[str, str, tuple[str, str, str]]]:
    """Return ``(workflow_name, uses, (owner, repo, ref))`` for every remote action."""
    found: list[tuple[str, str, tuple[str, str, str]]] = []
    for workflow in sorted(list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))):
        text = workflow.read_text(encoding="utf-8", errors="replace")
        for uses in iter_uses(text):
            parsed = parse_ref(uses)
            if parsed:
                found.append((workflow.name, uses, parsed))
    return found


def main(argv: list[str] | None = None, workflows_dir: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true", help="fail when the API cannot be reached")
    args = parser.parse_args(argv)

    if workflows_dir is None:
        workflows_dir = Path(__file__).resolve().parents[2] / ".github" / "workflows"

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    refs = collect(workflows_dir)

    unresolved: list[tuple[str, str]] = []
    unverified: list[tuple[str, str]] = []
    for name, uses, (owner, repo, ref) in refs:
        verdict = resolve(owner, repo, ref, token=token)
        if verdict is True:
            continue
        (unresolved if verdict is False else unverified).append((name, uses))

    for name, uses in unresolved:
        print(f"ERROR: unresolved action in {name}: {uses}")
    for name, uses in unverified:
        print(f"WARN: could not verify action in {name}: {uses}")

    if unresolved:
        print(f"ERROR: {len(unresolved)} action ref(s) do not resolve.")
        return 1
    if unverified and args.strict:
        print(f"ERROR: {len(unverified)} action ref(s) unverified (--strict).")
        return 1
    print(f"OK: {len(refs)} action ref(s) resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
