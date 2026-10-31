"""Erase a user's personal data on request (Bot Developer Terms; described in the privacy policy).

    python -m scripts.delete_user TELEGRAM_ID

Removes name, username, photo, Predictions and queued bot messages, and detaches the Telegram id.
What stays, anonymously: League memberships, final standings and Trophies (other Members' results
depend on them), and Tip/payment records (kept for refunds and disputes).
"""
import argparse
import sys

from sqlalchemy import Connection, delete, select, update

from app.schema import notifications, predictions, users
from scripts._db import direct_engine

DELETED_NAME = "Deleted user"


def delete_user(conn: Connection, telegram_id: int) -> dict:
    uid = conn.execute(select(users.c.id).where(users.c.telegram_id == telegram_id)).scalar()
    if uid is None:
        return {"deleted": False}
    conn.execute(delete(predictions).where(predictions.c.user_id == uid))
    conn.execute(delete(notifications).where(notifications.c.user_id == uid))
    # A negative id can never collide with a real Telegram id and frees the old one for a fresh account.
    conn.execute(update(users).where(users.c.id == uid).values(
        telegram_id=-uid, username=None, photo_url=None, first_name=DELETED_NAME))
    return {"deleted": True, "user_id": uid}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("telegram_id", type=int)
    args = ap.parse_args(argv)
    with direct_engine().begin() as conn:
        out = delete_user(conn, args.telegram_id)
    if not out["deleted"]:
        sys.exit(f"error: no user with Telegram id {args.telegram_id}")
    print(f"erased personal data of user {out['user_id']}")


if __name__ == "__main__":
    main()
