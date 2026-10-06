---
name: web-esenciales
description: >-
  Audits and completes the 20 must-haves of a business website before sign-off (custom 404, above-the-fold CTA, internal links, thank-you page, breadcrumbs, success stories, 5 FAQs, response-time promise, sticky mobile CTA, robots.txt, unique titles, meta descriptions, og:image, map + address, real reviews, image alts, LocalBusiness schema, privacy, Google Analytics, team photo). Use whenever the user talks about a website: create, improve, polish, add details, "revisa mi web", "mejora la landing", "que le falta a mi pagina", "optimiza el sitio", "detalles finales", "esta lista para publicar", "review my site", "improve my landing", "is my site ready". Audit FIRST with scripts/check_web_esenciales.py or manual review; if all 20 are present do nothing else (avoids misfires). If at least one is missing, report gaps and ask the user before implementing each one.
---

# Web Esenciales — the 20 must-haves

Original name proposed by the user: *WebNecesaris*. Renamed to
`web-esenciales`: kebab-case like the rest of the repo, correct spelling,
immediate meaning in ES/CA.

Turns an "almost done" site into a complete business website. Not design
(that is `impeccable` / `ui-ux-pro-max`) nor cloning (`web-cloner`): it is
the must-have gate every commercial site must pass.

## No-misfire gate (mandatory, first, no exceptions)

1. Audit the site (script below or manual page-by-page review).
2. If all 20 are present: say so in one line and STOP. Propose nothing.
3. If at least one is missing: follow the workflow. Never skip the audit.

## Checklist (20)

Conversion (5): `cta-sin-scroll` CTA visible without scrolling ·
`cta-movil-fijo` sticky/fixed CTA on mobile · `tiempo-respuesta` explicit
promise ("we reply within 24 h") · `casos-exito` success stories/clients ·
`resenas-reales` real reviews or testimonials with names.

Trust (4): `faq-5` at least 5 FAQs · `foto-equipo` real team photo ·
`mapa-direcciones` map + address · `pagina-gracias` thank-you page after
forms.

SEO/technical (8): `404` custom 404 page · `robots-txt` robots.txt file ·
`titulos-unicos` unique `<title>` per page · `metadescripciones` meta
description per page · `og-image` social share image · `alt-imagenes`
contentful alt on every `<img>` · `schema-local` JSON-LD LocalBusiness ·
`analytics` Google Analytics / tag manager.

Structure/legal (3): `enlaces-internos` internal links between pages ·
`breadcrumbs` breadcrumbs or equivalent · `privacidad` privacy policy.

## Workflow

1. **Audit.** `python scripts/check_web_esenciales.py <dir>` on local HTML
   (or manual review for URLs/mockups). Save the result as a
   present/missing table per item.
2. **Report.** One line per gap: what is missing + why it matters (1 sentence).
   No more than 5 lines in the initial report; detail comes later.
3. **Ask.** For each gap, ask the user whether to implement it (batched in a
   single question, not 20 turns). Only confirmed items get touched.
4. **Implement.** Confirmed items, with the minimal pattern from
   `references/patrones.md` if present; otherwise the project stack standard.
5. **Re-audit.** Re-run the script: zero confirmed gaps = DONE.

## Rules

- A gap the user did not confirm is NOT implemented. Listed as pending, done.
- If the project already uses `impeccable` or `ui-ux-pro-max`, this skill
  redesigns nothing: it only adds the missing must-haves with existing tokens.
- Special characters (accents, `ñ`, emojis) go directly in UTF-8; never
  shell escapes in the HTML.

## Scripts

- `scripts/check_web_esenciales.py` — `audit(root)` audits a directory of
  HTML and returns `{item: bool}` + CLI printing JSON and table.
  (`python scripts/check_web_esenciales.py <dir>`)
- Tests: `tests/test_web_esenciales.py` (`python -m pytest skills/web-esenciales -v`).
