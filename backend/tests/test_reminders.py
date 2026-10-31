from datetime import timedelta

import pytest
from sqlalchemy import text

from app import config, notifications, reminders
from app.db import get_engine
from tests.test_api import header  # noqa: F401
from tests.test_leagues_api import T0, add_match, api, join, make_league, predict, user  # noqa: F401

KICKOFF = T0 + timedelta(days=1, hours=5)  # Jun 2 17:00 UTC; Leagues start Jun 2, so Members can still join
MARK = KICKOFF - timedelta(hours=1)        # the Reminder is due from here
LINK = "https://t.me/test_bot/app"


@pytest.fixture(autouse=True)
def mini_app_link(monkeypatch):
    monkeypatch.setattr(config, "MINI_APP_LINK", LINK)


def q(sql, **params):
    with get_engine().connect() as c:
        return c.execute(text(sql), params).all()


def activate(*leagues):
    """Make the Leagues active and every Member a Member since long before the Reminder hour."""
    with get_engine().begin() as c:
        for lg in leagues:
            c.execute(text("UPDATE leagues SET status='active' WHERE id=:i"), {"i": lg["id"]})
        c.execute(text("UPDATE league_members SET joined_at=:t"), {"t": T0 - timedelta(days=1)})


def queue(now):
    with get_engine().begin() as c:
        return reminders.queue_reminders(c, now)


def deliver(now):
    sent = []

    def sender(tg, body, button=None):
        sent.append((tg, body, button))

    with get_engine().begin() as c:
        notifications.deliver_pending(c, sender, now)
    return sent


def two_member_league(api, start=T0.date() + timedelta(days=1)):
    lg = make_league(api, start=start)
    join(api, lg, 2)
    return lg


def test_reminder_goes_to_members_without_a_prediction_with_deep_link_button(api):
    lg = two_member_league(api)
    m = add_match(1, KICKOFF)
    activate(lg)
    predict(api, lg, m, 1)                       # U1 already predicted
    assert queue(MARK) == {"queued": 1}
    sent = deliver(MARK)
    assert [tg for tg, _, _ in sent] == [8002]
    _, body, button = sent[0]
    assert "starts in an hour" in body.lower() and "A" in body and "B" in body and "Friends" in body
    assert button == ("Make a prediction", f"{LINK}?startapp=league_{lg['id']}")


def test_same_kickoff_matches_and_leagues_are_one_message(api):
    l1, l2 = two_member_league(api), two_member_league(api)
    add_match(1, KICKOFF)
    add_match(2, KICKOFF)
    activate(l1, l2)
    assert queue(MARK) == {"queued": 2}          # one per user
    sent = deliver(MARK)
    assert len(sent) == 2
    assert sent[0][1].count("A – B") == 2
    # several Leagues or matches: no single destination, so the button opens the Leagues list
    assert sent[0][2] == ("Make a prediction", LINK)


def test_different_kickoffs_are_separate_messages(api):
    lg = two_member_league(api)
    add_match(1, KICKOFF)
    add_match(2, KICKOFF + timedelta(hours=2))
    activate(lg)
    queue(MARK)
    assert len(deliver(MARK)) == 2
    queue(MARK + timedelta(hours=2))
    assert len(deliver(MARK + timedelta(hours=2))) == 2
    assert q("SELECT count(*) FROM notifications") == [(4,)]


def test_not_due_before_the_hour(api):
    lg = two_member_league(api)
    add_match(1, KICKOFF)
    activate(lg)
    assert queue(MARK - timedelta(minutes=1)) == {"queued": 0}


def test_missed_hour_is_not_made_up(api):
    lg = two_member_league(api)
    add_match(1, KICKOFF)
    activate(lg)
    assert queue(MARK + reminders.CATCH_UP + timedelta(minutes=1)) == {"queued": 0}


def test_skipped_ticks_within_catch_up_still_queue(api):
    lg = two_member_league(api)
    add_match(1, KICKOFF)
    activate(lg)
    assert queue(MARK + reminders.CATCH_UP - timedelta(minutes=1)) == {"queued": 2}


