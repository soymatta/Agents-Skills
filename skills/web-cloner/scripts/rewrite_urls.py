"""Rewrite remote asset references in HTML to local relative paths.

Offline and deterministic: given HTML text plus a resolver
(remote URL -> local relative path), rewrites src/href/srcset and CSS
url(...) references. Unmapped URLs are left intact and reported.

Usage:
    python rewrite_urls.py page.html map.json [--base https://site.com/]
Reads page.html, applies map.json {"remote_url": "local/rel/path"},
writes the rewritten HTML to stdout.
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

# Lazy-load mirrors (data-src et al. carry the real URL on many sites).
LAZY_ATTRS: dict[str, str] = {
    "data-src": "url",
    "data-srcset": "srcset",
    "data-poster": "url",
}
LAZY_TAGS = ("img", "source", "video", "audio", "track", "embed")

# (tag, {attr}) pairs whose URL-valued attributes get rewritten.
URL_ATTRS: dict[str, tuple[str, ...]] = {
    "a": ("href",),
    "img": ("src", "srcset"),
    "script": ("src",),
    "link": ("href",),
    "source": ("src", "srcset"),
    "video": ("src", "poster"),
    "audio": ("src",),
    "track": ("src",),
    "embed": ("src",),
    "iframe": ("src",),
}

_CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)")


def _is_kept_verbatim(url: str) -> bool:
    """Refs that stay exactly as written (never downloaded, never pending)."""
    return url.startswith(("data:", "#", "about:", "blob:", "javascript:", "mailto:", "tel:"))

# srcset consciente de data: URIs (llevan una coma dentro: partir por comas
# a ciegas rompe "data:image/gif;base64,AAA 1x" en dos URLs falsas).
_SRCSET_CAND = re.compile(
    r"data:[^\s,]+,\s*[^\s,]+(?:\s+[0-9.]+[wx])?|[^\s,]+(?:\s+[0-9.]+[wx])?"
)


def _srcset_candidates(value: str) -> list[str]:
    """Parte un srcset en candidatos sin romper data: URIs."""
    return [m.group(0) for m in _SRCSET_CAND.finditer(value)]


def local_path_for(url_path: str) -> str:
    """Map a URL path to a safe local relative path.

    '/' and directory paths become index.html; query strings and fragments
    are dropped; unsafe characters are replaced with '_'.
    """
    path = urlparse(url_path).path or "/"
    if path.endswith("/"):
        path = path + "index.html"
    name = PurePosixPath(path).name or "index.html"
    stem, dot, ext = name.rpartition(".")
    if not dot:  # sin extension
        stem, ext, dot = name, "", ""
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "asset"
    safe_ext = re.sub(r"[^A-Za-z0-9]+", "", ext)[:8]
    safe_name = safe_stem + ("." + safe_ext if safe_ext else "")
    parent = str(PurePosixPath(path).parent)
    if parent in (".", "/"):
        return safe_name
    safe_parent = re.sub(r"[^A-Za-z0-9/_-]+", "_", parent.strip("/")).strip("_")
    return f"{safe_parent}/{safe_name}" if safe_parent else safe_name


class AssetCollector(HTMLParser):
    """Collect (tag, attr, url) references from HTML, including CSS url()."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for attr, value in attrs:
            if not value:
                continue
            if attr in URL_ATTRS.get(tag, ()):
                if attr == "srcset":
                    for candidate in _srcset_candidates(value):
                        url = candidate.split(" ")[0]
                        if url and not _is_kept_verbatim(url):
                            self.refs.append((tag, attr, url))
                elif not _is_kept_verbatim(value):
                    self.refs.append((tag, attr, value))
            elif tag in LAZY_TAGS and attr in LAZY_ATTRS and not _is_kept_verbatim(value):
                if LAZY_ATTRS[attr] == "srcset":
                    for candidate in _srcset_candidates(value):
                        url = candidate.split(" ")[0]
                        if url and not _is_kept_verbatim(url):
                            self.refs.append((tag, attr, url))
                else:
                    self.refs.append((tag, attr, value))
            if tag == "style" or attr == "style":
                continue  # style bodies handled in handle_data
        # <style> tag bodies arrive via handle_data; inline style attrs too.

    def handle_data(self, data: str) -> None:
        for m in _CSS_URL_RE.finditer(data):
            url = m.group(2).strip()
            if url and not _is_kept_verbatim(url):
                self.refs.append(("css", "url", url))


