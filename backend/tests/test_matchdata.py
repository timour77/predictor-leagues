from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app import matchdata
from app.db import get_engine
from app.matchdata.football_data import FootballDataClient
from app.schema import matches

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)


def match(ext, comp=2021, kickoff=None, status="SCHEDULED", home=None, away=None):
    return {
        "external_id": ext, "competition_id": comp, "competition_name": f"Comp {comp}",
        "matchday": 1, "home_team": "A", "away_team": "B", "home_crest": None,
        "away_crest": None, "kickoff": kickoff or NOW + timedelta(days=3), "status": status,
        "home_goals": home, "away_goals": away,
    }


class FakeClient:
    def __init__(self, data=None, failing=()):
        self.data = data or {}
        self.failing = set(failing)
        self.calls = []

    def competition_matches(self, competition_id):
        self.calls.append(competition_id)
        if competition_id in self.failing:
            raise RuntimeError("boom")
        return self.data.get(competition_id, [])


@pytest.fixture
def conn(migrated_db):
    with get_engine().begin() as c:
        c.execute(text("TRUNCATE matches, competition_sync RESTART IDENTITY"))
    with get_engine().begin() as c:
        yield c


def rows(conn):
    return {r["external_id"]: r for r in conn.execute(select(matches)).mappings()}


# --- adapter ---------------------------------------------------------------

class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response, self.requests = response, []

    def get(self, url, headers=None, timeout=None):
        self.requests.append((url, headers, timeout))
        return self.response


def test_adapter_normalises_football_data_payload():
    payload = {"matches": [{
        "id": 99, "utcDate": "2026-06-11T19:00:00Z", "status": "FINISHED", "matchday": 3,
        "competition": {"id": 2000, "name": "FIFA World Cup"},
        "homeTeam": {"name": "Mexico", "crest": "m.svg"}, "awayTeam": {"name": "Poland", "crest": None},
        "score": {"fullTime": {"home": 2, "away": 1}},
    }, {
        "id": 100, "utcDate": "2026-06-12T19:00:00Z", "status": "TIMED",
        "competition": {"id": 2000, "name": "FIFA World Cup"},
        "homeTeam": {"name": "TBD"}, "awayTeam": {"name": "TBD"}, "score": {"fullTime": {}},
    }]}
    session = FakeSession(FakeResponse(payload))
    out = FootballDataClient("key", session=session).competition_matches(2000)
    assert session.requests[0][0].endswith("/competitions/2000/matches")
    assert session.requests[0][1] == {"X-Auth-Token": "key"}
    assert out[0] == {
        "external_id": 99, "competition_id": 2000, "competition_name": "FIFA World Cup",
        "matchday": 3, "home_team": "Mexico", "away_team": "Poland", "home_crest": "m.svg",
        "away_crest": None, "kickoff": datetime(2026, 6, 11, 19, tzinfo=timezone.utc),
        "status": "FINISHED", "home_goals": 2, "away_goals": 1,
    }
    assert out[1]["home_goals"] is None and out[1]["status"] == "TIMED"


def test_adapter_wraps_http_errors():
    with pytest.raises(matchdata.MatchDataError):
        FootballDataClient("k", session=FakeSession(FakeResponse({}, status=429))).competition_matches(1)


# --- sync ------------------------------------------------------------------

def test_sync_upserts_and_is_idempotent(conn):
    client = FakeClient({2021: [match(1), match(2, home=None)]})
    matchdata.sync_matches(conn, client, now=NOW, competition_ids=[2021])
    matchdata.sync_matches(conn, client, now=NOW, competition_ids=[2021])
    assert set(rows(conn)) == {1, 2}


def test_sync_updates_score_status_and_reschedule(conn):
    old = NOW + timedelta(days=3)
    client = FakeClient({2021: [match(1, kickoff=old)]})
    matchdata.sync_matches(conn, client, now=NOW, competition_ids=[2021])
    new = old + timedelta(days=2)
    client.data[2021] = [match(1, kickoff=new, status="FINISHED", home=2, away=0)]
    matchdata.sync_matches(conn, client, now=NOW, competition_ids=[2021])
    r = rows(conn)[1]
    assert r["kickoff"] == new and r["status"] == "FINISHED" and (r["home_goals"], r["away_goals"]) == (2, 0)


@pytest.mark.parametrize("status", ["POSTPONED", "CANCELLED"])
def test_postponed_and_cancelled_stored_as_is(conn, status):
    client = FakeClient({2021: [match(1, status=status)]})
    matchdata.sync_matches(conn, client, now=NOW, competition_ids=[2021])
    assert rows(conn)[1]["status"] == status


def test_sync_refreshes_at_most_8_round_robin(conn):
    ids = list(range(100, 112))  # 12 competitions
    client = FakeClient({i: [match(i, comp=i)] for i in ids})
    first = matchdata.sync_matches(conn, client, now=NOW, competition_ids=ids)
    assert len(first["synced"]) == 8
    second = matchdata.sync_matches(conn, client, now=NOW + timedelta(minutes=1), competition_ids=ids)
    assert len(second["synced"]) == 8
    assert set(first["synced"]) | set(second["synced"]) == set(ids)
    assert set(second["synced"]) >= set(ids) - set(first["synced"])  # the unsynced four go first


def test_priority_competitions_go_first_even_if_recently_synced(conn):
    ids = list(range(100, 112))
    client = FakeClient({i: [match(i, comp=i)] for i in ids})
    matchdata.sync_matches(conn, client, now=NOW, competition_ids=ids)  # 100-107 now stale-ish
    client.calls.clear()
    out = matchdata.sync_matches(conn, client, now=NOW + timedelta(minutes=1),
                                 competition_ids=ids, priority_ids=[100])
    assert out["synced"][0] == 100


def test_competitions_with_matches_near_kickoff_are_prioritised(conn):
    ids = list(range(100, 112))
    client = FakeClient({i: [match(i, comp=i, kickoff=NOW + timedelta(days=9))] for i in ids})
    client.data[105] = [match(105, comp=105, kickoff=NOW + timedelta(minutes=30))]
    matchdata.sync_matches(conn, client, now=NOW, competition_ids=ids)
    out = matchdata.sync_matches(conn, client, now=NOW + timedelta(minutes=1), competition_ids=ids)
    assert 105 in out["synced"][:1]


def test_no_active_leagues_yet_means_no_priority(conn):
    assert matchdata.priority_competition_ids(conn, NOW) == []


def test_failing_competition_does_not_block_others_or_starve(conn):
    ids = [100, 101, 102]
    client = FakeClient({i: [match(i, comp=i)] for i in ids}, failing={100})
    out = matchdata.sync_matches(conn, client, now=NOW, competition_ids=ids)
    assert set(out["synced"]) == {101, 102} and list(out["failed"]) == [100]
    assert set(rows(conn)) == {101, 102}
    row = conn.execute(text("SELECT last_error, last_synced_at FROM competition_sync WHERE competition_id=100")).one()
    assert row.last_error == "boom" and row.last_synced_at is None


def test_list_matches_filters(conn):
    client = FakeClient({2021: [match(1), match(2, kickoff=NOW + timedelta(days=30))],
                         2001: [match(3, comp=2001)]})
    matchdata.sync_matches(conn, client, now=NOW, competition_ids=[2021, 2001])
    assert {m["external_id"] for m in matchdata.list_matches(conn)} == {1, 2, 3}
    assert {m["external_id"] for m in matchdata.list_matches(conn, competition_id=2001)} == {3}
    got = matchdata.list_matches(conn, date_to=NOW + timedelta(days=5))
    assert {m["external_id"] for m in got} == {1, 3}
