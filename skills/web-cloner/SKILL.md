---
name: web-cloner
description: >-
  Clones web pages and full sites into organized local code (index.html, styles/, scripts/, assets/). Detects the original stack (Wappalyzer-style), picks the tool (Playwright/Chromium/Selenium/static fetch), maps the site, downloads HTML/CSS/JS/images, rewrites URLs to local paths, and ports to Astro, React, Vue, or Svelte. Use when the user asks to clone a web page, download a site, copy a landing, replicate a site in another framework, "clone this website", "descarga esta pagina", or migrate a site to static HTML, Astro, React, Vue, or Svelte, even without the word "clone". Also fires on a link with intent (pasted URL with an action verb, "mira esta pagina", "te paso este link", "bajame esto", "quiero esto en HTML", "look at this page", "download this for me"): then apply the scope triage below before touching anything.
---

# Web Cloner

Turns a public URL into a faithful, organized local project. By default it
produces static HTML + CSS + JavaScript; if the user asks for a framework
(Astro, React, Vue, Svelte), it ports the result. The user's choice always
wins over automatic detection.

## Link triage (mandatory when the input is a URL)

Download nothing until this is answered with the user. Ask once, with a
recommendation:

1. **Just this page** (recommended) — the HTML + assets of that URL, fast.
2. **This page + sublinks** — same-origin BFS from here, depth 2.
3. **Full site from root** — go to the domain `/` and map everything.

If the user already stated the scope ("just this one", "the whole site"),
do not ask: that order wins.

## 0. Scope and rights (first, no exceptions)

- Only clone own sites, authorized ones, or public content for
  learning/internal migration. If it smells like paywall, login, or ToS that
  forbids it: say so in one line and ask for explicit confirmation first.
- Respect `robots.txt` by default (override only with the user's explicit
  order; see `--ignore-robots`).
- Never extract credentials, tokens, PII, or other users' data even if they
  show up in traffic.
- Paywall or login: ask the user for credentials. If given, use them only
  for the session (env vars or storage-state in temp OUTSIDE the repo/output)
  and delete storage when done; never store credentials in the repo,
  `map.json`, or logs. Without credentials the scope ends there: deliver the
  public part + a report of what is blocked.

## 1. Recon: detect the original stack

Before downloading, identify what the page is built with (to suggest the
same stack for the port). In order, cheapest first:

1. HTTP headers (`server`, `x-powered-by`) + `curl -sI <url>`.
2. HTML markers: `__NEXT_DATA__` (Next.js/React), `__NUXT__`/`_nuxt/`
   (Nuxt/Vue), `astro-`/`Astro.` (Astro), `data-svelte`/`svelte-` (Svelte),
   `wp-content` (WordPress), `cdn.shopify` (Shopify).
3. JS bundles: `/_next/`, `/assets/index-*.js` (Vite), `main.*.chunk.js` (CRA).
4. `python -m pip show wappalyzer 2>/dev/null || npx -y wappalyzer-cli <url>`
   for fine confirmation if needed.

Report in one line: detected stack + suggested framework for the port.
If the user already named a framework, that choice wins and the rest is
informational.

## 2. Pick the tool

| Case | Tool |
|------|------|
| Static page or SSR with full HTML | `curl`/fetch + this skill's scripts |
| SPA / JS-rendered content | Playwright + headless Chromium (default) |
| Playwright fails (WebGL, DRM, captchas) | Selenium + real Chrome; manual as last resort |
| Light antibot only (Cloudflare check, rate-limit) | Real Chromium, `headless=False` once, wait for `networkidle`, retry with backoff, 1-3 s delays between pages |

**Bounded aggressive evasion** (automation anti-detection): persistent real
Chromium profile (not classic headless: `headless=new` or headed), common
viewport and user-agent, a single session, human-like waits (`networkidle`
+ 1-3 s), exponential backoff on 429/403, honor `Retry-After`. Hard stops
(it ends there, reported, never worked around): interactive CAPTCHA,
persistent 403 after 3 retries, login without credentials, banned IP. Out of
scope: captcha-solving services and aggressive rotation to evade bans.

Prerequisites (install once): `python -m pip install playwright &&
python -m playwright install chromium`. Selenium only if Playwright is not
enough.

## 3. Map the site

- Start: the requested URL. Single page = just it + its assets.
- Site: same-origin BFS to depth 3 by default (ask for more), plus
  `sitemap.xml` URLs and internal links from the HTML.
- Save the map as `map.json`: `{ "remote_url": "relative/local/path" }`.
  It is the contract the scripts below use.

## 4. Download assets

Use `scripts/clone_site.py` as the driver (fetch, map, download, rewrite,
and verify in one deterministic pass). Manual only if the driver does not
cover the case.

- Final post-JS HTML (`page.content()` in Playwright) + linked CSS/JS/
  images/fonts/media. Images at original resolution (`srcset`: largest by
  default, all with `--all-srcset`). Lazy-load included: `data-src`/
  `data-srcset`/`data-poster` treated as `src`/`srcset`.
