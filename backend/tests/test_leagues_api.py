from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import insert, text

from app import leagues as leagues_mod
from app.db import get_engine
from app.routers.leagues import get_now
from app.schema import matches
from tests.test_api import header

T0 = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
COMP = 2021


class Clock:
    now = T0


@pytest.fixture
def api(client):
    from main import app

    with get_engine().begin() as c:
        c.execute(text("TRUNCATE matches, leagues, users RESTART IDENTITY CASCADE"))
    Clock.now = T0
    app.dependency_overrides[get_now] = lambda: Clock.now
    yield client
    app.dependency_overrides.clear()


def user(n):
    return header({"id": 8000 + n, "first_name": f"U{n}", "username": f"u{n}"})


def add_match(ext, kickoff, comp=COMP, status="SCHEDULED", score=None):
    with get_engine().begin() as c:
        return c.execute(insert(matches).values(
            external_id=ext, competition_id=comp, home_team="A", away_team="B", kickoff=kickoff,
            status=status, home_goals=score[0] if score else None, away_goals=score[1] if score else None,
        ).returning(matches.c.id)).scalar()


def make_league(api, who=1, start=T0.date(), end=T0.date() + timedelta(days=10), comps=(COMP,)):
    r = api.post("/api/leagues", headers=user(who), json={
        "name": "Friends", "competition_ids": list(comps),
        "window_start": start.isoformat(), "window_end": end.isoformat()})
    assert r.status_code == 201, r.text
    return r.json()


def join(api, league, who):
    return api.post(f"/api/leagues/invite/{league['invite_code']}/join", headers=user(who))


def predict(api, league, match, who, h=1, a=0):
    return api.put(f"/api/leagues/{league['id']}/matches/{match}/prediction", headers=user(who),
                   json={"home_goals": h, "away_goals": a})


# --- Leagues ---------------------------------------------------------------

def test_create_makes_creator_a_member_and_open(api):
    lg = make_league(api)
    assert lg["status"] == "open" and lg["competition_ids"] == [COMP]
    detail = api.get(f"/api/leagues/{lg['id']}", headers=user(1)).json()
    assert [m["username"] for m in detail["members"]] == ["u1"]
    assert not any(k in lg for k in ("entry_fee", "prize_pool", "price"))


@pytest.mark.parametrize("patch", [
    {"name": "  "}, {"name": "x" * 61}, {"competition_ids": []}, {"competition_ids": [999]},
    {"window_start": "2026-05-31"},                                  # in the past
    {"window_start": "2026-06-10", "window_end": "2026-06-09"},      # reversed
    {"window_end": "2028-06-01"},                                    # too long
])
def test_create_validates(api, patch):
    body = {"name": "L", "competition_ids": [COMP], "window_start": "2026-06-01", "window_end": "2026-06-05"}
    assert api.post("/api/leagues", headers=user(1), json={**body, **patch}).status_code == 422


def test_join_via_invite_is_free_and_idempotent(api):
    lg = make_league(api)
    add_match(1, T0 + timedelta(days=2))
    assert join(api, lg, 2).status_code == 200
    assert join(api, lg, 2).status_code == 200
    detail = api.get(f"/api/leagues/{lg['id']}", headers=user(1)).json()
    assert len(detail["members"]) == 2
    assert [l["id"] for l in api.get("/api/leagues", headers=user(2)).json()["leagues"]] == [lg["id"]]


def test_invite_preview_hides_code_and_unknown_code_404(api):
    lg = make_league(api)
    prev = api.get(f"/api/leagues/invite/{lg['invite_code']}", headers=user(2)).json()
    assert prev["member_count"] == 1 and prev["is_member"] is False and "invite_code" not in prev
    assert api.get("/api/leagues/invite/nope", headers=user(2)).status_code == 404


def test_join_closes_at_first_kickoff_of_window(api):
    lg = make_league(api)
    add_match(1, T0 + timedelta(days=3))
    add_match(2, T0 + timedelta(days=1))
    add_match(3, T0 + timedelta(hours=1), comp=2014)   # other Competition: irrelevant
    closes = api.get(f"/api/leagues/{lg['id']}", headers=user(1)).json()["join_closes_at"]
    assert datetime.fromisoformat(closes) == T0 + timedelta(days=1)
    Clock.now = T0 + timedelta(days=1) - timedelta(seconds=1)
    assert join(api, lg, 2).status_code == 200
    Clock.now = T0 + timedelta(days=1)
    assert join(api, lg, 3).status_code == 409


def test_join_closes_at_window_start_without_matches_and_when_not_open(api):
    lg = make_league(api, start=T0.date() + timedelta(days=1))
    assert join(api, lg, 2).status_code == 200
    Clock.now = T0 + timedelta(days=2)
    assert join(api, lg, 3).status_code == 409
    Clock.now = T0
    with get_engine().begin() as c:
        c.execute(text("UPDATE leagues SET status='cancelled'"))
    assert join(api, lg, 4).status_code == 409


