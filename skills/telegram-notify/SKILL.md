---
name: telegram-notify
description: >-
  Sends Telegram messages from projects — notifications, alerts, file uploads, status updates. Full Telegram
  Bot API client (text MarkdownV2/HTML, photos, documents, videos, audio, media groups, webhooks, polling,
  edit/delete) with auto-retry and exponential backoff. Never blocks execution (failures log as warnings).
  Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (real values, never placeholders). Notification backbone
  for backtest-run, backtest-validate, research-pipeline, and roadmaps. Use when the user wants to send/notify
  via Telegram or upload a file. Triggers: "telegram", "notificar", "notify", "alerta", "alert",
  "enviar telegram", "send message".
compatibility: Provides notification service used by roadmaps, backtest-run, and research-pipeline. Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env or environment.
---

# Telegram Notify

Send Telegram notifications for project events using the bundled `telegram_bot.py` module. Never ask the user. Credentials from `.env`.

## When to use
- User wants to send Telegram messages from their project
- Keywords: "notificar", "notify", "telegram", "alerta", "alert", "notificacion", "mensaje telegram", "bot telegram", "enviar telegram", "send telegram", "send message", "upload file telegram", "sendDocument", "status update telegram", "backtest notification", "research notification"
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

Set these as **real** values — either in a `.env` file in the project root (loaded
by your assistant's env loader) or as environment variables. **Never** auto-create
a `.env` with placeholder values: writing fake credentials makes every downstream
send fail silently and teaches the pipeline to look healthy when it is not.

```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=-1001234567890
```

**Getting real credentials:**
1. Talk to [@BotFather](https://t.me/BotFather) on Telegram to create a bot and get a token
2. Add the bot to your chat/channel
3. Send a message to the chat
4. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` to find your chat_id

If the token/chat_id are missing or empty, **fail fast**: log a clear message
with the setup instructions above and return a failure. Do not invent credentials.

## Usage

The `telegram_notify.scripts.telegram_bot` import resolves when the repo root is
importable (e.g. `pip install -e .` from the repo, or the repo being on
`PYTHONPATH`). If you're launched from inside the skill directory, import the
module directly instead:
`from telegram_bot import TelegramBot` with `scripts/` on the path.

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
- **Token/chat_id missing or empty:** fail fast with clear setup instructions (BotFather + getUpdates). Never auto-create placeholder `.env`.
- **Invalid bot token:** log a warning, do not block execution.
- **Chat not found:** log a warning, suggest adding the bot to the chat first.
- **Rate limited (429):** auto-retry with exponential backoff.
- **Network error:** auto-retry up to 3 times, then log a warning and continue.
- **Message too long (>4000 chars):** truncate at 4000 and append `…`, or use `send_document()` for full content.
- **Corrupt/partial credentials:** treat empty token or empty chat_id as distinct failure states and report which one is missing.

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
- Max 4000 chars per message. Truncate at 4000 + `…`, or use `send_document()` for longer content.
- Key metrics only. `key: value` format
- Do NOT include bot name — not needed
- Use the convenience methods: `notify()`, `notify_silent()`, `notify_error()`
- Always notify on completion of long-running tasks
- Silent on failure: log as warning, never block execution
- **DO NOT** auto-create `.env` or any file with placeholder credentials — fail fast with setup instructions instead
- **DO NOT** block main execution flow on notification failure
- **DO NOT** store bot token in code — always use `.env` or environment variables
