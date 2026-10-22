---
name: ui-ux-orchestrator
description: >-
  Orchestrates the frontend skill set from one request: classifies the phase,
  routes to the owning skill (ui-ux-pro-max to generate a design system from
  zero, impeccable to craft/refine/audit an existing interface,
  web-design-guidelines to review code against the Vercel Web Interface
  Guidelines, web-esenciales for the 20 business must-haves, qa-tester for
  runtime verification before launch), fixes the order and the precedence so
  the results never contradict each other, hands each tier the artifact and the
  brief the next one needs (the tiers communicate through files on disk, not
  prose), and merges the executable checks
  into one prioritized report via scripts/ui_gate.py. Routing is the means: on
  an existing surface it runs the routed design phase and owes changed,
  rendered UI, not only findings. A call runs the whole constellation by
  default (design-system reference, craft, guidelines review, business gate,
  runtime verification), with every skipped tier named and justified. Use
  whenever a frontend request needs more than one UI/UX skill, or when you must
  decide which UI/UX skill(s) to run and in what order: "haz mi web", "mejora el
  diseno", "revisa mi UI", "audita mi interfaz", "que le falta a mi web",
  "prepara mi sitio para publicar", "design system", "UI review", "orchestrate
  UI", "corre el orquestador UI/UX", "usa todas las skills de UI/UX", "que
  skills de UI aplico". Delegates, never reimplements: the routed skills keep
  their own rules and permissions. Not for backend-only work.
---

# UI/UX Orchestrator

One entry point for the frontend skill set. It does six things and nothing
else: classify the phase, route to the owner, run the routed design phase, fix
order and precedence, carry each handoff (artifact + brief) between tiers, and
run the deterministic gate. It never reimplements a routed skill and never edits
a third-party skill.

Routing is the means, not the deliverable. On an existing surface the run owes
a changed, rendered interface plus the verification that proves it; the gate
report is the proof, not the product.

## Constellation (the web surface, three tiers)

| Tier | Skill | Owns | Kind |
|---|---|---|---|
| Design | `ui-ux-pro-max` | generating a design system from zero (pattern, style, palette, typography) | third-party |
| Design | `impeccable` | craft / refine / redesign an existing interface; `audit` (a11y, perf, responsive); browser live iteration | third-party |
| Design | `web-design-guidelines` | reviewing code against the Vercel Web Interface Guidelines (`file:line` findings) | third-party |
| Gate | `web-esenciales` | the 20 business/SEO must-haves | first-party |
| Verify | `qa-tester` | runtime QA: a11y (axe), perf, multi-device, E2E | first-party |

Third-party skills are used read-only here. To change one, pull from upstream;
do not patch it in place (repo rule).

**Not in this set** (never route UI work through them): `web-cloner` replicates
and ports a site into code, it is an input source, not a UI skill; `refactor`
does code quality, security and architecture, and its web-launch checklist
reuses `web-esenciales` instead of duplicating it.

## Full pass (the default when this skill is called)

Calling the orchestrator means the **whole constellation**, one owner per tier,
not whichever slice the request seems to need. Each tier is engaged and each is
accounted for in the output:

| # | Tier | Skill | What a full pass takes from it |
|---|---|---|---|
| 1 | Seed | `ui-ux-pro-max` | design-system reference for the product category: pattern, palette, type pairing, anti-patterns. **New surface only.** On an existing surface it is skipped by default, because `impeccable` owns craft there and `ui-ux-pro-max` owns from-zero generation; it runs only when the user asked for a design-system reference or a redesign, and then its output is **advisory** (candidates to accept or reject, never a replacement of the incumbent tokens) |
| 2 | Design | `impeccable` | the design work itself: its owning playbook for the request, plus the craft floor while editing |
| 3 | Review | `web-design-guidelines` | prose review of the changed code, `file:line` findings |
| 4 | Gate | `web-esenciales` | the 20 business/SEO must-haves; asks before implementing each gap |
| 5 | Verify | `qa-tester` | runtime on the built output: a11y, performance, device classes, E2E |

`scripts/ui_gate.py` is the offline half of tiers 3 and 4 and always runs in the
same pass.

