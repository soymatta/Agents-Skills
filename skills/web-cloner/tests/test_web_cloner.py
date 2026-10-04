"""Tests for the web-cloner deterministic scripts (offline, no network)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_links import find_broken
from clone_site import absolutize_same_origin, asset_local, depth_prefix
from clone_site import main as clone_main, page_local
from rewrite_urls import AssetCollector, local_path_for, rewrite_html

BASE = "https://example.com/blog/post/"


def resolve(mapping):
    return lambda url: mapping.get(url)


# ── local_path_for ──────────────────────────────────────────────────────
def test_root_becomes_index():
    assert local_path_for("https://x.com/") == "index.html"


def test_directory_becomes_index():
    assert local_path_for("https://x.com/blog/") == "blog/index.html"


def test_query_and_fragment_dropped():
    assert local_path_for("https://x.com/a/img.png?v=2#frag") == "a/img.png"


def test_unsafe_chars_sanitized():
    out = local_path_for("https://x.com/a/mi foto(1).PNG")
    assert out == "a/mi_foto_1.PNG"


# ── AssetCollector ──────────────────────────────────────────────────────
def test_collects_tags_and_css_urls():
    html = (
        '<img src="/i/a.png" srcset="/i/a.png 1x, /i/a@2x.png 2x">'
        '<script src="https://cdn.x.com/lib.js"></script>'
        '<link href="/s/main.css">'
        "<style>.h{background:url('/i/bg.jpg')}</style>"
    )
    c = AssetCollector()
    c.feed(html)
    urls = [u for _, _, u in c.refs]
    for expected in ("/i/a.png", "/i/a@2x.png", "https://cdn.x.com/lib.js",
                     "/s/main.css", "/i/bg.jpg"):
        assert expected in urls


def test_ignores_data_urls():
    c = AssetCollector()
    c.feed('<img src="data:image/png;base64,AAA">')
    assert c.refs == []


# ── rewrite_html ────────────────────────────────────────────────────────
MAPPING = {
    "https://example.com/i/a.png": "assets/img/a.png",
    "https://example.com/blog/s.css": "styles/s.css",
    "https://example.com/blog/app.js": "scripts/app.js",
}


def test_rewrites_relative_to_local():
    html = '<link href="../s.css"><script src="../app.js"></script><img src="/i/a.png">'
    new_html, unresolved = rewrite_html(html, BASE, resolve(MAPPING))
    assert 'href="styles/s.css"' in new_html
    assert 'src="scripts/app.js"' in new_html
    assert 'src="assets/img/a.png"' in new_html
    assert unresolved == []


def test_unmapped_stays_and_is_reported():
    html = '<img src="/i/missing.png">'
    new_html, unresolved = rewrite_html(html, BASE, resolve(MAPPING))
    assert 'src="/i/missing.png"' in new_html
    assert unresolved == ["/i/missing.png"]


def test_srcset_and_css_rewritten():
    html = ('<img srcset="/i/a.png 1x">'
            "<style>.h{background:url('/i/a.png')}</style>")
    new_html, unresolved = rewrite_html(html, BASE, resolve(MAPPING))
    assert "assets/img/a.png 1x" in new_html
    assert "url(assets/img/a.png)" in new_html
    assert unresolved == []


def test_srcset_with_data_uri_comma():
    """Apple-style: data: URI con coma dentro no se parte en dos URLs."""
    blob = "data:image/gif;base64,R0lGODlhAQABAAAAACw="
    html = f'<img srcset="{blob} 1x, /i/a.png 2x">'
    c = AssetCollector()
    c.feed(html)
    assert [u for _, _, u in c.refs] == ["/i/a.png"]
    new_html, unresolved = rewrite_html(html, BASE, resolve(MAPPING))
    assert blob in new_html
    assert "assets/img/a.png 2x" in new_html
    assert unresolved == []


def test_srcset_data_uri_space_after_comma():
    """Apple real: 'data:image/gif;base64, <blob>' con espacio."""
    blob = "R0lGODlhAQABAAAAACw="
    html = f'<source srcset="data:image/gif;base64, {blob}" media="(min-width:0px)" />'
    c = AssetCollector()
    c.feed(html)
    assert c.refs == []
    new_html, unresolved = rewrite_html(html, BASE, resolve(MAPPING))
    assert blob in new_html
    assert unresolved == []


def test_external_and_fragments_untouched():
    html = '<a href="https://other.com/x">e</a><a href="#top">t</a>'
    new_html, unresolved = rewrite_html(html, BASE, resolve(MAPPING))
    assert "https://other.com/x" in new_html
    assert unresolved == []


# ── find_broken ─────────────────────────────────────────────────────────
def test_find_broken(tmp_path):
    (tmp_path / "styles").mkdir()
    (tmp_path / "styles" / "ok.css").write_text("x")
    (tmp_path / "index.html").write_text(
        '<link href="styles/ok.css"><img src="assets/img/gone.png">'
        '<a href="https://external.com/">e</a>'
    )
    broken = find_broken(tmp_path)
    assert broken == [("index.html", "assets/img/gone.png")]


def test_find_broken_clean(tmp_path):
    (tmp_path / "index.html").write_text('<img src="a.png">')
    (tmp_path / "a.png").write_text("x")
    assert find_broken(tmp_path) == []


def test_cli_prefix_for_nested_pages(tmp_path):
    """Regresion: pages/*.html necesitan ../ en rutas locales."""
    page = tmp_path / "p.html"
    page.write_text('<img src="/i/a.png">', encoding="utf-8")
    map_file = tmp_path / "map.json"
    map_file.write_text(json.dumps({"https://example.com/i/a.png": "assets/img/a.png"}), encoding="utf-8")
    script = Path(__file__).resolve().parent.parent / "scripts" / "rewrite_urls.py"
    r = subprocess.run(
        [sys.executable, str(script), str(page), str(map_file),
         "--base", "https://example.com/", "--prefix", "../"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert 'src="../assets/img/a.png"' in r.stdout


def test_cli_out_writes_utf8_directly(tmp_path):
    """--out escribe el archivo directo (nunca por stdout del shell)."""
    page = tmp_path / "p.html"
    page.write_text('<p>caf\u00e9 \u2014 listo</p><img src="/i/a.png">', encoding="utf-8")
    map_file = tmp_path / "map.json"
    map_file.write_text(json.dumps({"https://example.com/i/a.png": "assets/img/a.png"}), encoding="utf-8")
    script = Path(__file__).resolve().parent.parent / "scripts" / "rewrite_urls.py"
    dest = tmp_path / "out.html"
    r = subprocess.run(
        [sys.executable, str(script), str(page), str(map_file),
         "--base", "https://example.com/", "--out", str(dest)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    raw = dest.read_bytes()
    assert "caf\u00e9".encode("utf-8") in raw
    assert 'src="assets/img/a.png"'.encode("utf-8") in raw


# ── layout policy (clone_site) ──────────────────────────────────────────
def test_page_local_mirrors_hierarchy():
    assert page_local("/") == "index.html"
    assert page_local("/tools/compress") == "tools/compress/index.html"
    assert page_local("/tools/compress/") == "tools/compress/index.html"
    assert page_local("/feed.xml") == "feed.xml"


def test_depth_prefix():
    assert depth_prefix("index.html") == ""
    assert depth_prefix("tools/compress/index.html") == "../../"


def test_asset_local_policy():
    used, css = set(), [0]
    assert asset_local("https://x.com/_next/static/chunks/a-1b2c.js", used, css) == "_next/static/chunks/a-1b2c.js"
    assert asset_local("https://x.com/_next/static/css/6d0be392af.css", used, css) == "styles/main.css"
    assert asset_local("https://x.com/i/mi foto.png", used, css) == "assets/img/mi_foto.png"
    assert asset_local("https://x.com/favicon.svg", used, css) == "favicon.svg"
    assert asset_local("https://x.com/blog/", used, css) is None
    assert asset_local("https://x.com/en-en/design", used, css) is None
    # Paginas con extension no se descargan como assets (fallback SPA 200)
    assert asset_local("https://x.com/index.html", used, css) is None
    assert asset_local("https://x.com/a/page.php", used, css) is None


def test_clone_end_to_end_file(tmp_path):
    """Mini-sitio via file://: layout jerarquico + cero rotos."""
    site = tmp_path / "site"
    (site / "sub").mkdir(parents=True)
    (site / "style.css").write_text("body{color:red}", encoding="utf-8")
    (site / "index.html").write_text(
        '<link href="style.css"><a href="sub/page.html">sub</a>', encoding="utf-8")
    (site / "sub" / "page.html").write_text(
        '<a href="../index.html">home</a>', encoding="utf-8")
    out = tmp_path / "clon"
    # Sin slash inicial: en file:// urljoin("/abs") resetearia al drive;
    # en http el flujo usa rutas absolutas (probado en el clon real).
    rc = clone_main([site.as_uri() + "/", "--pages", "index.html", "sub/page.html",
                     "--out", str(out), "--delay", "0"])
    assert rc == 0
    assert (out / "index.html").exists()
    assert (out / "sub" / "page.html").exists()
    assert (out / "styles" / "style.css").exists()
    assert (out / "map.json").exists()
    assert (out / "pending.txt").exists()
    assert find_broken(out) == []


def test_single_page_lands_on_root_index(tmp_path):
    """Regla raiz: clon de una sola pagina -> index.html en la raiz."""
    site = tmp_path / "site"
    site.mkdir()
    (site / "deep.html").write_text('<img src="a.png">', encoding="utf-8")
    (site / "a.png").write_text("x")
    out = tmp_path / "clon"
    rc = clone_main([site.as_uri() + "/", "--pages", "deep.html",
                     "--out", str(out), "--delay", "0"])
    assert rc == 0
    assert (out / "index.html").exists()
    assert find_broken(out) == []


def test_absolutize_same_origin():
    html = ('<a href="/co/iphone/">p</a><img src="/i/a.png">'
            '<a href="https://cdn.x.com/y">c</a><img src="//cdn.x.com/z.png">'
            '<img src="rel/b.png">')
    out = absolutize_same_origin(html, "https://example.com")
    assert 'href="https://example.com/co/iphone/"' in out
    assert 'src="https://example.com/i/a.png"' in out
    assert "https://cdn.x.com/y" in out and "//cdn.x.com/z.png" in out
    assert 'src="rel/b.png"' in out


def test_find_broken_root_absolute(tmp_path):
    (tmp_path / "ok.css").write_text("x")
    (tmp_path / "index.html").write_text(
        '<link href="/ok.css"><link href="/nope.css">')
    assert find_broken(tmp_path) == [("index.html", "/nope.css")]


def test_about_blank_kept():
    html = '<iframe src="about:blank"></iframe>'
    new_html, unresolved = rewrite_html(html, BASE, resolve(MAPPING))
    assert 'src="about:blank"' in new_html
    assert unresolved == []


def test_nested_sitemap_file(tmp_path):
    from clone_site import discover_sitemap
    sub = tmp_path / "sub.xml"
    sub.write_text("<urlset><url><loc>file:///a/page</loc></url></urlset>", encoding="utf-8")
    idx = tmp_path / "index.xml"
    idx.write_text(
        f"<sitemapindex><sitemap><loc>{sub.as_uri()}</loc></sitemap></sitemapindex>",
        encoding="utf-8")
    assert discover_sitemap(idx.as_uri(), "") == ["/a/page"]


def test_quote_url_unicode():
    from clone_site import quote_url
    out = quote_url("https://x.pl/en/Aktualności?a=1&b=ó")
    assert out == "https://x.pl/en/Aktualno%C5%9Bci?a=1&b=%C3%B3"


def test_robots_wildcards():
    from clone_site import _robots_match
    assert _robots_match("/a/b.json", "/*.json$")
    assert not _robots_match("/a/b.jsonx", "/*.json$")
    assert _robots_match("/js/app.js", "/js/")
    assert not _robots_match("/css/a.css", "/js/")


def test_strip_selectors():
    from clone_site import strip_selectors
    html = ('<div><div id="gate"><p>bloqueo<span>x</span></p></div>'
            '<main>contenido</main></div>')
    out, n = strip_selectors(html, ["#gate"])
    assert n == 1
    assert "bloqueo" not in out and "contenido" in out
    out2, n2 = strip_selectors('<div class="a modal b">x</div><p>y</p>', [".modal"])
    assert n2 == 1 and out2 == "<p>y</p>"
    out3, n3 = strip_selectors("<p>y</p>", ["#nada"])
    assert n3 == 0 and out3 == "<p>y</p>"


def test_max_assets_cap(tmp_path):
    from clone_site import clone
    site = tmp_path / "site"
    site.mkdir()
    (site / "a.css").write_text("x")
    (site / "b.css").write_text("y")
    (site / "index.html").write_text('<link href="a.css"><link href="b.css">', encoding="utf-8")
    out = tmp_path / "clon"
    rc = clone(site.as_uri() + "/", ["index.html"], out, 0, None, 0.0, 1)
    assert rc == 1  # incompleto reportado con honestidad
    assert len(list((out / "styles").glob("*.css"))) == 1
    assert "max-assets" in (out / "pending.txt").read_text(encoding="utf-8")


def test_collect_js_urls():
    from rewrite_urls import collect_js_urls
    js = ('import("./chunk-abc.js");fetch("/api/data");'
          'const u="https://cdn.z.com/lib.js";'
          "//# sourceMappingURL=app.js.map")
    urls = collect_js_urls(js)
    assert "./chunk-abc.js" in urls
    assert "/api/data" in urls
    assert "https://cdn.z.com/lib.js" in urls
    assert not any(u.endswith(".map") for u in urls)


def test_rewrite_js_local_and_live():
    from rewrite_urls import rewrite_js
    mapping = {"https://example.com/s/chunk.js": "scripts/chunk.js"}
    js = 'import("./chunk.js");fetch("/api/live");import("https://cdn.z.com/e.js");'
    out, unresolved = rewrite_js(js, "https://example.com/s/app.js", resolve(mapping))
    assert 'import("scripts/chunk.js")' in out
    assert 'fetch("https://example.com/api/live")' in out
    assert "https://cdn.z.com/e.js" in out
    # /api/live se absolutiza pero se reporta (el clon filtra /-prefijos de pending)
    assert unresolved == ["/api/live"]


def test_lazy_attrs_collected_and_rewritten():
    html = ('<img data-src="/i/lazy.png" src="data:image/gif;base64,AAA">'
            '<video data-poster="/i/post.jpg"></video>')
    c = AssetCollector()
    c.feed(html)
    assert [u for _, _, u in c.refs] == ["/i/lazy.png", "/i/post.jpg"]
    new_html, unresolved = rewrite_html(html, BASE, resolve(MAPPING))
    assert 'data-src="assets/img/a.png"' not in new_html  # /i/lazy.png no mapeado
    assert unresolved == ["/i/lazy.png", "/i/post.jpg"]


def test_lazy_mapped_rewrites():
    mapping = dict(MAPPING)
    mapping["https://example.com/i/lazy.png"] = "assets/img/lazy.png"
    html = '<img data-src="/i/lazy.png">'
    new_html, unresolved = rewrite_html(html, BASE, resolve(mapping))
    assert 'data-src="assets/img/lazy.png"' in new_html
    assert unresolved == []


def test_rewrite_css_relative_to_stylesheet():
    from rewrite_urls import collect_css_urls, rewrite_css
    css = ('.h{background:url(../img/bg.png)}'
           "@import 'more.css';"
           '.x{background:url(https://cdn.z.com/e.png)}')
    assert "../img/bg.png" in collect_css_urls(css)
    assert "more.css" in collect_css_urls(css)
    mapping = {
        "https://example.com/img/bg.png": "assets/img/bg.png",
        "https://example.com/s/more.css": "styles/more.css",
    }
    out, unresolved = rewrite_css(css, "https://example.com/s/main.css", resolve(mapping))
    assert "url(assets/img/bg.png)" in out  # el prefijo ../ lo pone el llamador
    assert '@import "styles/more.css"' in out
    assert "https://cdn.z.com/e.png" in out
    assert unresolved == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
