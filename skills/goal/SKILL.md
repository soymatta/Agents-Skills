---
name: goal
description: >-
  Reaches an objective via an iterative autonomous loop (measure → diagnose → plan → execute → repeat), driving a
  flow until the goal is achieved. Handles maximize/minimize/exact-value targets (metrics, hyperparameters,
  quality gates, completion criteria), prioritizes lower-cost approaches first (deterministic > rules > ML > LLM),
  persists progress in goal_state.json, reverts on degradation, and stops on an exhausted budget. Asks one scoping
  question then runs autonomously. Use when the user wants to set a goal or objective and reach it: improve a
  metric to X%, tune parameters, hit a quantitative target, or iterate toward a measurable outcome.
  NOT for step-by-step task tracking (use roadmaps). Triggers:
  "goal", "objetivo", "alcanzar", "reach X%", "optimizar", "optimize", "target", "improve metric", "tune",
  "accuracy".
---

# Goal

Iterative autonomous loop that drives a flow toward a measurable objective. Framing-inspired: define what
"done" means as a number you can check, then loop until the goal is reached or the budget is exhausted. Asks
**one** scoping question up front (objective, budget, measurement command), then runs autonomously without
further interruption.

## When to use
- User sets a goal or objective with a measurable success criterion (not only metrics: coverage %, error rate,
  latency, iteration milestones, any "reach this target" ask)
- Hyperparameter tuning, accuracy improvement, performance optimization
- Any iterative numerical goal with a clear, measurable success criterion
- Targets to maximize, minimize, or hit an exact value
- **Keywords:** "goal", "objetivo", "meta", "alcanzar", "llegar a", "reach X%", "optimizar", "optimize", "target",
  "improve metric", "maximize", "minimize", "hyperparameter", "accuracy", "performance", "tune", "auto-tune",
  "reduce error rate", "latency reduction", "ceiling", "plateau", "get to 95%"

## When NOT to use
- No measurable objective defined (only qualitative improvement)
- User wants a single experiment, not iteration
- Problem requires human judgment at each step
- Goal cannot be evaluated programmatically

## Upfront scoping (ask ONCE, then stop asking)

Before starting the loop, confirm these (they determine correct logic and a
safe runtime). Ask them together as a single question, then never ask again:

1. **Direction** — is the target to `maximize`, `minimize`, or hit `exact`?
   (If unspoken, infer from the phrasing: "maximize/improve up" → maximize;
   "reduce/lower/down" → minimize; "get to exactly X" → exact; milestones →
   exact with tolerance.)
2. **Measurement command** — the exact command/script that returns the metric
   (needed so iterations can reproduce and compare fairly).
3. **Budget** — `max_iterations` (e.g. 30), `max_cost` (e.g. "no paid APIs"),
   and/or a `deadline`. If the user has no preference, default to
   `max_iterations: 20` and "no paid APIs unless already provisioned".

If the objective is unambiguous and these are inferable, you may proceed — but
if measurement or direction are genuinely unknown, default to `maximize` and a
predictable baseline rather than guessing an arbitrary heuristic.

## State file

Uses `.opencode/decisions/goal_state.json` to persist progress. Auto-creates if
missing. The schema is direction- and budget-aware:

```json
{
  "goal": "string — description of the goal",
  "mode": "maximize | minimize | exact",
  "target": 90.0,
  "current_metric": 85.0,
  "best_metric": 87.0,
  "iterations": 5,
  "achieved": false,
  "budget": {"max_iterations": 20, "max_cost": null, "deadline": null, "budget_exhausted": false},
  "measure_cmd": "string — command that returns the metric",
  "history": [
    {"iteration": 1, "metric": 80.0, "action": "initial baseline", "checkpoint": "git sha / diff ref"}
  ],
  "blockers": [
    {"iteration": 3, "issue": "out of memory", "resolution": "reduced batch size"}
  ],
  "last_action": "description of what was tried last",
  "approach_tried": ["deterministic", "rules", "regex"],
  "approach_ceiling": "current observed ceiling, e.g. 'deterministic caps at 87%'"
}
```

**Checkpoints for revert:** before each EXECUTE, record a revert point —
prefer a git commit hash or a saved copy of the changed files in
`.opencode/decisions/checkpoints/iteration-<N>/`. A revert with nothing to
revert to is not a revert.

## Direction-aware logic

- `maximize`: success when `current >= target`; `best_metric = max(best, current)`.
- `minimize`: success when `current <= target`; `best_metric = min(best, current)`.
- `exact`: success when `current` is within tolerance of `target` (default
  tolerance = 1% of target unless stated); `best_metric` = value closest to target.
