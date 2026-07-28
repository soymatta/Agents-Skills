---
name: backtest-run
description: Use when the user needs to run a backtest for a trading strategy, including spec definition, data preparation, execution with slippage/fill modeling, metrics calculation, robustness checks, and conclusion. Triggers on keywords like "backtest", "backtesting", "backtestear", "strategia", "trading strategy", "backtest run", "ejecutar backtest". This skill handles the full backtest pipeline autonomously — never prompt the user for decisions. Use before backtest-validate (which evaluates the quality of the output).
compatibility: Used by backtest-validate and telegram-notify. Remote execution via scripts/cloud.py (SSH). Produces output consumed by backtest-validate.
---

# Backtest Run

Execute autonomously. Default environment: local (VM has 1 GB RAM).

La clave de un backtest util no es backtestear mucho, sino backtestear bien: con overfitting controlado, con realismo en ejecucion (slippage, fill probability), y con metricas que realmente importan para decision real. Sin estos controles, un backtest es ruido.

## When to use
- User wants to run a backtest for a trading strategy
- Keywords: "backtest", "backtesting", "backtestear", "strategia", "trading strategy", "ejecutar backtest"
- Need to evaluate a strategy's performance with realistic execution modeling

## When NOT to use
- User wants to validate an existing backtest (use `backtest-validate`)
- User wants to build a live trading bot (not this skill's scope)
- No clear strategy specification provided
- User wants to design a strategy without executing a backtest

## Workflow

### 1. SPEC — Define entry, sizing, exit, universe, date range. Display target metrics.

### 2. DATA — Min 90 days. Split train/val/test 60/20/20 chronological.

### 3. EXECUTE — Slippage: min(0.5% or 1 tick) per trade. Fill probability: 80% at mid price.

### 4. METRICS — Required: total_return, sharpe_ratio, max_drawdown, win_rate, avg_hold_time, num_trades. Optional: calmar_ratio, profit_factor, expectancy.

### 5. ROBUSTNESS — Monte Carlo entry permutation, parameter sensitivity (+-10%, +-20%), slippage scenarios (0.1%, 0.5%, 1.0%, 2.0%), sub-period analysis.

### 6. CONCLUSION — Outperform baseline? Statistical significance? Deploy with real capital? If no, what to change?

## Remote execution

For backtests that need more resources, use the bundled cloud runner:
```bash
python -m skills.backtest-run.scripts.cloud backtest [args]
```
Configure with `CLOUD_HOST`, `CLOUD_USER`, `CLOUD_KEY` env vars or `.opencode/cloud.json`.

## Scripts

| Script | Args | Description |
|--------|------|-------------|
| `scripts/cloud.py` | `backtest [args]` | Remote backtest execution via SSH |

## Output format
- Strategy spec summary
- Metrics table (total_return, sharpe_ratio, max_drawdown, win_rate, avg_hold_time, num_trades)
- Robustness report (Monte Carlo, parameter sensitivity, slippage scenarios)
- Conclusion with deploy/refine/abandon recommendation

## Dependencies
No additional pip packages required for local execution. Cloud execution requires SSH access configured via env vars.

## Error handling
- **Insufficient data (<90 days):** Extend date range or reduce universe. Never proceed with less than 90 days
- **Execution errors during backtest:** Log error, attempt fix, retry once. If persistent, skip and document
- **Cloud SSH failure:** Fall back to local execution. Log warning
- **Overfitting detected (Sharpe > 3.0):** Flag in conclusion, recommend parameter reduction

## File structure
```
backtest-run/
├── SKILL.md
└── scripts/
    ├── __init__.py
    └── cloud.py
```

## Restrictions
- **DO NOT** prompt the user for decisions — execute autonomously
- **DO NOT** optimize on test set
- **DO NOT** skip robustness checks
- **DO NOT** proceed with less than 90 days of data
- **DO NOT** ignore Sharpe > 3.0 or win rate > 80% — investigate overfitting
- Max 3 parameter optimizations per backtest
- Log every parameter tried, including failures
- Sharpe > 3.0 → investigate for overfitting before concluding
- Win rate > 80% → check for look-ahead bias
