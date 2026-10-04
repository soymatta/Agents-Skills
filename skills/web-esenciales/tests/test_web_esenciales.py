"""Tests de web-esenciales: el audit distingue web completa de incompleta."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_web_esenciales import ITEMS, audit

FULL_INDEX = """<!doctype html><html lang="es"><head>
<title>Fontanero Madrid 24h</title>
<meta name="description" content="Fontanero en Madrid.">
<meta property="og:image" content="https://x/img.jpg">
<script>gtag('config','G-1');</script>
<script type="application/ld+json">{"@type":"LocalBusiness","name":"X"}</script>
</head><body>
<nav class="breadcrumb"><a href="/">Inicio</a></nav>
<header><h1>Fontanero</h1><a class="cta fixed" style="position:fixed" href="/contacto">Pide presupuesto</a></header>
<p>Respondemos en menos de 2 horas.</p>
<a href="/servicios.html">Servicios</a>
<section><h2>Casos de exito</h2><p>Nuestros clientes opinan.</p></section>
<section class="faq"><details><summary>q1?</summary></details><details><summary>q2?</summary></details>
<details><summary>q3?</summary></details><details><summary>q4?</summary></details><details><summary>q5?</summary></details></section>
<section><h2>Resenas</h2><p>Maria: 5 estrellas.</p></section>
<section><h2>Nuestro equipo</h2><img src="e.jpg" alt="Equipo"></section>
<iframe src="https://www.google.com/maps/embed"></iframe><p>Calle Mayor 1, Madrid</p>
<img src="t.jpg" alt="Trabajo">
<a href="/privacidad.html">Politica de privacidad</a>
</body></html>"""


def _site(tmp_path: Path, *, full: bool) -> Path:
    (tmp_path / "index.html").write_text(FULL_INDEX if full else "<html><head><title>X</title></head><body><p>Hola</p></body></html>", encoding="utf-8")
    if full:
        for name in ("404.html", "gracias.html", "privacidad.html", "servicios.html"):
            (tmp_path / name).write_text(f"<html><head><title>{name}</title><meta name='description' content='d'></head><body></body></html>", encoding="utf-8")
        (tmp_path / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
        (tmp_path / "style.css").write_text(".cta{position:fixed}", encoding="utf-8")
    return tmp_path


def test_items_son_20() -> None:
    assert len(ITEMS) == 20


def test_web_completa_pasa_todo(tmp_path: Path) -> None:
    res = audit(_site(tmp_path, full=True))
    assert all(res.values()), f"faltan: {[k for k, v in res.items() if not v]}"


def test_web_minima_falla_mayoria(tmp_path: Path) -> None:
    res = audit(_site(tmp_path, full=False))
    assert sum(res.values()) < 10
    assert res["robots-txt"] is False
    assert res["404"] is False
