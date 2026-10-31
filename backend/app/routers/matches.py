from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import Connection

from app import matchdata
from app.auth import get_current_user
from app.db import get_conn

router = APIRouter()


@router.get("/matches")
def list_matches(
    competition_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_conn),
):
    """Read-only view of the local `matches` table; never calls football-data.org."""
    rows = matchdata.list_matches(conn, competition_id, date_from, date_to)
    return {"matches": rows, "attribution": matchdata.ATTRIBUTION}
