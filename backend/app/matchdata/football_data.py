"""football-data.org v4 adapter. Returns normalised match dicts; knows nothing about our DB."""
from datetime import datetime

import requests

BASE_URL = "https://api.football-data.org/v4"
TIMEOUT_SECONDS = 10


class MatchDataError(RuntimeError):
    pass


class FootballDataClient:
    def __init__(self, api_key: str, session=None):
        self._headers = {"X-Auth-Token": api_key}
        self._session = session or requests.Session()

    def competition_matches(self, competition_id: int) -> list[dict]:
        """All matches of a Competition's current season."""
        url = f"{BASE_URL}/competitions/{competition_id}/matches"
        try:
            resp = self._session.get(url, headers=self._headers, timeout=TIMEOUT_SECONDS)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:  # network, HTTP status (429 rate limit included), bad JSON
            raise MatchDataError(f"football-data.org {competition_id}: {e}") from e
        return [_normalise(m, competition_id) for m in payload.get("matches", [])]


def _normalise(m: dict, competition_id: int) -> dict:
    comp = m.get("competition") or {}
    full_time = (m.get("score") or {}).get("fullTime") or {}
    return {
        "external_id": m["id"],
        "competition_id": comp.get("id", competition_id),
        "competition_name": comp.get("name"),
        "matchday": m.get("matchday"),
        "home_team": m["homeTeam"].get("name") or "TBD",
        "away_team": m["awayTeam"].get("name") or "TBD",
        "home_crest": m["homeTeam"].get("crest"),
        "away_crest": m["awayTeam"].get("crest"),
        "kickoff": datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")),
        "status": m["status"],
        "home_goals": full_time.get("home"),
        "away_goals": full_time.get("away"),
    }
