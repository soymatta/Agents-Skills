---
name: backtest-run
description: Runs backtests with project-specific configuration. Never ask the user. Execute autonomously.
---

# Backtest Run

Execute autonomously. Default environment: local (VM has 1 GB RAM). For remote: `python deploy/cloud.py backtest`.

## Procedure

1. **SPEC** — Define entry, sizing, exit, universe, date range. Display target metrics.

2. **DATA** — Min 90 days. Split train/val/test 60/20/20 chronological.

3. **EXECUTE** — Slippage: min(0.5% or 1 tick) per trade. Fill probability: 80% at mid price.

4. **METRICS** — Required: total_return, sharpe_ratio, max_drawdown, win_rate, avg_hold_time, num_trades. Optional: calmar_ratio, profit_factor, expectancy.

5. **ROBUSTNESS** — Monte Carlo entry permutation, parameter sensitivity (±10%, ±20%), slippage scenarios (0.1%, 0.5%, 1.0%, 2.0%), sub-period analysis.

6. **CONCLUSION** — Outperform baseline? Statistical significance? Deploy with real capital? If no, what to change?

## Anti-overfitting
- Max 3 parameter optimizations per backtest
- Never optimize on test set
- Sharpe > 3.0 → suspect overfitting
- Win rate > 80% → check look-ahead bias
- Log every parameter tried (including failures)
