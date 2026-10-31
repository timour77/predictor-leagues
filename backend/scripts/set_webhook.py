"""Register the Telegram webhook and print getWebhookInfo.

    python -m scripts.set_webhook [--test-env] [--drop-pending]

Needs BOT_TOKEN, TELEGRAM_WEBHOOK_SECRET and PUBLIC_URL (https origin of the deployment).
"""
import argparse
import json
import re
import sys

import requests

from app import config
from app.payments import TelegramBot

ALLOWED_UPDATES = ["message", "pre_checkout_query"]


def params(public_url: str, secret: str) -> dict:
    if not public_url.startswith("https://"):
        raise ValueError("PUBLIC_URL must be an https URL")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", secret):
        raise ValueError("TELEGRAM_WEBHOOK_SECRET must be 1-256 characters of A-Z a-z 0-9 _ -")
    return {"url": f"{public_url}/api/telegram/webhook", "secret_token": secret,
            "allowed_updates": ALLOWED_UPDATES}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--test-env", action="store_true", help="use Telegram's test server")
    ap.add_argument("--drop-pending", action="store_true", help="discard queued updates")
    args = ap.parse_args(argv)
    if args.test_env:
        config.TELEGRAM_TEST_ENV = True
    if not config.BOT_TOKEN:
        sys.exit("error: BOT_TOKEN is not set")
    try:
        body = params(config.PUBLIC_URL, config.TELEGRAM_WEBHOOK_SECRET)
    except ValueError as e:
        sys.exit(f"error: {e}")
    bot = TelegramBot(config.BOT_TOKEN)
    r = requests.post(bot.method_url("setWebhook"), json={**body, "drop_pending_updates": args.drop_pending},
                      timeout=10).json()
    print("setWebhook:", json.dumps(r))
    if not r.get("ok"):
        sys.exit(1)
    info = requests.get(bot.method_url("getWebhookInfo"), timeout=10).json()
    print("getWebhookInfo:", json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
