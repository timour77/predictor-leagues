"""Scoring: pure functions, no I/O. Rules from ticket #8 (see GLOSSARY.md).

A correct outcome earns 1 point and an exact score 3 more. A Missed match scores 0.
Standings tiebreak: number of exact scores; Members still tied share a rank.
"""
from dataclasses import dataclass
from datetime import datetime

OUTCOME_POINTS = 1
EXACT_SCORE_POINTS = 3

Score = tuple[int, int]


@dataclass(frozen=True)
class Final:
    """The match counts with this result (played, or awarded by a governing body)."""
    home_goals: int
    away_goals: int


@dataclass(frozen=True)
class Pending:
    """Not decided yet; may still be played inside the Grace period."""


@dataclass(frozen=True)
class Dropped:
    """Scores nothing for anyone; Predictions on it are ignored."""


MatchState = Final | Pending | Dropped


def outcome(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def match_state(
    status: str,
    home_goals: int | None,
    away_goals: int | None,
    now: datetime,
    grace_ends: datetime,
) -> MatchState:
    """Classify a match from the stored football-data.org status."""
    if status == "CANCELLED":
        return Dropped()
    if status in ("FINISHED", "AWARDED") and home_goals is not None and away_goals is not None:
        return Final(home_goals, away_goals)
    # Postponed, suspended/abandoned or still to be played: wait until the Grace period ends.
    return Dropped() if now >= grace_ends else Pending()


def score_prediction(prediction: Score | None, actual: Score) -> tuple[int, bool]:
    """(points, is_exact). No Prediction (a Missed match) is 0 points and not exact."""
    if prediction is None:
        return 0, False
    points = OUTCOME_POINTS if outcome(*prediction) == outcome(*actual) else 0
    exact = tuple(prediction) == tuple(actual)
    if exact:
        points += EXACT_SCORE_POINTS
    return points, exact


def rank_standings(rows: list[dict]) -> list[dict]:
    """Sort by points then exact scores and add `rank`; equal rows share a rank (1, 2, 2, 4)."""
    ordered = sorted(rows, key=lambda r: (-r["points"], -r["exact"], r["user_id"]))
    ranked, prev, prev_rank = [], None, 0
    for i, r in enumerate(ordered, start=1):
        key = (r["points"], r["exact"])
        prev_rank = prev_rank if key == prev else i
        prev = key
        ranked.append({**r, "rank": prev_rank})
    return ranked
