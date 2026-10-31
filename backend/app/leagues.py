"""Leagues: create, join, and the status machine.

Leagues are always free (ADR 0002). Joining closes when the first match of the Window kicks
off. The tick steps that start, cancel and settle Leagues belong to #15; they use `transition`.
"""
import secrets
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import Connection, func, insert, select, update

from app.errors import Conflict, Invalid, NotFound
from app.schema import league_competitions, league_members, leagues, matches, users

GRACE_PERIOD = timedelta(days=7)
MAX_WINDOW_DAYS = 400
MAX_NAME_LENGTH = 60

TRANSITIONS = {
    "open": {"active", "cancelled"},
    "active": {"settling"},
    "settling": {"settled"},
    "settled": set(),
    "cancelled": set(),
}


def can_transition(current: str, new: str) -> bool:
    return new in TRANSITIONS.get(current, set())


def window_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """The Window as UTC instants: [start 00:00, day after end 00:00)."""
    lo = datetime.combine(start, time.min, tzinfo=timezone.utc)
    hi = datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return lo, hi


def grace_ends(league: dict) -> datetime:
    return window_bounds(league["window_start"], league["window_end"])[1] + GRACE_PERIOD


def create_league(
    conn: Connection,
    creator_id: int,
    name: str,
    competition_ids: list[int],
    window_start: date,
    window_end: date,
    now: datetime,
    allowed_competitions: list[int],
) -> dict:
    name = name.strip()
    if not 1 <= len(name) <= MAX_NAME_LENGTH:
        raise Invalid(f"Name must be 1-{MAX_NAME_LENGTH} characters")
    competition_ids = list(dict.fromkeys(competition_ids))
    if not competition_ids:
        raise Invalid("Pick at least one Competition")
    unknown = [c for c in competition_ids if c not in allowed_competitions]
    if unknown:
        raise Invalid(f"Unsupported Competitions: {unknown}")
    if window_end < window_start:
        raise Invalid("Window must end on or after it starts")
    if (window_end - window_start).days > MAX_WINDOW_DAYS:
        raise Invalid(f"Window can be at most {MAX_WINDOW_DAYS} days")
    if window_start < now.astimezone(timezone.utc).date():
        raise Invalid("Window cannot start in the past")

    league = conn.execute(
        insert(leagues).values(
            name=name,
            creator_id=creator_id,
            invite_code=secrets.token_urlsafe(6),
            window_start=window_start,
            window_end=window_end,
        ).returning(leagues)
    ).mappings().one()
    conn.execute(insert(league_competitions), [
        {"league_id": league["id"], "competition_id": c} for c in competition_ids
    ])
    conn.execute(insert(league_members).values(league_id=league["id"], user_id=creator_id))
    return dict(league)


def get_league(conn: Connection, league_id: int) -> dict:
    row = conn.execute(select(leagues).where(leagues.c.id == league_id)).mappings().first()
    if row is None:
        raise NotFound("League not found")
    return dict(row)


def get_league_by_code(conn: Connection, code: str) -> dict:
    row = conn.execute(select(leagues).where(leagues.c.invite_code == code)).mappings().first()
    if row is None:
        raise NotFound("Invite not found")
    return dict(row)


def competition_ids(conn: Connection, league_id: int) -> list[int]:
    return sorted(conn.execute(
        select(league_competitions.c.competition_id).where(league_competitions.c.league_id == league_id)
    ).scalars())


def is_member(conn: Connection, league_id: int, user_id: int) -> bool:
    return conn.execute(
        select(league_members.c.user_id).where(
            league_members.c.league_id == league_id, league_members.c.user_id == user_id
        )
    ).first() is not None


def get_league_for_member(conn: Connection, league_id: int, user_id: int) -> dict:
    """404 for non-Members too, so League ids do not leak."""
    league = get_league(conn, league_id)
    if not is_member(conn, league_id, user_id):
        raise NotFound("League not found")
    return league


def window_matches_filter(league: dict, comps: list[int]):
    lo, hi = window_bounds(league["window_start"], league["window_end"])
    return (matches.c.competition_id.in_(comps), matches.c.kickoff >= lo, matches.c.kickoff < hi)


def join_closes_at(conn: Connection, league: dict) -> datetime:
    """Kickoff of the Window's first match; the Window's start if none is known yet."""
    first = conn.execute(
        select(func.min(matches.c.kickoff)).where(
            *window_matches_filter(league, competition_ids(conn, league["id"]))
        )
    ).scalar()
    return first or window_bounds(league["window_start"], league["window_end"])[0]


def join_league(conn: Connection, league: dict, user_id: int, now: datetime) -> None:
    """Idempotent for existing Members."""
    if is_member(conn, league["id"], user_id):
        return
    if league["status"] != "open" or now >= join_closes_at(conn, league):
        raise Conflict("Joining this League has closed")
    conn.execute(insert(league_members).values(league_id=league["id"], user_id=user_id))


def transition(conn: Connection, league_id: int, current: str, new: str) -> bool:
    """Move a League along the status machine. Returns False if it was no longer in
    `current` (another tick got there first), so callers can be safely repeated."""
    if not can_transition(current, new):
        raise Conflict(f"Cannot move a League from {current} to {new}")
    result = conn.execute(
        update(leagues).where(leagues.c.id == league_id, leagues.c.status == current).values(status=new)
    )
    return result.rowcount == 1


def members(conn: Connection, league_id: int) -> list[dict]:
    rows = conn.execute(
        select(users.c.id.label("user_id"), users.c.username, users.c.first_name, users.c.photo_url,
               league_members.c.joined_at)
        .join(league_members, league_members.c.user_id == users.c.id)
        .where(league_members.c.league_id == league_id)
        .order_by(league_members.c.joined_at, users.c.id)
    ).mappings()
    return [dict(r) for r in rows]


def list_for_user(conn: Connection, user_id: int) -> list[dict]:
    rows = conn.execute(
        select(leagues).join(league_members, league_members.c.league_id == leagues.c.id)
        .where(league_members.c.user_id == user_id).order_by(leagues.c.created_at.desc(), leagues.c.id.desc())
    ).mappings()
    return [dict(r) for r in rows]


def league_view(conn: Connection, league: dict) -> dict:
    return {
        "id": league["id"],
        "name": league["name"],
        "creator_id": league["creator_id"],
        "invite_code": league["invite_code"],
        "window_start": league["window_start"],
        "window_end": league["window_end"],
        "status": league["status"],
        "competition_ids": competition_ids(conn, league["id"]),
        "join_closes_at": join_closes_at(conn, league),
    }
