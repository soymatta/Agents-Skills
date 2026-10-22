"""Telegram Bot API client — full coverage of messaging methods.

Usage:
    from telegram_bot import TelegramBot
    bot = TelegramBot()
    bot.send_message(chat_id, "Hello!")
    bot.send_photo(chat_id, "path/to/image.jpg", caption="Look!")
    bot.send_document(chat_id, "path/to/report.pdf")
"""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

log = logging.getLogger("telegram_bot")


class TelegramError(Exception):
    """Raised when the Telegram API returns a non-OK status."""


class TelegramBot:
    """Minimal Telegram Bot API wrapper. Reads credentials from environment."""

    BASE = "https://api.telegram.org/bot{token}/"

    def __init__(
        self,
        token: str | None = None,
        chat_id: str | None = None,
        *,
        session: requests.Session | None = None,
    ) -> None:
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.default_chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        self._session = session or requests.Session()
        if not self.token:
            log.warning("TELEGRAM_BOT_TOKEN not set — bot will be a no-op")

    # ------------------------------------------------------------------
    # Low-level
    # ------------------------------------------------------------------

    @property
    def _api_url(self) -> str:
        return self.BASE.format(token=self.token)

    def _call(
        self,
        method: str,
        *,
        params: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        if not self.token:
            log.debug("telegram: no token, skipping %s", method)
            return {"ok": False, "description": "No token configured"}

        url = urljoin(self._api_url, method)
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                resp = self._session.post(
                    url,
                    data=params,
                    files=files,
                    timeout=30,
                )
                data: dict[str, Any] = resp.json()
            except requests.RequestException as exc:
                last_error = exc
                log.warning("telegram: attempt %d/%d failed: %s", attempt + 1, retries, exc)
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                continue

            if not data.get("ok"):
                desc = data.get("description", "unknown error")
                if "retry after" in desc.lower():
                    wait = data.get("parameters", {}).get("retry_after", 5)
                    log.warning("telegram: rate limited, waiting %ds", wait)
                    time.sleep(wait + 1)
                    continue
                raise TelegramError(f"{method}: {desc}")

            return data

        raise TelegramError(f"{method}: all retries exhausted") from last_error

    def _resolve_chat_id(self, chat_id: str | int | None = None) -> str | int:
        return chat_id if chat_id is not None else self.default_chat_id

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def send_message(
        self,
        text: str,
        chat_id: str | int | None = None,
        *,
        parse_mode: str | None = "MarkdownV2",
        disable_web_page_preview: bool = True,
        disable_notification: bool = False,
        reply_to_message_id: int | None = None,
        reply_markup: dict | None = None,
    ) -> dict[str, Any]:
        """Send a text message.

        parse_mode: "MarkdownV2" | "HTML" | None.
        """
        cid = self._resolve_chat_id(chat_id)
        params: dict[str, Any] = {
            "chat_id": cid,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
            "disable_notification": disable_notification,
        }
        if parse_mode:
            params["parse_mode"] = parse_mode
        if reply_to_message_id is not None:
            params["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        return self._call("sendMessage", params=params)

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------

    def _resolve_media(self, media: str | Path | bytes) -> tuple[str, Any]:
        """Return (field_value, file_tuple_or_None)."""
        if isinstance(media, bytes):
            return ("attach://file", ("file", media))
        p = Path(media)
        if p.exists():
            mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            return ("attach://file", ("file", p.read_bytes(), mime))
        return (str(media), None)  # URL or file_id

    def send_photo(
        self,
        photo: str | Path | bytes,
        chat_id: str | int | None = None,
        *,
        caption: str | None = None,
        parse_mode: str | None = "MarkdownV2",
        disable_notification: bool = False,
        reply_markup: dict | None = None,
    ) -> dict[str, Any]:
        cid = self._resolve_chat_id(chat_id)
        photo_val, file_tuple = self._resolve_media(photo)
        params: dict[str, Any] = {"chat_id": cid, "photo": photo_val}
        if caption:
            params["caption"] = caption
        if parse_mode:
            params["parse_mode"] = parse_mode
        if disable_notification:
            params["disable_notification"] = True
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        files = {"photo": file_tuple} if file_tuple else None
        return self._call("sendPhoto", params=params, files=files)

    def send_document(
        self,
        document: str | Path | bytes,
        chat_id: str | int | None = None,
        *,
        caption: str | None = None,
        parse_mode: str | None = "MarkdownV2",
        disable_notification: bool = False,
        thumbnail: str | Path | bytes | None = None,
        reply_markup: dict | None = None,
    ) -> dict[str, Any]:
        cid = self._resolve_chat_id(chat_id)
        doc_val, doc_file = self._resolve_media(document)
        params: dict[str, Any] = {"chat_id": cid, "document": doc_val}
        if caption:
            params["caption"] = caption
        if parse_mode:
            params["parse_mode"] = parse_mode
        if disable_notification:
            params["disable_notification"] = True
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        files: dict[str, Any] = {"document": doc_file} if doc_file else {}
        if thumbnail:
            _, thumb_file = self._resolve_media(thumbnail)
            if thumb_file:
                files["thumbnail"] = thumb_file
        return self._call("sendDocument", params=params, files=files or None)

    def send_video(
        self,
        video: str | Path | bytes,
        chat_id: str | int | None = None,
        *,
        caption: str | None = None,
        parse_mode: str | None = "MarkdownV2",
        duration: int | None = None,
        width: int | None = None,
        height: int | None = None,
        supports_streaming: bool = False,
        disable_notification: bool = False,
        thumbnail: str | Path | bytes | None = None,
        reply_markup: dict | None = None,
    ) -> dict[str, Any]:
        cid = self._resolve_chat_id(chat_id)
        vid_val, vid_file = self._resolve_media(video)
        params: dict[str, Any] = {"chat_id": cid, "video": vid_val}
        if caption:
            params["caption"] = caption
        if parse_mode:
            params["parse_mode"] = parse_mode
        if duration:
            params["duration"] = duration
        if width:
            params["width"] = width
        if height:
            params["height"] = height
        if supports_streaming:
            params["supports_streaming"] = True
        if disable_notification:
            params["disable_notification"] = True
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        files: dict[str, Any] = {"video": vid_file} if vid_file else {}
        if thumbnail:
            _, thumb_file = self._resolve_media(thumbnail)
            if thumb_file:
                files["thumbnail"] = thumb_file
        return self._call("sendVideo", params=params, files=files or None)

    def send_audio(
        self,
        audio: str | Path | bytes,
        chat_id: str | int | None = None,
        *,
        caption: str | None = None,
        parse_mode: str | None = None,
        duration: int | None = None,
        performer: str | None = None,
        title: str | None = None,
        disable_notification: bool = False,
        reply_markup: dict | None = None,
    ) -> dict[str, Any]:
        cid = self._resolve_chat_id(chat_id)
        aud_val, aud_file = self._resolve_media(audio)
        params: dict[str, Any] = {"chat_id": cid, "audio": aud_val}
        if caption:
            params["caption"] = caption
        if parse_mode:
            params["parse_mode"] = parse_mode
        if duration:
            params["duration"] = duration
        if performer:
            params["performer"] = performer
        if title:
            params["title"] = title
        if disable_notification:
            params["disable_notification"] = True
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        files = {"audio": aud_file} if aud_file else None
        return self._call("sendAudio", params=params, files=files)

    def send_media_group(
        self,
        media: list[dict[str, Any]],
        chat_id: str | int | None = None,
        *,
        disable_notification: bool = False,
    ) -> dict[str, Any]:
        """Send an album (group of photos/videos).

        Each entry: {"type": "photo", "media": "file_id|URL|path"}
        """
        cid = self._resolve_chat_id(chat_id)
        files: dict[str, Any] = {}
        processed: list[dict[str, Any]] = []
        for i, item in enumerate(media):
            m = dict(item)
            val, file_tuple = self._resolve_media(m["media"])
            if file_tuple:
                key = f"file_{i}"
                m["media"] = f"attach://{key}"
                files[key] = file_tuple
            else:
                m["media"] = val
            processed.append(m)
        params: dict[str, Any] = {
            "chat_id": cid,
            "media": json.dumps(processed),
        }
        if disable_notification:
            params["disable_notification"] = True
        return self._call("sendMediaGroup", params=params, files=files or None)

    # ------------------------------------------------------------------
    # Message editing / deletion
    # ------------------------------------------------------------------

    def edit_message_text(
        self,
        text: str,
        chat_id: str | int | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
        *,
        parse_mode: str | None = "MarkdownV2",
        reply_markup: dict | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"text": text}
        if chat_id:
            params["chat_id"] = self._resolve_chat_id(chat_id)
        if message_id is not None:
            params["message_id"] = message_id
        if inline_message_id:
            params["inline_message_id"] = inline_message_id
        if parse_mode:
            params["parse_mode"] = parse_mode
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        return self._call("editMessageText", params=params)

    def edit_message_caption(
        self,
        caption: str,
        chat_id: str | int | None = None,
        message_id: int | None = None,
        inline_message_id: str | None = None,
        *,
        parse_mode: str | None = "MarkdownV2",
        reply_markup: dict | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"caption": caption}
        if chat_id:
            params["chat_id"] = self._resolve_chat_id(chat_id)
        if message_id is not None:
            params["message_id"] = message_id
        if inline_message_id:
            params["inline_message_id"] = inline_message_id
        if parse_mode:
            params["parse_mode"] = parse_mode
        if reply_markup:
            params["reply_markup"] = json.dumps(reply_markup)
        return self._call("editMessageCaption", params=params)

    def delete_message(
        self,
        chat_id: str | int,
        message_id: int,
    ) -> dict[str, Any]:
        return self._call("deleteMessage", params={
            "chat_id": self._resolve_chat_id(chat_id),
            "message_id": message_id,
        })

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    def set_webhook(
        self,
        url: str,
        *,
        certificate: str | Path | None = None,
        max_connections: int = 40,
        allowed_updates: list[str] | None = None,
        secret_token: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "url": url,
            "max_connections": max_connections,
        }
        files: dict[str, Any] = {}
        if certificate:
            cert_path = Path(certificate)
            if cert_path.exists():
                files["certificate"] = ("certificate.pub", cert_path.read_bytes())
        if allowed_updates:
            params["allowed_updates"] = json.dumps(allowed_updates)
        if secret_token:
            params["secret_token"] = secret_token
        return self._call("setWebhook", params=params, files=files or None)

    def remove_webhook(self) -> dict[str, Any]:
        return self._call("deleteWebhook")

    def get_webhook_info(self) -> dict[str, Any]:
        return self._call("getWebhookInfo")

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def get_updates(
        self,
        offset: int | None = None,
        limit: int = 100,
        timeout: int = 30,
        allowed_updates: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "offset": offset or 0,
            "limit": limit,
            "timeout": timeout,
        }
        if allowed_updates:
            params["allowed_updates"] = json.dumps(allowed_updates)
        data = self._call("getUpdates", params=params)
        return data.get("result", [])

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def get_me(self) -> dict[str, Any]:
        """Verify the bot token and get bot info."""
        return self._call("getMe")

    def send_chat_action(
        self,
        action: str,
        chat_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Send a chat action (typing, upload_photo, etc.).

        Common actions: typing, upload_photo, upload_document, upload_video,
                       record_audio, record_video, find_location.
        """
        cid = self._resolve_chat_id(chat_id)
        return self._call("sendChatAction", params={
            "chat_id": cid,
            "action": action,
        })

    # ------------------------------------------------------------------
    # Convenience wrappers for notifications
    # ------------------------------------------------------------------

    def notify(
        self,
        message: str,
        chat_id: str | int | None = None,
        *,
        parse_mode: str | None = "MarkdownV2",
    ) -> dict[str, Any]:
        """Shortcut for send_message with silent notification."""
        return self.send_message(
            message,
            chat_id=chat_id,
            parse_mode=parse_mode,
            disable_notification=False,
        )

    def notify_silent(
        self,
        message: str,
        chat_id: str | int | None = None,
        *,
        parse_mode: str | None = "MarkdownV2",
    ) -> dict[str, Any]:
        """Shortcut for send_message with silent notification."""
        return self.send_message(
            message,
            chat_id=chat_id,
            parse_mode=parse_mode,
            disable_notification=True,
        )

    def notify_error(
        self,
        error: str,
        chat_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Send an error notification with HTML formatting."""
        return self.send_message(
            f"\u26a0\ufe0f *ERROR*: {error}",
            chat_id=chat_id,
            parse_mode="MarkdownV2",
            disable_notification=False,
        )
