"""MatchData: the only place that talks to football-data.org. Everything else reads `matches`."""
from app.matchdata.football_data import FootballDataClient, MatchDataError
from app.matchdata.sync import list_matches, priority_competition_ids, sync_matches

ATTRIBUTION = "Football data provided by the Football-Data.org API"

__all__ = [
    "ATTRIBUTION", "FootballDataClient", "MatchDataError",
    "list_matches", "priority_competition_ids", "sync_matches",
]
