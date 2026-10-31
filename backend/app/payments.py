"""Payments: Tips in Telegram Stars.

A Tip is a voluntary gift (ADR 0002): joining a League never depends on it and nothing is
refunded or paid out. The server creates the invoice, answers pre_checkout_query from its own
rows, and journals successful_payment keyed by Telegram's charge id so redelivery is a no-op.
"""
import secrets

import requests
from sqlalchemy import Connection, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import config
from app.errors import Invalid
from app.schema import payment_events, tips, users

CURRENCY = "XTR"
MIN_TIP = 1
MAX_TIP = 100_000


class TelegramBot:
    def __init__(self, token: str):
        self.token = token

    def method_url(self, method: str) -> str:
        test = "/test" if config.TELEGRAM_TEST_ENV else ""
        return f"https://api.telegram.org/bot{self.token}{test}/{method}"

    def refund_star_payment(self, user_id: int, charge_id: str) -> None:
        r = requests.post(
            self.method_url("refundStarPayment"),
            json={"user_id": user_id, "telegram_payment_charge_id": charge_id},
            timeout=10,
        )
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"refundStarPayment failed: {data.get('description')}")

    def create_invoice_link(self, *, title: str, description: str, payload: str, amount: int) -> str:
        r = requests.post(
            self.method_url("createInvoiceLink"),
            json={
                "title": title,
                "description": description,
                "payload": payload,
                "currency": CURRENCY,
                "prices": [{"label": title, "amount": amount}],
            },
            timeout=8,
        )
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"createInvoiceLink failed: {data.get('description')}")
        return data["result"]


def create_tip(conn: Connection, bot, user_id: int, amount: int) -> dict:
    if not MIN_TIP <= amount <= MAX_TIP:
        raise Invalid(f"Tip must be between {MIN_TIP} and {MAX_TIP} Stars")
    payload = secrets.token_urlsafe(16)
    tip_id = conn.execute(
        insert(tips).values(user_id=user_id, amount=amount, payload=payload).returning(tips.c.id)
    ).scalar_one()
    url = bot.create_invoice_link(
        title="Tip", description="Thank you for supporting Predictor Leagues", payload=payload, amount=amount
    )
    return {"id": tip_id, "payload": payload, "invoice_url": url}


def pre_checkout_answer(conn: Connection, query: dict) -> dict:
    """Approve only a pending Tip whose payer, amount and currency match our row. DB reads only."""
    answer = {"method": "answerPreCheckoutQuery", "pre_checkout_query_id": query["id"]}
    row = conn.execute(
        select(tips.c.amount, tips.c.status, users.c.telegram_id)
        .join(users, users.c.id == tips.c.user_id)
        .where(tips.c.payload == query.get("invoice_payload"))
    ).first()
    ok = (
        row is not None
        and row.status == "pending"
        and row.amount == query.get("total_amount")
        and query.get("currency") == CURRENCY
        and row.telegram_id == (query.get("from") or {}).get("id")
    )
    if ok:
        return {**answer, "ok": True}
    return {**answer, "ok": False, "error_message": "This tip is no longer valid"}


def record_payment(conn: Connection, message: dict) -> None:
    """Journal a successful_payment. The journal is the source of truth: a payment for an
    unknown payload is still recorded (money moved) with tip_id NULL."""
    sp = message["successful_payment"]
    tip = conn.execute(select(tips.c.id).where(tips.c.payload == sp.get("invoice_payload"))).first()
    inserted = conn.execute(
        pg_insert(payment_events)
        .values(
            telegram_payment_charge_id=sp["telegram_payment_charge_id"],
            provider_payment_charge_id=sp.get("provider_payment_charge_id"),
            tip_id=tip.id if tip else None,
            telegram_user_id=(message.get("from") or {}).get("id"),
            amount=sp["total_amount"],
            currency=sp["currency"],
            raw=sp,
        )
        .on_conflict_do_nothing(index_elements=["telegram_payment_charge_id"])
        .returning(payment_events.c.id)
    ).first()
    if inserted and tip:
        conn.execute(update(tips).where(tips.c.id == tip.id).values(status="paid"))
