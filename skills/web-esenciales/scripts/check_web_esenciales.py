"""Audita los 20 imprescindibles de web-esenciales sobre HTML local.

Usage:
    python check_web_esenciales.py <dir>

Imprime JSON {item: bool} y una tabla presente/faltante. Solo stdlib.
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ITEMS = [
    "404", "cta-sin-scroll", "enlaces-internos", "pagina-gracias",
    "breadcrumbs", "casos-exito", "faq-5", "tiempo-respuesta",
    "cta-movil-fijo", "robots-txt", "titulos-unicos", "metadescripciones",
    "og-image", "mapa-direcciones", "resenas-reales", "alt-imagenes",
    "schema-local", "privacidad", "analytics", "foto-equipo",
]

CTA_RE = re.compile(r"contacta|presupuesto|reserv|comprar|pide|cotiza|llama|whatsapp|empezar|prueba gratis", re.I)
TIME_RE = re.compile(r"respond\w+ en|respuesta en|en 24\s?h|en menos de \d+|plazo de \d+", re.I)
SUCCESS_RE = re.compile(r"casos?\s+de\s+exito|casos?\s+de\s+éxito|clientes|portfolio|proyectos", re.I)
REVIEW_RE = re.compile(r"rese\xf1as|resenas|opiniones|testimonios|valoraci|reseñas", re.I)
TEAM_RE = re.compile(r"equipo|nosotros|team|staff", re.I)
MAP_RE = re.compile(r"google\.[a-z]+/maps|openstreetmap|maps\.google|iframe.*mapa|Nuestra ubicaci|direcci\xf3n|dirección|C/ [A-Z]", re.I)


class _Info(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.titles: list[str] = []
        self.metas: list[str] = []
        self.og_image = False
        self.alts: list[str | None] = []
        self.has_img = False
        self.internal_links = 0
        self.breadcrumb = False
        self.schema_local = False
        self.analytics = False
        self.sticky_cta = False
        self.faq_count = 0
        self.text = ""
        self._in_title = False
        self._in_ld = False
        self._ld_buf = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        cls = (a.get("class") or "") + " " + (a.get("id") or "")
        style = a.get("style") or ""
        if tag == "title":
            self._in_title = True
            self._title_buf = ""
        if tag == "meta":
            name = (a.get("name") or "").lower()
            prop = (a.get("property") or "").lower()
            if name == "description" and (a.get("content") or "").strip():
                self.metas.append(a["content"].strip())  # type: ignore[index]
            if prop == "og:image" and (a.get("content") or "").strip():
                self.og_image = True
        if tag == "img":
            self.has_img = True
            self.alts.append(a.get("alt"))
        if tag == "a":
            href = a.get("href") or ""
            if href.startswith("/") and len(href) > 1 or href.endswith(".html") and "http" not in href or href.startswith(("./", "../", "#")) and len(href) > 1:
                self.internal_links += 1
        if "breadcrumb" in cls.lower():
            self.breadcrumb = True
        if tag == "script" and (a.get("type") or "") == "application/ld+json":
            self._in_ld = True
            self._ld_buf = ""
        src = (a.get("src") or "") + " " + (a.get("href") or "")
        if "googletagmanager" in src or "google-analytics" in src or "gtag" in src:
            self.analytics = True
        if ("fixed" in style or "sticky" in style or "fixed" in cls or "sticky" in cls) and ("cta" in cls.lower() or "whatsapp" in cls.lower()):
            self.sticky_cta = True
        if tag in ("details",) or "faq" in cls.lower() or "accordion" in cls.lower():
            self.faq_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            self.titles.append(getattr(self, "_title_buf", ""))
        if tag == "script" and self._in_ld:
            self._in_ld = False
            if "LocalBusiness" in self._ld_buf or "BreadcrumbList" in self._ld_buf and True:
                if "LocalBusiness" in self._ld_buf:
                    self.schema_local = True
                if "BreadcrumbList" in self._ld_buf:
                    self.breadcrumb = True

    def handle_data(self, data: str) -> None:
        if getattr(self, "_in_title", False):
            self._title_buf = getattr(self, "_title_buf", "") + data
        if self._in_ld:
            self._ld_buf += data
        else:
            self.text += data + "\n"
        if "gtag(" in data or "ga(" in data or "googletagmanager" in data:
            self.analytics = True


def audit(root: str | Path) -> dict[str, bool]:
    """Audita un directorio con HTML. Devuelve {item: bool} con los 20 items."""
    base = Path(root)
    pages = sorted(base.rglob("*.html"))
    texts = {p: p.read_text("utf-8", errors="replace") for p in pages}
    infos: dict[Path, _Info] = {}
    for p, html in texts.items():
        info = _Info()
        info.feed(html)
        infos[p] = info

    names = {p.name.lower() for p in pages}
    all_text = "\n".join(texts.values())
    css_text = ""
    for f in base.rglob("*.css"):
        css_text += f.read_text("utf-8", errors="replace")

    index = next((p for p in pages if p.name.lower() == "index.html"), pages[0] if pages else None)
    index_info = infos.get(index) if index else None
    index_html = texts.get(index, "") if index else ""

    titles = [t.strip() for info in infos.values() for t in info.titles if t.strip()]
    result: dict[str, bool] = {}
    result["404"] = "404.html" in names
    head = index_html[:8000]
    result["cta-sin-scroll"] = bool(index_info) and bool(CTA_RE.search(head))
    result["enlaces-internos"] = any(i.internal_links > 0 for i in infos.values())
    result["pagina-gracias"] = "gracias.html" in names or "thank-you.html" in names or bool(re.search(r"gracias por", all_text, re.I))
    result["breadcrumbs"] = any(i.breadcrumb for i in infos.values())
    result["casos-exito"] = bool(SUCCESS_RE.search(all_text))
    faq_total = sum(i.faq_count for i in infos.values())
    questions = len(re.findall(r"\?\s*$", all_text, re.M))
    result["faq-5"] = faq_total >= 5 or questions >= 5
    result["tiempo-respuesta"] = bool(TIME_RE.search(all_text))
    result["cta-movil-fijo"] = any(i.sticky_cta for i in infos.values()) or bool(re.search(r"position\s*:\s*(fixed|sticky)", css_text) and CTA_RE.search(css_text + all_text))
    result["robots-txt"] = (base / "robots.txt").exists()
    result["titulos-unicos"] = len(pages) > 0 and len(titles) >= len(pages) and len(set(titles)) == len(titles)
    result["metadescripciones"] = len(pages) > 0 and all(len(i.metas) > 0 for i in infos.values())
    result["og-image"] = any(i.og_image for i in infos.values())
    result["mapa-direcciones"] = bool(MAP_RE.search(all_text))
    result["resenas-reales"] = bool(REVIEW_RE.search(all_text))
    if not any(i.has_img for i in infos.values()):
        result["alt-imagenes"] = True  # sin imagenes no hay falta
    else:
        result["alt-imagenes"] = all(a is not None and a.strip() != "" for i in infos.values() for a in i.alts)
    result["schema-local"] = any(i.schema_local for i in infos.values())
    result["privacidad"] = "privacidad.html" in names or bool(re.search(r"pol.tica de privacidad|aviso legal", all_text, re.I))
    result["analytics"] = any(i.analytics for i in infos.values())
    result["foto-equipo"] = bool(TEAM_RE.search(all_text))
    return result


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python check_web_esenciales.py <dir>", file=sys.stderr)
        return 2
    res = audit(sys.argv[1])
    missing = [k for k, v in res.items() if not v]
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print(f"\nPresentes: {sum(res.values())}/{len(res)}" + (f" | Faltan: {', '.join(missing)}" if missing else " | Todo presente: no disparar la skill."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
