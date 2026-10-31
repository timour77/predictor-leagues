import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.telegram_auth import InitDataError, verify_init_data

BOT_TOKEN = "123456:TEST-TOKEN"


def sign(fields: dict, bot_token: str = BOT_TOKEN) -> str:
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    fields = {**fields, "hash": hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()}
    return urlencode(fields)


def fields(auth_date=None, user=None):
    return {
        "auth_date": str(int(time.time() if auth_date is None else auth_date)),
        "query_id": "AAH",
        "user": json.dumps(user or {"id": 42, "first_name": "Ann", "username": "ann"}),
    }


def test_valid_init_data_returns_user():
    user = verify_init_data(sign(fields()), BOT_TOKEN, max_age=60)
    assert user["id"] == 42 and user["username"] == "ann"


def test_tampered_payload_rejected():
    raw = sign(fields()).replace("Ann", "Eve")
    with pytest.raises(InitDataError):
        verify_init_data(raw, BOT_TOKEN, max_age=60)


def test_wrong_bot_token_rejected():
    with pytest.raises(InitDataError):
        verify_init_data(sign(fields(), "999:OTHER"), BOT_TOKEN, max_age=60)


def test_missing_hash_rejected():
    with pytest.raises(InitDataError):
        verify_init_data("auth_date=1&user=%7B%7D", BOT_TOKEN, max_age=60)


def test_expired_auth_date_rejected():
    with pytest.raises(InitDataError, match="expired"):
        verify_init_data(sign(fields(auth_date=time.time() - 120)), BOT_TOKEN, max_age=60)


def test_future_auth_date_rejected():
    with pytest.raises(InitDataError):
        verify_init_data(sign(fields(auth_date=time.time() + 3600)), BOT_TOKEN, max_age=60)


def test_missing_user_rejected():
    f = fields()
    del f["user"]
    with pytest.raises(InitDataError):
        verify_init_data(sign(f), BOT_TOKEN, max_age=60)
