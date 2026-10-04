---
name: web-esenciales
description: Audita y completa los 20 imprescindibles de una web de negocio antes de darla por buena (404 personalizada, CTA visible sin scroll, enlaces internos, pagina de gracias, breadcrumbs, casos de exito, 5 FAQs, promesa de tiempo de respuesta, CTA fijo en movil, robots.txt, titulos unicos, metadescripciones, og:image, mapa y direcciones, resenas reales, alt en imagenes, schema LocalBusiness, privacidad, Google Analytics, foto del equipo). Usa esta skill SIEMPRE que el usuario hable de una web: crearla, mejorarla, pulirla, darle detalles, "revisa mi web", "mejora la landing", "que le falta a mi pagina", "optimiza el sitio", "detalles finales", "esta lista para publicar". PRIMERO audita con scripts/check_web_esenciales.py o revision manual; si los 20 estan presentes NO hagas nada mas (evita el disparo innecesario). Si falta al menos uno, reporta faltantes y pregunta al usuario si implementa cada uno antes de tocar codigo.
---

# Web Esenciales — los 20 imprescindibles

Nombre original propuesto por el usuario: *WebNecesaris*. Se renombra a
`web-esenciales`: kebab-case como el resto del repo, ortografia correcta y
significado inmediato en ES/CA.

Convierte una web "casi lista" en una web completa de negocio. No es diseño
(eso es `impeccable` / `ui-ux-pro-max`) ni clonado (`web-cloner`): es el gate
de imprescindibles que toda web comercial debe tener.

## Gate anti-disparo (obligatorio, primero, sin excepcion)

1. Audita la web (script de abajo o revision manual pagina por pagina).
2. Si los 20 estan presentes: dilo en una linea y PARA. No propongas nada.
3. Si falta al menos uno: sigue al workflow. Nunca te saltes la auditoria.

## Checklist (20)

Conversión (5): `cta-sin-scroll` CTA visible sin hacer scroll · `cta-movil-fijo`
CTA fijo/sticky en movil · `tiempo-respuesta` promesa explicita ("respondemos en
24 h") · `casos-exito` casos de exito/clientes · `resenas-reales` resenas o
testimonios reales con nombre.

Confianza (4): `faq-5` minimo 5 preguntas frecuentes · `foto-equipo` foto del
equipo real · `mapa-direcciones` mapa + direccion · `pagina-gracias` pagina de
agradecimiento tras formulario.

SEO/tecnico (8): `404` pagina 404 personalizada · `robots-txt` archivo robots.txt ·
`titulos-unicos` `<title>` unico por pagina · `metadescripciones` meta description
por pagina · `og-image` imagen para compartir en redes · `alt-imagenes` alt con
contenido en toda `<img>` · `schema-local` JSON-LD LocalBusiness · `analytics`
Google Analytics / tag manager.

Estructura/legal (3): `enlaces-internos` enlaces internos entre paginas ·
`breadcrumbs` migas de pan o equivalente · `privacidad` politica de privacidad.

## Workflow

1. **Audita.** `python scripts/check_web_esenciales.py <dir>` sobre el HTML local
   (o revision manual si es URL/maqueta). Guarda el resultado como tabla
   presente/faltante por item.
2. **Reporta.** Una linea por faltante: que falta + por que importa (1 frase).
   No mas de 5 lineas en el reporte inicial; el detalle va despues.
3. **Pregunta.** Por cada faltante, pregunta al usuario si lo implementa
   (lote en una sola pregunta, no 20 turnos). Solo los confirmados se tocan.
4. **Implementa.** Lo confirmado, con el patron minimo de `references/patrones.md`
   si existe; si no, el patron estandar del stack del proyecto.
5. **Re-audita.** Vuelve a correr el script: cero faltantes confirmados = DONE.

## Reglas

- Un faltante no confirmado por el usuario NO se implementa. Se lista como
  pendiente y listo.
- Si el proyecto ya usa `impeccable` o `ui-ux-pro-max`, esta skill no rediseña
  nada: solo añade los imprescindibles faltantes con los tokens existentes.
- Caracteres especiales (tildes, `ñ`, emojis) van directo en UTF-8; nunca
  escapes del shell en el HTML.

## Scripts

- `scripts/check_web_esenciales.py` — `audit(root)` audita un directorio con
  HTML y devuelve `{item: bool}` + CLI que imprime JSON y tabla.
  (`python scripts/check_web_esenciales.py <dir>`)
- Tests: `tests/test_web_esenciales.py` (`python -m pytest skills/web-esenciales -v`).
