"""Tick steps that start, cancel and settle Leagues (#15).

Every step is safe to repeat and to skip: each picks up whatever is due *now*, so a tick that
did not run is made up by the next one, and the status machine (`leagues.transition`) turns a
second attempt into a no-op. One League failing does not block the others.
"""
import logging
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import Connection, delete, func, insert, select, update

from app import leagues as leagues_mod, notifications, standings as standings_mod
from app.errors import Conflict
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


def _winners(ranked: list[dict], matches_scored: int) -> list[int]:
    """Every Member ranked first wins, unless nothing was scored (then there is nothing to win)."""
    return [r["user_id"] for r in ranked if r["rank"] == 1 and r["points"] > 0] if matches_scored else []


def _award_trophies(conn: Connection, league_id: int, winners: list[int]) -> dict:
    """Make the League's Trophies exactly `winners`; a kept Trophy keeps its award time."""
    held = set(conn.execute(select(trophies.c.user_id).where(trophies.c.league_id == league_id)).scalars())
    added, removed = sorted(set(winners) - held), sorted(held - set(winners))
    if removed:
        conn.execute(delete(trophies).where(trophies.c.league_id == league_id, trophies.c.user_id.in_(removed)))
    if added:
        conn.execute(insert(trophies), [{"league_id": league_id, "user_id": u} for u in added])
    return {"added": added, "removed": removed}


def _fix_result(conn: Connection, league: dict, now: datetime) -> dict:
    """Compute the standings from current match data and store them with the Trophies; returns
    the trophy changes. Shared by Settlement and re-settlement so scoring lives in one place."""
    result = standings_mod.compute_standings(conn, league, now)
    ranked = result["standings"]
    conn.execute(delete(final_standings).where(final_standings.c.league_id == league["id"]))
    if ranked:
        conn.execute(insert(final_standings), [
            {"league_id": league["id"], "user_id": r["user_id"], "rank": r["rank"],
             "points": r["points"], "exact": r["exact"]} for r in ranked
        ])
    changes = _award_trophies(conn, league["id"], _winners(ranked, result["matches_scored"]))
    conn.execute(update(leagues).where(leagues.c.id == league["id"]).values(matches_scored=result["matches_scored"]))
    return changes


def settle_league(conn: Connection, league: dict, now: datetime) -> bool:
    """Fix the final standings and award Trophies in the caller's transaction."""
    if not leagues_mod.transition(conn, league["id"], "active", "settling"):
        return False
    _fix_result(conn, league, now)
    conn.execute(update(leagues).where(leagues.c.id == league["id"]).values(settled_at=now))
    leagues_mod.transition(conn, league["id"], "settling", "settled")
    return True


def _stored_standings(conn: Connection, league_id: int) -> dict[int, dict]:
    return {
        r["user_id"]: {"rank": r["rank"], "points": r["points"], "exact": r["exact"]}
        for r in conn.execute(select(final_standings).where(final_standings.c.league_id == league_id)).mappings()
    }


def resettle_league(conn: Connection, league_id: int, now: datetime, dry_run: bool = False,
                    notify: bool = False) -> dict:
    """Operator action (scripts/resettle_league.py): recompute a settled League's final standings
    and Trophies from the current match data, after the data source corrected a result.

    Runs in the caller's transaction; with `dry_run` it computes the diff and rolls the writes
    back. Repeating it with unchanged data changes nothing. Members are told only if `notify`."""
    league = leagues_mod.get_league(conn, league_id)
    if league["status"] != "settled":
        raise Conflict(f"League {league_id} is {league['status']}, only settled Leagues can be re-settled")
    with conn.begin_nested() as sp:
        old = _stored_standings(conn, league_id)
        old_scored = league["matches_scored"]
        trophy_changes = _fix_result(conn, league, now)
        new = _stored_standings(conn, league_id)
        new_scored = leagues_mod.get_league(conn, league_id)["matches_scored"]
        standings = [{"user_id": u, "old": old.get(u), "new": new.get(u)} for u in sorted(old.keys() | new.keys())]
        changed = (any(r["old"] != r["new"] for r in standings) or old_scored != new_scored
                   or bool(trophy_changes["added"] or trophy_changes["removed"]))
        if notify and changed and not dry_run:
            _notify_resettled(conn, league, standings, trophy_changes)
        if dry_run:
            sp.rollback()
    return {"league_id": league_id, "name": league["name"], "dry_run": dry_run, "changed": changed,
            "matches_scored": {"old": old_scored, "new": new_scored},
            "standings": standings, "trophies": trophy_changes}


def _notify_resettled(conn: Connection, league: dict, standings: list[dict], trophy_changes: dict) -> None:
    """Tell each Member whose result changed; the key makes a repeated run a no-op."""
    for r in standings:
        trophy = ("won" if r["user_id"] in trophy_changes["added"]
                  else "lost" if r["user_id"] in trophy_changes["removed"] else "")
        if r["old"] == r["new"] and not trophy or r["new"] is None:
            continue
        body = (f"The result of League \"{league['name']}\" was corrected: you are now "
                f"#{r['new']['rank']} with {r['new']['points']} points.")
        if trophy:
            body += " You " + ("won" if trophy == "won" else "no longer hold") + " the Trophy."
        notifications.enqueue(conn, r["user_id"], "league_resettled", body,
                              f"league_resettled:{league['id']}:{r['user_id']}:{r['old']}:{r['new']}:{trophy}")


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
