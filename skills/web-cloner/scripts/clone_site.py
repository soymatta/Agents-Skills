"""Mirror a small static site to a local folder.

Deterministic core of the web-cloner skill: fetch -> collect -> download ->
map.json -> rewrite (depth-aware) -> verify. All files are written by this
script in UTF-8; never round-trip HTML through a shell string (that
double-encodes non-ASCII and produces mojibake like --- showing as garbage).

Usage:
    python clone_site.py BASE --pages / /tools/a --out clones/site [--delay 1.0]
    python clone_site.py BASE --sitemap https://site/sitemap.xml --out ...
    python clone_site.py BASE --crawl 2 --out ...   # BFS same-origin HTML pages
Exit 0 when clean; 1 when pages failed or local refs are broken.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_links import find_broken
from rewrite_urls import (AssetCollector, collect_css_urls, collect_js_urls,
                          local_path_for, rewrite_css, rewrite_html,
                          rewrite_js)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) web-cloner/1.0 (site mirror)"

# Opt-in (--insecure): ignora errores TLS (cert autofirmado/cadena rota).
# Solo para sitios propios o indicados por el usuario, nunca por defecto.
_SSL_INSECURE = False

# Opt-in (--ignore-robots): skip Disallow rules. Only with explicit user
# order; default always respects robots.txt.
_IGNORE_ROBOTS = False


def urlopen(req, timeout=30):
    if _SSL_INSECURE:
        return urllib.request.urlopen(req, timeout=timeout,
                                      context=ssl._create_unverified_context())
    return urllib.request.urlopen(req, timeout=timeout)

_HASHY = re.compile(r"^(?:[0-9a-f]{6,}|.*-[0-9a-f]{6,}|.*-[0-9a-zA-Z_-]{8,})$")


def _is_hashy(stem: str) -> bool:
    return bool(_HASHY.match(stem))


def decode_bytes(raw: bytes, headers) -> str:
    """Decode with header charset, else <meta charset>, else UTF-8."""
    ctype = headers.get_content_charset()
    if ctype:
        try:
            return raw.decode(ctype, errors="replace")
        except (LookupError, UnicodeError):
            pass
    head = raw[:4096].decode("ascii", errors="ignore")
    m = re.search(r'<meta[^>]+charset=["\']?\s*([A-Za-z0-9_-]+)', head, re.I)
    if m:
        try:
            return raw.decode(m.group(1), errors="replace")
        except (LookupError, UnicodeError):
            pass
    return raw.decode("utf-8", errors="replace")


def fetch(url: str, timeout: int = 30) -> tuple[str | None, str | None]:
    """Return (html_or_None, error_or_None)."""
    req = urllib.request.Request(quote_url(url), headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=timeout) as res:
            return decode_bytes(res.read(), res.headers), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except Exception as e:  # timeout, DNS, TLS: report, don't crash
        return None, str(e)


def page_local(url_path: str) -> str:
    """Mirror URL hierarchy: / -> index.html, /a/b -> a/b/index.html."""
    path = urllib.parse.urlparse(url_path).path or "/"
    if path.endswith("/"):
        return (path.strip("/") + "/index.html") if path != "/" else "index.html"
    last = path.rsplit("/", 1)[-1]
    if "." in last:
        return path.strip("/")
    return path.strip("/") + "/index.html"


def depth_prefix(html_local: str) -> str:
    """Relative prefix from a page to the clone root: a/b/index.html -> ../../."""
    return "../" * (len(Path(html_local).parts) - 1)


def absolutize_same_origin(html: str, base: str) -> str:
    """Same-origin refs left remote by scope (single-page clones) go back to
    full absolute URLs so navigation keeps working against the live site.
    Protocol-relative (//cdn/...) is never touched."""
    root = base.rstrip("/")

    def _ss(m: re.Match) -> str:
        parts = []
        for part in m.group(1).split(","):
            toks = part.split()
            if toks and toks[0].startswith("/") and not toks[0].startswith("//"):
                toks[0] = root + toks[0]
            parts.append(" ".join(toks))
        return 'srcset="' + ", ".join(parts) + '"'

    html = re.sub(r'srcset="([^"]*)"', _ss, html)
    html = re.sub(r'((?:href|src|poster)=["\'])/(?!/)', rf"\1{root}/", html)
    html = re.sub(r"url\(/(?!/)", f"url({root}/", html)
    return html


_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
              "link", "meta", "source", "track", "wbr", "param"}


