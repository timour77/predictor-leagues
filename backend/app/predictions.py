"""Predictions: one exact score per Member, League and match, locked by the Deadline.

The Deadline is the match's kickoff in our own `matches` copy (so a rescheduled match
carries it along), compared with server time. Until then a Prediction can be changed or
withdrawn; other Members' scores are only revealed from the Deadline on.
"""
from datetime import datetime

from sqlalchemy import Connection, delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app import leagues as leagues_mod, scoring
from app.errors import Conflict, Invalid, NotFound
from app.schema import league_members, matches, predictions, users

MAX_GOALS = 99
CLOSED_STATUSES = ("FINISHED", "AWARDED", "CANCELLED")


def before_deadline(kickoff: datetime, now: datetime) -> bool:
    return now < kickoff


def revealed(kickoff: datetime, now: datetime) -> bool:
    """Reveal happens at the Deadline."""
    return not before_deadline(kickoff, now)


def _editable_match(conn: Connection, league: dict, match_id: int, now: datetime) -> dict:
    if league["status"] not in ("open", "active"):
        raise Conflict("This League is closed for Predictions")
    match = conn.execute(select(matches).where(matches.c.id == match_id)).mappings().first()
    if match is None:
        raise NotFound("Match not found")
    comps = leagues_mod.competition_ids(conn, league["id"])
    lo, hi = leagues_mod.window_bounds(league["window_start"], league["window_end"])
    if match["competition_id"] not in comps or not lo <= match["kickoff"] < hi:
        raise Invalid("Match is not part of this League")
    if match["status"] in CLOSED_STATUSES or not before_deadline(match["kickoff"], now):
        raise Conflict("The Deadline for this match has passed")
    return dict(match)


def put_prediction(
    conn: Connection, league: dict, user_id: int, match_id: int, home_goals: int, away_goals: int,
    now: datetime,
) -> dict:
    if not (0 <= home_goals <= MAX_GOALS and 0 <= away_goals <= MAX_GOALS):
        raise Invalid(f"Goals must be between 0 and {MAX_GOALS}")
    _editable_match(conn, league, match_id, now)
    stmt = insert(predictions).values(
        league_id=league["id"], user_id=user_id, match_id=match_id,
        home_goals=home_goals, away_goals=away_goals, updated_at=now,
    )
    conn.execute(stmt.on_conflict_do_update(
        index_elements=["league_id", "user_id", "match_id"],
        set_={"home_goals": home_goals, "away_goals": away_goals, "updated_at": now},
    ))
    return {"match_id": match_id, "home_goals": home_goals, "away_goals": away_goals,
            "outcome": scoring.outcome(home_goals, away_goals)}


def withdraw_prediction(conn: Connection, league: dict, user_id: int, match_id: int, now: datetime) -> None:
    _editable_match(conn, league, match_id, now)
    conn.execute(delete(predictions).where(
        predictions.c.league_id == league["id"], predictions.c.user_id == user_id,
        predictions.c.match_id == match_id,
    ))


def match_predictions(
    conn: Connection, league: dict, match_id: int, viewer_id: int, now: datetime
) -> dict:
    """Who has predicted a match; scores only for the viewer's own row until Reveal."""
    match = conn.execute(select(matches).where(matches.c.id == match_id)).mappings().first()
    if match is None or match["competition_id"] not in leagues_mod.competition_ids(conn, league["id"]):
        raise NotFound("Match not found")
    is_revealed = revealed(match["kickoff"], now)
    rows = conn.execute(
        select(users.c.id.label("user_id"), users.c.username, users.c.first_name,
               predictions.c.home_goals, predictions.c.away_goals)
        .select_from(
            league_members.join(users, users.c.id == league_members.c.user_id)
            .outerjoin(predictions, (predictions.c.league_id == league_members.c.league_id)
                       & (predictions.c.user_id == league_members.c.user_id)
                       & (predictions.c.match_id == match_id))
        )
        .where(league_members.c.league_id == league["id"])
        .order_by(league_members.c.joined_at, users.c.id)
    ).mappings()
    out = []
    for r in rows:
        predicted = r["home_goals"] is not None
        show = predicted and (is_revealed or r["user_id"] == viewer_id)
        out.append({
            "user_id": r["user_id"], "username": r["username"], "first_name": r["first_name"],
            "predicted": predicted,
            "home_goals": r["home_goals"] if show else None,
            "away_goals": r["away_goals"] if show else None,
        })
    return {"match_id": match_id, "revealed": is_revealed, "predictions": out}


def league_matches(conn: Connection, league: dict, viewer_id: int, now: datetime) -> list[dict]:
    """The Window's matches with the viewer's own Prediction, points once decided, and how
    many Members have predicted (never their scores before Reveal)."""
    comps = leagues_mod.competition_ids(conn, league["id"])
    rows = conn.execute(
        select(matches).where(*leagues_mod.window_matches_filter(league, comps))
        .order_by(matches.c.kickoff, matches.c.id)
    ).mappings().all()
    mine = {
        r["match_id"]: (r["home_goals"], r["away_goals"])
        for r in conn.execute(select(predictions).where(
            predictions.c.league_id == league["id"], predictions.c.user_id == viewer_id
        )).mappings()
    }
    counts = dict(conn.execute(
        select(predictions.c.match_id, func.count()).where(predictions.c.league_id == league["id"])
        .group_by(predictions.c.match_id)
    ).all())
    grace = leagues_mod.grace_ends(league)
    out = []
    for m in rows:
        state = scoring.match_state(m["status"], m["home_goals"], m["away_goals"], now, grace)
        prediction = mine.get(m["id"])
        points = exact = None
        if isinstance(state, scoring.Final):
            points, exact = scoring.score_prediction(prediction, (state.home_goals, state.away_goals))
        out.append({
            "match_id": m["id"], "competition_id": m["competition_id"],
            "home_team": m["home_team"], "away_team": m["away_team"],
            "home_crest": m["home_crest"], "away_crest": m["away_crest"],
            "kickoff": m["kickoff"], "status": m["status"],
            "home_goals": m["home_goals"], "away_goals": m["away_goals"],
            "state": type(state).__name__.lower(),
            "can_predict": league["status"] in ("open", "active") and m["status"] not in CLOSED_STATUSES
                           and before_deadline(m["kickoff"], now),
            "prediction": None if prediction is None else
                {"home_goals": prediction[0], "away_goals": prediction[1]},
            "predicted_count": counts.get(m["id"], 0),
            "points": points, "exact": exact,
        })
    return out
