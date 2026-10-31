"""Per-minute tick: a list of idempotent steps run under a Postgres advisory lock.

Vercel cron is best-effort (runs can be skipped or doubled), so every step must be
safe to repeat and safe to skip. Later tickets register their steps in `app/routers/cron.py`.
"""
import logging
from typing import Callable

from sqlalchemy import text
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)

TICK_LOCK_KEY = 7_201_201  # arbitrary app-wide constant for pg_advisory_xact_lock

Step = tuple[str, Callable]


def run_tick(engine: Engine, steps: list[Step]) -> dict:
    """Run steps in order inside one transaction holding the tick lock.

    A concurrent tick finds the lock taken and does nothing. Each step runs in its own
    savepoint: if it raises, only its writes roll back and the next step still runs.
    """
    with engine.begin() as conn:
        got = conn.execute(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": TICK_LOCK_KEY}).scalar()
        if not got:
            return {"skipped": "locked"}
        results = {}
        for name, fn in steps:
            try:
                with conn.begin_nested():
                    results[name] = {"ok": True, "result": fn(conn)}
            except Exception as e:
                log.exception("tick step %s failed", name)
                results[name] = {"ok": False, "error": str(e)}
        return {"steps": results}
