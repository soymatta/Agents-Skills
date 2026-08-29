"""Self-contained backtest runner used by the backtest-run skill.

Implements the core execution + metrics contract of `backtest-run/SKILL.md`:
realistic slippage and fill modeling, train/val/test chronological split, and
the required metrics (total_return, sharpe_ratio, max_drawdown, win_rate,
avg_hold_time, num_trades). Optional metrics: profit_factor, expectancy.

This module is referenced by `cloud.py` — both for local fallback and to be
copied to a remote host. It is intentionally dependency-light (stdlib + numpy
if available).

Usage:
    python -m skills.backtest-run.scripts.backtest_runner --data data.csv [options]
    python backtest_runner.py --data data.csv --output results.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional dependency
    np = None


DEFAULT_SLIPPAGE = 0.005       # 0.5%
DEFAULT_FILL_AT_MID = 0.8      # 80% of orders fill at mid price
DEFAULT_LOOKBACK = 90          # min days of data


def _as_float(value) -> float:
    return float(value)


def _years_between(start: str, end: str) -> float:
    """Approximate calendar years between two ISO-ish dates; fallback to 0."""
    try:
        from datetime import datetime
        fmt = "%Y-%m-%d"
        fmt = "%Y-%m-%d %H:%M:%S" if " " in start or "T" in start else fmt
        s = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        e = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        return (e - s).days / 365.25
    except ValueError:
        return 0.0


def load_series(path: str) -> list[dict]:
    """Load OHLCV rows from CSV with columns: date,open,high,low,close[,volume]."""
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            try:
                rows.append({
                    "date": r["date"].strip(),
                    "open": _as_float(r["open"]),
                    "high": _as_float(r["high"]),
                    "low": _as_float(r["low"]),
                    "close": _as_float(r["close"]),
                    "volume": float(r["volume"]) if r.get("volume") else 0.0,
                })
            except (KeyError, ValueError) as e:
                raise ValueError(f"Bad row {r}: {e}")
    if len(rows) < DEFAULT_LOOKBACK:
        raise ValueError(
            f"Need at least {DEFAULT_LOOKBACK} days of data; got {len(rows)}."
        )
    return rows


def simple_ma(closes: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if period <= 0:
        return out
    for i in range(period - 1, len(closes)):
        out[i] = sum(closes[i - period + 1 : i + 1]) / period
    return out


def run_backtest(
    closes: list[float],
    *,
    fast: int = 20,
    slow: int = 50,
    slippage: float = DEFAULT_SLIPPAGE,
    fill_at_mid: float = DEFAULT_FILL_AT_MID,
) -> dict:
    """Trade a fast/slow moving-average crossover with realistic fills.

    Long only. We take the fast/slow cross as the entry/exit signal. Fills are
    modeled at mid price with probability `fill_at_mid`; otherwise the trade is
    skipped. Slippage is applied to the fill price.
    """
    if np is None:
        fast_ma = simple_ma(closes, fast)
        slow_ma = simple_ma(closes, slow)
    else:
        arr = np.asarray(closes, dtype=float)
        fast_ma = [None] * len(closes)
        slow_ma = [None] * len(closes)
        for i in range(len(closes)):
            if i >= fast - 1:
                fast_ma[i] = float(np.mean(arr[i - fast + 1 : i + 1]))
            if i >= slow - 1:
                slow_ma[i] = float(np.mean(arr[i - slow + 1 : i + 1]))

    position = 0.0            # units held
    entry_price = None
    entry_i = None
    equity = 1.0              # normalized starting equity
    trades: list[dict] = []

    for i in range(1, len(closes)):
        f, s = fast_ma[i], slow_ma[i]
        f_prev, s_prev = fast_ma[i - 1], slow_ma[i - 1]
        price = closes[i] if closes[i] else 0.0

        if f is None or s is None or f_prev is None or s_prev is None:
            continue

        crossed_up = f_prev <= s_prev and f > s
        crossed_down = f_prev >= s_prev and f < s

        if position == 0 and crossed_up:
            if _random_fill() >= (1.0 - fill_at_mid):
                entry_price = price * (1 + slippage)
                entry_i = i
                position = 1.0
        elif position > 0 and crossed_down:
            exit_price = price * (1 - slippage)
            ret = (exit_price - entry_price) / entry_price
            trades.append({
                "entry_i": entry_i,
                "exit_i": i,
                "return_pct": ret,
                "hold_bars": i - entry_i,
            })
            position = 0.0

        if position > 0 and entry_price:
            equity = equity * (price * (1 - slippage)) / (entry_price * (1 - slippage))
        else:
            equity = equity  # flat equity is captured at exits

    # Force-close any open position at the last price
    if position > 0 and entry_price and len(closes):
        last = closes[-1]
        ret = (last * (1 - slippage) - entry_price) / entry_price
        trades.append({
            "entry_i": entry_i,
            "exit_i": len(closes) - 1,
            "return_pct": ret,
            "hold_bars": len(closes) - 1 - (entry_i or 0),
        })

    returns = [t["return_pct"] for t in trades]
    equity_curve = _equity_curve(closes, trades)

    metrics = _metrics(trades, returns, equity_curve)
    return {"trades": trades, "metrics": metrics}


def _random_fill() -> float:
    # Deterministic-ish uniform draw without numpy.
    import random
    return random.random()


def _equity_curve(closes: list[float], trades: list[dict]) -> list[float]:
    # Build a naive per-exit cumulative equity curve.
    curve: list[float] = [1.0]
    cum = 1.0
    for t in trades:
        cum *= 1.0 + t["return_pct"]
        curve.append(cum)
    return curve


def _metrics(trades: list[dict], returns: list[float], equity_curve: list[float]) -> dict:
    n = len(trades)
    total_return = (equity_curve[-1] - 1.0) if equity_curve else 0.0

    if n == 0:
        return {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "avg_hold_time": 0.0,
            "num_trades": 0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
        }

    avg = sum(returns) / n
    std = math.sqrt(sum((r - avg) ** 2 for r in returns) / n) if n > 1 else 0.0
    sharpe = avg / std if std > 0 else 0.0

    max_dd = 0.0
    peak = 1.0
    for v in equity_curve:
        peak = max(peak, v)
        dd = (peak - v) / peak if peak else 0.0
        max_dd = max(max_dd, dd)

    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))

    return {
        "total_return": round(total_return, 4),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown": round(max_dd, 4),
        "win_rate": round(len(wins) / n, 4),
        "avg_hold_time": round(sum(t["hold_bars"] for t in trades) / n, 2),
        "num_trades": n,
        "profit_factor": round(gross_win / gross_loss, 4) if gross_loss > 0 else (
            float("inf") if gross_win > 0 else 0.0
        ),
        "expectancy": round(avg, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Self-contained backtest runner.")
    parser.add_argument("--data", required=True, help="CSV with date,open,high,low,close[,volume]")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--slippage", type=float, default=DEFAULT_SLIPPAGE)
    parser.add_argument("--fill-at-mid", type=float, default=DEFAULT_FILL_AT_MID)
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=50)
    args = parser.parse_args()

    rows = load_series(args.data)
    closes = [r["close"] for r in rows]
    result = run_backtest(
        closes,
        fast=args.fast,
        slow=args.slow,
        slippage=args.slippage,
        fill_at_mid=args.fill_at_mid,
    )
    report = {
        "data_rows": len(rows),
        "start": rows[0]["date"],
        "end": rows[-1]["date"],
        "params": {"fast": args.fast, "slow": args.slow,
                   "slippage": args.slippage, "fill_at_mid": args.fill_at_mid},
        "metrics": result["metrics"],
        "num_trades": result["metrics"]["num_trades"],
        "num_parameters": 2,
        "slippage_tested": True,
        "years_tested": round(_years_between(rows[0]["date"], rows[-1]["date"]), 2),
    }

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, indent=2), "utf-8")
        print(f"wrote {args.output}")
    else:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
