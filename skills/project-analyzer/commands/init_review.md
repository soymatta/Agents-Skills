---
description: >-
  First command when opening a project. Understands the whole project (purpose, relevant files, structure),
  finds blockers and pending work, flags useless/overlapping files and structure-optimization opportunities,
  shows the full report on screen only (writes no files), then — once the user picks a fix scope — hands off
  to opencode's default build agent to apply the fixes.
agent: plan
---

# init_review — Project onboarding + health scan + guided fixes

Run this FIRST when working on a project you don't fully know. The `plan` agent runs a
read-only scan (diagnose and summarize, do not edit), shows the results on screen only, then
offers the user a choice of what to fix. The default opencode `build` agent applies the
chosen scope. The scan never writes files: no report copy, no JSON, nothing under `reports/`.

Scope: default is the current directory; use `$ARGUMENTS` to focus on a subpath, module,
or specific concern (e.g. `/init_review src/` or `/init_review auth`). If `$ARGUMENTS`
asks for a deep-dive on one area, dispatch to the **project-analyzer** skill for the
detailed pass; keep this command's output as the short summary.

Exclude by default: `.git/`, `node_modules/`, `.venv/`, `venv/`, `build/`, `dist/`,
caches, lockfiles, generated binaries. Cap the file set read (~200 files / ~1MB) and
sample representative files instead of reading everything.

## Phase 1 — Scan (read-only, agent: plan)

### F1 — Understand the project
1. Read identity files: `README.md`, `AGENTS.md`, `package.json`/`pyproject.toml`,
   `setup.py`, `Dockerfile`, `.gitignore`, CI config (`.github/workflows/`).
2. Map the structure (glob + listing) and identify the **relevant/core files** —
   entry points, main modules, and configs — vs. everything else.
3. State, in 2-3 lines: what the project does, its stack, and how it runs/builds.

### F2 — Blockers (things that keep it from working)
- Broken build/test/config: syntax/import errors, missing dependencies,
  wrong env vars, invalid config, CI that would fail.
- Empty or stub files, `pass`/`TODO` bodies, commented-out code, dead imports.
- Runner scripts that don't match their docs; commands promised in docs that
  don't exist.
- For each blocker: file:line, what breaks, and user-visible impact.
  Severity: CRITICAL (won't work) > MAJOR (breaks part) > MINOR > SUGGESTION.

### F3 — Pending work
- `TODO`/`FIXME`/`HACK`/`XXX` markers, unfinished implementations, placeholders.
- `roadmap.md` / `.roadmap-state`, open issues, half-done migrations.
- Group by area; don't report every marker, just the meaningful ones.

### F4 — File hygiene & structure optimization
Review the file tree for structure-level opportunities (recommend only — never
move/delete during the scan; fixes happen in Phase 2):
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

### F5 — Show the report on screen
Present the complete, token-optimized summary in the terminal. The scan writes no files at
all: no report copy, no JSON, nothing under `reports/`. Remain read-only with respect to
the audited project. Number every finding within each section (1, 2, 3...) so the user can
reference them when choosing a scope. Structure:

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

## Estado del proyecto
[Saludable | Con problemas | Rotto] — 1 línea de resumen

> Siguiente paso: elige el scope (opciones 1-5). Sin recap.
```

## Phase 2 — Offer fix scope (agent: plan)

After showing the report, the `plan` agent asks the user which scope to fix. Present
the options exactly:

1. **Aplicar todo** — fix every finding (CRITICAL + MAJOR + MINOR + SUGGESTION)
2. **Solo lo crítico** — fix only CRITICAL findings
3. **Solo estructura** — fix only F4 findings (file hygiene / structure)
4. **Solo código** — fix only F2 (blockers) + F3 (pending work) findings
5. **No hacer nada** — stop here, no changes

The moment the user answers, `plan` stops and hands off immediately to opencode's default
`build` agent (built-in, full permissions). Do not run any further scan, summary, or
report pass after the question; the switch is immediate and unconditional.

If the user hesitates, offer the easy default with an effort estimate: "Si no estás seguro,
empieza por **Solo lo crítico** (~5 min)".

## Phase 3 — Apply fixes (agent: build)

If the user picks any scope except "No hacer nada", **hand off to opencode's default
`build` agent** — the built-in build agent, not a custom one — with the full findings
context so it applies the fixes. The build agent:

- Receives the list of findings in scope, each with `file:line`, severity, issue, and
  suggested fix.
- Applies them surgically, following the project's conventions and the fix priority
  (severity x probability x effort).
- Skips any finding that turns out to be a false positive or would introduce risk,
  and reports it as skipped with the reason.
- Runs the project's tests/lint/build to verify the fixes where applicable.
- Reports what was fixed, what was skipped, and any finding it needs user input on.

Each chosen finding must map to a concrete fix; nothing is fixed silently. The build
agent may ask the user for confirmation before a destructive or behavior-changing fix.

When the fixes land, close with a single next action: re-run `init_review` to confirm zero
blockers, or, if everything is committed, say so (nothing pending).