def test_non_member_cannot_see_league(api):
    lg = make_league(api)
    for path in ("", "/standings", "/matches"):
        assert api.get(f"/api/leagues/{lg['id']}{path}", headers=user(2)).status_code == 404


def test_status_machine():
    ok = [("open", "active"), ("open", "cancelled"), ("active", "settling"), ("settling", "settled")]
    for a, b in ok:
        assert leagues_mod.can_transition(a, b)
    for a, b in [("open", "settled"), ("active", "open"), ("settled", "active"), ("cancelled", "open"),
                 ("active", "cancelled"), ("settling", "active")]:
        assert not leagues_mod.can_transition(a, b)


def test_transition_is_guarded_and_repeatable(api):
    lg = make_league(api)
    with get_engine().begin() as c:
        assert leagues_mod.transition(c, lg["id"], "open", "active") is True
        assert leagues_mod.transition(c, lg["id"], "open", "active") is False   # already moved
        with pytest.raises(Exception):
            leagues_mod.transition(c, lg["id"], "active", "settled")


# --- Predictions and Deadline ---------------------------------------------

def test_prediction_edit_withdraw_until_deadline(api):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=2))
    r = predict(api, lg, m, 1, 2, 1)
    assert r.json() == {"match_id": m, "home_goals": 2, "away_goals": 1, "outcome": "home"}
    assert predict(api, lg, m, 1, 0, 0).json()["outcome"] == "draw"      # last version stands
    rows = api.get(f"/api/leagues/{lg['id']}/matches", headers=user(1)).json()["matches"]
    assert rows[0]["prediction"] == {"home_goals": 0, "away_goals": 0} and rows[0]["can_predict"]
    assert api.delete(f"/api/leagues/{lg['id']}/matches/{m}/prediction", headers=user(1)).status_code == 204
    rows = api.get(f"/api/leagues/{lg['id']}/matches", headers=user(1)).json()["matches"]
    assert rows[0]["prediction"] is None


def test_deadline_is_kickoff_and_uses_server_time(api):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=2))
    assert predict(api, lg, m, 1).status_code == 200
    Clock.now = T0 + timedelta(hours=2) - timedelta(seconds=1)
    assert predict(api, lg, m, 1, 3, 3).status_code == 200
    Clock.now = T0 + timedelta(hours=2)
    assert predict(api, lg, m, 1, 4, 4).status_code == 409
    assert api.delete(f"/api/leagues/{lg['id']}/matches/{m}/prediction", headers=user(1)).status_code == 409
    rows = api.get(f"/api/leagues/{lg['id']}/matches", headers=user(1)).json()["matches"]
    assert rows[0]["prediction"] == {"home_goals": 3, "away_goals": 3} and not rows[0]["can_predict"]


def test_rescheduled_match_carries_its_deadline(api):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=2))
    Clock.now = T0 + timedelta(hours=3)
    assert predict(api, lg, m, 1).status_code == 409
    with get_engine().begin() as c:     # MatchData sync moved the match
        c.execute(text("UPDATE matches SET kickoff = :k, status='TIMED'"), {"k": T0 + timedelta(days=1)})
    assert predict(api, lg, m, 1).status_code == 200


def test_prediction_rules(api):
    lg = make_league(api)
    in_window = add_match(1, T0 + timedelta(hours=2))
    outside = add_match(2, T0 + timedelta(days=30))
    other_comp = add_match(3, T0 + timedelta(hours=2), comp=2014)
    cancelled = add_match(4, T0 + timedelta(hours=2), status="CANCELLED")
    assert predict(api, lg, in_window, 1, -1, 0).status_code == 422
    assert predict(api, lg, in_window, 1, 100, 0).status_code == 422
    for m in (outside, other_comp):
        assert predict(api, lg, m, 1).status_code == 422
    assert predict(api, lg, cancelled, 1).status_code == 409
    assert predict(api, lg, 12345, 1).status_code == 404
    assert predict(api, lg, in_window, 2).status_code == 404      # not a Member
    api.put(f"/api/leagues/{lg['id']}/matches/{in_window}/prediction", headers=user(1),
            json={"home_goals": 1})
    with get_engine().begin() as c:
        c.execute(text("UPDATE leagues SET status='settling'"))
    assert predict(api, lg, in_window, 1).status_code == 409


def test_predictions_are_per_league(api):
    a, b = make_league(api), make_league(api)
    m = add_match(1, T0 + timedelta(hours=2))
    predict(api, a, m, 1, 2, 0)
    predict(api, b, m, 1, 0, 2)
    get = lambda lg: api.get(f"/api/leagues/{lg['id']}/matches", headers=user(1)).json()["matches"][0]
    assert get(a)["prediction"]["home_goals"] == 2 and get(b)["prediction"]["home_goals"] == 0


