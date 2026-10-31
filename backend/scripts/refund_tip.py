"""Refund a Tip in full by Telegram's charge id (Stars sellers must offer refunds).

    python -m scripts.refund_tip TELEGRAM_PAYMENT_CHARGE_ID [--test-env]

Needs BOT_TOKEN. The charge id is in payment_events (and the user's payment message).
Calls refundStarPayment first; the Tip is marked refunded only if Telegram accepts.
"""
import argparse
import sys

from sqlalchemy import Connection, func, select, update

from app import config
from app.payments import TelegramBot
from app.schema import payment_events, tips
from scripts._db import direct_engine


class RefundError(Exception):
    pass


def refund(conn: Connection, bot, charge_id: str) -> None:
    ev = conn.execute(
        select(payment_events.c.id, payment_events.c.tip_id, payment_events.c.telegram_user_id,
               payment_events.c.refunded_at)
        .where(payment_events.c.telegram_payment_charge_id == charge_id)
        .with_for_update()
    ).first()
    if ev is None:
        raise RefundError(f"no payment with charge id {charge_id}")
    if ev.refunded_at is not None:
        raise RefundError("already refunded")
    if ev.telegram_user_id is None:
        raise RefundError("payment has no Telegram user id")
    bot.refund_star_payment(ev.telegram_user_id, charge_id)
    conn.execute(update(payment_events).where(payment_events.c.id == ev.id).values(refunded_at=func.now()))
    if ev.tip_id is not None:
        conn.execute(update(tips).where(tips.c.id == ev.tip_id).values(status="refunded"))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("charge_id")
    ap.add_argument("--test-env", action="store_true", help="use Telegram's test server")
    args = ap.parse_args(argv)
    if args.test_env:
        config.TELEGRAM_TEST_ENV = True
    try:
        with direct_engine().begin() as conn:
            refund(conn, TelegramBot(config.BOT_TOKEN), args.charge_id)
    except (RefundError, RuntimeError) as e:
        sys.exit(f"error: {e}")
    print(f"refunded {args.charge_id}")


if __name__ == "__main__":
    main()
