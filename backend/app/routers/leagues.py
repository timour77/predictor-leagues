from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Connection

from app import config, leagues, predictions, standings
from app.auth import get_current_user
from app.db import get_conn

router = APIRouter()


def get_now() -> datetime:
    return datetime.now(timezone.utc)


class CreateLeague(BaseModel):
    name: str
    competition_ids: list[int]
    window_start: date
    window_end: date


class PredictionIn(BaseModel):
    home_goals: int
    away_goals: int


@router.post("/leagues", status_code=201)
def create_league(
    body: CreateLeague,
    user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
):
    league = leagues.create_league(
        conn, user["id"], body.name, body.competition_ids, body.window_start, body.window_end,
        now, config.MATCHDATA_COMPETITION_IDS,
    )
    return leagues.league_view(conn, league)


@router.get("/leagues")
def my_leagues(user: dict = Depends(get_current_user), conn: Connection = Depends(get_conn)):
    return {"leagues": [leagues.league_view(conn, lg) for lg in leagues.list_for_user(conn, user["id"])]}


@router.get("/leagues/invite/{code}")
def invite_preview(code: str, user: dict = Depends(get_current_user), conn: Connection = Depends(get_conn)):
    """What an invitee sees before joining; no Predictions, no invite code echo for outsiders."""
    league = leagues.get_league_by_code(conn, code)
    view = leagues.league_view(conn, league)
    view.pop("invite_code")
    view["member_count"] = len(leagues.members(conn, league["id"]))
    view["is_member"] = leagues.is_member(conn, league["id"], user["id"])
    return view


@router.post("/leagues/invite/{code}/join")
def join(
    code: str,
    user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
):
    league = leagues.get_league_by_code(conn, code)
    leagues.join_league(conn, league, user["id"], now)
    return leagues.league_view(conn, league)


@router.get("/leagues/{league_id}")
def league_detail(league_id: int, user: dict = Depends(get_current_user), conn: Connection = Depends(get_conn)):
    league = leagues.get_league_for_member(conn, league_id, user["id"])
    return {**leagues.league_view(conn, league), "members": leagues.members(conn, league_id)}


@router.get("/leagues/{league_id}/standings")
def league_standings(
    league_id: int,
    user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
):
    league = leagues.get_league_for_member(conn, league_id, user["id"])
    return standings.standings_for(conn, league, now)


@router.get("/leagues/{league_id}/matches")
def league_matches(
    league_id: int,
    user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
):
    league = leagues.get_league_for_member(conn, league_id, user["id"])
    return {"matches": predictions.league_matches(conn, league, user["id"], now)}


@router.put("/leagues/{league_id}/matches/{match_id}/prediction")
def put_prediction(
    league_id: int,
    match_id: int,
    body: PredictionIn,
    user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
):
    league = leagues.get_league_for_member(conn, league_id, user["id"])
    return predictions.put_prediction(conn, league, user["id"], match_id, body.home_goals, body.away_goals, now)


@router.delete("/leagues/{league_id}/matches/{match_id}/prediction", status_code=204)
def withdraw_prediction(
    league_id: int,
    match_id: int,
    user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
):
    league = leagues.get_league_for_member(conn, league_id, user["id"])
    predictions.withdraw_prediction(conn, league, user["id"], match_id, now)


@router.get("/leagues/{league_id}/matches/{match_id}/predictions")
def match_predictions(
    league_id: int,
    match_id: int,
    user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_conn),
    now: datetime = Depends(get_now),
):
    league = leagues.get_league_for_member(conn, league_id, user["id"])
    return predictions.match_predictions(conn, league, match_id, user["id"], now)
