from datetime import datetime, timedelta, timezone

import pytest

from app import scoring
from app.scoring import Final, Pending, Dropped

END = datetime(2026, 6, 30, tzinfo=timezone.utc)  # exclusive end of the Window
NOW = END - timedelta(days=1)


def test_outcome_is_derived_from_score():
    assert scoring.outcome(2, 1) == "home"
    assert scoring.outcome(0, 3) == "away"
    assert scoring.outcome(1, 1) == "draw"


@pytest.mark.parametrize("pred,actual,points,exact", [
    ((2, 1), (2, 1), 4, True),    # outcome 1 + exact 3
    ((3, 0), (2, 1), 1, False),   # right outcome only
    ((1, 1), (0, 0), 1, False),   # draw, wrong score
    ((0, 0), (0, 0), 4, True),
    ((2, 1), (1, 2), 0, False),
    ((1, 0), (1, 1), 0, False),
])
def test_score_prediction(pred, actual, points, exact):
    assert scoring.score_prediction(pred, actual) == (points, exact)


def test_missed_match_scores_zero_and_is_not_exact():
    assert scoring.score_prediction(None, (2, 1)) == (0, False)


def state(status, hg=None, ag=None, now=NOW):
    return scoring.match_state(status, hg, ag, now=now, grace_ends=END + timedelta(days=7))


def test_finished_and_awarded_matches_are_final_with_their_score():
    assert state("FINISHED", 2, 1) == Final(2, 1)
    assert state("AWARDED", 3, 0) == Final(3, 0)  # walkover scores by awarded result


def test_cancelled_is_dropped_immediately():
    assert state("CANCELLED") == Dropped()


@pytest.mark.parametrize("status", ["SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "POSTPONED", "SUSPENDED"])
def test_unfinished_match_is_pending_inside_grace_then_dropped(status):
    assert state(status) == Pending()
    assert state(status, now=END + timedelta(days=6)) == Pending()
    assert state(status, now=END + timedelta(days=7)) == Dropped()


def test_finished_without_score_is_not_final():
    assert state("FINISHED") == Pending()


def test_postponed_match_played_in_grace_counts():
    assert state("FINISHED", 1, 0, now=END + timedelta(days=3)) == Final(1, 0)


def test_standings_rank_by_points_then_exact_scores_ties_share_rank():
    rows = [
        {"user_id": 1, "points": 10, "exact": 1},
        {"user_id": 2, "points": 10, "exact": 2},
        {"user_id": 3, "points": 10, "exact": 2},
        {"user_id": 4, "points": 12, "exact": 0},
        {"user_id": 5, "points": 3, "exact": 0},
    ]
    ranked = scoring.rank_standings(rows)
    assert [(r["user_id"], r["rank"]) for r in ranked] == [(4, 1), (2, 2), (3, 2), (1, 4), (5, 5)]


def test_standings_zero_members():
    assert scoring.rank_standings([]) == []
