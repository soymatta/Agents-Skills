---
name: telegram-notify
description: Sends Telegram notifications for project events — roadmap, backtest, pipeline, errors.
---

# Telegram Notify

Send Telegram notifications for project events. Never ask the user. Credentials from `.env`.

## Events

| Event | Trigger | Format |
|---|---|---|
| Roadmap iteration | Step 4 (NOTIFY) | `Roadmap #{n}: {summary}` |
| Backtest complete | After `run_shortterm_backtest()` | `Backtest: {name} \| Precision: {p} \| Return: {r} \| Sharpe: {s} \| Signals: {n}` |
| Pipeline run | After `monitor.run_once()` | `Pipeline: signals={n} precision={p} trades={t}` |
| Error | Exception in pipeline/backtest | `ERROR: {description}` |

## Rules
- Max 4000 chars. Key metrics only. `key: value` format
- Do NOT include "PolymarketBot:" — prepended automatically
- Use `send_notification()`, `notify_backtest_result()`, `notify_roadmap_complete()`, `notify_pipeline_run()`
- Always send on roadmap/backtest completion
- Silent on failure: log as warning, never block execution
