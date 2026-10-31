from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Connection, and_, select, update

from app.auth import get_current_user
from app.db import get_conn
from app.schema import final_standings, leagues, trophies, users

router = APIRouter()


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "telegram_id": user["telegram_id"],
        "username": user["username"],
        "first_name": user["first_name"],
        "photo_url": user["photo_url"],
        "reminders_enabled": user["reminders_enabled"],
    }


class RemindersBody(BaseModel):
    enabled: bool


@router.put("/me/reminders")
def set_reminders(body: RemindersBody, user: dict = Depends(get_current_user), conn: Connection = Depends(get_conn)):
    conn.execute(update(users).where(users.c.id == user["id"]).values(reminders_enabled=body.enabled))
    return {"reminders_enabled": body.enabled}


@router.get("/me/trophies")
def my_trophies(user: dict = Depends(get_current_user), conn: Connection = Depends(get_conn)):
    rows = conn.execute(
        select(trophies.c.league_id, leagues.c.name.label("league_name"), trophies.c.awarded_at,
               final_standings.c.points, final_standings.c.exact)
        .join(leagues, leagues.c.id == trophies.c.league_id)
        .join(final_standings, and_(final_standings.c.league_id == trophies.c.league_id,
                                    final_standings.c.user_id == trophies.c.user_id))
        .where(trophies.c.user_id == user["id"])
        .order_by(trophies.c.awarded_at.desc(), trophies.c.league_id.desc())
    ).mappings()
    return {"trophies": [dict(r) for r in rows]}
