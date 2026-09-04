---
name: project-memory
description: >-
  Builds and maintains the project's memory of its architecture, conventions, decisions, and
  codebase map, so every session starts with durable context instead of re-discovering the
  project. Set up, refresh, or rewire. Use when setting up a new project, or when the user
  wants the agent to remember structure/conventions/decisions. Triggers: "project memory",
  "memoria del proyecto", "set up memory", "context", "codebase map", "documentar el proyecto".
compatibility: Language-agnostic. Writes memory files under a docs dir (default `aidd_docs/memory/`).
---

# Project Memory

Give the AI a durable memory of the project architecture, conventions, and decisions, so a
fresh session starts grounded instead of re-reading everything.

## Actions

| Action | Does                                            |
| ------ | ----------------------------------------------- |
| scan   | read the project                               |
| write  | write the memory files                         |
| check  | show what drifted, change nothing              |
| sync   | refresh memory references in agent context     |

Run the flow: scan → write → sync. For `refresh`: scan → check → write.

## Transversal rules

- **If a referenced file cannot be read, stop and say so. Never invent its content.**
- Ask before anything ambiguous. Never default silently.
- **A memory bank that already exists changes only through what the user approved, file by
  file and line by line.**
- End with a short report of what changed.

## Memory files (default layout under `aidd_docs/memory/`)

- `project-brief.md` — purpose, stack, how it runs/builds, audience.
- `architecture.md` — high-level structure, layered boundaries, key modules.
- `codebase-map.md` — directory map, entry points, core vs. peripheral files.
- `conventions.md` — coding style, naming, framework/pattern choices, commit style.
- `decisions.md` — ADRs: significant decisions and their rationale.
- `vcs.md` — branch strategy, commit conventions, release flow.
- `testing.md` — how to run tests, what coverage exists, test conventions.
- `deployment.md` — build/deploy steps, env vars required.

The exact set adapts to the project; never invent files for content the project doesn't have.

## 'External' vs 'internal' memory

- Memory intended to be loaded on every session lives in the main bank (e.g. `project-brief`,
  `codebase-map`, `conventions`).
- Dense or infrequently-needed detail lives in subfolders read only when the task needs it
  (`external/` for third-party context, `internal/` for deep project internals).

## Workflow

1. **Scan** — read the project: identity files, structure, configs, DOCS.
2. **Write/refresh** — produce or update memory files from the scan, grounded in what was
   actually read, not guessed.
3. **Check** (refresh only) — report what drifted from the current memory, change nothing
   without approval.
4. **Sync** — update the agent's context references to point at the current memory bank.
5. **Report** — what changed, file by file.

## Integration

- Used by `builder` and any agent that benefits from durable project context.
- Pair with `agent-self-improver` / `roadmaps` state, but keep memory content distinct from
  task state: memory is durable project truth, not a to-do list.

## Keywords
"project memory", "memoria del proyecto", "context", "codebase map", "arquitectura", "convenciones", "ADRs", "decisiones", "set up memory", "refresh memory"
