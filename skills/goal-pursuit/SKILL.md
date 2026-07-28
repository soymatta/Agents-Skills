---
name: goal-pursuit
description: Use when the user wants to optimize a numerical metric or reach a quantitative target through iterative improvement. Triggers on keywords like "optimizar", "optimize", "target", "meta numerica", "improve metric", "reach X%", "goal", "autonomous loop", "pursuit", "optimization loop", "maximize", "minimize". This skill runs an autonomous loop that measures, diagnoses, plans, executes, and repeats until the target is met — never asking the user for input. Use for hyperparameter tuning, accuracy improvement, performance optimization, and any iterative numerical goal.
compatibility: Creates runtime state in .opencode/decisions/goal_state.json. Directory auto-created if missing.
---

# Goal Pursuit

Never ask the user anything. Never pause for input. This skill is designed for scenarios where the user has a clearly defined numerical target (e.g., "reach 90% accuracy") and wants the system to autonomously iterate until it gets there. The loop prioritizes lower-cost approaches first (deterministic code before deep learning) to find the best solution efficiently.

## How the state file works

The skill uses `.opencode/decisions/goal_state.json` to persist progress between loop iterations. This allows the loop to be interrupted (e.g., by rate limits, environment restarts) and resume where it left off.

**Auto-creation:** If the file or directory does not exist, it is created automatically on first run with default `null` values.

**State format:**
```json
{
  "goal": "string — description of the target",
  "target": 90.0,
  "current_metric": 85.0,
  "best_metric": 87.0,
  "iterations": 5,
  "achieved": false,
  "history": [
    {"iteration": 1, "metric": 80.0, "action": "initial baseline"},
    {"iteration": 2, "metric": 85.0, "action": "added feature normalization"}
  ],
  "blockers": [
    {"iteration": 3, "issue": "out of memory", "resolution": "reduced batch size"}
  ],
  "last_action": "description of what was tried in the last iteration",
  "approach_tried": ["deterministic", "rules", "regex"],
  "approach_ceiling": "current ceiling observed, e.g., 'deterministic caps at 87%'"
}
```

A template is available at `templates/goal_state_template.json` — copy it to `.opencode/decisions/goal_state.json` to start with a structured baseline.

## Loop

### 1. STATE — Read current state
Read from `.opencode/decisions/goal_state.json`. Init with `null` values if absent. Create the directory `.opencode/decisions/` if it does not exist.

### 2. STATUS — Display current vs target
Log current metric, best metric, iteration count. Show progress bar or delta.

### 3. EVALUATE — Check completion
If `current >= target`: set `achieved=true`, return SUCCESS. The loop never terminates until the target is met.

### 4. DIAGNOSE — Analyze gap
Answer these questions systematically:
- Is there a performance ceiling?
- Was a similar approach tried before and failed (check `history`)?
- Is there a clear bottleneck (data quality, feature engineering, model capacity)?
- What changed since the last iteration — did the metric improve, regress, or plateau?

### 5. PLAN — Choose next action
**Priority (ascending cost):** deterministic code > rules > regex > classical algorithms > classic ML > deep learning > LLM.

| Condition | Action |
|-----------|--------|
| Current approach + tuning can reach target | Iterate (adjust parameters) |
| Ceiling below target | Change paradigm (e.g., rules > ML) |
| Lower-cost option untested | Try first |
| Same approach failed 3+ times | Switch paradigm |
| Metric regressed | Revert to last best, try different |

### 6. EXECUTE — Implement plan
Write only necessary code. Auto-fix errors. Do not modify unrelated code.

### 7. MEASURE — Run target metric
Auto-retry on failure. `best_metric = max(best, current)`.

### 8. LOG — Record iteration
Write to `.opencode/decisions/goal_state.json` with: goal, target, current, best, iterations, achieved, history, blockers, approach_tried.

### 9. GOTO 1 — Repeat

## Rules
- Never ask the user. Never stop.
- Metric regresses > revert, log failure, try next approach
- 5 flat iterations (no improvement) > change paradigm
- Execution error > log blocker, try alternative immediately
- Efficiency first: equal expected improvement > pick lower cost approach
- Always check `history` before repeating a failed approach

## Example workflow

User: "Optimize this model to reach 92% accuracy"
1. Read state > no existing state, init with target=92
2. Measure baseline accuracy > 85%
3. Diagnose: data preprocessing basic, using default params
4. Plan: try feature scaling (lowest cost untested)
5. Execute: add StandardScaler
6. Measure: 87% (+2%)
7. Log: record iteration, update .opencode/decisions/goal_state.json
8. Repeat until 92% achieved or ceiling reached

## When to use
- User wants to optimize a numerical metric to reach a specific target
- Keywords: "optimizar", "optimize", "target", "meta numerica", "improve metric", "reach X%", "goal", "autonomous loop"
- Hyperparameter tuning, accuracy improvement, performance optimization
- Any iterative numerical goal that requires autonomous execution

## When NOT to use
- Qualitative improvements (writing style, design)
- Tasks requiring user decisions at each step
- Non-numerical goals

## Dependencies
No external dependencies. Uses only standard Python and existing project code.

## Error handling
- **State file corrupted:** Delete and reinitialize with null values
- **Metric cannot be measured:** Log blocker, try alternative measurement approach
- **All approaches exhausted:** Report ceiling to user, suggest manual intervention
- **Execution error in code:** Auto-fix and retry, log blocker

## File structure
```
goal-pursuit/
├── SKILL.md
├── templates/
│   └── goal_state_template.json  # State file template
└── tests/
    └── test_goal_pursuit.py      # Tests
```
