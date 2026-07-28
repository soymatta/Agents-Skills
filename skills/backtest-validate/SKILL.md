---
name: backtest-validate
description: Use when the user needs to validate, evaluate, or verify the quality of a backtested trading strategy before live deployment. Triggers on keywords like "validar", "validate", "backtest review", "backtest quality", "scoring", "backtest score", "strategy evaluation", "stress test", "robustness check", "is this backtest any good". This skill scores backtest quality across 5 dimensions (Sample Size, Expectancy, Risk Management, Robustness, Execution Realism), detects red flags, and outputs a Deploy/Refine/Abandon verdict. Use AFTER backtest-run (which produces the backtest results to validate).
compatibility: Requires backtest-run output to validate. Produces reports consumed by telegram-notify. Includes evaluate_backtest.py scoring script.
---

# Backtest Validate

Systematic backtest quality validation. Goal: find strategies that "break the least", not those that "profit the most" on paper.

## When to use
- Validating systematic trading strategies before live deployment
- Assessing robustness before committing real capital
- Troubleshooting misleading backtests
- Detecting overfitting, look-ahead bias, survivorship bias
- Keywords: "validar", "validate", "backtest review", "backtest quality", "scoring", "backtest score", "strategy evaluation", "stress test", "robustness check", "is this backtest any good"

## When NOT to use
- Running a new backtest (use `backtest-run` first)
- Strategy has no backtest results to validate yet
- User wants to design a strategy, not evaluate one
- No clear entry/exit rules defined

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
# Desde la raiz del proyecto:
python3 scripts/evaluate_backtest.py \
  --total-trades 150 --win-rate 62 \
  --avg-win-pct 1.8 --avg-loss-pct 1.2 \
  --max-drawdown-pct 15 --years-tested 8 \
  --num-parameters 3 --slippage-tested \
  --output-dir reports/
```

El script genera `reports/backtest_eval_<timestamp>.json` y `.md`. Si el directorio `reports/` no existe, se crea automaticamente.

### 7. Decide
- **Deploy** (score ≥70): Survives all stress tests
- **Refine** (score 40-69): Core logic sound, needs adjustment
- **Abandon** (score <40): Fails stress tests or fragile

## Scripts

| Script | Args | Description |
|--------|------|-------------|
| `scripts/evaluate_backtest.py` | `--total-trades`, `--win-rate`, `--avg-win-pct`, `--avg-loss-pct`, `--max-drawdown-pct`, `--years-tested`, `--num-parameters`, `--slippage-tested`, `--output-dir` | Scores backtest quality across 5 dimensions |

## Scoring Dimensions
Each 0-20 pts, total 100: Sample Size, Expectancy, Risk Management, Robustness, Execution Realism.

## Output format
- `reports/backtest_eval_<timestamp>.json` — structured scores, red flags, verdict
- `reports/backtest_eval_<timestamp>.md` — human-readable report

## Dependencies
No additional pip packages required. Uses only standard Python libraries.

## Error handling
- **Insufficient backtest data:** Require min 30 trades. If fewer, recommend running `backtest-run` with longer date range
- **Missing parameters:** Use conservative defaults for any missing metric
- **Script fails:** Log error, fall back to manual scoring using the 5 dimensions
- **reports/ directory doesn't exist:** Auto-create it
- **Conflicting signals (high score but red flags):** Always trust red flags over score — flag in verdict

## File structure
```
backtest-validate/
├── SKILL.md
├── scripts/
│   └── evaluate_backtest.py
└── tests/
    ├── conftest.py
    └── test_evaluate_backtest.py
```

## Restrictions
- **DO NOT** validate a backtest with fewer than 30 trades — recommend more data
- **DO NOT** skip stress testing — it is 80% of the validation work
- **DO NOT** recommend Deploy with score <70
- **DO NOT** ignore red flags even if overall score is high
- **DO NOT** run backtest-run — this skill validates existing results only