def _rewrite_srcset(value: str, one, unresolved: list[str]) -> str:
    """Rewrite each URL inside a srcset value. Unresolvable entries are kept
    verbatim; only same-origin misses land in unresolved (via one)."""
    parts: list[str] = []
    for candidate in _srcset_candidates(value):
        tokens = candidate.split()
        if not tokens:
            continue
        before = len(unresolved)
        new = one(tokens[0])
        if len(unresolved) > before:
            parts.append(candidate)
        else:
            parts.append(" ".join([new, *tokens[1:]]))
    return ", ".join(parts)


def rewrite_html(html: str, page_url: str, resolve) -> tuple[str, list[str]]:
    """Rewrite asset references using resolve(absolute_url) -> local path|None.

    Returns (rewritten_html, unresolved_urls). resolve receives absolute
    URLs (page_url-joined); data: and fragment-only refs are never touched.
    """

    class _Rewriter(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=False)
            self.out: list[str] = []
            self.unresolved: list[str] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            attr_chunks: list[str] = []
            for attr, value in attrs:
                if value and (attr in URL_ATTRS.get(tag, ()) or (tag in LAZY_TAGS and attr in LAZY_ATTRS)):
                    kind = "srcset" if attr in ("srcset",) or LAZY_ATTRS.get(attr) == "srcset" else "url"
                    if kind == "srcset":
                        new = _rewrite_srcset(value, lambda u: self._one(u), self.unresolved)
                        attr_chunks.append(f'{attr}="{new}"')
                    else:
                        attr_chunks.append(f'{attr}="{self._one(value)}"')
                elif value is None:
                    attr_chunks.append(attr)
                else:
                    attr_chunks.append(f'{attr}="{value}"')
            self.out.append(f"<{tag} {' '.join(attr_chunks)}>" if attr_chunks else f"<{tag}>")

        def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            self.handle_starttag(tag, attrs)
            self.out[-1] = self.out[-1][:-1] + " />"

        def handle_endtag(self, tag: str) -> None:
            self.out.append(f"</{tag}>")

        def handle_data(self, data: str) -> None:
            def _css(m: re.Match) -> str:
                url = m.group(2).strip()
                if not url or _is_kept_verbatim(url):
                    return m.group(0)
                return f"url({self._one(url)})"

            self.out.append(_CSS_URL_RE.sub(_css, data))

        def handle_comment(self, data: str) -> None:
            self.out.append(f"<!--{data}-->")

        def handle_decl(self, decl: str) -> None:
            self.out.append(f"<!{decl}>")

        def handle_entityref(self, name: str) -> None:
            self.out.append(f"&{name};")

        def handle_charref(self, name: str) -> None:
            self.out.append(f"&#{name};")

        def _one(self, url: str) -> str:
            """Local path, or the original URL when it stays remote by design."""
            if _is_kept_verbatim(url):
                return url
            absolute = urljoin(page_url, url)
            if urlparse(absolute).netloc.lower() != urlparse(page_url).netloc.lower():
                return url  # externo: se queda remoto por diseño, no es pendiente
            new = resolve(absolute)
            if new is None:
                self.unresolved.append(url)
                return url
            return new

    rw = _Rewriter()
    rw.feed(html)
    return "".join(rw.out), sorted(set(rw.unresolved))


_CSS_IMPORT_RE = re.compile(
    r"@import\s+(?:url\(\s*['\"]?([^'\")]+)['\"]?\s*\)|['\"]([^'\"]+)['\"])")


def collect_css_urls(css_text: str) -> list[str]:
    """URLs from url(...) + @import in a stylesheet (data: skipped)."""
    urls = []
    for m in _CSS_URL_RE.finditer(css_text):
        url = m.group(2).strip()
        if url and not _is_kept_verbatim(url):
            urls.append(url)
    for m in _CSS_IMPORT_RE.finditer(css_text):
        url = (m.group(1) or m.group(2) or "").strip()
        if url and not _is_kept_verbatim(url):
            urls.append(url)
    return urls


