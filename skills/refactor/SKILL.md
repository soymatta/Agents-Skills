---
name: refactor
description: >-
  Improves code across four axes (cleanup, performance, security, architecture) by scanning and
  fixing, or applying findings from a project-analyzer audit report. Use when the user wants to
  refactor, optimize, harden, or remove code. NOT for read-only diagnosis (use project-analyzer)
  or adding features. Behavior-preserving except security, which may change behavior to close a
  hole. Triggers: "refactor", "refactorizar", "optimize", "clean up", "hardening", "limpiar codigo".
compatibility: Language-agnostic. Edits target code. Verifies with tests/type-checks.
---

# Refactor

The act-side of code improvement: it changes code to make it better. Behavior-preserving for
cleanup, performance, and architecture; security may change behavior on purpose to close a hole.

## Axes

| #   | Axis           | Lens                                                        |
| --- | -------------- | ----------------------------------------------------------- |
| 01  | `performance`  | N+1, hot paths, batching, memoization, unnecessary I/O      |
| 02  | `security`     | OWASP, input validation, authz, secrets: harden and fix     |
| 03  | `cleanup`      | clean code: rename, extract, DRY, dead code, complexity      |
| 04  | `architecture` | extract layers, fix coupling, enforce boundaries             |

Run the one axis named, or offer all applicable when the request is unscoped. A request to
delete or remove code runs `cleanup` directly with no axis question. Never silently default
to one axis.

## Transversal rules

- **Behavior-preserving** for cleanup, performance, architecture: public inputs and outputs
  stay identical, verified by tests, type checks, or a side-by-side run. Security may alter
  behavior to close a vulnerability and must call that out explicitly.
- **Scope each refactor**: a refactor fixes the target code and nothing else. Do not bundle
  drive-by feature changes or unrelated rewrites. Delete/restructure only what the chosen
  axis calls for; confirm before destructive moves.
- **Audit-fed, optional**: when the caller pushes an audit report (a path to a report or
  pasted findings), take its findings for this axis as the fix list and skip the scan. The
  bridge is the report artifact; this skill never loads or calls another skill.
- **Tests**: add tests only as a regression for a security fix, never otherwise. Verify the
  refactor with the project's existing tests / type checks / a side-by-side run.
- **Severity** uses the project's shared scale (`CRITICAL` / `MAJOR` / `MINOR` / `SUGGESTION`).

## Web launch checklist (solo webs de negocio)

Cuando el target es una web pública, verifica estos 20 puntos como parte del
eje que corresponda (casi todo es `architecture` o `security`; nada cambia
comportamiento visible salvo `security`). Marca cada uno ✔/✘ con
`archivo:línea` o comando. Solapa con `web-esenciales`: si esa skill ya
auditó la web, reutiliza su reporte en vez de repetirlo.

Indexación y buscadores:

1. Sin `noindex` residual en prod (ni meta ni `X-Robots-Tag` ni
   `Disallow: /` en `robots.txt`).
2. Alta en Search Console (propiedad verificada) + sitemap enviado.
3. Alta en Bing Webmaster Tools (propiedad verificada) + sitemap enviado.

URLs y enlaces:

4. Una sola versión del dominio (con/sin `www` + `http`→`https` con 301).
5. Redirects 301 reales para URLs viejas/cambiadas (no 302 ni meta-refresh).
6. URLs canónicas (`rel="canonical"` absoluta, una por página).
7. URLs limpias (legibles, minúsculas, sin IDs ni parámetros de sesión).
8. Jerarquía de enlaces internos (toda página a ≤3 clics del inicio, sin
   huérfanas ni cadenas de redirects).
9. Una página por intención de búsqueda (sin canibalización entre URLs).

Contacto y social:

10. Teléfono (`tel:`) y correo (`mailto:`) tocables en móvil y escritorio.
11. Iconos de redes sociales reales (apuntan a los perfiles, no a `#`).
12. Vista previa al compartir (Open Graph + Twitter Card con imagen absoluta
    ≥1200×630, título y descripción por página).

Infra:

13. Caché configurada (estáticos con hash + `Cache-Control`, HTML revalidado).
14. SSL válido con renovación automática (expiry >30 días + cron/timer verificado).
15. Copias de seguridad automáticas (qué, cada cuánto, dónde, retención).
16. Avisos si la web se cae (monitor uptime con alerta al canal del dueño).

Contenido y validación:

17. Contenido de prueba borrado (lorem, imágenes de stock con marca, usuarios demo).
18. Probada en varios navegadores (Chromium + Firefox + WebKit, sin errores de consola).
19. Página de gracias tras cada formulario (conversión confirmada + no reenvío al recargar).
20. Conversiones medidas (evento de analytics en cada objetivo: formulario, llamada, compra).

## Workflow

1. **Triage** — print size (`small` / `medium` / `large`), which axis runs, and the files it
   affects, before touching code.
2. **Scope** — confirm the axis (asked once if unscoped); gather the fix list (scan or audit).
3. **Fix** — apply changes surgically, one finding at a time, mapping each to a concrete edit.
   Skip with reason anything that would introduce risk.
4. **Verify** — run tests / type-check / side-by-side run; confirm behavior preserved (or the
   security change is intentional and flagged).
5. **Report** — what changed, what was verified, what was skipped and why.

## Handoff

Output is a token-optimized report listing each change with `file:line`, the axis, and the
verification evidence. Another agent or the user can judge the refactor from the report.

## Keywords
"refactor", "refactorizar", "optimize", "optimizar", "clean up", "limpiar", "hardening", "eliminar codigo muerto", "remove dead code", "extract helper"
