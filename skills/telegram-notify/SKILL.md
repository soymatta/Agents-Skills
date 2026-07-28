---
name: telegram-notify
description: Use when the user wants to send Telegram messages from their project — notifications, alerts, file uploads, or status updates. Triggers on keywords like "notificar", "notify", "telegram", "alerta", "alert", "notificacion", "mensaje telegram", "bot telegram", "enviar telegram", "send telegram". This skill provides a complete Telegram Bot API client with support for text, photos, documents, videos, audio, media groups, webhooks, and polling. It never blocks execution — failures are logged as warnings and the main process continues.
compatibility: Provides notification service used by roadmaps, backtest-run, and research-pipeline. Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env or environment. Bundles telegram_bot.py with full Bot API coverage.
---

# Telegram Notify

Send Telegram notifications for project events using the bundled `telegram_bot.py` module. Never ask the user. Credentials from `.env`.

## When to use
- User wants to send Telegram messages from their project
- Keywords: "notificar", "notify", "telegram", "alerta", "alert", "notificacion", "mensaje telegram", "bot telegram", "enviar telegram", "send telegram"
- Need to send alerts, status updates, file uploads, or completion notifications
- Other skills (backtest-run, research-pipeline, roadmaps) trigger notifications automatically

## When NOT to use
- User wants to create or manage a Telegram bot (use BotFather directly)
- No TELEGRAM_BOT_TOKEN configured and user doesn't provide one
- User wants to read incoming Telegram messages (this skill sends, not receives)
- Notifications are not needed for the current task

## Setup

### Requirements

```bash
pip install requests
```

### Credentials

Create a `.env` file in the project root:

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=-1001234567890
```

Or set environment variables directly.

**Getting credentials:**

1. Talk to [@BotFather](https://t.me/BotFather) on Telegram to create a bot and get a token
2. Add the bot to your chat/channel
3. Send a message to the chat
4. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` to find your chat_id

## Usage

```python
from telegram_notify.scripts.telegram_bot import TelegramBot

bot = TelegramBot()

# Simple notification
bot.notify("Backtest complete! Sharpe: 1.8")

# Error alert
bot.notify_error("Pipeline crashed: out of memory")

# With files
bot.send_photo("chart.png", caption="Equity curve")
bot.send_document("report.pdf")
```

## Scripts

| Script | Args | Description |
|--------|------|-------------|
| `scripts/telegram_bot.py` | — | Full Telegram Bot API client module |

### Bundled script methods

The included `scripts/telegram_bot.py` covers the full Telegram Bot API:

| Method                     | What it does                                |
| -------------------------- | ------------------------------------------- |
| `send_message()`         | Text with MarkdownV2/HTML formatting        |
| `send_photo()`           | Image with optional caption                 |
| `send_document()`        | Any file with caption + thumbnail           |
| `send_video()`           | Video with streaming support                |
| `send_audio()`           | Audio with performer/title metadata         |
| `send_media_group()`     | Album of photos/videos                      |
| `edit_message_text()`    | Update sent message text                    |
| `edit_message_caption()` | Update sent message caption                 |
| `delete_message()`       | Remove a sent message                       |
| `set_webhook()`          | Register a webhook URL for incoming updates |
| `remove_webhook()`       | Remove the webhook                          |
| `get_webhook_info()`     | Check current webhook status                |
| `get_updates()`          | Poll for new messages (long polling)        |
| `send_chat_action()`     | Show typing/uploading indicator             |
| `get_me()`               | Verify bot token                            |

Each method accepts `chat_id` or falls back to `TELEGRAM_CHAT_ID`.

### Auto-retry

The client retries on network errors and rate limits (429) with exponential backoff. Failed notifications are logged as warnings — they never block the main execution flow.

## Output format
- Telegram message delivered to configured chat_id
- Return value from Telegram Bot API (message_id on success)
- Warnings logged on failure (never blocks execution)

## Dependencies
```bash
pip install requests
```

## Error handling
- **Missing .env file:** Auto-create `.env` with placeholder values and report to user
- **Invalid bot token:** Log warning, do not block execution
- **Chat not found:** Log warning, suggest adding bot to chat first
- **Rate limited (429):** Auto-retry with exponential backoff
- **Network error:** Auto-retry up to 3 times, then log warning and continue
- **Message too long (>4000 chars):** Use `send_document()` instead

## File structure
```
telegram-notify/
├── SKILL.md
└── scripts/
    ├── __init__.py
    └── telegram_bot.py
```

## Integration with other skills

This skill acts as a notification backbone for the project. Other skills use it:

| Skill                 | When it notifies                                  |
| --------------------- | ------------------------------------------------- |
| `backtest-run`      | On backtest completion (Sharpe, return, drawdown) |
| `backtest-validate` | On validation verdict (Deploy/Refine/Abandon)     |
| `research-pipeline` | On pipeline step completion or error              |
| `roadmaps`          | On roadmap step completion                        |

When these skills are active, notifications are sent automatically using:

```python
from telegram_notify.scripts.telegram_bot import TelegramBot
bot = TelegramBot()
bot.notify("Backtest done: Sharpe 2.1, Return +15%")
```

## Restrictions
- Max 4000 chars per message. Use `send_document()` for longer content.
- Key metrics only. `key: value` format
- Do NOT include bot name — not needed
- Use the convenience methods: `notify()`, `notify_silent()`, `notify_error()`
- Always notify on completion of long-running tasks
- Silent on failure: log as warning, never block execution
- Auto-create `.env` with placeholder if missing and report it to the user
- **DO NOT** block main execution flow on notification failure
- **DO NOT** store bot token in code — always use .env or environment variables