def parse_strip_selector(sel: str) -> tuple[str, str] | None:
    sel = sel.strip()
    if sel.startswith("#") and len(sel) > 1:
        return ("id", sel[1:])
    if sel.startswith(".") and len(sel) > 1:
        return ("class", sel[1:])
    return None


class _SelectorStripper(HTMLParser):
    """Remove elements matching id/class selectors (subtree included)."""

    def __init__(self, selectors: list[tuple[str, str]]) -> None:
        super().__init__(convert_charrefs=False)
        self.selectors = selectors
        self.out: list[str] = []
        self.removed = 0
        self._depth = 0

    def _hit(self, attrs: list) -> bool:
        d = dict(attrs)
        for kind, name in self.selectors:
            if kind == "id" and d.get("id") == name:
                return True
            if kind == "class" and name in (d.get("class") or "").split():
                return True
        return False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if self._depth:
            if tag not in _VOID_TAGS:
                self._depth += 1
            return
        if self._hit(attrs):
            self.removed += 1
            if tag not in _VOID_TAGS:
                self._depth = 1
            return
        self.out.append(self.get_starttag_text())

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        if self._depth or self._hit(attrs):
            if self._hit(attrs):
                self.removed += 1
            return
        self.out.append(self.get_starttag_text())

    def handle_endtag(self, tag: str) -> None:
        if self._depth:
            self._depth -= 1
            return
        self.out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self._depth:
            self.out.append(data)

    def handle_comment(self, data: str) -> None:
        if not self._depth:
            self.out.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        if not self._depth:
            self.out.append(f"<!{decl}>")

    def handle_entityref(self, name: str) -> None:
        if not self._depth:
            self.out.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self._depth:
            self.out.append(f"&#{name};")


def strip_selectors(html: str, selectors: list[str]) -> tuple[str, int]:
    """Remove #id/.class subtrees. Returns (html, removed_count)."""
    parsed = [s for s in (parse_strip_selector(x) for x in selectors) if s]
    if not parsed:
        return html, 0
    stripper = _SelectorStripper(parsed)
    stripper.feed(html)
    return "".join(stripper.out), stripper.removed


