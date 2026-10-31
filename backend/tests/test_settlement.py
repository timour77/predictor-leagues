from datetime import datetime, time, timedelta, timezone

import pytest
from sqlalchemy import text

from app import notifications, settlement
from app.cron import run_tick
from app.db import get_engine
from tests.test_leagues_api import T0, add_match, api, join, make_league, predict, user, Clock  # noqa: F401

START = T0.date() + timedelta(days=3)           # a League that starts in 3 days
WINDOW_START = datetime.combine(START, time.min, tzinfo=timezone.utc)
GRACE_END = datetime(2026, 6, 19, tzinfo=timezone.utc)   # Window ends Jun 11, +7 days grace


def q(sql, **params):
    with get_engine().connect() as c:
        return c.execute(text(sql), params).all()


def run(fn, now):
    with get_engine().begin() as c:
        return fn(c, now)


def status_of(lg):
    return q("SELECT status FROM leagues WHERE id=:i", i=lg["id"])[0][0]


def finish(match_id, h, a, status="FINISHED"):
    with get_engine().begin() as c:
        c.execute(text("UPDATE matches SET status=:s, home_goals=:h, away_goals=:a WHERE id=:i"),
                  {"s": status, "h": h, "a": a, "i": match_id})


# --- Starting and Cancellation ---------------------------------------------

def test_league_with_two_members_starts_at_window_start_not_before(api):
    lg = make_league(api, start=START)
    join(api, lg, 2)
    run(settlement.start_leagues, WINDOW_START - timedelta(minutes=1))
    assert status_of(lg) == "open"
    out = run(settlement.start_leagues, WINDOW_START)
    assert status_of(lg) == "active" and out == {"started": 1, "cancelled": 0}
    assert run(settlement.start_leagues, T0 + timedelta(days=4)) == {"started": 0, "cancelled": 0}


def test_league_with_one_member_is_cancelled_and_creator_notified_once(api):
    lg = make_league(api, who=1, start=START)
    for now in (T0 + timedelta(days=3), T0 + timedelta(days=3, minutes=1)):
        run(settlement.start_leagues, now)
    assert status_of(lg) == "cancelled"
    rows = q("SELECT user_id, kind, body FROM notifications")
    assert len(rows) == 1 and rows[0][1] == "league_cancelled" and "Friends" in rows[0][2]
    creator = q("SELECT id FROM users WHERE telegram_id=8001")[0][0]
    assert rows[0][0] == creator


def test_skipped_ticks_still_start_late(api):
    lg = make_league(api, start=START)
    join(api, lg, 2)
    run(settlement.start_leagues, T0 + timedelta(days=30))     # the tick was down for weeks
    assert status_of(lg) == "active"


# --- Settlement ------------------------------------------------------------

def test_settlement_waits_for_grace_period(api):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=1))
    join(api, lg, 2)
    predict(api, lg, m, 1, 1, 0)
    finish(m, 1, 0)
    run(settlement.start_leagues, T0)
    assert run(settlement.settle_leagues, GRACE_END - timedelta(seconds=1)) == {"settled": 0, "failed": 0}
    assert status_of(lg) == "active"
    assert run(settlement.settle_leagues, GRACE_END) == {"settled": 1, "failed": 0}
    assert status_of(lg) == "settled"


def test_winner_gets_trophy_and_final_standings_are_stored(api):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=1))
    join(api, lg, 2)
    predict(api, lg, m, 1, 2, 1)       # u1 exact
    predict(api, lg, m, 2, 1, 0)       # u2 outcome only
    finish(m, 2, 1)
    run(settlement.start_leagues, T0)
    run(settlement.settle_leagues, GRACE_END)
    final = q("SELECT rank, points, exact, u.telegram_id FROM final_standings f JOIN users u ON u.id=f.user_id "
              "ORDER BY rank")
    assert final == [(1, 4, 1, 8001), (2, 1, 0, 8002)]
    assert q("SELECT u.telegram_id FROM trophies t JOIN users u ON u.id=t.user_id") == [(8001,)]


