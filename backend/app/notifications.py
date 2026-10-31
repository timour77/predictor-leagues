"""Notifications outbox: rows are written in the same transaction as the domain change, and the
tick delivers them afterwards, since Telegram calls cannot join a database transaction (ADR 0001).
Delivery is at-least-once: a crash between the Telegram call and the commit may resend a message."""
from datetime import datetime
from typing import Callable

from sqlalchemy import Connection, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.schema import notifications, users

MAX_ATTEMPTS = 5
BATCH = 50

Sender = Callable[[int, str], None]   # (telegram_id, body); raises on failure


def enqueue(conn: Connection, user_id: int, kind: str, body: str, dedupe_key: str) -> None:
    conn.execute(
        pg_insert(notifications).values(user_id=user_id, kind=kind, body=body, dedupe_key=dedupe_key)
        .on_conflict_do_nothing(index_elements=["dedupe_key"])
    )


def deliver_pending(conn: Connection, sender: Sender, now: datetime) -> dict:
    rows = conn.execute(text(
        "SELECT n.id, n.body, u.telegram_id FROM notifications n JOIN users u ON u.id = n.user_id "
        "WHERE n.sent_at IS NULL AND n.attempts < :max ORDER BY n.id LIMIT :batch "
        "FOR UPDATE OF n SKIP LOCKED"
    ), {"max": MAX_ATTEMPTS, "batch": BATCH}).all()
    sent = failed = 0
    for row in rows:
        try:
            sender(row.telegram_id, row.body)
        except Exception as e:
            failed += 1
            conn.execute(
                notifications.update().where(notifications.c.id == row.id)
                .values(attempts=notifications.c.attempts + 1, last_error=str(e)[:500])
            )
        else:
            sent += 1
            conn.execute(
                notifications.update().where(notifications.c.id == row.id)
                .values(attempts=notifications.c.attempts + 1, sent_at=now, last_error=None)
            )
    return {"sent": sent, "failed": failed}
