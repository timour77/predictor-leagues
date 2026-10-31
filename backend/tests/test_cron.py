import pytest
from sqlalchemy import text

from app import config, cron
from app.db import get_engine
from tests.test_matchdata import FakeClient, match
from tests.test_api import header

SECRET = "s3cret"


@pytest.fixture
def tick_client(client, migrated_db, monkeypatch):
    from app.routers import cron as cron_router
    from main import app

    monkeypatch.setattr(config, "CRON_SECRET", SECRET)
    with get_engine().begin() as c:
        c.execute(text("TRUNCATE matches, competition_sync RESTART IDENTITY"))
    fake = FakeClient({2021: [match(1)]})
    monkeypatch.setattr(config, "MATCHDATA_COMPETITION_IDS", [2021])
    app.dependency_overrides[cron_router.get_football_client] = lambda: fake
    yield client
    app.dependency_overrides.clear()


def auth(secret=SECRET):
    return {"Authorization": f"Bearer {secret}"}


def test_tick_rejects_missing_or_wrong_secret(tick_client):
    assert tick_client.get("/api/cron/tick").status_code == 401
    assert tick_client.get("/api/cron/tick", headers=auth("nope")).status_code == 401


def test_tick_refuses_when_secret_not_configured(tick_client, monkeypatch):
    monkeypatch.setattr(config, "CRON_SECRET", "")
    assert tick_client.get("/api/cron/tick", headers=auth("")).status_code == 401
    assert tick_client.get("/api/cron/tick").status_code == 401


def test_tick_syncs_matches_and_is_repeatable(tick_client):
    for _ in range(2):
        body = tick_client.get("/api/cron/tick", headers=auth()).json()
        assert body["steps"]["match_sync"]["ok"] is True
    ms = tick_client.get("/api/matches", headers=header()).json()
    assert [m["external_id"] for m in ms["matches"]] == [1]
    assert "Football-Data.org" in ms["attribution"]


def test_tick_skips_when_another_tick_holds_the_lock(tick_client):
    with get_engine().connect() as other:
        with other.begin():
            other.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": cron.TICK_LOCK_KEY})
            body = tick_client.get("/api/cron/tick", headers=auth()).json()
    assert body == {"skipped": "locked"}
    assert tick_client.get("/api/matches", headers=header()).json()["matches"] == []


def test_failing_step_does_not_block_others(migrated_db):
    ran = []

    def bad(conn):
        conn.execute(text("INSERT INTO users (telegram_id) VALUES (8888)"))
        raise RuntimeError("bad step")

    def good(conn):
        ran.append("good")
        return {"n": 1}

    out = cron.run_tick(get_engine(), [("bad", bad), ("good", good)])
    assert out["steps"]["bad"] == {"ok": False, "error": "bad step"}
    assert out["steps"]["good"] == {"ok": True, "result": {"n": 1}}
    with get_engine().connect() as c:  # the failed step's writes were rolled back
        assert c.execute(text("SELECT count(*) FROM users WHERE telegram_id=8888")).scalar() == 0
