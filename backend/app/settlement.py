"""Tick steps that start, cancel and settle Leagues (#15).

Every step is safe to repeat and to skip: each picks up whatever is due *now*, so a tick that
did not run is made up by the next one, and the status machine (`leagues.transition`) turns a
second attempt into a no-op. One League failing does not block the others.
"""
import logging
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import Connection, func, insert, select, update

from app import leagues as leagues_mod, notifications, standings as standings_mod
from app.schema import final_standings, league_members, leagues, trophies

log = logging.getLogger(__name__)


def _member_count(conn: Connection, league_id: int) -> int:
    return conn.execute(
        select(func.count()).select_from(league_members).where(league_members.c.league_id == league_id)
    ).scalar()


def start_leagues(conn: Connection, now: datetime) -> dict:
    """Open Leagues whose Window has started become active, or are Cancelled with fewer than
    two Members (the Creator is notified through the outbox)."""
    started = cancelled = 0
    for lg in conn.execute(select(leagues).where(leagues.c.status == "open").order_by(leagues.c.id)).mappings():
        lg = dict(lg)
        if now < leagues_mod.window_bounds(lg["window_start"], lg["window_end"])[0]:
            continue
        with conn.begin_nested():
            if _member_count(conn, lg["id"]) < 2:
                if leagues_mod.transition(conn, lg["id"], "open", "cancelled"):
                    notifications.enqueue(
                        conn, lg["creator_id"], "league_cancelled",
                        f"Your League \"{lg['name']}\" was cancelled: it needs at least 2 Members "
                        f"when its Window starts.",
                        f"league_cancelled:{lg['id']}",
                    )
                    cancelled += 1
            elif leagues_mod.transition(conn, lg["id"], "open", "active"):
                started += 1
    return {"started": started, "cancelled": cancelled}


def _award_trophies(conn: Connection, league_id: int, ranked: list[dict], matches_scored: int) -> None:
    """Every Member ranked first wins, unless nothing was scored (then there is nothing to win)."""
    winners = [r for r in ranked if r["rank"] == 1 and r["points"] > 0] if matches_scored else []
    if winners:
        conn.execute(insert(trophies), [{"league_id": league_id, "user_id": r["user_id"]} for r in winners])


def settle_league(conn: Connection, league: dict, now: datetime) -> bool:
    """Fix the final standings and award Trophies in the caller's transaction."""
    if not leagues_mod.transition(conn, league["id"], "active", "settling"):
        return False
    result = standings_mod.compute_standings(conn, league, now)
    ranked = result["standings"]
    if ranked:
        conn.execute(insert(final_standings), [
            {"league_id": league["id"], "user_id": r["user_id"], "rank": r["rank"],
             "points": r["points"], "exact": r["exact"]} for r in ranked
        ])
    _award_trophies(conn, league["id"], ranked, result["matches_scored"])
    conn.execute(update(leagues).where(leagues.c.id == league["id"]).values(
        matches_scored=result["matches_scored"], settled_at=now))
    leagues_mod.transition(conn, league["id"], "settling", "settled")
    return True


def settle_leagues(conn: Connection, now: datetime) -> dict:
    """Settle active Leagues whose Grace period is over. Each League is its own savepoint."""
    settled = failed = 0
    active = conn.execute(select(leagues).where(leagues.c.status == "active").order_by(leagues.c.id)).mappings().all()
    for lg in map(dict, active):
        if now < leagues_mod.grace_ends(lg):
            continue
        try:
            with conn.begin_nested():
                settled += settle_league(conn, lg, now)
        except Exception:
            log.exception("settling League %s failed", lg["id"])
            failed += 1
    return {"settled": settled, "failed": failed}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def tick_steps(sender: notifications.Sender, now_fn: Callable[[], datetime] = _utcnow) -> list:
    """The tick steps of this module, in order: start/Cancel, settle, then deliver the outbox."""
    return [
        ("start_leagues", lambda conn: start_leagues(conn, now_fn())),
        ("settle_leagues", lambda conn: settle_leagues(conn, now_fn())),
        ("deliver_notifications", lambda conn: notifications.deliver_pending(conn, sender, now_fn())),
    ]
