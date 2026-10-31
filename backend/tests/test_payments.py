import pytest
from sqlalchemy import text

from app import config
from app.db import get_engine
from tests.test_api import header

SECRET = "wh-secret"
WH = "/api/telegram/webhook"
USER = {"id": 8001, "first_name": "Tipper"}


class FakeBot:
    def __init__(self):
        self.calls = []

    def create_invoice_link(self, **kw):
        self.calls.append(kw)
        return "https://t.me/$invoice-" + kw["payload"]


@pytest.fixture
def pay(client, migrated_db, monkeypatch):
    from app.routers import payments as router
    from main import app

    monkeypatch.setattr(config, "TELEGRAM_WEBHOOK_SECRET", SECRET)
    with get_engine().begin() as c:
        c.execute(text("TRUNCATE users, tips, payment_events RESTART IDENTITY CASCADE"))
    bot = FakeBot()
    app.dependency_overrides[router.get_bot] = lambda: bot
    client.bot = bot
    yield client
    app.dependency_overrides.clear()


def wh(secret=SECRET):
    return {"X-Telegram-Bot-Api-Secret-Token": secret}


def new_tip(c, amount=50):
    r = c.post("/api/tips", json={"amount": amount}, headers=header(USER))
    assert r.status_code == 201, r.text
    return {**r.json(), "payload": rows("SELECT payload FROM tips ORDER BY id DESC LIMIT 1")[0]["payload"]}


def rows(sql):
    with get_engine().begin() as c:
        return c.execute(text(sql)).mappings().all()


def pre_checkout(payload, amount=50, uid=8001, currency="XTR"):
    return {"update_id": 1, "pre_checkout_query": {
        "id": "pcq1", "from": {"id": uid}, "currency": currency,
        "total_amount": amount, "invoice_payload": payload}}


def paid(payload, charge="tg-charge-1", amount=50, uid=8001):
    return {"update_id": 2, "message": {"from": {"id": uid}, "successful_payment": {
        "currency": "XTR", "total_amount": amount, "invoice_payload": payload,
        "telegram_payment_charge_id": charge, "provider_payment_charge_id": "prov-1"}}}


def test_tip_creates_xtr_invoice(pay):
    body = new_tip(pay, 50)
    assert body["invoice_url"].startswith("https://t.me/")
    call = pay.bot.calls[0]
    assert call["amount"] == 50 and call["payload"]
    assert rows("SELECT status, amount FROM tips")[0] == {"status": "pending", "amount": 50}


@pytest.mark.parametrize("amount", [0, -5, 100001])
def test_tip_amount_bounds(pay, amount):
    r = pay.post("/api/tips", json={"amount": amount}, headers=header(USER))
    assert r.status_code == 422
    assert not pay.bot.calls


def test_tip_requires_auth(pay):
    assert pay.post("/api/tips", json={"amount": 5}).status_code == 401


def test_webhook_rejects_bad_or_missing_secret(pay):
    assert pay.post(WH, json={"update_id": 1}).status_code == 401
    assert pay.post(WH, json={"update_id": 1}, headers=wh("nope")).status_code == 401


def test_webhook_closed_when_secret_unconfigured(pay, monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_WEBHOOK_SECRET", "")
    assert pay.post(WH, json={"update_id": 1}, headers=wh("")).status_code == 401


def test_pre_checkout_approved_for_known_pending_tip(pay):
    tip = new_tip(pay)
    r = pay.post(WH, json=pre_checkout(tip["payload"]), headers=wh())
    assert r.json() == {"method": "answerPreCheckoutQuery", "pre_checkout_query_id": "pcq1", "ok": True}


@pytest.mark.parametrize("kw", [{"amount": 51}, {"uid": 9}, {"currency": "USD"}])
def test_pre_checkout_declined_on_mismatch(pay, kw):
    tip = new_tip(pay)
    r = pay.post(WH, json=pre_checkout(tip["payload"], **kw), headers=wh()).json()
    assert r["ok"] is False and r["error_message"]


def test_pre_checkout_declined_for_unknown_payload(pay):
    assert pay.post(WH, json=pre_checkout("nope"), headers=wh()).json()["ok"] is False


def test_successful_payment_is_journaled_and_tip_marked_paid(pay):
    tip = new_tip(pay)
    assert pay.post(WH, json=paid(tip["payload"]), headers=wh()).status_code == 200
    ev = rows("SELECT * FROM payment_events")
    assert len(ev) == 1
    assert ev[0]["telegram_payment_charge_id"] == "tg-charge-1" and ev[0]["amount"] == 50
    assert rows("SELECT status FROM tips")[0]["status"] == "paid"


def test_successful_payment_redelivery_is_idempotent(pay):
    tip = new_tip(pay)
    for _ in range(3):
        assert pay.post(WH, json=paid(tip["payload"]), headers=wh()).status_code == 200
    assert len(rows("SELECT 1 FROM payment_events")) == 1


def test_successful_payment_for_unknown_payload_still_journaled(pay):
    assert pay.post(WH, json=paid("ghost"), headers=wh()).status_code == 200
    ev = rows("SELECT tip_id FROM payment_events")
    assert len(ev) == 1 and ev[0]["tip_id"] is None


def test_charge_id_is_unique_in_db(pay):
    tip = new_tip(pay)
    pay.post(WH, json=paid(tip["payload"]), headers=wh())
    with pytest.raises(Exception):
        with get_engine().begin() as c:
            c.execute(text("INSERT INTO payment_events (telegram_payment_charge_id, amount, currency, raw) "
                           "VALUES ('tg-charge-1', 1, 'XTR', '{}')"))


def test_unrelated_updates_are_acknowledged(pay):
    assert pay.post(WH, json={"update_id": 5, "message": {"text": "hi"}}, headers=wh()).status_code == 200
