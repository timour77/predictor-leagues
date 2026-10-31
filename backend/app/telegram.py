"""Outgoing Telegram bot messages. Only the notifications outbox calls this."""
import requests

from app import config, payments


def send_message(telegram_id: int, body: str) -> None:
    """Raises on any failure so the outbox keeps the message for a retry."""
    resp = requests.post(
        payments.TelegramBot(config.BOT_TOKEN).method_url("sendMessage"),
        json={"chat_id": telegram_id, "text": body},
        timeout=10,
    )
    resp.raise_for_status()
