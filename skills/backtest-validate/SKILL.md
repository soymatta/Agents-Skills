---
name: backtest-validate
description: Expert guidance for systematic backtesting of trading strategies. Scores quality across 5 dimensions, detects red flags, outputs Deploy/Refine/Abandon verdict.
---

# Backtest Validate

Systematic backtest quality validation. Goal: find strategies that "break the least", not those that "profit the most" on paper.

## When to Use
- Validating systematic trading strategies
- Assessing robustness before live deployment
- Troubleshooting misleading backtests
- Detecting overfitting, look-ahead bias, survivorship bias

## Workflow

### 1. State Hypothesis
Define edge in one sentence. If unclear, do not proceed.

### 2. Codify Rules
Entry, exit, sizing, filters, universe. Zero discretion — every decision rule-based and unambiguous.

### 3. Run Initial Backtest
Min 5 years (pref 10+). Multiple market regimes. Realistic commissions + conservative slippage.

### 4. Stress Test (80% of time)
- **Parameter sensitivity**: Vary stop loss ±50%, profit target ±20%, timing ±15-30min. Seek plateaus, not peaks.
- **Execution friction**: Slippage 1.5-2x typical, worst-case fills, order rejection scenarios.
- **Time robustness**: Year-by-year analysis. Require positive expectancy in majority of years.
- **Sample size**: Min 30 trades, pref 100+, high confidence 200+.

### 5. Out-of-Sample Validation
Walk-forward analysis. Compare in-sample vs out-of-sample. Warning if OOS <50% of IS.

### 6. Run Evaluation Script
```bash
python3 skills/backtest-validate/evaluate_backtest.py \
  --total-trades 150 --win-rate 62 \
  --avg-win-pct 1.8 --avg-loss-pct 1.2 \
  --max-drawdown-pct 15 --years-tested 8 \
  --num-parameters 3 --slippage-tested \
  --output-dir reports/
```

### 7. Decide
- **Deploy** (score ≥70): Survives all stress tests
- **Refine** (score 40-69): Core logic sound, needs adjustment
- **Abandon** (score <40): Fails stress tests or fragile

## Scoring Dimensions
Each 0-20 pts, total 100: Sample Size, Expectancy, Risk Management, Robustness, Execution Realism.

## Output
- `reports/backtest_eval_<timestamp>.json` — structured scores, red flags, verdict
- `reports/backtest_eval_<timestamp>.md` — human-readable report
