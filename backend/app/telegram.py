"""Outgoing Telegram bot messages. Only the notifications outbox calls this."""
import requests

from app import config, payments


def send_message(telegram_id: int, body: str, button: tuple[str, str] | None = None) -> None:
    """Raises on any failure so the outbox keeps the message for a retry.
    `button` is (text, url): an inline URL button under the message."""
    payload = {"chat_id": telegram_id, "text": body}
    if button:
        payload["reply_markup"] = {"inline_keyboard": [[{"text": button[0], "url": button[1]}]]}
    resp = requests.post(
        payments.TelegramBot(config.BOT_TOKEN).method_url("sendMessage"),
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
