---
name: backtest-run
description: >-
  Executes the full backtest pipeline autonomously for any trading strategy: spec definition, data prep
  (min 90 days, train/val/test), realistic execution (slippage, 80% fill at mid), metrics (Sharpe, drawdown,
  win rate, expectancy), robustness checks (Monte Carlo, parameter sensitivity), and a deploy/refine/abandon
  conclusion. Local or remote via SSH. Use when the user wants to backtest a trading strategy, test a trading
  idea, or simulate trades. Run BEFORE backtest-validate; executes autonomously with a scoping round.
  Triggers: "backtest", "backtesting", "backtestear", "probar estrategia", "simular trades".
compatibility: Used by backtest-validate and telegram-notify. Remote execution via scripts/cloud.py (SSH). Produces output consumed by backtest-validate.
---

# Backtest Run

Execute autonomously. Default environment: local (VM has 1 GB RAM).

A *useful* backtest is not backtesting a lot, but backtesting *well*: with
overfitting controlled, realistic execution (slippage, fill probability), and
metrics that actually inform a real decision. Without these controls, a backtest
is noise.

## When to use
- User wants to run a backtest for a trading strategy
- Keywords: "backtest", "backtesting", "backtestear", "strategia", "trading strategy", "backtest run", "ejecutar backtest", "probar estrategia", "evaluar estrategia", "simular trades", "prueba de fuego", "backtesting python", "backtest with slippage", "walk-forward", "monte carlo trading", "strategy test", "trading simulation", "quant backtest", "backtest script"
- Need to evaluate a strategy's performance with realistic execution modeling

## When NOT to use
- User wants to validate an existing backtest (use `backtest-validate`)
- User wants to build a live trading bot (not this skill's scope)
- No clear strategy specification provided
- User wants to design a strategy without executing a backtest

## Before starting — one scoping confirmation (1 round)
Ask one short confirmation covering: **universe** (which instruments), **date range**,
and **data source** (provider / file path). Confirm the strategy idea is clear
enough to express as entry/exit/sizing. After that, execute autonomously.

## Workflow

### 0. SCOPE — confirm universe, date range, and data source (1 round). Then autonomous.

### 1. SPEC — Write a concrete, machine-checkable spec with this required format.
```
strategy: <name>
entry:   <condition, e.g. 'fast_MA(20) crosses above slow_MA(50)'>
exit:    <condition, e.g. 'fast below slow' or 'stop/target'>
sizing:  <e.g. '1.0 units per signal' or '1% risk per trade'>
universe: <instruments>
date_range: <start..end>
baseline: <e.g. 'buy and hold' or 'SPY'>
```
No 1-line placeholder: if any of entry/exit/sizing is undefined, stop and ask.

### 2. DATA — Min 90 days of present OHLCV.
- **Source must be explicit** (e.g. local CSV `date,open,high,low,close[,volume]`,
  yfinance, or a provided file). If no source is configured, ask; never fabricate prices.
- Split train/val/test **60/20/20 chronological**. Use the bundled runner:
  `python scripts/backtest_runner.py --data data.csv --output reports/backtest_<ts>.json`.
- **Never** tune on the test slice.

### 3. EXECUTE — Slippage: min(0.5% or 1 tick) per trade. Fill probability: 80% at mid price.

### 4. METRICS — Required: total_return, sharpe_ratio, max_drawdown, win_rate, avg_hold_time, num_trades. Optional: calmar_ratio, profit_factor, expectancy. Persist to `reports/backtest_<ts>.json` (handoff contract for backtest-validate).

### 5. ROBUSTNESS — Monte Carlo entry permutation, parameter sensitivity (+-10%, +-20%), slippage scenarios (0.1%, 0.5%, 1.0%, 2.0%), sub-period analysis.

### 6. CONCLUSION — Outperform baseline? Statistical significance? Deploy with real capital? If no, what to change? Write a short verdict + the `reports/` JSON.

## Remote execution

For backtests that need more resources, use the bundled cloud runner:
```bash
python -m skills.backtest-run.scripts.cloud backtest [args]
```
Configure with `CLOUD_HOST`, `CLOUD_USER`, `CLOUD_KEY` env vars or `.opencode/cloud.json`.
`cloud.py` copies the bundled `backtest_runner.py` to the remote automatically when
available, and falls back to **local** execution (instead of erroring) if no host is
configured or the copy fails.

## Scripts

| Script | Args | Description |
|--------|------|-------------|
| `scripts/cloud.py` | `backtest [args]` | Remote backtest execution via SSH (falls back to local) |
| `scripts/backtest_runner.py` | `--data F --output O` | Self-contained backtest engine + metrics (used locally and copied to remote) |

## Output format
- Strategy spec summary
- Metrics table (total_return, sharpe_ratio, max_drawdown, win_rate, avg_hold_time, num_trades)
- `reports/backtest_<ts>.json` with spec + metrics (handoff to backtest-validate)
- Robustness report (Monte Carlo, parameter sensitivity, slippage scenarios)
- Conclusion with deploy/refine/abandon recommendation

## Dependencies
No additional pip packages required for local execution. Cloud execution requires SSH access configured via env vars.

## Error handling
- **Insufficient data (<90 days):** Extend date range or reduce universe. Never proceed with less than 90 days
- **Execution errors during backtest:** Log error, attempt fix, retry once. If persistent, skip and document
- **Cloud SSH failure:** Fall back to local execution. Log warning
- **Overfitting suspected:** flag `num_parameters >= 7` and `win_rate > 90 AND max_drawdown < 5` in the conclusion; these match backtest-validate's red flags so the handoff is consistent. Recommend parameter reduction

## File structure
```
backtest-run/
├── SKILL.md
└── scripts/
    ├── __init__.py
    ├── backtest_runner.py
    └── cloud.py
```

## Restrictions
- Do the ONE scoping confirmation up front, then **DO NOT** prompt the user again — execute autonomously
- **DO NOT** optimize on test set
- **DO NOT** skip robustness checks
- **DO NOT** proceed with less than 90 days of data
- **DO NOT** fabricate prices when no data source is configured — ask instead
- Max 3 parameter optimizations per backtest
- Log every parameter tried, including failures
- Overfit flags (match backtest-validate): `num_parameters >= 7`, or `win_rate > 90` with `max_drawdown < 5`