def rewrite_css(css_text: str, css_url: str, resolve) -> tuple[str, list[str]]:
    """Rewrite url()/@import refs relative to the STYLESHEET url.

    Returns (rewritten_css, unresolved). Same contract as rewrite_html.
    """
    unresolved: list[str] = []

    def one(url: str) -> str:
        if _is_kept_verbatim(url):
            return url
        absolute = urljoin(css_url, url)
        if urlparse(absolute).netloc.lower() != urlparse(css_url).netloc.lower():
            return url
        new = resolve(absolute)
        if new is None:
            unresolved.append(url)
            return url
        return new

    def _url(m: re.Match) -> str:
        return f"url({one(m.group(2).strip())})"

    def _import(m: re.Match) -> str:
        url = (m.group(1) or m.group(2) or "").strip()
        if not url or _is_kept_verbatim(url):
            return m.group(0)
        return f'@import "{one(url)}"'

    out = _CSS_URL_RE.sub(_url, css_text)
    out = _CSS_IMPORT_RE.sub(_import, out)
    return out, sorted(set(unresolved))


# Quoted URL-ish strings inside JS (dynamic import(), fetch(), workers).
# Sourcemaps (//# sourceMappingURL=) are left alone: devtools-only noise.
_JS_URL_RE = re.compile(r"""(['"])((?:https?://|/|\./|\.\./)[^'"]+?)\1""")
_JS_SKIP_EXT = (".map",)


def collect_js_urls(js_text: str) -> list[str]:
    """Same-origin-candidate URLs quoted inside JS. Caller filters by host."""
    urls = []
    for m in _JS_URL_RE.finditer(js_text):
        url = m.group(2)
        if _is_kept_verbatim(url):
            continue
        if url.lower().endswith(_JS_SKIP_EXT):
            continue
        urls.append(url)
    return urls


def rewrite_js(js_text: str, js_url: str, resolve) -> tuple[str, list[str]]:
    """Rewrite same-origin quoted URLs inside JS to local/absolute targets.

    Unmapped same-origin URLs become absolute (live) so dynamic imports keep
    working online instead of 404ing locally. Same contract otherwise.
    """
    unresolved: list[str] = []

    def one(url: str) -> str:
        if _is_kept_verbatim(url):
            return url
        absolute = urljoin(js_url, url)
        if urlparse(absolute).netloc.lower() != urlparse(js_url).netloc.lower():
            return url
        new = resolve(absolute)
        if new is None:
            unresolved.append(url)
            return absolute
        return new

    def _rep(m: re.Match) -> str:
        q, url = m.group(1), m.group(2)
        if _is_kept_verbatim(url) or url.lower().endswith(_JS_SKIP_EXT):
            return m.group(0)
        return f"{q}{one(url)}{q}"

    return _JS_URL_RE.sub(_rep, js_text), sorted(set(unresolved))


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: rewrite_urls.py page.html map.json [--base URL] [--prefix ../] [--out file.html]", file=sys.stderr)
        return 2
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass  # stdout no reconfigurable: seguir con el encoding por defecto
    page_path, map_path = argv[1], argv[2]
    base = ""
    if "--base" in argv:
        base = argv[argv.index("--base") + 1]
    prefix = ""
    if "--prefix" in argv:
        prefix = argv[argv.index("--prefix") + 1]
    out_path = ""
    if "--out" in argv:
        out_path = argv[argv.index("--out") + 1]
    mapping: dict[str, str] = json.loads(open(map_path, encoding="utf-8").read())

    def resolve(absolute: str) -> str | None:
        local = mapping.get(absolute)
        return prefix + local if local is not None else None

    html = open(page_path, encoding="utf-8").read()
    new_html, unresolved = rewrite_html(html, base, resolve)
    if out_path:
        # Escritura directa UTF-8: nunca redirigir HTML por stdout del shell
        # (PowerShell recodifica y produce mojibake).
        open(out_path, "w", encoding="utf-8").write(new_html)
    else:
        sys.stdout.write(new_html)
    for u in unresolved:
        print(f"unresolved: {u}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
