import json
import time

from sqlalchemy import create_engine, text

from app.db import get_engine
from tests.test_telegram_auth import fields, sign
from tests.conftest import BOT_TOKEN


def header(user=None, auth_date=None):
    return {"Authorization": "tma " + sign(fields(auth_date=auth_date, user=user), BOT_TOKEN)}


def test_health_needs_no_auth(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_me_requires_auth(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer x"}).status_code == 401
    assert client.get("/api/me", headers={"Authorization": "tma garbage"}).status_code == 401


def test_me_rejects_expired_init_data(client):
    assert client.get("/api/me", headers=header(auth_date=time.time() - 10 * 86400)).status_code == 401


def test_me_creates_then_updates_user(client):
    h = header({"id": 7001, "first_name": "Ann", "username": "ann"})
    first = client.get("/api/me", headers=h).json()
    assert first["telegram_id"] == 7001 and first["username"] == "ann"

    h = header({"id": 7001, "first_name": "Ann", "username": "ann2"})
    second = client.get("/api/me", headers=h).json()
    assert second["id"] == first["id"] and second["username"] == "ann2"


def test_removed_endpoints_are_gone(client):
    for path in ("/api/auth/login", "/api/auth/register", "/api/admin/init-db",
                 "/api/admin/recalculate-scores"):
        assert client.post(path).status_code == 404


def test_request_transaction_rolls_back_on_error(migrated_db):
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import Connection

    from app.db import get_conn

    app = FastAPI()

    @app.post("/boom")
    def boom(conn: Connection = Depends(get_conn)):
        conn.execute(text("INSERT INTO users (telegram_id) VALUES (9999)"))
        raise RuntimeError("boom")

    TestClient(app, raise_server_exceptions=False).post("/boom")
    with get_engine().connect() as c:
        assert c.execute(text("SELECT count(*) FROM users WHERE telegram_id=9999")).scalar() == 0
