---
name: backtest-validate
description: >-
  Validates, evaluates, and scores a backtested trading strategy before live deployment. Scores across 5
  dimensions (Sample Size, Expectancy, Risk Management, Robustness, Execution Realism), runs ±50% stop-loss
  / ±20% profit-target sensitivity, out-of-sample walk-forward, and overfitting heuristics, then outputs a
  Deploy (>=70) / Refine (40-69) / Abandon (<40) verdict with an optional hard red-flag override.
  Includes evaluate_backtest.py (flag or --input JSON mode). Use when validating a backtest, checking if a
  strategy is good, stress-testing it, or deciding whether to deploy. Run AFTER backtest-run.
  Triggers: "validar backtest", "validate", "backtest review", "is this backtest any good", "should I deploy",
  "evaluar estrategia", "deploy or not".
compatibility: Requires backtest-run output to validate. Produces reports consumed by telegram-notify. Includes evaluate_backtest.py scoring script.
---

# Backtest Validate

Systematic backtest quality validation. Goal: find strategies that "break the least", not those that "profit the most" on paper.

## When to use
- Validating systematic trading strategies before live deployment
- Assessing robustness before committing real capital
- Troubleshooting misleading backtests
- Detecting overfitting, look-ahead bias, survivorship bias
- Keywords: "validar backtest", "validate", "backtest review", "backtest quality", "scoring", "backtest score", "strategy evaluation", "stress test", "robustness check", "is this backtest any good", "is the strategy good", "should I deploy", "es bueno este backtest", "evaluar estrategia", "revisar backtest", "overfitting check", "walk-forward", "parameter sensitivity", "strategy robustness", "backtest report", "deploy or not"

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

Two ways to run the scorer:

**a) From backtest-run output (preferred, no transcription):** read the metrics
directly from the `reports/backtest_*.json` written by backtest-run:
```bash
python skills/backtest-validate/scripts/evaluate_backtest.py \
  --input reports/backtest_<timestamp>.json \
  --years-tested 8 --num-parameters 3 \
  --force-abandon-on-high-redflag \
  --output-dir reports/
```

**b) Manual flag mode** (when only summary metrics are available):
```bash
python skills/backtest-validate/scripts/evaluate_backtest.py \
  --total-trades 150 --win-rate 62 \
  --avg-win-pct 1.8 --avg-loss-pct 1.2 \
  --max-drawdown-pct 15 --years-tested 8 \
  --num-parameters 3 --slippage-tested \
  --output-dir reports/
```

The script writes `reports/backtest_eval_<timestamp>.json` and `.md`
(auto-creating `reports/` if missing).

> **`--input` mapping notes:** backtest-run's JSON exposes `win_rate`, `max_drawdown`,
> and `num_trades`, but not `avg_win_pct`/`avg_loss_pct` per trade. Those default to
> `0.0` (conservative), which depresses the Expectancy/Risk scores. Pass explicit
> `--avg-win-pct`/`--avg-loss-pct` when you have them.

### 7. Decide
- **Deploy** (score ≥70): Survives all stress tests
- **Refine** (score 40-69): Core logic sound, needs adjustment
- **Abandon** (score <40): Fails stress tests or fragile
- **Hard override:** with `--force-abandon-on-high-redflag`, any high-severity red
  flag forces **Abandon** regardless of score — this implements the
  "trust red flags over score" principle as a hard rule, not just guidance.

## Scripts

| Script | Args | Description |
|--------|------|-------------|
| `scripts/evaluate_backtest.py` | `--input JSON` (preferred), or `--total-trades`, `--win-rate`, `--avg-win-pct`, `--avg-loss-pct`, `--max-drawdown-pct`, `--years-tested`, `--num-parameters`, `--slippage-tested`; `--force-abandon-on-high-redflag`, `--output-dir` | Scores backtest quality across 5 dimensions |

## Scoring Dimensions
Each 0-20 pts, total 100: Sample Size, Expectancy, Risk Management, Robustness, Execution Realism.

## Output format
- `reports/backtest_eval_<timestamp>.json` — structured scores, red flags, verdict (+ `red_flag_override` when forced)
- `reports/backtest_eval_<timestamp>.md` — human-readable report

## Dependencies
No additional pip packages required. Uses only standard Python libraries.

## Error handling
- **Insufficient backtest data:** Require min 30 trades. If fewer, recommend running `backtest-run` with longer date range
- **Missing parameters:** Use conservative defaults for any missing metric
- **Script fails:** Log error, fall back to manual scoring using the 5 dimensions
- **reports/ directory doesn't exist:** Auto-create it
- **Conflicting signals (high score but high-severity red flags):** Trust red flags over score — pass `--force-abandon-on-high-redflag` so the verdict is hard-forced to Abandon, and flag it in the verdict

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
- **DO NOT** ignore red flags even if overall score is high — prefer the hard `--force-abandon-on-high-redflag` override
- **DO NOT** claim the script *detected* look-ahead/survivorship bias — it only flags heuristic signs; real bias needs manual audit
- **DO NOT** run backtest-run — this skill validates existing results only
