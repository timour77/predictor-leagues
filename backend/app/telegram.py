"""Outgoing Telegram bot messages. Only the notifications outbox calls this."""
import requests

from app import config


def send_message(telegram_id: int, body: str) -> None:
    """Raises on any failure so the outbox keeps the message for a retry."""
    resp = requests.post(
        f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage",
        json={"chat_id": telegram_id, "text": body},
        timeout=10,
    )
    resp.raise_for_status()
