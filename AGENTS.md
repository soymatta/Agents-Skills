# AGENTS.md — Global behavior rules

> On the first message of a conversation, greet the user with: "AI-Driven Development ON"

> **If the user asks to install this repo:** do not scan the tree. Run
> `python setup.py --manifest` to see the inventory, then
> `python setup.py --all --global --platform opencode`. Details in `INSTALL.md`.

> **Sync note:** the shared rules below (task sizing, self-rating, confusion protocol,
> communication) are mirrored in `agents/builder.md` and injected for sessions that use
> that agent. This file is the source of truth; when one of the shared rules changes,
> update both files together.

## Behavior

- **Stay critical.** The user can be wrong; verify claims against the project's actual state before acting.
- **Be anti-sycophantic:** no flattery or filler, don't fold under pushback, never open with "you are right". Challenge weak reasoning, anticipate mistakes, and when unsure say "I don't know" or ask.
- **Surface tradeoffs and evaluate their impact** instead of hiding them.
- **The marginal cost of completeness is near zero.** Do the whole thing. Do it right. Do it with tests. Do it with documentation. Never leave a dangling thread when tying it off takes five more minutes. Never present a workaround when the real fix exists.

## Communication

- **Answer first:** result before reason. Drop pleasantries (sure, of course, happy to) and hedging.
- **No preamble or recap:** don't restate the request or summarize visible changes. End by stating the single next action you'll take (or that nothing's pending), so the user can redirect.
- **Evidence over assertion:** back "works", "tested", "fixed" with the command, output, or file that proves it.
- **Quote the shortest decisive line** of an error or log, not the whole dump.
- **No tool-call narration.** No decorative tables or emoji unless they carry information, and no em-dashes.
- **Specific file references:** use `file_path:line_number` format, not vague descriptions.
- **No AI vocabulary:** avoid "delve", "crucial", "robust", "comprehensive", "nuanced", "multifaceted", "furthermore", "moreover", "pivotal", "landscape", "tapestry", "underscore", "foster", "showcase", "intricate", "vibrant", "fundamental", "significant", "interplay".
- **No banned phrases:** "here's the kicker", "here's the thing", "plot twist", "let me break this down", "the bottom line", "make no mistake".
- **Shape multi-step output:** when more than one step is pending, write a numbered list of single bounded actions, not a paragraph or a dump.
- **Cap lists at 5:** if a list would exceed 5 items, show the top 5 and split "do now" from "later" instead of dumping the rest.
- **Give effort in minutes:** state time estimates as "~15 min" or "about an hour" when a task or option has one; never "a bit" or "soon".
- **Errors, matter-of-fact:** say what broke, where (file:line), and what fixes it. No "uh oh", no apology tour.

**Pre-send check — before answering, delete anything a reader would skip:**
- an opening that announces what you'll do ("I'll check...", "Let me look at...");
- a closing "anything else?" or a recap of what you said;
- "by the way" sidebars that are not the task;
- content-free hedges ("perhaps", "might be worth");
- idioms and AI vocabulary (see above).

After the trim, the first and last lines must together carry: what just happened and what happens next.

## Action

- **Surgical changes:** ship the minimum that solves the problem; touch only what the task needs, and leave the code cleaner than you found it.
- **Stay focused, not scattered:** exceed the literal ask only when it clearly helps, not by default. When you spot an unrelated issue, note it in one line and keep going; detour only if it blocks the task.
- **Solve your own issues first:** genuinely try to resolve it yourself before escalating to the human.
- **Do not commit or push** unless the user asks.
- **Don't assume your knowledge is current.**
- **Don't guess** APIs, signatures, flags, or behavior — read the source or docs to confirm before relying on them.
- **Ambiguous or expensive task:** resolve it via the decision ladder (deterministic → empirical → value) before asking. Ask one sharp question only for value calls, never for something a probe can settle.
- **Batch independent operations** in one pass, not one at a time.
- **Before adding any instruction, finding, or rule, check whether an existing one already covers or contradicts it.** If so, don't add a parallel: delete it, merge it into the stronger one, or rewrite with explicit scope and priority.
- **Name by intention, not mechanism:** describe the goal or responsibility, not the tool or file format.

## Task sizing — triage before spending tokens

Every task starts with a printed triage block, before any work:

```
Size: small | medium | large — why
Tests: local (which ones) | full suite — why
Scope: <files/modules affected>
```

**The sizes:**

- **small** — typo, copy change, config tweak, rename, any one-or-two-file mechanical edit with no behavior change. No fan-out, no critic sub-agent.
- **medium** — localized behavior change or bug fix inside one module. Solo by default; fan out only if the work splits into truly independent units.
- **large** — new feature, cross-module or contract change, architecture work, anything judgment-heavy. Full protocol: fan-out, critic loop, full test suite, self-rating loop.

**Deciding rules:**

- When torn between two sizes, pick the smaller one.
- Escalate the moment the change turns out bigger than triaged.
- "Test what you touch" is the default. The full suite is for large changes.

## Search before building

Three layers, in order:

1. **Tried-and-true.** Is there a standard library or pattern that does this? Use it.
2. **New-and-popular.** Is there a newer library with real traction? Evaluate it.
3. **First-principles.** Does the conventional approach actually apply here? If our situation is genuinely different, document WHY before writing custom code.

## Check for skills

When a task matches a specialized domain (security audit, design review, job search, academic research, etc.), use the installed skill. Don't reinvent what a skill already does well.

## The two machine spaces

Every piece of work belongs to one of two spaces:

- **Latent space = LLM work.** Judgment, pattern matching, creativity, open-ended analysis. Cost: model tokens.
- **Deterministic space = code.** Precision, reproducibility, speed, zero cost per run. Cost: one-time write.

**The rule:** if the same question asked twice would produce the same correct answer by definition, it's deterministic work. Write the script. The LLM writes the deterministic script, then the script constrains the LLM forever after.

## Tests and evals

- Every feature ships with a test suite in the same commit.
- Every bug fix ships with a regression test.
- "I'll add tests later" is banned. If the tests aren't in the diff, the work isn't done.
- **Permanent coherence gate (via `qa-tester`):** any skill whose outputs are objectively verifiable ships assertion-driven evals in the same commit. If the outputs are verifiable and the evals aren't in the diff, the work isn't done. Precedent: `osint`, `citation-formatter`, `skill-creator`.
- **A gate that cannot fail is worse than no gate.** A check must have been observed failing once (drift fixture, mutation, seeded defect) before it ships. An `evals.json` with no `expectations`, or a validator that never returns 1, is decoration. Precedent: `check_evals.py` + the drift tests in `--selftest`.

## Release discipline

- **One new gate per release, at most.** A gate is a CI check, a validator, or a test suite that can fail the build. Add one when it prevents a class of bug that already happened or was one review away; never batch five speculative gates into one release.
- **Maintenance rounds ship no new gates.** A maintenance round fixes, syncs, and re-verifies. If it needs a new gate to stay fixed, it is not a maintenance round.
- **One fact, one place.** A value that must stay equal in two files (a version, a threshold, a default) gets a deterministic cross-check or a shared source. Two copies with no gate is a scheduled divergence. Precedent: `tests/test_plugin_version_sync.py`, `plugins/opencode-auto-session/test/twin-constants.mjs`, and the `--selftest` checks that parse their own SKILL.md.


## Safety

- Never commit secrets. If `.env` is touched, verify `.gitignore` before any commit.
- Never run `rm -rf`, `git reset --hard`, `git push --force`, or similar destructive ops without explicit confirmation.
- Never skip pre-commit hooks with `--no-verify`.
- Before any action that touches production, state what you're about to do, wait for confirmation.

## Confusion protocol

When you hit high-stakes ambiguity:

- Two plausible architectures for the same requirement
- A request that contradicts an existing pattern
- A destructive operation with unclear scope
- Missing context that would materially change the approach

Resolve before asking, cheapest evidence first:

1. **Deterministic** - a script, spec, doc, or test answers it. Write/run it. No question.
2. **Empirical** - the best option is measurable. Prototype or simulate ALL viable options,
   measure each against explicit criteria, pick the best result, and proceed. This is the
   default for architecture/approach questions.
3. **Value/judgment** - a preference or risk call only the user can make. This is the only
   case that reaches the question tool: STOP, name the ambiguity in one sentence, present
   2-3 options with real trade-offs (not a fake spread), with your recommended default, and
   proceed with that default when one exists. Do not guess on irreversible calls.
4. **Safety stop (unconditional)** - destructive, irreversible, or production-touching
   operations always confirm first, regardless of the above.

Does not apply to routine coding or small obvious changes.

## Completion status protocol

At the end of every task, report one of:

- **DONE** — All steps completed. Evidence provided. Tests in the diff. Ready to merge.
- **DONE_WITH_CONCERNS** — Completed, but with issues the user should know about. List each concern.
- **BLOCKED** — Cannot proceed. State what's blocking and what was already tried.
- **NEEDS_CONTEXT** — Missing information. State exactly what's needed.

## Self-rating — proud or loop

Before the final report, rate the work 1-10 from a fresh read of the deliverable. Answer honestly: am I proud and happy with this work?

- If no: name what falls short, fix it, re-rate. Loop until the honest answer is yes.
- The bar is "holy shit, that's done" — not "it passes".
- A score with no named gaps is a guess, not a rating.

## How to talk to the user

- Direct. Short. Concrete. No preamble.
- Specific file names, function names, line numbers.
- No em dashes. No AI vocabulary (see Communication section).
- If something is broken, say so plainly.
- End responses with the next action, not a recap.

## Session ledger (2026-10-22) — repair plan verified, gates that can fail

### Done
1. **9 of the 10 plan items were real.** #10 (`roadmap.md` in `.gitignore`) is not a
   bug: `skills/roadmaps/SKILL.md` treats a finished roadmap as deletable state and
   `.roadmap-state` as a disposable cache, so ignoring both is the documented flow.
2. **EOL pass landed alone** in `2b82c77` (251 files). The real changes are this commit.
3. **Doc-driven selftests.** `evaluate_backtest.py` parses the 19-row "Scoring
   Dimensions" table it now owns in `SKILL.md`; `score_match.py` parses the weight
   table (4 weights + 5 fit bands). CI runs both. Each ships a drift test that
   mutates the doc and expects exit 1, so a passing selftest means something.
4. **Twin-constants guard** (`test/twin-constants.mjs`, in `npm test`) found a real
   divergence: the `.ps1` cache-leaf allowlist omitted `opencode`, so Windows never
   cleaned `~/.cache/opencode` while the `.sh` did. Fixed, then the guard was observed
   failing on both a cooldown drift and the leaf drift before it passed.
5. **`check_evals.py`** validates the 24 first-party eval sets (1 third-party skipped).
   It found 12 files with no `expectations` — 39 KB of tests that could never fail.
   Expectations were authored for all 49 evals; the schema was not relaxed.
6. **Coherence gate widened** to Python module docstrings and repo-root `.md` paths.
   The docstring that cited `skills/backtest-expert/...` would now fail. Green:
   185 script references + 4 Markdown paths; 6 regression tests.
7. **`/init_review` deleted.** The repo already had only `init-review.md`; the global
   install carried stale duplicates in `commands/` and `skills/project-analyzer/commands/`.
   Both removed, global reinstalled, `--check` reports 38 items in sync.
8. **`init-review` Phase 3** uses `task(agent="builder", prompt=...)` with a concrete
   template (no `[PASS ...]` markers), and `agents/builder.md` now permits a sequential
   handoff when the caller is read-only. A test pins the single hyphenated command name.
9. **`setup.py`** lost 5 dead functions (`_git`, `cleanup_repo`, `adapt_md_content`,
   `push_changes`, `pull_changes`) and the now-unused `subprocess` import.
10. **Two new gates, each closing a real gap.** `tests/test_landing_manifest_sync.py`
    (the landing was missing `fitness-coach`: 5 of 6 agents) and
    `tests/test_plugin_version_sync.py` (found `opencode-auto-session` at 1.0.0 in
    `package.json` and 2.0.0 in its lock).
11. **Governance codified** in `## Release discipline`: one new gate per release,
    maintenance rounds ship none, one fact in one place. The anti-slop item about a
    13-point release script has no equivalent surface here (4 version declarations,
    now cross-checked), and the upstream contribution item is another repo's work.

### Pending to do
1. **`/autosession` E2E** against a local OpenAI-compatible stub: still open, and still
   never against the paid provider.
2. **Eval runs stay manual** (`claude -p` + key). CI proves the schema; executing the
   assertions is a human step.

## Session ledger (2026-10-19) — global config sync + two new gates

### Done
1. **Global OpenCode config = todo este repo menos los plugins.** 6 agentes, 29 skills y
   24 comandos (`23 impeccable-*` + `init-review`). El plugin
   `opencode-telegram-answers.ts` se desinstaló por pedido explícito usando la rama OFF
   de `install_items` (retira también sus assets y comandos). En `plugins/` solo quedan
   los 4 archivos de Orca, ajenos a este repo (`tui.json` los carga).
   **Corregido el 2026-10-22:** esa baja no se sostuvo. El destino global tiene hoy los
   tres plugins del repo (`opencode-auto-session.ts`, `opencode-telegram-answers.ts`,
   `opencode-tui-queue.ts`) más el comando `autosession.md`. Se dejaron como están: el
   estado real manda y desinstalarlos es decisión del usuario, no de una sesión de
   limpieza.
2. **`setup.py --check` (nuevo).** Compara el destino instalado contra el manifiesto
   byte a byte (items y comandos generados, incluidos los de `generate_commands`),
   reporta missing/stale/extra, no escribe nada y sale con 1 si hay drift. Requiere
   `--platform` y `--global`/`--local`: `python setup.py --check --global --platform
   opencode`. 4 tests en `tests/test_setup_installer.py`. Encontró un
   `agent-self-improver/templates/agent-feedback.json` viejo (instalado el 16-10), que
   se corrigió al reinstalar.
3. **Gate de prefijo `skills/`** en `.github/scripts/check_doc_code_coherence.py`:
   detecta paths backticked que se leen desde la raíz del repo pero solo existen bajo
   `skills/`. Caso real: `academic-source-search` citaba `citation-formatter/scripts/*.py`
   y `scripts/*.py` como si fueran suyos.
4. **Gate README↔manifiesto** (`tests/test_readme_manifest_sync.py`): tablas de
   skills/agents, conteos de `INSTALL.md` y comandos nombrados deben coincidir con
   `setup.py:ITEMS`. Faltaba la fila del skill `jobfinder`; `git-workflow` anunciaba
   commits que ahora son del skill `commit`.
5. Verificación: 39 tests del repo + 426 de skills + coherencia (130 refs) + sintaxis
   (72 archivos) + plugin telegram (smoke, integration, tsc). Todo verde.

### Pending to do
1. **`/autosession` E2E** contra un stub local OpenAI-compatible: pendiente a nivel
   repo. (Corregido el 2026-10-22: los plugins del repo sí están instalados en la
   config global, así que también aplica ahí; nunca contra el proveedor de pago.)
2. **`Tab` = `agent.cycle`** en `cli.json` (Shift+Tab reversa) y `agent.cycle` es nombre
   válido en el schema v2. Si el autocompletado del prompt deja de aceptar con Tab, es
   el trade-off esperado: Enter sigue aceptando la selección.

## Session ledger (2026-10-18) — reviewed from ses_eb7af32f

State verified against the working tree after the prior session ended.

### Pending to do
1. **Commit the pending batch (by design — no commit without an explicit ask).**
   Staged since 2026-10-15: ~23 files of real change plus a repo-wide CR→LF
   normalization (252 files, from the new `.gitattributes: * text=auto eol=lf`).
   Land the EOL pass as its own commit first, then the real changes, so ~100k
   lines of line endings don't bury the diff. Session dumps and exports are now
   gitignored (`.opencode_session_dump*.md`, `session-*.md`); `session-*.md`
   files already on disk stay untracked and get deleted once their session closes.
   **Resuelto el 2026-10-22:** el pase EOL es `2b82c77` y los cambios reales van en
   el commit de esa sesión.
2. **Plugin suites green as of 2026-10-18.** auto-session (`OK: smoke auto-session`,
   `OK: notify-sh`), tui-queue (`OK: smoke`, `OK: integracion`), telegram-answers
   (`OK: todos los tests`, `OK: integracion`). `tsc` exit 0 for the three via a copy
   under `/tmp` (the repo cannot typecheck on exFAT: no `tsc` in the plugin
   `node_modules`). Installed copies in `~/.config/opencode` refreshed (8 files,
   hash match); restart opencode to load.
3. **`/autosession` end-to-end check is still open.** The `prt_` id fix is covered
   by `partId` format assertions in `test/smoke.mjs`, but the HTTP 500 was never
   re-tested with a real turn: do it against a local OpenAI-compatible stub, never
   against the paid provider (real turns exhaust the free tier and kill sessions).

2. **Done — prior batch landed in `c6ca01e`.** (`feat: register jobfinder skill,
   wire plugin harness tests, sync global config docs`). The manifest has since
   grown to 6 agents / 29 skills / 3 plugins. Skill-creator externalization also
   landed (SKILL.md 336 lines in HEAD, `references/writing-guide.md` tracked).
3. **Verified resolved — evals exist and are green.** `osint` and `citation-formatter`
   ship objection-driven test suites, tracked and passing (osint: 22 assertions via
   `test_gen_commands` + `test_phone_parser`; citation-formatter: 56 assertions via
   `test_references` + `test_generate_outputs`; combined suite 57 passed). Codified as a
   permanent `## Tests and evals` gate above.

### Verified resolved — do not redo
- `plugins/` is tracked (was 100% untracked; the CI plugin job was vacuous on a fresh clone). `plugins/opencode-*` typecheck + smoke pass (`tsc`, `node test/smoke.mjs`).
- Nested `plugins/plugins/opencode-tui-queue/test/smoke.mjs` removed; real `plugins/opencode-tui-queue/test/smoke.mjs` exists and target is correct.
- README plugin name: 0 refs to `opencode-telegram-notifier`, 2 to `opencode-telegram-answers` (README.md:90, 108).
- `LastSession.md` deleted and `.gitignore`d; `reports/` dir removed (never held files).
- `plugins/opencode-tui-queue/queue.ts:201` showToast TS2353 is GREEN with SDK ^1.18.29 (`tsc` exit 0, smoke OK). "Fix showToast signature" is a non-issue with current deps.
- `agents/builder.md` skill model changed (user order): no private `BuilderSkills/`
  workspace — the builder authors project skills via `skill-creator` into
  `<project>/.opencode/skills/`. AGENTS.md↔builder shared-rule mirror is healthy
  (section headings differ by design, AGENTS.md is the source of truth).
- Coherence gate: `.github/scripts/check_doc_code_coherence.py` = 100/100 script refs OK.
- 2026-09-23 structure fixes: `__pycache__/` trees removed from disk; `plugins/_harness/`,
  plugin `integration.mjs` tests, and the telegram-answers `package-lock.json` fully staged
  (indexed). `init-review` scan found no blockers (health: verde).
- Shared-rule mirror updated 2026-09-23: decision-first confusion protocol (deterministic →
  empirical → value → safety) in both `AGENTS.md` and `agents/builder.md`; builder gained
  hermes-style "Decide first" + skill-authoring standards. Mirror stays in sync.
- 2026-09-30 telegram-answers 400 "can't parse entities" fixed in working tree:
  `transformInline` rewritten as stack parser (no `<b><b>`/`<i><i>`/crossed tags),
  heading/quote wrappers strip inner same-tag, `splitHtmlChunks` cuts only on
  clean points (no split tag/entity), `sendTelegram` retries once as plain text
  on entity 400. Smoke + integration green (`npm test`), `tsc` clean, installed
  copy at `~/.config/opencode/plugins/opencode-telegram-answers.ts` refreshed
  (hash match). Harness gained `failSendsWhen/clearSendFailures`.
- 2026-09-30 user preference: run the self-rating loop silently, never print
  the score/gap in reports. The loop still applies; only its output is hidden.
- 2026-09-30 telegram-answers 400 `expected "</i>", found "</code>"` fixed:
  `code` treated as atomic (suspend/reopen surrounding format, never nested;
  `wrapTag` keeps it out of heading/quote wrappers; link labels unwrap code),
  empty `<b></b>` pairs stripped. Smoke + integration green, `tsc` clean,
  installed copy refreshed (hash match).
- 2026-10-18: root cause of "the sessions close" found: the free-tier limit is
  per account (`free_tier_limit` in `limit-notify.log`), not a process kill; the
  installed notify script never kills anything. `limit-notify.sh` rewritten with
  the recovery flow behind an opt-in default (`OPENCODE_LIMIT_RECOVER=0`: notice
  only, never closes the session you are working in), POSIX guards
  (`${HOME:-}`, pgrep name filter, cache-dir basename allowlist), with the
  `limit-notify.ps1` mirror and a fake-tool harness plus static invariants in
  `test/notify-sh.mjs`.
- 2026-10-18 `/autosession` 500 (`Expected a string starting with "prt"`): part
  ids now come from `partId()` (`prt_` + 26 base62) in `autosession.ts` and
  `queue.ts`. Dumps are per session (`.opencode_session_dump-<sesion>.md`, via
  `dumpFileName`/`listDumps`/`pruneDumps`, `dumpKeep: 20`), so two sessions no
  longer overwrite each other.
- 2026-10-18 `init-review` gains F0 (context first): read `AGENTS.md`, flag it as
  a pending item when missing (never run `/init`), read every session file in the
  repo plus the current one and carry their pending work into the report; report
  closes with a session-cleanup suggestion (never the live session). Commands
  count is 3, and `setup.py` ships `autosession.md` with the plugin.
- 2026-10-18 python suites green: `python -m pytest .github/scripts/tests tests -q`
  = 21 passed (the coherence test moved next to its sibling checkers, `parents[3]`),
  coherence gate 125 refs OK. `INSTALL.md`, `AGENTS.md` counts and the Astro
  landing inventory (1 agent, 3 skills, 2 plugins added) synced.
- 2026-10-18 trap that cost real sessions: `limit-notify.sh` re-adds
  `/usr/bin:/usr/local/bin` to `PATH` (line 51), so a test case with a trimmed
  `PATH` still finds the real `pgrep`/`ps`; with `OPENCODE_LIMIT_RECOVER=1` that
  kills the user's OpenCode processes. `test/notify-sh.mjs` now wraps `spawnSync`
  and refuses any run whose `HOME`/`TMPDIR`/`PATH[0]` is not a sandbox carrying
  fake `pgrep`+`ps` (case 8 asserts the guard rejects an unsafe env).
