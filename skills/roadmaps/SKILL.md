---
name: roadmaps
description: "Create, update, and follow adaptive roadmaps for any project. USE THIS SKILL whenever the user mentions roadmap, plan, step-by-step, milestones, workflow, task breakdown, 'break this down', 'what should I do next', 'how do I achieve X', implementation path. Also use when roadmap.md exists in project root — always check before starting work. Essential for any multi-step goal; use proactively, not just when asked."
---

# Roadmaps

## Agent assignment
- `explore` for roadmap check/read (fast, read-only)
- `general` for roadmap create/update (needs write)
- `build` for execution steps requiring code changes

## Protocol

1. Check `roadmap.md` exists in project root before ANY significant work
2. If exists → read immediately, identify in-progress step
3. If not exists → ask: "Create a roadmap?" If yes, build one
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

1. Ask: goal (1 sentence), major phases, decision points, completion criteria, loop needs, parallel steps. Use template if applicable.
2. Draft `roadmap.md`, show user for approval
3. Once approved, set Step 1 to `in_progress`, write `.roadmap-state`, execute

## Completion

- All milestones completed + final step completed + user confirms goal met
- Set `Status: completed`, archive steps under "## Completed", delete `.roadmap-state`
