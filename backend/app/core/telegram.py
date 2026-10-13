"""Telegram bot notifications for new leads.

No-op when ``telegram_bot_token``/``telegram_chat_id`` are unset, so local and
test environments don't need a bot. Network/HTTP errors are swallowed and
logged — a failed notification must never break lead submission.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def send_message(text: str) -> None:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info("Telegram not configured; skipping notification")
        return

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
    except Exception:  # noqa: BLE001 - notification is best-effort
        logger.exception("Failed to send Telegram notification")
