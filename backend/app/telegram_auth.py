"""Telegram Mini App initData verification (stateless; run on every request)."""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

CLOCK_SKEW_SECONDS = 60


class InitDataError(ValueError):
    pass


def verify_init_data(init_data: str, bot_token: str, max_age: int) -> dict:
    """Check the HMAC and auth_date of raw initData and return the Telegram user dict."""
    if not bot_token:
        raise InitDataError("bot token not configured")
    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = fields.pop("hash", "")
    if not received_hash:
        raise InitDataError("missing hash")

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("bad signature")

    try:
        age = time.time() - int(fields["auth_date"])
    except (KeyError, ValueError):
        raise InitDataError("missing auth_date")
    if age > max_age:
        raise InitDataError("expired")
    if age < -CLOCK_SKEW_SECONDS:
        raise InitDataError("auth_date in the future")

    try:
        user = json.loads(fields["user"])
        user["id"] = int(user["id"])
    except (KeyError, ValueError, TypeError):
        raise InitDataError("missing user")
    return user
