---
description: >-
  Orchestrates the end-to-end frontend UI/UX workflow across the project or target surface:
  determines the phase (from-scratch seed vs craft on existing UI), coordinates the skill
  constellation (ui-ux-pro-max, impeccable, web-design-guidelines, web-esenciales, qa-tester),
  and enforces deterministic verification via scripts/ui_gate.py.
---

# /init-ui-ux — Frontend UI/UX Initialization & Orchestration

Run this command to initiate and execute frontend design, refinement, and verification workflows following [`SKILL.md`](../SKILL.md).

## When to Use

- When launching a new frontend or web surface and needing a design system from scratch.
- When refining or auditing existing application interfaces, components, or pages.
- When preparing an interface for launch and requiring visual consistency, guidelines compliance, business checks, and runtime accessibility.

## Arguments & Scope

```bash
/init-ui-ux [path or surface target] [options]
```

- Target: default is current repository root or frontend directory (`src/`, `app/`, `frontend/`).
- Scope parameter `$ARGUMENTS`: specify a target file, component, route, or module (e.g., `/init-ui-ux src/components/Dashboard` or `/init-ui-ux --seed`).

## Execution Workflow

Follow the progressive disclosure pipeline strictly in sequence. Do not skip tiers silently; explicitly record any inapplicable tier in the final report.

### Phase 1 — Phase Classification & Ingestion
1. **Detect Surface State:**
   - **New surface / from scratch:** invoke `ui-ux-pro-max` to generate design tokens, visual hierarchy, style, palette, and typography pairing.
   - **Existing surface:** inspect incumbent styles, CSS/Tailwind tokens, and load or generate `PRODUCT.md` via `impeccable-init` without overriding established branding tokens.
2. **Context Boundaries:** Define target responsive breakpoints, theme mode (dark/light), and accessible contrast targets (WCAG AA minimum).

### Phase 2 — Craft & Implementation
1. **Playbook Execution:** Apply matching `impeccable` playbook according to requirements:
   - Structure & spacing: `impeccable-layout`
   - Typography & rhythm: `impeccable-typeset`
   - Component state & ergonomics: `impeccable-shape`
   - Micro-interactions & feedback: `impeccable-polish`
   - Production readiness: `impeccable-harden`
2. **Implementation Rule:** Produce rendered and functional code edits on disk. Pure text findings without code updates do not satisfy this phase.

### Phase 3 — Quality Gate & Linting
1. **Deterministic Fast Gate:** Run the offline linter script on modified files:
   ```bash
   python <skills>/ui-ux-orchestrator/scripts/ui_gate.py <target_path>
   ```
2. **Design Guidelines Review:** Cross-examine diffs against `web-design-guidelines` (interaction ergonomics, tap targets, layout shifts, empty states).

### Phase 4 — Business & Runtime Verification
1. **Business Essentials:** Check the 20 web fundamentals from `web-esenciales` (metadata, OpenGraph, favicons, robots, basic analytics hooks, error boundaries).
2. **Runtime Verification:** If live dev server or test runner is available, dispatch `qa-tester` for automated Axe accessibility checks, responsive rendering, and console hygiene.

## Output Specification

Present the deliverable in the following structured format:

```markdown
### UI/UX Orchestration Summary
- **Target Surface:** `<path/component>`
- **Phase Mode:** `Seed (from scratch)` | `Craft (existing)`
- **Routed Skills Engaged:** `ui-ux-pro-max`, `impeccable (<playbook>)`, `web-design-guidelines`, `web-esenciales`, `qa-tester`
- **Skipped Tiers:** (state reasons if any tier was omitted)

### Implemented Changes
- `<file_path:line>`: description of design token/layout/component changes applied.

### Gate Results (scripts/ui_gate.py)
- `<PASS | FAIL>`: findings breakdown with line numbers.

### Next Action
- Single immediate next step (e.g. previewing build, running browser test, or committing).
```
