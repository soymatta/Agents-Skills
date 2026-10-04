"""Find broken local references inside a cloned site directory.

Walks *.html under root, resolves local href/src/srcset against each file,
and reports targets missing from disk. External URLs (http/data/mailto/#)
are ignored.

Usage:
    python check_links.py clon/
Prints "file -> ref" lines; exit 0 when clean, 1 when broken refs exist.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from rewrite_urls import AssetCollector


def _is_external(url: str) -> bool:
    scheme = urlparse(url).scheme.lower()
    return scheme in ("http", "https", "data", "mailto", "tel", "javascript", "blob", "about")


def find_broken(root: str | Path) -> list[tuple[str, str]]:
    """Return [(html_file, ref)] for local refs missing from disk.

    Leading-/ refs resolve against the clone root (they used to escape to
    the filesystem root and were silently skipped). Remote URLs are ignored.
    """
    root = Path(root)
    broken: list[tuple[str, str]] = []
    for html_file in sorted(root.rglob("*.html")):
        collector = AssetCollector()
        collector.feed(html_file.read_text(encoding="utf-8", errors="replace"))
        for _tag, _attr, url in collector.refs:
            if not url or url.startswith("#") or _is_external(url):
                continue
            if url.startswith("/"):
                target = (root / unquote(urlparse(url).path).lstrip("/")).resolve()
            else:
                target = (html_file.parent / unquote(urlparse(url).path)).resolve()
            try:
                target.relative_to(root.resolve())
            except ValueError:
                continue  # escapes the clone root: not our file to check
            if not target.exists():
                broken.append((str(html_file.relative_to(root)), url))
    return broken


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: check_links.py <clon-dir>", file=sys.stderr)
        return 2
    broken = find_broken(argv[1])
    for html_file, ref in broken:
        print(f"{html_file} -> {ref}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