def test_exact_score_tiebreak_decides_the_winner(api):
    lg = make_league(api)
    ids = [add_match(i, T0 + timedelta(hours=i)) for i in (1, 2, 3, 4)]
    join(api, lg, 2)
    predict(api, lg, ids[0], 1, 1, 0)          # u1: one exact score = 4 points, 1 exact
    for m in ids:
        predict(api, lg, m, 2, 2, 0)           # u2: four right outcomes = 4 points, 0 exact
        finish(m, 1, 0)
    run(settlement.start_leagues, T0)
    run(settlement.settle_leagues, GRACE_END)
    assert q("SELECT u.telegram_id, points, exact FROM final_standings f JOIN users u ON u.id=f.user_id "
             "ORDER BY rank") == [(8001, 4, 1), (8002, 4, 0)]
    assert q("SELECT u.telegram_id FROM trophies t JOIN users u ON u.id=t.user_id") == [(8001,)]


def test_full_tie_awards_every_tied_winner(api):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=1))
    for w in (2, 3):
        join(api, lg, w)
    predict(api, lg, m, 1, 1, 0)
    predict(api, lg, m, 2, 2, 0)       # both outcome-only, same points and exact count
    predict(api, lg, m, 3, 0, 1)
    finish(m, 3, 0)
    run(settlement.start_leagues, T0)
    run(settlement.settle_leagues, GRACE_END)
    winners = sorted(r[0] for r in q("SELECT u.telegram_id FROM trophies t JOIN users u ON u.id=t.user_id"))
    assert winners == [8001, 8002]


def test_dropped_matches_score_nothing_and_do_not_block_settlement(api):
    lg = make_league(api)
    played = add_match(1, T0 + timedelta(hours=1))
    cancelled = add_match(2, T0 + timedelta(hours=2))
    postponed = add_match(3, T0 + timedelta(hours=3))
    join(api, lg, 2)
    predict(api, lg, played, 1, 0, 1)
    predict(api, lg, played, 2, 1, 0)                          # u2 exact (4)
    predict(api, lg, cancelled, 1, 1, 0)
    predict(api, lg, postponed, 1, 1, 0)
    finish(played, 1, 0)
    finish(cancelled, None, None, status="CANCELLED")
    finish(postponed, None, None, status="POSTPONED")          # never played within the Grace period
    run(settlement.start_leagues, T0)
    run(settlement.settle_leagues, GRACE_END)
    final = q("SELECT u.telegram_id, points FROM final_standings f JOIN users u ON u.id=f.user_id ORDER BY rank")
    assert final == [(8002, 4), (8001, 0)]
    assert q("SELECT u.telegram_id FROM trophies t JOIN users u ON u.id=t.user_id") == [(8002,)]


def test_league_without_scored_matches_awards_no_trophy(api):
    lg = make_league(api)
    add_match(1, T0 + timedelta(hours=1))   # joining is open until the first kickoff
    join(api, lg, 2)
    run(settlement.start_leagues, T0)
    run(settlement.settle_leagues, GRACE_END)
    assert status_of(lg) == "settled"
    assert q("SELECT count(*) FROM trophies") == [(0,)]
    assert q("SELECT count(*) FROM final_standings") == [(2,)]


def test_settlement_is_idempotent_and_final(api):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=1))
    join(api, lg, 2)
    predict(api, lg, m, 1, 1, 0)
    finish(m, 1, 0)
    run(settlement.start_leagues, T0)
    run(settlement.settle_leagues, GRACE_END)
    again = run(settlement.settle_leagues, GRACE_END + timedelta(days=1))
    assert again == {"settled": 0, "failed": 0}
    assert q("SELECT count(*) FROM trophies") == [(1,)]
    finish(m, 0, 5)                                            # a late data correction changes nothing
    detail = api.get(f"/api/leagues/{lg['id']}/standings", headers=user(1)).json()
    assert detail["final"] is True and detail["standings"][0]["points"] == 4


def test_settlement_is_all_or_nothing_per_league(api, monkeypatch):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=1))
    join(api, lg, 2)
    predict(api, lg, m, 1, 1, 0)
    finish(m, 1, 0)
    run(settlement.start_leagues, T0)

    def boom(*a, **k):
        raise RuntimeError("trophy insert failed")
    monkeypatch.setattr(settlement, "_award_trophies", boom)
    assert run(settlement.settle_leagues, GRACE_END) == {"settled": 0, "failed": 1}
    assert status_of(lg) == "active"
    assert q("SELECT count(*) FROM final_standings") == [(0,)]
    monkeypatch.undo()
    assert run(settlement.settle_leagues, GRACE_END) == {"settled": 1, "failed": 0}   # next tick retries


