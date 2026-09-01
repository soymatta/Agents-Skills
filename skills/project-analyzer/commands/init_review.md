---
description: First command when opening a project. Understands the whole project (purpose, relevant files, structure), finds blockers and pending work, flags useless/overlapping files and structure-optimization opportunities, and ends with a short, precise token-optimized handoff summary for another agent to fix.
agent: builder
---

# init_review — Project onboarding + health scan

Run this FIRST when working on a project you don't fully know. Read-only over the
audited code: diagnose and summarize, do not edit. Produce a concise, precise
summary that lets another agent (e.g. builder) fix things.

Scope: default is the current directory; use `$ARGUMENTS` to focus on a subpath,
module, or specific concern (e.g. `/init_review src/` or `/init_review auth`).
If `$ARGUMENTS` asks for a deep-dive on one area, dispatch to the
**project-analyzer** skill for the detailed pass; keep this command's output as
the short summary.

Exclude by default: `.git/`, `node_modules/`, `.venv/`, `venv/`, `build/`,
`dist/`, caches, lockfiles, generated binaries. Cap the file set read (~200
files / ~1MB) and sample representative files instead of reading everything.

## F1 — Understand the project
1. Read identity files: `README.md`, `AGENTS.md`, `package.json`/`pyproject.toml`,
   `setup.py`, `Dockerfile`, `.gitignore`, CI config (`.github/workflows/`).
2. Map the structure (glob + listing) and identify the **relevant/core files** —
   entry points, main modules, and configs — vs. everything else.
3. State, in 2-3 lines: what the project does, its stack, and how it runs/builds.

## F2 — Blockers (things that keep it from working)
- Broken build/test/config: syntax/import errors, missing dependencies,
  wrong env vars, invalid config, CI that would fail.
- Empty or stub files, `pass`/`TODO` bodies, commented-out code, dead imports.
- Runner scripts that don't match their docs; commands promised in docs that
  don't exist.
- For each blocker: file:line, what breaks, and user-visible impact.
  Severity: CRITICAL (won't work) > MAJOR (breaks part) > MINOR > SUGGESTION.

## F3 — Pending work
- `TODO`/`FIXME`/`HACK`/`XXX` markers, unfinished implementations, placeholders.
- `roadmap.md` / `.roadmap-state`, open issues, half-done migrations.
- Group by area; don't report every marker, just the meaningful ones.

## F4 — File hygiene & structure optimization
Review the file tree for structure-level opportunities (recommend only — never
move/delete in this command):
- **Useless files**: orphaned/duplicated files, dead scripts, unused assets,
  leftover generated artifacts, backup/temp files (`*.bak`, `*.orig`, `~`),
  files no longer referenced by code/docs/imports.
- **Overlapping files**: near-duplicate modules, repeated helpers/logic spread
  across files, copy-pasted blocks that could be a shared helper.
- **Merge candidates**: 2+ files with overlapping responsibility that could be
  consolidated into one without hurting separation of concerns (respect
  deliberate division, don't suggest merges that increase coupling).
- **Compaction**: bloated single files that should split, generated/boilerplate
  that could collapse, dead code removable on the next pass.
- **Structural optimization**: misplaced files (e.g. scripts under root that
  belong in `src/`, tests mixed with code), wrong folder layering, inconsistent
  naming, redundant wrapper layers, circular imports between modules.
- Order by effort vs. payoff (fix high-value, low-effort first).

## F5 — Handoff summary (small and precise)
Produce a SHORT summary optimized for tokens — this is the deliverable another
agent will act on. Keep it tight:

```
## Qué hace
<2-3 líneas: propósito, stack, cómo se ejecuta>

## Archivos clave
<5-10 archivos: entrada, módulos núcleo, config>

## Bloqueantes
- [CRITICAL] file:line — qué rompe
- [MAJOR] file:line — qué afecta

## Pendientes
- <TODO significativos agrupados>

## Estructura / archivos optimizables
- <archivos inútiles>
- <fusionar: files A + B → C>
- <compactar/partir: file X>
- <reestructurar: lista>

## Siguiente paso sugerido
<una frase: qué agente/módulo debe corregir primero>
```

Write a copy to `reports/init-review-<iso>.md` (JSON optional) so re-runs can
compare deltas. Remain read-only with respect to the audited project.