def test_rerun_is_idempotent_even_after_delivery(api):
    lg = two_member_league(api)
    add_match(1, KICKOFF)
    activate(lg)
    assert queue(MARK) == {"queued": 2}
    assert queue(MARK + timedelta(minutes=1)) == {"queued": 0}
    deliver(MARK)
    queue(MARK + timedelta(minutes=2))
    assert q("SELECT count(*) FROM notifications WHERE kind='reminder'") == [(2,)]
    assert deliver(MARK + timedelta(minutes=3)) == []


def test_no_reminder_when_switched_off(api):
    lg = two_member_league(api)
    add_match(1, KICKOFF)
    activate(lg)
    api.put("/api/me/reminders", headers=user(2), json={"enabled": False})
    assert queue(MARK) == {"queued": 1}
    assert [tg for tg, _, _ in deliver(MARK)] == [8001]


def test_switching_off_after_queueing_still_suppresses_the_send(api):
    lg = two_member_league(api)
    add_match(1, KICKOFF)
    activate(lg)
    queue(MARK)
    api.put("/api/me/reminders", headers=user(2), json={"enabled": False})
    assert [tg for tg, _, _ in deliver(MARK)] == [8001]


def test_prediction_made_after_queueing_suppresses_the_send_and_is_not_retried(api):
    lg = two_member_league(api)
    m = add_match(1, KICKOFF)
    activate(lg)
    queue(MARK)
    predict(api, lg, m, 2)
    assert [tg for tg, _, _ in deliver(MARK)] == [8001]
    assert deliver(MARK + timedelta(minutes=1)) == []
    assert q("SELECT count(*) FROM notifications WHERE sent_at IS NULL") == [(0,)]


def test_late_joiner_gets_no_reminder(api):
    lg = two_member_league(api)
    add_match(1, KICKOFF)
    activate(lg)
    join(api, lg, 3)
    with get_engine().begin() as c:
        c.execute(text("UPDATE league_members SET joined_at=:t WHERE user_id="
                       "(SELECT id FROM users WHERE telegram_id=8003)"), {"t": MARK + timedelta(minutes=5)})
    assert queue(MARK + timedelta(minutes=10)) == {"queued": 2}


def test_league_started_after_the_hour_is_skipped(api):
    # Window starts Jun 3 00:00; the match at 00:30 has its hour before that.
    lg = two_member_league(api, start=T0.date() + timedelta(days=2))
    add_match(1, T0.replace(hour=0, minute=30) + timedelta(days=2))
    activate(lg)
    assert queue(T0.replace(hour=23, minute=30) + timedelta(days=1)) == {"queued": 0}


def test_only_active_leagues_with_the_match_in_window_and_competition(api):
    two_member_league(api)                       # stays open
    other_comp = make_league(api, start=T0.date() + timedelta(days=1), comps=(2001,))
    join(api, other_comp, 2)
    add_match(1, KICKOFF)
    activate(other_comp)
    assert queue(MARK) == {"queued": 0}


def test_postponed_match_is_not_reminded(api):
    lg = two_member_league(api)
    add_match(1, KICKOFF, status="POSTPONED")
    activate(lg)
    assert queue(MARK) == {"queued": 0}


def test_profile_toggle_defaults_on_and_round_trips(api):
    assert api.get("/api/me", headers=user(1)).json()["reminders_enabled"] is True
    assert api.put("/api/me/reminders", headers=user(1), json={"enabled": False}).json() == {"reminders_enabled": False}
    assert api.get("/api/me", headers=user(1)).json()["reminders_enabled"] is False
    assert api.put("/api/me/reminders", headers=user(1), json={"enabled": "nope"}).status_code == 422


def test_blocked_bot_uses_ordinary_retries(api):
    lg = two_member_league(api)
    add_match(1, KICKOFF)
    activate(lg)
    queue(MARK)

    def blocked(tg, body, button=None):
        raise RuntimeError("403 bot was blocked by the user")

    with get_engine().begin() as c:
        notifications.deliver_pending(c, blocked, MARK)
    assert q("SELECT attempts, sent_at IS NULL FROM notifications ORDER BY id") == [(1, True), (1, True)]


def test_tick_steps_queue_reminders_before_delivery():
    from app import settlement

    names = [n for n, _ in settlement.tick_steps(lambda *a, **k: None)]
    assert "queue_reminders" in names and names.index("queue_reminders") < names.index("deliver_notifications")