- Three collection phases (all deterministic and tested): HTML
  (`AssetCollector`), downloaded CSS (`collect_css_urls`: `url()`/`@import`
  relative to the CSS, rewritten with their own prefix) and downloaded JS
  (`collect_js_urls`: `import()`/`fetch()`/quoted strings; fixed point,
  max 2 rounds). Anything not downloadable inside JS/CSS stays absolutized
  to the live site, same as in HTML.
- Budgets: `--asset-delay` (default 0.3 s; pages use `--delay`) and
  `--max-assets` (default 400, reported in `pending.txt`). Without budgets,
  large sites never finish.
- Names (`asset_local`, with tests): `.js` keeps its original subtree
  (bundles reference each other by hash: renaming breaks the app); `.css`
  goes to `styles/` (hash → `main.css`/`style-N.css`); images/fonts/media
  get friendly names in `assets/img|fonts|media`; `favicon.*`,
  `apple-touch-icon*`, `*.webmanifest` stay at root (browsers request them
  there automatically).
- Rewrite references with `scripts/rewrite_urls.py` using `map.json`
  (or let `clone_site.py` do it); unmapped stays intact and is listed as
  pending. Nested pages use `--prefix ../` per level (`clone_site.py`
  computes it alone with `depth_prefix`).
- Encoding: HTML never passes through shell strings (PowerShell re-encodes
  stdout and produces `ÔÇö` mojibake). `rewrite_urls.py --out` writes the
  file directly in UTF-8; `clone_site.py` always does so.
- Out-of-scope links stay absolutized to the live site (navigation keeps
  working) and do NOT count as pending.
- Purpose rule: `scripts/` are 100% generic (zero domains, zero selectors,
  zero single-site paths). Case-specific code (orchestrators, browser dumps)
  lives in temp, never committed, never enters the skill.

## 5. Output layout (always the same: mirrors the URL hierarchy)

```
/              → index.html
/a/b           → a/b/index.html
clon/
  index.html
  <original/path>/index.html  # e.g. tools/compress/index.html
  favicon.svg                 # root files, at root
  styles/*.css                # (JS bundles keep their original subtree)
  <original-js-subtree>/      # e.g. _next/static/chunks/*.js
  assets/img|fonts|media/     # created only if something lands inside
  map.json                    # remote_url -> local path contract
```

No empty folders: each dir is created only on its first file.
Client routers (Next/Nuxt) expect the original routes: with mirrored
hierarchy navigation never 404s.
Root rule: every clone carries `index.html` at root (single-page clone:
that page IS the `index.html`, even if its URL is `/co/` or `/en`).

## Blocking gates and modals (cookie walls, email gates, newsletters)

1. Capture served HTML + screenshot: confirm it truly blocks.
2. Inspect: is the content in the static HTML (merely hidden) or served by
   the backend after the gate?
3. Content present and purely visual gate → `--strip "#gate-id"`
   (verify served that the page stays usable, not black).
4. Server-gated content (like a signup returning data) → NO bypass: ask the
   user for credentials; without them the scope ends there and the clone
   stays faithful (with gate, like the live site).

## 6. Framework port (only if asked)

| Target | Rule |
|--------|------|
| Astro (default if origin is static) | `src/pages/*.astro` + `src/styles/`, `astro build` must pass |
| React | `src/components/` + `src/App.jsx`, `npm run build` must pass |
| Vue | `src/components/*.vue`, `npm run build` must pass |
| Svelte | `src/routes/` + `src/lib/`, `npm run build` must pass |

The target framework build must finish green; if not, deliver the static
version and report the build error as-is.

## 7. Verify before delivering

1. `python scripts/check_links.py clon/` → zero local broken links.
2. Review `pending.txt`: download failures (retry or report) and unresolved
   relative refs. Out-of-scope links stay absolutized to the live site by
   design (not pending).
3. Counts: pages in `map.json` == HTML on disk; listed assets == assets on disk.
3. Bytes: zero double-encoded sequences (`Ã` in latin1 = mojibake).
4. Preview SERVED (`python -m http.server` or `npx serve` in `clon/`),
   never `file://`: client routers and relative fetch require it.
   Click the main navigation and confirm no page 404s.

## Scripts

- `scripts/clone_site.py` — full driver: fetch (with header/meta charset),
  `robots.txt`, sitemap/crawl, download, `map.json`, depth-prefixed rewrite
  and report. `--pages`, `--sitemap` (follows one sitemap-index level),
  `--crawl N`, `--delay`, `--insecure` (broken TLS only, opt-in),
  `--ignore-robots` (ONLY with the user's explicit order). Writes
  `pending.txt` (download failures + unresolved refs).
- `scripts/rewrite_urls.py` — sanitizes paths (`local_path_for`), extracts
  references (`AssetCollector`) and rewrites them to local (`rewrite_html`,
  `--prefix`, `--out` for direct UTF-8 writes).
- `scripts/check_links.py` — `find_broken(root)` lists broken local
  references in `*.html`.
- Tests: `tests/test_web_cloner.py` (`python -m pytest skills/web-cloner -v`).
