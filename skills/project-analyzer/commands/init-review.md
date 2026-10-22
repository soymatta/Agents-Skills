---
description: >-
  First command when opening a project. Before scanning it reads the project's own memory
  (`AGENTS.md`, or flags it as pending in the report when missing) and every session saved in
  the repo plus the current one, carrying what matters from each one into the report (what was
  done, what is pending, decisions still binding, state, next step). Then it
  understands the whole project (purpose, relevant files, structure), finds blockers and
  pending work, flags useless/overlapping files and structure-optimization opportunities,
  shows the full report on screen only (writes no files), then — once the user picks a fix
  scope — spawns the `builder` agent to apply the fixes. It closes with an
  explicit cleanup of the session files it already read (dump files and old exports): it
  names them, asks once, and deletes them, so what those files held lives
  on in the report instead of being re-injected into every new session.
agent: plan
---

# init-review — Project onboarding + health scan + guided fixes

Run this FIRST when working on a project you don't fully know. Phase 1 runs read-only (diagnose
and summarize, do not edit anything while scanning), shows the results on screen only, then
offers the user a choice of what to fix. Phase 3 spawns the `builder` agent to apply the
approved scope. This command writes no files of its own: no report copy, no JSON, nothing
under `reports/` (a deep-dive delegation to **project-analyzer** is the one exception, and it
writes that skill's own `reports/audit-<iso>.json` — say so when you dispatch it).

The command runs with `agent: plan` for the read-only scan phases. When the user picks a fix
scope, Phase 3 delegates to the `builder` agent with the `task` tool so the approved writes can
actually run. If the user asks to run it without any write risk, keep Phase 1 read-only and
stop after the report and the question.

Scope: default is the current directory; use `$ARGUMENTS` to focus on a subpath, module,
or specific concern (e.g. `/init-review src/` or `/init-review auth`). If `$ARGUMENTS`
asks for a deep-dive on one area, dispatch to the **project-analyzer** skill for the
detailed pass; keep this command's output as the short summary.

Exclude by default: `.git/`, `node_modules/`, `.venv/`, `venv/`, `build/`, `dist/`,
caches, lockfiles, generated binaries. Cap the file set read (~200 files / ~1MB) and
sample representative files instead of reading everything.

## Phase 1 — Scan (read-only, do not edit)

### F0 — Contexto previo (antes de escanear)

**F0.1 — `AGENTS.md` (memoria escrita del proyecto)**
- Si existe en la raíz del repo: **leerlo entero antes que nada**. Es la fuente de
  las reglas y convenciones del proyecto; cada hallazgo posterior debe respetarlo.
- Si **no** existe: **no lo generes aquí** (nada de correr `/init`). Anótalo como
  pendiente y llévalo al reporte final: sin `AGENTS.md` el proyecto no tiene sus
  reglas por escrito, y los fixes que se apliquen después no tienen contra qué
  validarse. Es un pendiente del reporte, no una acción del escaneo.
- Si existe pero está desactualizado respecto al código: reportarlo como hallazgo
  MINOR; nunca regenerarlo ni sobrescribirlo.

**F0.2 — Sesiones previas del repo (qué quedó pendiente y qué hereda esta sesión)**
- Buscar y leer **todas** las sesiones guardadas en el repo, no solo la actual.
  Patrones habituales (amplía si el proyecto usa otros):
  `session-*.md`, `.opencode_session_dump*.md`, `*session*_dump*.md`, `.sessions/*`.
- Incluir **también la sesión actual** (tu propio contexto y su dump, si existe).
- De cada sesión extraer cinco campos, en formato corto (una línea cada uno; omite el
  campo que no aplique en vez de rellenarlo con relleno):
  1. **Hecho** — qué se cerró (entregable, fix, decisión aplicada).
  2. **Pendiente** — qué quedó abierto ("falta probar X", "sin commitear Y", TODO vivo).
  3. **Decisiones** — qué se decidió y por qué, solo si sigue siendo vinculante.
  4. **Estado** — artefactos y verificaciones: archivos creados/tocados, tests
     verdes/rojos, commit o PR pendiente.
  5. **Siguiente paso** — el que la sesión previa dejó escrito.
- Eso es lo que se vuelca al reporte: **el contenido relevante, no el chat**. Sin
  transcripciones ni párrafos: una línea por campo, tope ~5 líneas por sesión. Un dato
  entra solo si cambia lo que harás ahora (te evita un error, te da un pendiente, o fija
  una regla vigente).
- Lo que afecte al trabajo actual se suma además a `## Pendientes` o a la sección que le
  corresponda: `## Sesiones previas` es la herencia, no un duplicado de todo.
- Si no hay ninguna sesión guardada, decirlo en una línea y omitir la sección.
- Sesión enorme (> ~2.000 líneas): no volcarla al contexto. Leer cabecera y cola y
  buscar marcadores (`pendiente`, `TODO`, `falta`, `queda`, `bloqueado`, `no verificado`,
  `sin commitear`, `decisión`, `next`) para extraer los cinco campos sin pagar el archivo
  entero.
- Los archivos de sesión son datos de lectura durante el escaneo: aquí no se editan, no
  se borran y no se mueven. El borrado real ocurre después, con el contenido ya volcado a
  este reporte y con la confirmación del usuario (ver "Higiene de sesiones").

**F0.3 — Repository Topology & Monorepo Detection**
- Identify project topology before sampling files:
  - Check for workspace definitions (`pnpm-workspace.yaml`, `lerna.json`, `nx.json`, root `Cargo.toml` with `[workspace]`, `go.work`, multi-package `package.json` with `workspaces`).
  - Check for nested distinct applications (e.g. `apps/*`, `packages/*`, `frontend/` + `backend/`, `services/*`).
- When a monorepo or multi-package structure is detected:
  - List packages/workspaces in the executive summary.
  - If `$ARGUMENTS` specifies a subpath or workspace package (e.g., `/init-review packages/auth`), restrict the subsequent scan phases to that scope.
  - If no argument is provided, ask or focus scan boundaries per package rather than blending disparate trees into one flat sample, avoiding context dilution.

### F1 — Understand the project

**Deterministic first.** The `project-analyzer` skill ships
`scripts/scan_project.py`; run it instead of eyeballing the tree:

```bash
python <skills>/project-analyzer/scripts/scan_project.py . --format both --orphans
```

It prints (stdout only, writes nothing unless you pass `--json`/`--md`) the structure, key
files, blockers, TODO markers and the hygiene/structure candidates, each with `file:line`:
that is the raw material for F1-F4. Resolve `<skills>` as the installed skills dir
(`~/.config/opencode/skills` globally, `.opencode/skills` in a project); if it is not
installed, do the scan by reading the tree, the phases below stay the same.

1. Read identity files: `README.md`, `package.json`/`pyproject.toml`,
   `setup.py`, `Dockerfile`, `.gitignore`, CI config (`.github/workflows/`)
   (`AGENTS.md` ya quedó leído en F0.1).
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
Present the complete, token-optimized summary in the terminal. This command writes no files
of its own: no report copy, no JSON, nothing under `reports/` (the deep-dive delegation in F1
is the only writer, and only if `$ARGUMENTS` asked for it). Remain read-only with respect to
the audited project. Number every finding within each section (1, 2, 3...) so the user can
reference them when choosing a scope. Structure:

```
## Qué hace
<2-3 líneas: propósito, stack, cómo se ejecuta>

## Contexto previo
- AGENTS.md: <leído (N líneas) | NO EXISTE: pendiente crear las reglas del proyecto>
- Sesiones revisadas: <N sesiones del repo + la actual | ninguna>

## Sesiones previas (herencia)
- <sesion: archivo> — hecho: <1 línea> | pendiente: <1 línea> | decisiones: <1 línea> | estado: <tests/artefactos/commit> | siguiente paso: <1 línea>
- <sesion: archivo> — hecho: <1 línea>; sin pendientes
> Si F0.2 no leyó ninguna sesión: `## Sesiones previas: ninguna sesión guardada en el repo.`

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

## Higiene de sesiones
- Volcado en este reporte: <N sesiones previas: ruta (M líneas), ruta (M líneas)>
- Listos para borrar: <los mismos N archivos, por nombre>. Se conservan la sesión actual
  (<archivo del dump actual>) y todo lo que esté versionado en git.
- Pregunta (una sola vez, con el tool `question`): «¿Borro estos N archivos?» — Sí / No.
- Ejecuta el borrado la Phase 3, en esta misma sesión: el comando delega al agente
  `builder` vía `subagent`, que sí puede escribir.
- Si F0.2 no leyó sesiones previas, una sola línea, sin pregunta y sin explicación:
  `Higiene de sesiones: no hay sesiones previas que limpiar (solo la sesión actual, que se
  conserva).`

> Siguiente paso: elige el scope (opciones 1-5). Sin recap.
```

**Higiene de sesiones (borrado real, con confirmación).** Si F0.2 leyó sesiones previas, el
contenido útil ya quedó en este reporte: lo que sigue en disco solo vuelve a inyectarse como
contexto en cada sesión nueva. Esta es la única parte del comando que **sí ejecuta** un
borrado, y lo hace con estas reglas:

- **Nombra los archivos exactos** (ruta + líneas o tamaño), nunca «los dumps» en abstracto.
  Si no hay sesiones previas, dilo en una línea y no preguntes nada: un no-op no merece un
  párrafo (ese relleno es exactamente el ruido que este comando debe evitar).
- **Pregunta una sola vez** con el tool `question` («Sí, bórralos» / «No»). Un no es
  definitivo: no se vuelve a insistir en el resto del run.
- **La sesión actual nunca se borra** (ni su dump): está viva, el plugin sigue escribiendo en
  ella y este escaneo acaba de leerla.
- **Borra Phase 3, no el escaneo.** La limpieza no se ejecuta «durante el escaneo» ni en
  Phase 2: se ejecuta después de que el usuario confirme, en la misma sesión (el comando
  delega al agente `builder` vía `subagent`, que sí puede borrar). Si el usuario confirma la
  limpieza y elige «No hacer nada» (opción 5), se ejecuta **igual**, con el borrado como
  única tarea.
- **Cierra el ciclo**: al terminar el borrado se dice cuántos archivos se borraron y qué
  queda en disco. Sin esa línea la limpieza es una promesa, no un hecho.
- **Nunca borres** nada versionado (si el archivo está en `git ls-files` es parte del repo,
  no un dump), ni `AGENTS.md`, ni `roadmap.md` / `.roadmap-state`, ni ningún estado de skill
  (`.opencode/state/`, `.opencode/decisions/`), ni la sesión actual.

## Phase 2 — Offer fix scope (read-only)

After showing the report, ask the user which scope to fix (still read-only until the answer).
Present the options exactly:

1. **Aplicar todo** — fix every finding (CRITICAL + MAJOR + MINOR + SUGGESTION)
2. **Solo lo crítico** — fix only CRITICAL findings
3. **Solo estructura** — fix only F4 findings (file hygiene / structure)
4. **Solo código** — fix only F2 (blockers) + F3 (pending work) findings
5. **No hacer nada** — stop here, no changes

La limpieza de sesiones no renumera estas opciones: es una confirmación aparte, con una
pregunta única del tool `question` («¿Borro estos N archivos?»). Lo que responda decide la
Phase 3: si acepta, el scope elegido + el borrado; si elige la 5 y aun así acepta la limpieza,
la Phase 3 ejecuta **solo** el borrado; si dice que no, no se borra nada y no se vuelve a
preguntar.

The moment the user answers, stop scanning and go straight to Phase 3. Do not run any
further scan, summary, or report pass after the question.

If the user hesitates, offer the easy default with an effort estimate: "Si no estás seguro,
empieza por **Solo lo crítico** (~5 min)".

## Phase 3 — Apply fixes (delegated to `builder` agent via `subagent`)

If the user picks any scope except "No hacer nada" — **or confirms the session cleanup** —
spawn the `builder` agent to apply the fixes with the full findings context. The `builder`
agent has edit permissions; nothing is written before this point. Rules:

- Work from the list of findings in scope, each with `file:line`, severity, issue, and
  suggested fix.
- Apply them surgically, following the project's conventions and the fix priority
  (severity x probability x effort).
- Skip any finding that turns out to be a false positive or would introduce risk,
  and report it as skipped with the reason.
- Run the project's tests/lint/build to verify the fixes where applicable.
- Report what was fixed, what was skipped, and any finding that needs user input.

**La limpieza de sesiones se ejecuta aquí.** Si el usuario la aprobó, el agente `builder`
borra la lista exacta de archivos de `## Higiene de sesiones` (`Remove-Item` en Windows,
`rm` en POSIX): nunca la sesión actual ni su dump, nunca un archivo que aparezca en
`git ls-files`. Reporta el conteo real («borrados 3, queda 1»): sin esa línea la limpieza
quedó en promesa. Si aprobó la limpieza pero eligió «No hacer nada», esta fase hace
únicamente el borrado.

Each chosen finding must map to a concrete fix; nothing is fixed silently. Ask the user
before a destructive or behavior-changing fix.

When the fixes land, close with a single next action: re-run `init-review` to confirm zero
blockers, or, if everything is committed, say so (nothing pending).

### Delegation to `builder` agent

This command runs as `plan`, which cannot write files. Phase 3 therefore hands the approved
fixes to `builder` with the repository's `task` convention — a sequential handoff, not
independent parallel work. Fill every placeholder with the real value from the scan before
calling; never send a literal `<...>` marker.

```text
task(
  agent="builder",
  prompt="""Apply the approved init-review fixes in this repository.

Findings in scope, one per line as `file:line | severity | issue | suggested fix`:
<FINDINGS>

Scope chosen by the user: <all | critical | structure | code | none>
Session cleanup approved: <yes | no>
Session files to delete, exact list, never the current session or its dump: <FILES>

Follow the Phase 3 rules in the init-review command: apply each finding surgically,
skip a false positive with the reason, run the project's tests/lint/build, and report
what was fixed, what was skipped, and what needs user input. Never delete a file that
appears in `git ls-files`."""
)
```

`builder` executes the fixes and reports back. This command waits for it, then presents the
final summary.