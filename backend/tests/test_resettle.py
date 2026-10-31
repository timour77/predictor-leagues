from datetime import timedelta

import pytest

from app import settlement
from app.errors import Conflict, NotFound
from scripts import resettle_league
from tests.test_leagues_api import T0, add_match, api, join, make_league, predict  # noqa: F401
from tests.test_settlement import GRACE_END, finish, q, run, status_of

LATER = GRACE_END + timedelta(days=30)


def settled_league(api):
    """u1 predicted an exact 2-1, u2 only the outcome; settled with u1 the winner."""
    lg = make_league(api)
    m = add_match(1, T0 + timedelta(hours=1))
    join(api, lg, 2)
    predict(api, lg, m, 1, 2, 1)
    predict(api, lg, m, 2, 1, 0)
    finish(m, 2, 1)
    run(settlement.start_leagues, T0)
    run(settlement.settle_leagues, GRACE_END)
    return lg, m


def final_rows():
    return q("SELECT u.telegram_id, rank, points, exact FROM final_standings f JOIN users u ON u.id=f.user_id "
             "ORDER BY rank, u.telegram_id")


def trophy_holders():
    return q("SELECT u.telegram_id FROM trophies t JOIN users u ON u.id=t.user_id ORDER BY 1")


def resettle(lg, **kw):
    return run(lambda c, now: settlement.resettle_league(c, lg["id"], now, **kw), LATER)


def uid(telegram_id):
    return q("SELECT id FROM users WHERE telegram_id=:t", t=telegram_id)[0][0]


def test_resettle_after_a_correction_that_leaves_nobody_scoring_removes_the_trophy(api):
    lg, m = settled_league(api)
    assert trophy_holders() == [(8001,)]
    finish(m, 0, 1)                      # corrected to an away win: both predicted a home win
    resettle(lg)
    assert final_rows() == [(8001, 1, 0, 0), (8002, 1, 0, 0)]
    assert trophy_holders() == []
    assert status_of(lg) == "settled"


def test_resettle_flips_the_winner(api):
    lg, m = settled_league(api)
    finish(m, 1, 0)                      # corrected to 1-0: u2 is now exact, u1 outcome only
    out = resettle(lg)
    assert out["changed"] is True
    assert out["trophies"] == {"added": [uid(8002)], "removed": [uid(8001)]}
    assert final_rows() == [(8002, 1, 4, 1), (8001, 2, 1, 0)]
    assert trophy_holders() == [(8002,)]


def test_resettle_is_idempotent_and_reports_no_change(api):
    lg, m = settled_league(api)
    before = (final_rows(), trophy_holders(), q("SELECT awarded_at FROM trophies"))
    out = resettle(lg)
    assert out["changed"] is False and out["trophies"] == {"added": [], "removed": []}
    assert (final_rows(), trophy_holders(), q("SELECT awarded_at FROM trophies")) == before
    finish(m, 1, 0)
    resettle(lg)
    once = (final_rows(), trophy_holders())
    assert resettle(lg)["changed"] is False
    assert (final_rows(), trophy_holders()) == once


def test_dry_run_reports_the_diff_and_writes_nothing(api):
    lg, m = settled_league(api)
    before = (final_rows(), trophy_holders())
    finish(m, 1, 0)
    out = resettle(lg, dry_run=True)
    assert out["changed"] is True and out["dry_run"] is True
    by_user = {r["user_id"]: r for r in out["standings"]}
    assert by_user[uid(8001)]["old"] == {"rank": 1, "points": 4, "exact": 1}
    assert by_user[uid(8001)]["new"] == {"rank": 2, "points": 1, "exact": 0}
    assert by_user[uid(8002)]["old"] == {"rank": 2, "points": 1, "exact": 0}
    assert by_user[uid(8002)]["new"] == {"rank": 1, "points": 4, "exact": 1}
    assert out["trophies"] == {"added": [uid(8002)], "removed": [uid(8001)]}
    assert (final_rows(), trophy_holders()) == before


def test_resettle_refuses_leagues_that_are_not_settled(api):
    lg = make_league(api)
    assert status_of(lg) in ("open", "active")
    with pytest.raises(Conflict):
        resettle(lg)
    run(settlement.start_leagues, T0 + timedelta(days=30))
    with pytest.raises(Conflict):
        resettle(lg)                     # active or cancelled, never settled
    with pytest.raises(NotFound):
        run(lambda c, now: settlement.resettle_league(c, 999999, now), LATER)


def test_resettle_keeps_settled_at_and_the_award_time_of_a_kept_winner(api):
    lg, m = settled_league(api)
    settled_at = q("SELECT settled_at FROM leagues WHERE id=:i", i=lg["id"])
    awarded = q("SELECT awarded_at FROM trophies WHERE user_id=:u", u=uid(8001))
    finish(m, 3, 1)                      # both outcome-only now: a tie, u1 keeps the Trophy, u2 gains one
    resettle(lg)
    assert trophy_holders() == [(8001,), (8002,)]
    assert q("SELECT settled_at FROM leagues WHERE id=:i", i=lg["id"]) == settled_at
    assert q("SELECT awarded_at FROM trophies WHERE user_id=:u", u=uid(8001)) == awarded


def test_notifications_only_when_asked_and_only_once(api):
    lg, m = settled_league(api)
    finish(m, 1, 0)
    resettle(lg)
    assert q("SELECT count(*) FROM notifications")[0][0] == 0
    finish(m, 2, 0)
    resettle(lg, notify=True)
    rows = q("SELECT kind FROM notifications")
    assert rows and {r[0] for r in rows} == {"league_resettled"}
    n = len(rows)
    resettle(lg, notify=True)            # nothing changed since: no second message
    assert q("SELECT count(*) FROM notifications")[0][0] == n


def test_script_dry_run_prints_diff_and_a_real_run_applies(api, capsys):
    lg, m = settled_league(api)
    finish(m, 0, 1)
    resettle_league.main([str(lg["id"]), "--dry-run"])
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "trophy" in out.lower()
    assert trophy_holders() == [(8001,)]
    resettle_league.main([str(lg["id"])])
    assert trophy_holders() == []
    assert "DRY RUN" not in capsys.readouterr().out


def test_script_exits_nonzero_for_a_league_that_is_not_settled(api):
    lg = make_league(api)
    with pytest.raises(SystemExit) as e:
        resettle_league.main([str(lg["id"])])
    assert e.value.code != 0
