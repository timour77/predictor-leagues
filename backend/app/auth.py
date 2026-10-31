"""Per-request authentication: `Authorization: tma <initData>`."""
from fastapi import Depends, Header, HTTPException
from sqlalchemy import Connection, insert, select, update

from app import config
from app.db import get_conn
from app.schema import users
from app.telegram_auth import InitDataError, verify_init_data


def get_current_user(
    authorization: str = Header(default=""),
    conn: Connection = Depends(get_conn),
) -> dict:
    scheme, _, init_data = authorization.partition(" ")
    if scheme.lower() != "tma" or not init_data:
        raise HTTPException(401, "Not authenticated")
    try:
        tg = verify_init_data(init_data, config.BOT_TOKEN, config.INIT_DATA_MAX_AGE_SECONDS)
    except InitDataError:
        raise HTTPException(401, "Invalid Telegram data")

    profile = {
        "username": tg.get("username"),
        "first_name": tg.get("first_name"),
        "photo_url": tg.get("photo_url"),
    }
    row = conn.execute(select(users).where(users.c.telegram_id == tg["id"])).mappings().first()
    if row is None:
        row = conn.execute(
            insert(users).values(telegram_id=tg["id"], **profile).returning(users)
        ).mappings().one()
    elif any(row[k] != v for k, v in profile.items()):
        row = conn.execute(
            update(users).where(users.c.id == row["id"]).values(**profile).returning(users)
        ).mappings().one()
    return dict(row)
