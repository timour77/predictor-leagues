"""Match sync: refresh a bounded batch of Competitions per tick, round-robin."""
from datetime import datetime, timedelta

from sqlalchemy import Connection, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.schema import competition_sync, matches

MAX_COMPETITIONS_PER_TICK = 8  # football-data.org free tier allows 10 requests/minute
LIVE_STATUSES = ("IN_PLAY", "PAUSED")
NEAR_KICKOFF_BEFORE = timedelta(hours=3)  # still possibly live / awaiting final score
NEAR_KICKOFF_AFTER = timedelta(hours=1)


def priority_competition_ids(conn: Connection, now: datetime) -> list[int]:
    """Competitions to refresh first because a League depends on them.

    Seam for #13: return the Competitions of active Leagues (Window running or about
    to start). Leagues do not exist yet, so nothing is prioritised on that account.
    """
    return []


def _near_kickoff_competitions(conn: Connection, now: datetime) -> set[int]:
    near = or_(
        matches.c.status.in_(LIVE_STATUSES),
        and_(
            matches.c.status.notin_(("FINISHED", "CANCELLED", "AWARDED")),
            matches.c.kickoff.between(now - NEAR_KICKOFF_BEFORE, now + NEAR_KICKOFF_AFTER),
        ),
    )
    return set(conn.execute(select(matches.c.competition_id).where(near).distinct()).scalars())


def _order(conn: Connection, now: datetime, candidates: list[int], priority_ids) -> list[int]:
    attempts = dict(conn.execute(
        select(competition_sync.c.competition_id, competition_sync.c.last_attempt_at)
    ).all())
    near = _near_kickoff_competitions(conn, now)
    priority = [c for c in dict.fromkeys(priority_ids) if c in candidates]

    def rank(cid: int):
        # never-attempted first, then least recently attempted; id keeps ties stable
        last = attempts.get(cid)
        return (last is not None, last or now, cid)

    rest = sorted((c for c in candidates if c not in priority and c in near), key=rank)
    rest += sorted((c for c in candidates if c not in priority and c not in near), key=rank)
    return priority + rest


def _upsert_matches(conn: Connection, rows: list[dict], now: datetime) -> None:
    if not rows:
        return
    stmt = insert(matches).values([{**r, "updated_at": now} for r in rows])
    update_cols = {c: stmt.excluded[c] for c in rows[0] if c != "external_id"}
    update_cols["updated_at"] = now
    conn.execute(stmt.on_conflict_do_update(index_elements=["external_id"], set_=update_cols))


def _record_attempt(conn: Connection, cid: int, now: datetime, error: str | None) -> None:
    values = {"last_attempt_at": now, "last_error": error}
    if error is None:
        values["last_synced_at"] = now
    stmt = insert(competition_sync).values(competition_id=cid, **values)
    conn.execute(stmt.on_conflict_do_update(index_elements=["competition_id"], set_=values))


def sync_matches(
    conn: Connection,
    client,
    now: datetime,
    competition_ids: list[int],
    priority_ids: list[int] | None = None,
    limit: int = MAX_COMPETITIONS_PER_TICK,
) -> dict:
    """Refresh up to `limit` Competitions. Safe to repeat; one failing Competition
    is recorded and skipped, never blocking the others."""
    if priority_ids is None:
        priority_ids = priority_competition_ids(conn, now)
    batch = _order(conn, now, list(competition_ids), priority_ids)[:limit]
    synced, failed = [], {}
    for cid in batch:
        try:
            with conn.begin_nested():
                _upsert_matches(conn, client.competition_matches(cid), now)
                _record_attempt(conn, cid, now, None)
            synced.append(cid)
        except Exception as e:
            failed[cid] = str(e)
            _record_attempt(conn, cid, now, str(e))
    return {"synced": synced, "failed": failed}


def list_matches(
    conn: Connection,
    competition_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict]:
    q = select(matches).order_by(matches.c.kickoff, matches.c.id)
    if competition_id is not None:
        q = q.where(matches.c.competition_id == competition_id)
    if date_from is not None:
        q = q.where(matches.c.kickoff >= date_from)
    if date_to is not None:
        q = q.where(matches.c.kickoff <= date_to)
    return [dict(r) for r in conn.execute(q).mappings()]
