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

# (telegram_id, body) or (telegram_id, body, button=(text, url)); raises on failure
Sender = Callable[..., None]


def enqueue(conn: Connection, user_id: int, kind: str, body: str, dedupe_key: str,
            payload: dict | None = None, button: tuple[str, str] | None = None) -> bool:
    """Returns False when the dedupe_key was already queued."""
    return conn.execute(
        pg_insert(notifications).values(
            user_id=user_id, kind=kind, body=body, dedupe_key=dedupe_key, payload=payload,
            button_text=button[0] if button else None, button_url=button[1] if button else None)
        .on_conflict_do_nothing(index_elements=["dedupe_key"]).returning(notifications.c.id)
    ).first() is not None


def deliver_pending(conn: Connection, sender: Sender, now: datetime) -> dict:
    rows = conn.execute(text(
        "SELECT n.id, n.user_id, n.kind, n.body, n.payload, n.button_text, n.button_url, u.telegram_id FROM notifications n JOIN users u ON u.id = n.user_id "
        "WHERE n.sent_at IS NULL AND n.attempts < :max ORDER BY n.id LIMIT :batch "
        "FOR UPDATE OF n SKIP LOCKED"
    ), {"max": MAX_ATTEMPTS, "batch": BATCH}).all()
    sent = failed = 0
    for row in rows:
        body, button = row.body, (row.button_text, row.button_url) if row.button_url else None
        if row.kind == "reminder":
            from app import reminders   # imports this module, so only at call time
            rendered = reminders.render_at_send(conn, row.user_id, row.payload, now)
            if rendered is None:   # predicted, switched off or no longer upcoming: settle it quietly
                conn.execute(
                    notifications.update().where(notifications.c.id == row.id)
                    .values(sent_at=now, last_error="skipped: nothing left to remind")
                )
                continue
            body, button = rendered
        try:
            if button:
                sender(row.telegram_id, body, button=button)
            else:
                sender(row.telegram_id, body)
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
