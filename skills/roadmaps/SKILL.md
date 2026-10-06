---
name: roadmaps
description: >-
  Creates, updates, and follows adaptive roadmaps for any project. Manages step-by-step execution plans
  with linear, decision, loop, parallel, and milestone step types; tracks state in .roadmap-state; handles
  failure strategies (retry/rollback/scope change/blocked deps). USE PROACTIVELY — check for roadmap.md
  before any significant work. Use when the user mentions a roadmap, plan, step-by-step, milestones,
  task breakdown, "break this down", "what should I do next", or multi-step tasks. Run this whenever
  roadmap.md exists in the project root. NOT for metric-optimization loops (use goal).
  Triggers: "roadmap", "plan", "que hago primero", "fases del
  proyecto", "multi-step", "big project".
---

# Roadmaps

## Agent assignment
Agent-agnostic by capability; opencode subagent roles are shown as hints only.
- **Read-only** (check/read roadmap) — e.g. opencode `explore`: fast, read-only
- **Read-write** (create/update roadmap, write `.roadmap-state`) — e.g. opencode `general`
- **Executes code changes** for steps requiring edits — e.g. opencode `build`

The skill itself works in any AI that can read/write files; it does not depend on
any specific subagent or AI. Use whichever agent/role owns the current task.

## Protocol

1. Check `roadmap.md` exists in project root before ANY significant work
2. If exists → read immediately, identify in-progress step
3. If not exists → **only for genuinely multi-step tasks**, ask: "Create a roadmap?"
   If yes, build one. For simple/single-step tasks, do NOT ask — just do the task
   (asking for a roadmap on a one-step task adds unproductive overhead).
4. After each step → update `roadmap.md` status + timestamp
5. On new task → re-read roadmap, assess fit

## Integration
- If `AGENTS.md` exists in project root, read it after loading roadmap — it may override step instructions or add context
- If `.roadmap-state` exists, use it as quick-reference for current step (faster than re-reading full roadmap)

## State cache (`.roadmap-state`)
Optional file to avoid re-reading full roadmap.md every turn. AI maintains it.

**Format:**
```
current_step: N
step_label: <Short name>
type: linear|decision|loop|parallel|milestone
status: in_progress
goal: <project goal>
updated: <ISO date>
```

**Rules:**
- Write after each step status change
- If `.roadmap-state` missing or stale (updated older than roadmap.md), fall back to reading roadmap.md
- `.roadmap-state` is cache only — always trust roadmap.md as source of truth

> Staleness reference: this "cache is stale if out-of-date vs the source of truth"
> rule is the shared convention to reuse for any `state` file in this repo
> (e.g. `.opencode/state/<skill>.json`), so all persistent state ages out
> consistently instead of lingering forever.

## Roadmap format (`roadmap.md`)

```
# Roadmap: <Project Name>

## Metadata
- Created: <date>
- Goal: <one sentence>
- Status: in_progress|completed|paused

## Steps

### Step N: <Short name>
- **Type**: linear|decision|loop|parallel|milestone
- **Status**: pending|in_progress|completed|skipped|blocked
- **Next**: Step N+1 (or —)

decision: add **Decision**, **If yes**, **If no**
loop: add **Loop condition**, **Loop back to**
parallel: add **Sub-steps**: N-a: desc, N-b: desc
```

## Step types

| Type | Behavior |
|------|----------|
| linear | Execute → mark complete → follow Next |
| decision | Evaluate condition → branch to If yes/If no |
| loop | Repeat until condition met; if 3+ iterations no progress, ask user |
| parallel | Execute all sub-steps (any order), done when all complete |
| milestone | Verify all completion criteria met |

## Navigation rules

- Skip completed steps unless roadmap changed
- On decision: jump directly to branched step
- Loop stall (3+ runs, no progress): pause, ask user
- Move completed prefix steps to "## Completed" section to keep active view short
- After update: renumber steps, fix Next refs

## Templates
Quick-start skeletons for common project types. Copy + fill values.

| Template | File |
|----------|------|
| Web app | `templates/web-app.md` |
| ML model | `templates/ml-model.md` |
| API service | `templates/api-service.md` |
| Migration | `templates/migration.md` |

## Failure strategies

| Scenario | Action |
|----------|--------|
| Network/timeout error | Retry (loop back) |
| Logic error | Go back 1-2 steps, different approach |
| Missing prerequisite | Go back to prerequisite-creating step |
| User changed scope | Rewrite roadmap from current position |
| Blocked external dep | Mark blocked, skip to independent step, or pause |
| Step irrelevant | Mark skipped, update previous step's Next |

## Creation process
Only for genuinely multi-step tasks (2+ real steps, or a decision/branch worth
tracking). For single-step tasks, skip — see "When NOT to use".

1. Ask: goal (1 sentence), major phases, decision points, completion criteria, loop needs, parallel steps. Use template if applicable.
2. Draft `roadmap.md`, show user for approval. Validate with `scripts/validate_roadmap.py` before presenting.
3. Once approved, set Step 1 to `in_progress`, write `.roadmap-state`, execute

## Completion

- All milestones completed + final step completed + user confirms goal met
- Set `Status: completed`, archive steps under "## Completed", delete `.roadmap-state`

## When to use
- Any multi-step project or task
- Keywords: "roadmap", "plan", "step-by-step", "milestones", "workflow", "task breakdown", "break this down", "what should I do next", "how do I achieve X", "que hago primero", "como logro X", "paso a paso", "que sigue", "proyecto", "fases del proyecto", "plan de trabajo", "sprint", "backlog", "to-do", "tasks", "phases", "road map", "ruta de implementacion", "execution plan", "project plan", "task list", "orden de tareas", "prioridades", "multi-step", "complex task", "big project", "feature plan", "release plan"
- "break this down", "what should I do next", "how do I achieve X"
- When `roadmap.md` exists in project root

## When NOT to use
- Single-step tasks
- Tasks already broken down in issue tracker
- User explicitly doesn't want planning overhead

## Dependencies
No external dependencies.

## Error handling
- **roadmap.md corrupted:** Rebuild from `.roadmap-state` cache if available
- **Step blocked by external dependency:** Mark blocked, skip to independent step
- **User changed scope mid-roadmap:** Rewrite roadmap from current position
- **Loop stall (3+ no progress):** Pause and ask user for guidance

## File structure
```
roadmaps/
├── SKILL.md
├── evals/
│   └── evals.json           # Test prompts
├── scripts/
│   └── validate_roadmap.py  # Roadmap validation
├── templates/
│   ├── web-app.md           # Web app template
│   ├── ml-model.md          # ML model template
│   ├── api-service.md       # API service template
│   └── migration.md         # Migration template
└── tests/
    └── test_roadmaps.py     # Tests
```