def test_reveal_at_kickoff_only(api):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=2))
    join(api, lg, 2)
    predict(api, lg, m, 1, 2, 1)
    predict(api, lg, m, 2, 0, 0)
    url = f"/api/leagues/{lg['id']}/matches/{m}/predictions"

    before = api.get(url, headers=user(1)).json()
    assert before["revealed"] is False
    by = {p["username"]: p for p in before["predictions"]}
    assert by["u1"]["home_goals"] == 2                                  # own score
    assert by["u2"]["predicted"] is True and by["u2"]["home_goals"] is None   # only that they predicted
    assert "home_goals" not in str(api.get(f"/api/leagues/{lg['id']}/matches", headers=user(1)).json()["matches"][0]["predicted_count"])

    Clock.now = T0 + timedelta(hours=2)
    after = api.get(url, headers=user(1)).json()
    assert after["revealed"] is True
    assert {p["username"]: (p["home_goals"], p["away_goals"]) for p in after["predictions"]} \
        == {"u1": (2, 1), "u2": (0, 0)}


def test_reveal_unpredicted_member_shows_not_predicted(api):
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=2))
    join(api, lg, 2)
    Clock.now = T0 + timedelta(hours=2)
    out = api.get(f"/api/leagues/{lg['id']}/matches/{m}/predictions", headers=user(1)).json()
    assert [p["predicted"] for p in out["predictions"]] == [False, False]


# --- Standings -------------------------------------------------------------

def standings(api, lg, who=1):
    return api.get(f"/api/leagues/{lg['id']}/standings", headers=user(who)).json()


def test_standings_points_exact_tiebreak_and_missed(api):
    lg = make_league(api)
    m1 = add_match(1, T0 + timedelta(hours=1))
    m2 = add_match(2, T0 + timedelta(hours=2))
    m3 = add_match(3, T0 + timedelta(hours=3))
    for w in (2, 3):
        join(api, lg, w)
    predict(api, lg, m1, 1, 2, 1)      # u1: exact (4)
    predict(api, lg, m2, 1, 0, 0)      #     wrong (0)
    predict(api, lg, m1, 2, 3, 0)      # u2: outcome (1)
    predict(api, lg, m2, 2, 1, 0)      #     outcome (1)  -> 2 total... plus m3 below
    predict(api, lg, m3, 2, 2, 0)      #     outcome (1)  -> 3
    predict(api, lg, m1, 3, 1, 0)      # u3: outcome (1)
    predict(api, lg, m2, 3, 2, 1)      #     exact (4)
    predict(api, lg, m3, 3, 1, 0)      #     exact (4)
    with get_engine().begin() as c:
        c.execute(text("UPDATE matches SET status='FINISHED', home_goals=2, away_goals=1 WHERE id=:i"), {"i": m1})
        c.execute(text("UPDATE matches SET status='FINISHED', home_goals=2, away_goals=1 WHERE id=:i"), {"i": m2})
        c.execute(text("UPDATE matches SET status='FINISHED', home_goals=1, away_goals=0 WHERE id=:i"), {"i": m3})
    Clock.now = T0 + timedelta(days=1)
    out = standings(api, lg)
    by = {r["username"]: r for r in out["standings"]}
    assert (by["u1"]["points"], by["u1"]["exact"]) == (4, 1)      # m3 missed = 0
    assert (by["u2"]["points"], by["u2"]["exact"]) == (3, 0)
    assert (by["u3"]["points"], by["u3"]["exact"]) == (9, 2)
    assert [r["username"] for r in out["standings"]] == ["u3", "u1", "u2"]
    assert out["matches_scored"] == 3 and out["matches_pending"] == 0


def test_standings_is_pure_read_and_ignores_dropped_and_unfinished(api):
    lg = make_league(api)
    ids = [add_match(i, T0 + timedelta(hours=i)) for i in (1, 2, 3, 4)]
    for m, s in zip(ids, [(1, 1), (1, 0), (1, 0), (3, 0)]):
        predict(api, lg, m, 1, *s)
    with get_engine().begin() as c:     # results arrive after the Predictions were made
        for m, status, score in zip(ids, ["FINISHED", "CANCELLED", "POSTPONED", "AWARDED"],
                                    [(1, 1), (None, None), (None, None), (3, 0)]):
            c.execute(text("UPDATE matches SET status=:s, home_goals=:h, away_goals=:a WHERE id=:i"),
                      {"s": status, "h": score[0], "a": score[1], "i": m})
    Clock.now = T0 + timedelta(days=1)

    def snapshot():
        with get_engine().connect() as c:
            return c.execute(text("SELECT (SELECT count(*) FROM predictions), "
                                  "(SELECT status FROM leagues LIMIT 1)")).one()
    before = snapshot()
    out = standings(api, lg)
    assert out["standings"][0]["points"] == 8       # done exact 4 + awarded exact 4
    assert out["matches_scored"] == 2 and out["matches_pending"] == 1
    assert snapshot() == before

    Clock.now = T0 + timedelta(days=19)    # past window end (day 11) + 7-day grace
    assert standings(api, lg)["matches_pending"] == 0


def test_standings_ties_share_rank(api):
    lg = make_league(api)
    add_match(1, T0 + timedelta(hours=1), status="FINISHED", score=(1, 0))
    join(api, lg, 2)
    Clock.now = T0 + timedelta(days=1)
    assert [r["rank"] for r in standings(api, lg)["standings"]] == [1, 1]
