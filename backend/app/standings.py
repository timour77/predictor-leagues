"""Standings: computed by query from Predictions and match results, never stored by a GET.

Settlement (#15) fixes the final standings by reusing `compute_standings` at that time.
"""
from datetime import datetime

from sqlalchemy import Connection, select

from app import leagues as leagues_mod, scoring
from app.schema import matches, predictions


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
