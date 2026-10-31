"""Standings: computed by query from Predictions and match results, never stored by a GET.

Settlement (app/settlement.py) fixes the final standings by reusing `compute_standings` at that time;
once a League is settled, `standings_for` serves the stored result.
"""
from datetime import datetime

from sqlalchemy import Connection, select

from app import leagues as leagues_mod, scoring
from app.schema import final_standings, matches, predictions, users


def compute_standings(conn: Connection, league: dict, now: datetime) -> dict:
    comps = leagues_mod.competition_ids(conn, league["id"])
    results = {}   # match_id -> (home, away) for Final matches
    pending = 0
    for m in conn.execute(select(matches).where(*leagues_mod.window_matches_filter(league, comps))).mappings():
        state = scoring.match_state(
            m["status"], m["home_goals"], m["away_goals"], now, leagues_mod.grace_ends(league)
        )
        if isinstance(state, scoring.Final):
            results[m["id"]] = (state.home_goals, state.away_goals)
        elif isinstance(state, scoring.Pending):
            pending += 1

    preds: dict[tuple[int, int], tuple[int, int]] = {
        (p["user_id"], p["match_id"]): (p["home_goals"], p["away_goals"])
        for p in conn.execute(select(predictions).where(predictions.c.league_id == league["id"])).mappings()
    }
    rows = []
    for member in leagues_mod.members(conn, league["id"]):
        points = exact = 0
        for match_id, actual in results.items():
            p, is_exact = scoring.score_prediction(preds.get((member["user_id"], match_id)), actual)
            points += p
            exact += is_exact
        rows.append({
            "user_id": member["user_id"], "username": member["username"],
            "first_name": member["first_name"], "photo_url": member["photo_url"],
            "points": points, "exact": exact,
        })
    return {
        "standings": scoring.rank_standings(rows),
        "matches_scored": len(results),
        "matches_pending": pending,
    }


def settled_standings(conn: Connection, league: dict) -> dict:
    rows = conn.execute(
        select(final_standings.c.user_id, users.c.username, users.c.first_name, users.c.photo_url,
               final_standings.c.points, final_standings.c.exact, final_standings.c.rank)
        .join(users, users.c.id == final_standings.c.user_id)
        .where(final_standings.c.league_id == league["id"])
        .order_by(final_standings.c.rank, final_standings.c.user_id)
    ).mappings()
    return {"standings": [dict(r) for r in rows], "matches_scored": league["matches_scored"], "matches_pending": 0}


def standings_for(conn: Connection, league: dict, now: datetime) -> dict:
    """Live standings, or the fixed final result once the League is settled."""
    if league["status"] == "settled":
        return {**settled_standings(conn, league), "final": True}
    return {**compute_standings(conn, league, now), "final": False}
