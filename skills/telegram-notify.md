---
name: telegram-notify
description: Use when the user wants to receive Telegram notifications for project events such as roadmap iterations, backtest completions, pipeline runs, and errors. Triggers on keywords like "notificar", "notify", "telegram", "alerta", "alert", "notificacion", "mensaje telegram", "bot telegram". This skill sends concise, formatted Telegram messages for key project events using credentials from .env. It never blocks execution — failures are logged as warnings and the main process continues.
compatibility: Provides notification service used by roadmaps, backtest-run, and research-pipeline. Requires .env file with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
---

# Telegram Notify

Send Telegram notifications for project events. Never ask the user. Credentials from `.env`. Las notificaciones asincronas son esenciales para procesos autonomos de larga duracion (backtests, roadmaps, pipelines) porque permiten al usuario desentenderse y recibir actualizaciones solo cuando hay resultados o errores. Nunca bloquean el flujo principal.

**Otros skills dependen de este** — cuando instalas `backtest-run`, `roadmaps` o `research-pipeline`, Telegram Notify se activa automaticamente para que recibas notificaciones sin tener que mirar la terminal.

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
