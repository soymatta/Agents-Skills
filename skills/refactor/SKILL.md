---
name: refactor
description: >-
  Improves code across four axes (cleanup, performance, security, architecture) by scanning and
  fixing, or applying findings from a project-analyzer audit report. Use when the user wants to
  refactor, optimize, harden, or remove code. NOT for read-only diagnosis (use project-analyzer)
  or adding features. Behavior-preserving except security, which may change behavior to close a
  hole. Use for public websites too: runs the 20-point web launch checklist (SEO, canonical URLs, SSL, backups, conversions).
  Triggers: "refactor", "refactorizar", "optimize", "optimizar", "clean up", "limpiar", "hardening",
  "limpiar codigo", "remove dead code", "extract helper", "checklist web", "web launch", "lista de lanzamiento".
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

## Web launch checklist (business websites only)

When the target is a public website, verify these 20 items under the matching
axis (almost all is `architecture` or `security`; nothing changes visible
behavior except `security`). Mark each ✔/✘ with `file:line` or command.
Overlaps `web-esenciales`: if that skill already audited the site, reuse its
report instead of repeating it.

Indexing and search:

1. No leftover `noindex` in prod (neither meta nor `X-Robots-Tag` nor
   `Disallow: /` in `robots.txt`).
2. Search Console signup (verified property) + sitemap submitted.
3. Bing Webmaster Tools signup (verified property) + sitemap submitted.

URLs and links:

4. Single domain version (with/without `www` + `http`→`https` with 301).
5. Real 301 redirects for old/changed URLs (no 302, no meta-refresh).
6. Canonical URLs (absolute `rel="canonical"`, one per page).
7. Clean URLs (readable, lowercase, no IDs or session params).
8. Internal link hierarchy (every page ≤3 clicks from home, no orphans,
   no redirect chains).
9. One page per search intent (no cannibalization between URLs).

Contact and social:

10. Tappable phone (`tel:`) and email (`mailto:`) on mobile and desktop.
11. Real social icons (point to the profiles, not to `#`).
12. Share preview (Open Graph + Twitter Card with absolute image
    ≥1200×630, title and description per page).

Infra:

13. Cache configured (hashed statics + `Cache-Control`, HTML revalidated).
14. Valid SSL with auto-renewal (expiry >30 days + cron/timer verified).
15. Automatic backups (what, how often, where, retention).
16. Downtime alerts (uptime monitor with alerts to the owner's channel).

Content and validation:

17. Test content removed (lorem, watermarked stock, demo users).
18. Tested in several browsers (Chromium + Firefox + WebKit, zero console errors).
19. Thank-you page after every form (conversion confirmed + no resubmit on reload).
20. Conversions measured (analytics event on each goal: form, call, purchase).

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
"refactor", "refactorizar", "optimize", "optimizar", "clean up", "limpiar", "hardening", "eliminar codigo muerto", "remove dead code", "extract helper", "checklist web", "web launch", "lista de lanzamiento", "pasar a produccion", "go live"