- "Degraded" means moving away from the target compared to `best_metric`:
  `maximize → current < best`; `minimize → current > best`;
  `exact → |current - target| > |best - target|`.

## Workflow (loop)

### 1. STATE — Read current state
Read `.opencode/decisions/goal_state.json`. Initialize if missing (capture
direction, budget, measure_cmd, and the current baseline).

### 2. STATUS — Show current vs target
Log current metric, best metric, iteration count, and remaining budget. Show
delta toward the target as `before → after` so the win is visible every turn.

### 3. CHECK BUDGET — Stop safely
If `iterations >= budget.max_iterations`, or `max_cost`/`deadline` is exceeded
or the budget flag is set: set `budget_exhausted=true`, log a report, and return
CEILING/STOP instead of continuing the loop.

### 4. EVALUATE — Check completeness
Using the direction-aware rule, if the target is reached: set `achieved=true`,
return SUCCESS.

### 5. DIAGNOSE — Analyze the gap
- Is there a performance ceiling (`approach_ceiling`)?
- Was a similar approach tried and failed before (check `history`)?
- Is there a clear bottleneck (data quality, feature engineering, model capacity)?
- What changed since the last iteration?

### 6. PLAN — Choose next action
**Priority (ascending cost):** deterministic code > rules > regex > classic
algorithms > classic ML > deep learning > LLM.

| Condition | Action |
|-----------|--------|
| Current approach + tuning can reach target | Iterate (adjust parameters) |
| Ceiling is below the target | Switch paradigm |
| Lower-cost option not yet tried | Try it first |
| Same approach failed/reached a plateau 3 consecutive times | Switch paradigm |
| Metric degraded | Revert to last best checkpoint, try different |

Use a **single** failure constant throughout: 3 consecutive flat-or-failed
iterations on the same approach → switch paradigm.

### 7. EXECUTE — Implement plan
Checkpoint first (see State file). Write only necessary code. Self-correct
errors. Do not modify unrelated code.

### 8. MEASURE — Run target metric
Run `measure_cmd`. Auto-retry transient failures (with a bounded retry count,
e.g. 3). To reduce noise, prefer a fixed seed and/or repeat the measurement a
small number of times and record the best-of-N or mean. Update
`best_metric` using the direction-aware rule. Increment `iterations`.

### 9. LOG — Log iteration
Write to `.opencode/decisions/goal_state.json` with the checkpoint reference.

### 10. GOTO 1 — Repeat (unless budget exhausted or achieved)

## Templates

| Template | File |
|----------|------|
| Goal state | `templates/goal_state_template.json` |

## Output
- `.opencode/decisions/goal_state.json` updated with progress
- Iteration log with metric history, checkpoints, blockers, approaches tried
- Final: SUCCESS (target reached), CEILING REACHED (with recommendation), or
  BUDGET EXHAUSTED (with progress summary)
- Progress updates to the user: one line with current/best/target, the `before → after`
  delta, and budget left (iterations, cost, deadline in minutes) — then the next move.

## Dependencies
None.

## Error handling
- **Corrupted state file:** Delete and reinitialize (preserve budget/direction by re-asking once if needed, else use defaults)
- **Metric measurement fails:** Log blocker, retry up to 3 times, then try an alternative measurement or mark blocked
- **Execution error:** Log blocker, revert to last checkpoint, try alternative immediately
- **Concurrent sessions:** The state file is single-writer; if a lock-token/session marker can't be set, warn and proceed (do not silently clobber another session's history)

## Restrictions
- **DO NOT** ask the user anything after the initial scoping — never interrupt once running
- **DO NOT** modify unrelated code
- **DO NOT** skip DIAGNOSE — every iteration must learn from history
- **DO NOT** repeat a failed approach without changing a variable
- **DO NOT** use costly approaches before exhausting cheaper ones
- **DO NOT** exceed the configured budget — stop and report instead of looping forever

## Rules
- Ask one scoping question up front (direction, budget, measurement), then never ask again.
- Direction-aware: use `mode` to decide success, best, and degradation.
- Metric degraded → revert to last checkpoint, log failure, try next approach.
- 3 consecutive flat or failed iterations on the same approach → switch paradigm.
- Execution error → log blocker, revert, try alternative immediately.
- Efficiency first: equal improvement → choose the lower-cost approach.
- Always check `history` before repeating a failed approach.
- Always record a revert checkpoint before each change, so "revert" is real.