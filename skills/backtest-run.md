---
name: backtest-run
description: Use when the user needs to run a backtest for a trading strategy, including spec definition, data preparation, execution with slippage/fill modeling, metrics calculation, robustness checks, and conclusion. Triggers on keywords like "backtest", "backtesting", "backtestear", "strategia", "trading strategy", "backtest run", "ejecutar backtest". This skill handles the full backtest pipeline autonomously — never prompt the user for decisions. Use before backtest-validate (which evaluates the quality of the output).
compatibility: Used by backtest-validate and telegram-notify. For remote execution requires deploy/cloud.py.
---

# Backtest Run

Execute autonomously. Default environment: local (VM has 1 GB RAM). For remote: `python deploy/cloud.py backtest`.

La clave de un backtest util no es backtestear mucho, sino backtestear bien: con overfitting controlado, con realismo en ejecucion (slippage, fill probability), y con metricas que realmente importan para decision real. Sin estos controles, un backtest es ruido.

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
