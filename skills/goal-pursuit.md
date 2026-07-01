---
name: goal-pursuit
description: Use when the user wants to optimize a numerical metric or reach a quantitative target through iterative improvement. Triggers on keywords like "optimizar", "optimize", "target", "meta numerica", "improve metric", "reach X%", "goal", "autonomous loop", "pursuit", "optimization loop", "maximize", "minimize". This skill runs an autonomous loop that measures, diagnoses, plans, executes, and repeats until the target is met — never asking the user for input. Use for hyperparameter tuning, accuracy improvement, performance optimization, and any iterative numerical goal.
---

# Goal Pursuit

Never ask the user anything. Never pause for input. This skill is designed for scenarios where the user has a clearly defined numerical target (e.g., "reach 90% accuracy") and wants the system to autonomously iterate until it gets there. The loop prioritizes lower-cost approaches first (deterministic code before deep learning) to find the best solution efficiently.

## Loop

### 1. STATE — Read current state
Fields: `current_metric`, `best_metric`, `iterations`, `history`, `blockers`. Read from `.opencode/decisions/goal_state.json`. Init with `null` if absent. Include cloud state if VM configured.

### 2. STATUS — Display current vs target
Log to `.opencode/decisions/goal_state.json`.

### 3. EVALUATE — Check completion
If `current >= target`: set `achieved=true`, return SUCCESS. Loop never terminates until met.

### 4. DIAGNOSE — Analyze gap
Is there a ceiling? A clear bottleneck? Was a similar approach tried before and failed?

### 5. PLAN — Choose next action
Priority (ascending cost): deterministic code → rules → regex → classical algorithms → classic ML → deep learning → LLM.
- If current approach + tuning can reach target → iterate
- If ceiling below target → change paradigm
- If lower-cost option untested → try first

### 6. EXECUTE — Implement plan
Write only necessary code. Auto-fix errors. Do not modify unrelated code.

### 7. MEASURE — Run target metric
Auto-retry on failure. `best_metric = max(best, current)`.

### 8. LOG — Record iteration
Write to state JSON with: goal, target, current, best, iterations, achieved, history, blockers.

### 9. GOTO 1 — Repeat

## Rules
- Never ask the user. Never stop.
- Metric regresses → revert, log failure, try next
- 5 flat iterations → change paradigm
- Execution error → log blocker, try alternative immediately
- Efficiency first: equal probability → pick lower cost