def test_a_skipped_league_start_still_settles_in_one_tick(api):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=1))
    join(api, lg, 2)
    predict(api, lg, m, 1, 1, 0)
    finish(m, 1, 0)
    steps = settlement.tick_steps(lambda tg, body: None, now_fn=lambda: GRACE_END + timedelta(days=5))
    out = run_tick(get_engine(), steps)
    assert status_of(lg) == "settled"
    assert out["steps"]["settle_leagues"]["ok"] is True


# --- Notifications outbox --------------------------------------------------

def test_outbox_delivers_once_and_retries_failures(api):
    lg = make_league(api, start=START)
    run(settlement.start_leagues, T0 + timedelta(days=3))
    sent = []

    def flaky(telegram_id, body):
        if not sent:
            sent.append("failed")
            raise RuntimeError("telegram down")
        sent.append((telegram_id, body))

    now = T0 + timedelta(days=3)
    with get_engine().begin() as c:
        assert notifications.deliver_pending(c, flaky, now) == {"sent": 0, "failed": 1}
    assert q("SELECT attempts, sent_at IS NULL, last_error FROM notifications") == [(1, True, "telegram down")]
    with get_engine().begin() as c:
        assert notifications.deliver_pending(c, flaky, now) == {"sent": 1, "failed": 0}
    with get_engine().begin() as c:
        assert notifications.deliver_pending(c, flaky, now) == {"sent": 0, "failed": 0}
    assert sent[1][0] == 8001 and "cancelled" in sent[1][1].lower()


def test_outbox_gives_up_after_max_attempts(api):
    make_league(api, start=START)
    run(settlement.start_leagues, T0 + timedelta(days=3))

    def down(telegram_id, body):
        raise RuntimeError("down")
    for _ in range(notifications.MAX_ATTEMPTS + 2):
        with get_engine().begin() as c:
            notifications.deliver_pending(c, down, T0)
    assert q("SELECT attempts FROM notifications") == [(notifications.MAX_ATTEMPTS,)]


# --- API -------------------------------------------------------------------

def test_api_exposes_result_and_trophies(api):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=1))
    join(api, lg, 2)
    predict(api, lg, m, 1, 1, 0)
    finish(m, 1, 0)
    run(settlement.start_leagues, T0)
    view = api.get(f"/api/leagues/{lg['id']}", headers=user(1)).json()
    assert view["status"] == "active" and view["winner_ids"] == []
    run(settlement.settle_leagues, GRACE_END)
    view = api.get(f"/api/leagues/{lg['id']}", headers=user(2)).json()
    winner = [m_["user_id"] for m_ in view["members"] if m_["username"] == "u1"]
    assert view["status"] == "settled" and view["winner_ids"] == winner
    trophies = api.get("/api/me/trophies", headers=user(1)).json()["trophies"]
    assert [(t["league_id"], t["league_name"]) for t in trophies] == [(lg["id"], "Friends")]
    assert api.get("/api/me/trophies", headers=user(2)).json()["trophies"] == []


def test_tick_runs_start_settle_and_outbox_steps(api, monkeypatch):
    from app import config
    from app.routers import cron as cron_router
    from main import app
    from tests.test_matchdata import FakeClient

    monkeypatch.setattr(config, "CRON_SECRET", "s")
    sent = []
    app.dependency_overrides[cron_router.get_football_client] = lambda: FakeClient({})
    app.dependency_overrides[cron_router.get_sender] = lambda: lambda tg, body: sent.append(tg)
    make_league(api, start=T0.date())          # 1 Member, window started
    monkeypatch.setattr(config, "MATCHDATA_COMPETITION_IDS", [])
    body = api.get("/api/cron/tick", headers={"Authorization": "Bearer s"}).json()
    assert set(body["steps"]) >= {"start_leagues", "settle_leagues", "deliver_notifications"}
    assert all(s["ok"] for s in body["steps"].values()), body
    assert sent == [8001]