def asset_local(url: str, used: set[str], css_counter: list[int]) -> str | None:
    """Naming policy (deterministic, tested):
    - root specials (favicon, manifest...) stay at root with original name
    - .js keeps its original subtree (bundles reference each other by hash)
    - .css -> styles/ (hash-like names become main/style-N.css)
    - images/fonts/media -> friendly names under assets/
    Returns None for directory-like URLs (those are pages, not assets).
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path or "/"
    if path.endswith("/"):
        return None
    raw_name = path.rsplit("/", 1)[-1]
    if not raw_name:
        return None
    root_specials = ("favicon.ico", "favicon.svg", "apple-touch-icon.png",
                     "apple-touch-icon-precomposed.png", "site.webmanifest",
                     "manifest.json", "browserconfig.xml")
    if raw_name.lower() in root_specials:
        return raw_name
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else ""
    if not ext and raw_name.lower() not in root_specials:
        # Sin extension y no es especial de raiz: parece pagina fuera de
        # alcance, no asset. Se queda remoto (absolutizado), no se descarga.
        return None
    if ext in ("html", "htm", "xhtml", "php", "asp", "aspx", "jsp", "jspx"):
        # Pagina con extension: o esta en el alcance (se fetchea como pagina)
        # o queda remota. Nunca se descarga como asset (el fallback SPA 200
        # nos colaria copias fantasma de la home).
        return None
    if ext == "js":
        # Bundles reference each other: preserve the original subtree.
        clean = re.sub(r"[^A-Za-z0-9/._-]+", "_", path.strip("/"))
        return clean or "scripts/bundle.js"
    if ext == "css":
        stem = raw_name.rsplit(".", 1)[0]
        if _is_hashy(stem):
            css_counter[0] += 1
            n = css_counter[0]
            return "styles/main.css" if n == 1 else f"styles/style-{n}.css"
        return f"styles/{local_path_for(path).rsplit('/', 1)[-1]}"
    friendly = local_path_for(path).rsplit("/", 1)[-1]
    if ext in ("png", "jpg", "jpeg", "gif", "svg", "webp", "avif", "ico", "bmp"):
        sub = "assets/img"
    elif ext in ("woff", "woff2", "ttf", "otf", "eot"):
        sub = "assets/fonts"
    else:
        sub = "assets/media"
    name = friendly
    k = 1
    while f"{sub}/{name}" in used:
        k += 1
        stem, dot, ext2 = friendly.partition(".")
        name = f"{stem}_{k}{dot + ext2 if dot else ''}"
    return f"{sub}/{name}"


def quote_url(url: str) -> str:
    """IRI -> URI: percent-encode path/query (Aktualności -> Aktualno%C5%9Bci)."""
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parts.path, safe="/%:")
    query = urllib.parse.quote(parts.query, safe="=&%")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def robots_rules(base: str) -> list[str]:
    """Raw Disallow values for User-agent: * (supports * and $ like Google)."""
    try:
        with urlopen(
            urllib.request.Request(base.rstrip("/") + "/robots.txt",
                                   headers={"User-Agent": UA}),
            timeout=15,
        ) as res:
            rules = res.read().decode("utf-8", errors="replace").splitlines()
    except Exception:
        return []
    disallow: list[str] = []
    in_star = True
    for line in rules:
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            in_star = value == "*"
        elif field == "disallow" and in_star and value:
            disallow.append(value)
    return disallow


def robots_denied(base: str, paths: list[str]) -> set[str]:
    """Minimal robots.txt check (User-agent: * + global Disallow)."""
    if _IGNORE_ROBOTS:
        return set()
    disallow = robots_rules(base)
    denied = set()
    for p in paths:
        if any(_robots_match(p, d) for d in disallow if d != "/"):
            denied.add(p)
        elif "/" in disallow:
            denied.add(p)
    return denied


def _robots_match(path: str, pattern: str) -> bool:
    """Match a Disallow pattern supporting * wildcard and $ end anchor."""
    if pattern.endswith("$"):
        rx = re.escape(pattern[:-1]).replace(r"\*", ".*") + "$"
    else:
        rx = re.escape(pattern).replace(r"\*", ".*")
    return re.match(rx, path) is not None


def discover_sitemap(sitemap_url: str, base_netloc: str, _depth: int = 0) -> list[str]:
    """Page paths from a sitemap; follows one level of sitemap-index nesting."""
    try:
        with urlopen(
            urllib.request.Request(quote_url(sitemap_url), headers={"User-Agent": UA}),
            timeout=20,
        ) as res:
            xml = res.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"sitemap unreadable: {e}", file=sys.stderr)
        return []
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    pages: list[str] = []
    for loc in locs:
        parsed = urllib.parse.urlparse(loc)
        if parsed.netloc.lower() != base_netloc:
            continue
        if _depth == 0 and re.search(r"\.xml(\.gz)?(\?|#|$)", parsed.path, re.I):
            pages += discover_sitemap(loc, base_netloc, _depth + 1)
        else:
            pages.append(parsed.path or "/")
    return pages


def crawl(base: str, max_depth: int, delay: float) -> list[str]:
    """BFS same-origin HTML pages from base up to max_depth."""
    netloc = urllib.parse.urlparse(base).netloc.lower()
    seen = {"/"}
    frontier = ["/"]
    for _ in range(max_depth + 1):
        nxt = []
        for p in frontier:
            html, err = fetch(urllib.parse.urljoin(base, p))
            if html is None:
                continue
            c = AssetCollector()
            c.feed(html)
            for tag, _attr, u in c.refs:
                if tag != "a":
                    continue
                absu = urllib.parse.urljoin(base + "/", u)
                parsed = urllib.parse.urlparse(absu)
                if parsed.netloc.lower() != netloc:
                    continue
                q = parsed.path or "/"
                if q not in seen and not re.search(r"\.(css|js|png|jpe?g|gif|svg|webp|avif|ico|woff2?|ttf|pdf|zip)(\?|#|$)", q, re.I):
                    seen.add(q)
                    nxt.append(q)
            time.sleep(delay)
        frontier = nxt
    if _IGNORE_ROBOTS:
        return sorted(seen)
    return sorted(p for p in seen if p not in robots_denied(base, [p]))


def clone(base: str, page_paths: list[str], out: Path, delay: float,
          strip: list[str] | None = None, asset_delay: float = 0.3,
          max_assets: int = 400) -> int:
    netloc = urllib.parse.urlparse(base).netloc.lower()
    denied = robots_denied(base, page_paths)
    if denied:
        print(f"robots.txt blocks: {sorted(denied)} (skipped)", file=sys.stderr)
    page_paths = [p for p in page_paths if p not in denied]
    out.mkdir(parents=True, exist_ok=True)

    raw: dict[str, str] = {}
    failed: dict[str, str] = {}
    for p in page_paths:
        html, err = fetch(urllib.parse.urljoin(base, p))
        if html is None:
            failed[p] = err or "unknown"
        else:
            raw[p] = html
        time.sleep(delay)
    if not raw:
        print("no pages fetched", file=sys.stderr)
        return 1

    # Collect same-origin assets (pages excluded: they are fetched, not downloaded).
    asset_urls: list[str] = []
    seen_assets: set[str] = set()
    abs_pages = {urllib.parse.urljoin(base + "/", p) for p in page_paths}
    asset_rules = [] if _IGNORE_ROBOTS else robots_rules(base)
    for p, html in raw.items():
        c = AssetCollector()
        c.feed(html)
        for _t, _a, u in c.refs:
            absu = urllib.parse.urljoin(base + "/", u)
            parsed = urllib.parse.urlparse(absu)
            if parsed.netloc.lower() != netloc:
                continue
            if absu in abs_pages:
                continue
            if any(_robots_match(parsed.path or "/", d) for d in asset_rules):
                continue  # Disallow: se queda remoto por robots.txt
            if absu not in seen_assets:
                seen_assets.add(absu)
                asset_urls.append(absu)

    # Download + map.
    mapping: dict[str, str] = {}
    used: set[str] = set()
    css_counter = [0]
    pending: list[str] = []
    capped: list[str] = []

    def budget_ok(url: str) -> bool:
        """Hard cap on asset downloads (JS phases can discover endlessly)."""
        if len(used) >= max_assets:
            capped.append(url)
            return False
        return True
    for absu in asset_urls:
        local = asset_local(absu, used, css_counter)
        if local is None:
            continue
        if not budget_ok(absu):
            continue
        used.add(local)
        dest = out / local
        dest.parent.mkdir(parents=True, exist_ok=True)  # lazy dirs: only what lands
        try:
            req = urllib.request.Request(quote_url(absu), headers={"User-Agent": UA})
            with urlopen(req, timeout=30) as res:
                dest.write_bytes(res.read())
            mapping[absu] = local
        except Exception as e:
            pending.append(f"{absu} ({e})")
        time.sleep(asset_delay)
    for p in raw:
        # Regla raiz: clon de una sola pagina -> index.html en la raiz.
        mapping[urllib.parse.urljoin(base, p)] = "index.html" if len(raw) == 1 else page_local(p)

    # Phase 2: stylesheets carry their own refs (img/fonts). Download + rewrite.
    reverse = {v: k for k, v in mapping.items()}
    for local in [v for v in mapping.values() if v.endswith(".css")]:
        remote_css = reverse.get(local, "")
        if not remote_css:
            continue
        css_text = (out / local).read_text(encoding="utf-8", errors="replace")
        prefix = depth_prefix(local)
        for u in collect_css_urls(css_text):
            absolute = urllib.parse.urljoin(remote_css, u)
            if urllib.parse.urlparse(absolute).netloc.lower() != netloc:
                continue
            if absolute in mapping:
                continue
            inner_local = asset_local(absolute, used, css_counter)
            if inner_local is None:
                continue
            if not budget_ok(absolute):
                continue
            used.add(inner_local)
            dest = out / inner_local
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                req = urllib.request.Request(quote_url(absolute), headers={"User-Agent": UA})
                with urlopen(req, timeout=30) as res:
                    dest.write_bytes(res.read())
                mapping[absolute] = inner_local
            except Exception as e:
                pending.append(f"{absolute} ({e})")
            time.sleep(asset_delay)

        def _css_resolve(absolute: str, _prefix=prefix) -> str | None:
            hit = mapping.get(absolute)
            return _prefix + hit if hit is not None else None

        new_css, css_unresolved = rewrite_css(css_text, remote_css, _css_resolve)
        (out / local).write_text(new_css, encoding="utf-8")
        for u in css_unresolved:
            if u.startswith(("http://", "https://", "/")):
                continue
            pending.append(f"{local} -> {u}")

    # Phase 3: JS pulls more chunks at runtime (dynamic import/fetch/API).
    # Fixpoint: new chunks can reference newer chunks (cap 2 rounds: a partir
    # de ahi casi todo es telemetria/endpoints vivos, que quedan remotos).
    for _round in range(2):
        reverse = {v: k for k, v in mapping.items()}
        new_found = False
        for local in [v for v in mapping.values() if v.endswith(".js")]:
            remote_js = reverse.get(local, "")
            if not remote_js:
                continue
            js_text = (out / local).read_text(encoding="utf-8", errors="replace")
            prefix = depth_prefix(local)
            for u in collect_js_urls(js_text):
                absolute = urllib.parse.urljoin(remote_js, u)
                if urllib.parse.urlparse(absolute).netloc.lower() != netloc:
                    continue
                if absolute in mapping:
                    continue
                js_local = asset_local(absolute, used, css_counter)
                if js_local is None:
                    continue
                if not budget_ok(absolute):
                    continue
                used.add(js_local)
                dest = out / js_local
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    req = urllib.request.Request(quote_url(absolute), headers={"User-Agent": UA})
                    with urlopen(req, timeout=30) as res:
                        dest.write_bytes(res.read())
                    mapping[absolute] = js_local
                    new_found = True
                except Exception as e:
                    pending.append(f"{absolute} ({e})")
                time.sleep(asset_delay)

            def _js_resolve(absolute: str, _prefix=prefix) -> str | None:
                hit = mapping.get(absolute)
                if hit is not None:
                    return _prefix + hit
                if urllib.parse.urlparse(absolute).netloc.lower() == netloc:
                    return absolute  # remoto por alcance: URL viva, no 404 local
                return None

            new_js, js_unresolved = rewrite_js(js_text, remote_js, _js_resolve)
            (out / local).write_text(new_js, encoding="utf-8")
            for u in js_unresolved:
                if u.startswith(("http://", "https://", "/")):
                    continue
                pending.append(f"{local} -> {u}")
        if not new_found:
            break

    with open(out / "map.json", "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    # Rewrite each page with its depth prefix (pending already holds
    # download failures from above).
    single_root = len(raw) == 1
    for p, html in raw.items():
        local = "index.html" if single_root else page_local(p)
        prefix = depth_prefix(local)

        def resolve(absolute: str, _prefix=prefix) -> str | None:
            hit = mapping.get(absolute)
            return _prefix + hit if hit is not None else None

        new_html, unresolved = rewrite_html(html, urllib.parse.urljoin(base, p), resolve)
        new_html = absolutize_same_origin(new_html, base)
        if strip:
            new_html, n_removed = strip_selectors(new_html, strip)
            if n_removed:
                print(f"strip {local}: {n_removed} nodo(s) fuera")
        dest = out / local
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(new_html, encoding="utf-8")
        for u in unresolved:
            # http(s) o /absoluta = remoto por alcance (ya absolutizado arriba)
            if u.startswith(("http://", "https://", "/")):
                continue
            pending.append(f"{p} -> {u}")

    if capped:
        pending.append(f"{len(capped)} urls skipped by --max-assets {max_assets}")
    (out / "pending.txt").write_text(
        "\n".join(sorted(set(pending))) + ("\n" if pending else ""), encoding="utf-8")

    broken = find_broken(out)
    print(f"pages: {len(raw)} ok, {len(failed)} failed {failed or ''}")
    print(f"assets: {len(mapping) - len(raw)} downloaded, {len(pending)} pending")
    for b in broken:
        print(f"BROKEN: {b[0]} -> {b[1]}")
    if failed or broken:
        return 1
    print("clone clean: all local refs resolve")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mirror a small static site locally.")
    ap.add_argument("base", help="Site root, e.g. https://example.com")
    ap.add_argument("--pages", nargs="*", default=[], help="Page paths: / /tools/a")
    ap.add_argument("--sitemap", default="", help="Sitemap URL to discover pages")
    ap.add_argument("--crawl", type=int, default=-1, help="BFS depth from base")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--delay", type=float, default=1.0, help="Seconds between page requests")
    ap.add_argument("--asset-delay", type=float, default=0.3, help="Seconds between asset requests")
    ap.add_argument("--insecure", action="store_true",
                    help="Skip TLS verification (self-signed/broken chain only)")
    ap.add_argument("--ignore-robots", action="store_true",
                    help="Skip robots.txt Disallow (requires explicit user order)")
    ap.add_argument("--strip", default="",
                    help="Comma-separated #id/.class selectors to remove from pages")
    ap.add_argument("--max-assets", type=int, default=400,
                    help="Hard cap on asset downloads (JS phases can discover endlessly)")
    args = ap.parse_args(argv)

    global _SSL_INSECURE
    _SSL_INSECURE = args.insecure
    global _IGNORE_ROBOTS
    _IGNORE_ROBOTS = args.ignore_robots

    paths: list[str] = list(args.pages)
    if args.sitemap:
        paths += discover_sitemap(args.sitemap, urllib.parse.urlparse(args.base).netloc.lower())
    if args.crawl >= 0:
        paths += crawl(args.base, args.crawl, args.delay)
    paths = sorted(set(paths)) or ["/"]
    strip = [s for s in args.strip.split(",") if s.strip()]
    return clone(args.base, paths, Path(args.out), args.delay, strip, args.asset_delay, args.max_assets)


if __name__ == "__main__":
    raise SystemExit(main())