Narrow the run only when a tier is genuinely inapplicable, and never silently:
say which tier was skipped and why ("no browser available", "no forms on this
surface", "static docs page: the business items are out of scope"). A dropped
tier that goes unmentioned is the failure this section exists to prevent,
because the caller asked for the whole set and cannot see what was left out.

Inside `impeccable`, name the playbook you run. A broad request usually means
the applicable refine/enhance set (layout, typeset, polish, adapt) as one
batch; opposite registers never pair in the same pass (`bolder` with `quieter`,
`distill` with `delight`) because they cancel out.

## Pipeline (canonical order)

1. **Seed.** New surface or "from zero" → `ui-ux-pro-max` generates the design
   system. Existing project → `impeccable init` captures PRODUCT.md. Pick
   exactly one; this is the only branch. (If the starting point must be obtained
   by cloning a site, that is `web-cloner`'s job before this skill runs; it is
   not a UI phase here.)
2. **Design.** Existing world → `impeccable` (its `shape`/`new-work`/craft
   flow). One-off tool or dashboard → `impeccable`. Never run `ui-ux-pro-max`
   and `impeccable` on the same surface without a reason; they answer different
   questions (generate vs. craft).
3. **Build.** `impeccable` craft floor while writing UI code.
4. **Review code.** `web-design-guidelines` (prose rules, fetched live) **and**
   `scripts/ui_gate.py` (the machine-checkable subset, runs offline). Same
   checklist, two engines: the script is the fast gate, the skill covers what
   needs judgment.
5. **Gate business/SEO.** `web-esenciales`. Its 20-item audit is the only
   source of truth for must-haves.
6. **Verify / pre-deploy.** `qa-tester` (runtime, a11y, perf, devices) when the
   user is about to ship.
7. **Merge.** One prioritized report; see precedence below. Never return two
   conflicting lists from two skills.

Phases are skip-able only against a named reason: a narrow polish request stops
at 2-4; a new site runs the whole chain. The default is the full pass above.

## Handoff contract (how the tiers communicate)

The tiers never talk in prose. Each hop has three parts: the **artifact** the previous tier
leaves on disk, the **brief** the next tier receives, and the **rule** that stops the next
tier from redoing the previous one's work. A routed skill invoked without a brief re-decides
the whole problem and silently overwrites the tier above it.

| Hop | Artifact on disk | Brief handed over | Never redone downstream |
|---|---|---|---|
| `ui-ux-pro-max` → `impeccable` | the accepted pattern, palette and type pairing, written into the project's token layer (`tokens.css` / `theme.css` / `tailwind.config.*`, or `DESIGN.md` when no token layer exists) | "these are the tokens; apply them to <section>" | re-picking the design system |
| `impeccable init` → every later tier | `PRODUCT.md` (+ `DESIGN.md` when generated) | "the product context lives in these files; respect it" | re-interviewing the user about the product |
| `impeccable` → tiers 3-4 | the changed paths (`git diff --stat` + the file list) | "review only these paths, findings as `file:line`" | reviewing untouched files; restating design rationale |
| tiers 3-4 → merged report | `ui_gate.py --json` output merged with the prose findings | n/a (this is the merge) | reporting one issue twice |
| merged report → `web-esenciales` | the must-haves still missing, numbered | "audit the 20 items; every gap is a question to the user, not an auto-fix" | re-flagging an a11y blocker tiers 3-4 already reported |
| `web-esenciales` gaps → `impeccable` | the accepted gap list | "implement these N gaps, nothing else" | re-deciding the design from tier 2 |
| `qa-tester` → `impeccable` (loop) | each failure with the command and viewport that produced it | "make these pass; here is the failing command" | closing the pass while a blocker reproduces |

**Brief every tier, every time.** Four fields: owner (which skill), target (paths), the
constraint the previous tier imposed, and the artifact expected back. Tiers are skills, not
subagents: load one at a time, in pipeline order, in this same session, and never let two
loaded skills own the same file in the same step.

**Loop back, do not just report.** A blocker or a failed must-have from tiers 5-6 returns to
`impeccable` (tier 2) and the pass repeats from tier 3 over the changed paths. Two rounds
maximum; a third failure goes to the user with the failing command, it is not retried again.

**Missing or failing tier.** If a routed skill is not installed, or `web-design-guidelines`
cannot fetch the Vercel rules, name the dropped tier and fall back deterministically:
`ui_gate.py` plus the prose rules you can still apply for tier 3, the `web-esenciales` script
for tier 4. Never substitute a different skill's output for the missing one, and never drop a
tier silently.

**Stop condition.** The pass closes when `ui_gate.py` is green at the chosen `--fail-on`, no
`web-esenciales` item is missing (or each remaining one is explicitly accepted by the user),
the render check passed, and no blocker from `qa-tester` still reproduces. Anything else ends
as named, accepted debt with the user's answer.

### Merged report (one list, one schema)

Every finding from any engine becomes one row:
`severity | file:line | issue | owner | source`.

- **severity**: `blocker` / `major` / `minor`. One ladder for every engine, so no engine's
  internal scale can outrank another's.
- **owner**: the tier that fixes it (`impeccable`, `web-esenciales`, `qa-tester`, or `user`
  when the fix is a decision).
- **source**: the engine(s) that flagged it. When several agree, one row listing all of them,
  at the highest severity.
- Header of the report: a coverage table `tier | ran | artifact | status`, with the reason
  whenever a tier is skipped.

**No brief? Then the design phases are the job, not the gate.** "Run the
orchestrator", "improve this page", "review my UI" with nothing further is a
design request on an existing surface: load `impeccable`, run the playbook that
owns it, and land a visible change. Reporting findings instead is the failure
mode to avoid here, because an audit answers a question the user did not ask
and reads as refusing the task. Once the surface changed, run phases 4-6 over
what you changed and quote that output as proof (a real render, not the diff).
Audit-only is correct solely when the user asked for an audit or a checklist
("que le falta", "is it ready to publish").

## Verify in a real render (a UI change is unverified until it renders)

Never sign off by reading the diff. Build, serve over **HTTP**, screenshot at
320 / 375 / 1280, and open the images:

```bash
npm run build
(cd dist && python3 -m http.server 8099 &)        # POSIX
# PowerShell: Start-Job { cd dist; python -m http.server 8099 }

chromium --headless --no-sandbox --hide-scrollbars \
  --virtual-time-budget=6000 --window-size=375,1100 \
  --screenshot=/tmp/shot-mobile.png http://127.0.0.1:8099/index.html
```

- **Never `file://`.** Framework builds emit absolute asset paths
  (`/_astro/*.css`); under `file://` those 404 and the page renders unstyled,
  which reads as "the CSS is broken" when it is not.
- Read the PNG back. A screenshot you did not open is not evidence.
- **Check the small viewport first.** Hidden navigation, clipped labels and
  overflow surface at 320-375px and nowhere else. A control that scrolls
  sideways with no affordance is a hidden control: wrap it instead.
- Kill the server by port, and never by matching its command line:
  `fuser -k 8099/tcp` on POSIX;
  `Get-NetTCPConnection -LocalPort 8099 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }`
  on Windows. `pkill -f "http.server 8099"` matches the shell running it and kills
  your own session.

## Precedence (conflict resolution)

When two skills disagree, resolve in this order, top wins:

1. **Accessibility and functional blockers.** A missing `alt`, a broken form, a
   blocked paste, `user-scalable=no`: fix regardless of aesthetics.
2. **Business must-haves** (`web-esenciales`). A missing CTA or privacy page
   outranks a color tweak.
3. **Incumbent identity.** If the request is a refinement, `impeccable`'s rule
   holds: preserve behavior, copy, and everything outside scope. Only a
   requested redesign replaces the visual world; then `impeccable` wins over
   any "keep it" instinct.
4. **Craft / polish last.** Motion, delight, typography hierarchy.

Deduplicate: if `impeccable audit`, `qa-tester` a11y and the Vercel rules flag
the same issue, report it once, at its highest severity, and name the owner.

## Deterministic gate

`scripts/ui_gate.py <path>` scans HTML/JSX/CSS/Vue/Svelte/Astro for the
machine-checkable subset of the Web Interface Guidelines and, when pointed at a
directory, merges the `web-esenciales` 20-item audit into the same report.

```bash
python scripts/ui_gate.py src/            # merged report, grouped by file
python scripts/ui_gate.py src/ --json     # machine-readable
python scripts/ui_gate.py src/ --fail-on warn
```

Point it at the built output (`dist/`) as well as the source: the source hides
what the framework emits, and a path named `dist` is scanned, not skipped, when
it is the root.

Rules it enforces (high precision, no judgment calls): `img` without `alt`,
`img` without dimensions, `div`/`span` with a click handler and no role,
`<html>` without `lang`, viewport disabling zoom, `target="_blank"` without
`rel=noopener`, `outline:none`/`outline-none` without a `focus-visible`
replacement, `transition: all`, blocking paste, `autoFocus`. Judgment rules
(hierarchy, POV, tone, copy) stay in `web-design-guidelines` and `impeccable`:
the script does not invent taste. Exit code is non-zero on any finding at or
above `--fail-on` (default `blocker`).

## Rules

- **Route, do not reimplement.** If a routed skill already does it, call it.
- **Every hop carries an artifact and a brief.** See the handoff contract: the
  previous tier's file on disk, plus owner / target / constraint / expected
  artifact for the next one. A tier invoked without a brief re-decides the whole
  problem and overwrites the tier above it.
- **The full constellation is the default.** Report coverage tier by tier (ran,
  or declined with the reason). Skipping a tier quietly answers a smaller
  question than the one asked.
- **A report is not a deliverable.** When the request is about how the surface
  looks, the run ends with changed, rendered UI and the check that proves it
  rendered. Findings alone are correct only for a requested audit.
- **One owner per phase.** Never let two skills produce competing versions of
  the same deliverable in one pass.
- **A missing tier is named, never silent.** Say which skill dropped out (not
  installed, fetch failed) and which deterministic fallback replaces it; never
  hand a tier's job to a different skill without saying so.
- **Stay critical.** If a routed skill's output contradicts the brief, say so;
  do not smooth it over.
- **Third-party is read-only.** `ui-ux-pro-max`, `impeccable` and
  `web-design-guidelines` are vendored; improvements go upstream.
- **Swapping a typeface?** Run `node skills/impeccable/scripts/detect.mjs --json
  <files>` before choosing. Its `overused-font` rule blacklists ~17 faces
  (Inter, Geist, Plus Jakarta Sans, Space Grotesk, Instrument Sans, Instrument
  Serif, Roboto, ...) in
  `skills/impeccable/scripts/detector/engines/regex/detect-text.mjs`. Picking
  from that list costs a whole rework cycle.

## Scripts

- `scripts/ui_gate.py` - merged deterministic gate (guidelines subset +
  `web-esenciales` audit). Stdlib only; finds the `web-esenciales` script as a
  sibling and degrades gracefully if it is not installed.
- Tests: `tests/test_ui_gate.py` (`python -m pytest skills/ui-ux-orchestrator -v`).
