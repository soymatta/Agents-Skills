# Web — Agents-Skills landing page

Single-page Astro site documenting the repo: agents, skills, slash commands, and
install steps. Content lives in `src/pages/index.astro` (hardcoded inventory — keep
it in sync with `README.md` and `setup.py` when adding a skill/agent).

## Commands

```sh
npm install       # install dependencies
npm run dev       # dev server at http://localhost:4321
npm run build     # static build output to dist/
npm run preview   # preview the production build
```

## Deploy notes

- `npm install` fails on exFAT volumes (`EACCES` creating links), so build off the
  USB drive or in CI. `dist/` is gitignored and goes stale silently otherwise.
- Editing on the USB and serving a copy: `astro dev` does not recompile the page's
  `<style>` when the source is replaced by a copy tool (rsync/cp), even when the
  markup updates. Serve `dist/` and rebuild instead; a stale dev server shows new
  markup with old CSS, which reads as a broken layout.
- `site` in `astro.config.mjs` is unset, so `canonical`, `og:url` and `og:image`
  are emitted root-relative. Setting `site` to the deploy origin makes them
  absolute (see `absolute()` in `src/layouts/Layout.astro`).
- `public/og-image.png` is generated, not hand-edited:
  `python3 scripts/make-og-image.py` (needs Pillow; DejaVu fonts).
