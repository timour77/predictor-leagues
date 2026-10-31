"""Prediction Reminders: one message per user per kickoff time, about an hour before the Deadline.

`queue_reminders` is a tick step that enqueues into the notifications outbox; the message is built
again at send time (`render_at_send`) so a Prediction made, or the switch turned off, in between
cancels it. Not made up: a missed hour is never sent late, and Members who joined (or Leagues that
started) after the hour began get nothing.
"""
from datetime import datetime, timedelta

from sqlalchemy import Connection, text

from app import config, notifications

LEAD = timedelta(hours=1)
# Vercel Cron may skip a tick; queue up to this long after the hour mark, then give up.
CATCH_UP = timedelta(minutes=10)
BUTTON_TEXT = "Make a prediction"

_MISSING = """
SELECT lm.user_id, m.id AS match_id, m.kickoff, m.home_team, m.away_team, l.id AS league_id, l.name AS league_name
FROM leagues l
JOIN league_members lm ON lm.league_id = l.id
JOIN users u ON u.id = lm.user_id
JOIN league_competitions lc ON lc.league_id = l.id
JOIN matches m ON m.competition_id = lc.competition_id
WHERE l.status = 'active'
  AND u.reminders_enabled
  AND m.status IN ('SCHEDULED', 'TIMED')
  AND m.kickoff > :now
  AND (m.kickoff AT TIME ZONE 'UTC')::date BETWEEN l.window_start AND l.window_end
  AND (l.window_start::timestamp AT TIME ZONE 'UTC') <= m.kickoff - :lead
  AND lm.joined_at <= m.kickoff - :lead
  AND NOT EXISTS (
    SELECT 1 FROM predictions p
    WHERE p.league_id = l.id AND p.user_id = lm.user_id AND p.match_id = m.id)
  {extra}
ORDER BY m.kickoff, m.id, l.id
"""


def _missing(conn: Connection, now: datetime, extra: str = "", **params) -> list:
    sql = _MISSING.format(extra=extra)
    return conn.execute(text(sql), {"now": now, "lead": LEAD, **params}).mappings().all()


def _compose(rows: list) -> tuple[str, tuple[str, str] | None]:
    by_match: dict[int, tuple[str, list[str]]] = {}
    for r in rows:
        by_match.setdefault(r["match_id"], (f"{r['home_team']} – {r['away_team']}", []))[1].append(r["league_name"])
    lines = [f"{title} ({', '.join(names)})" for title, names in by_match.values()]
    body = "⏰ Starts in an hour. You haven't predicted yet:\n\n" + "\n".join(lines)
    if not config.MINI_APP_LINK:
        return body, None
    league_ids = {r["league_id"] for r in rows}
    if len(by_match) == 1 and len(league_ids) == 1:
        return body, (BUTTON_TEXT, f"{config.MINI_APP_LINK}?startapp=league_{league_ids.pop()}")
    return body, (BUTTON_TEXT, config.MINI_APP_LINK)   # several matches or Leagues: the Leagues list


def queue_reminders(conn: Connection, now: datetime) -> dict:
    """Enqueue Reminders for kickoffs whose hour began within CATCH_UP. Safe to repeat and to skip."""
    rows = _missing(conn, now, "AND m.kickoff <= :now + :lead AND m.kickoff >= :now + :lead - :catch_up",
                    catch_up=CATCH_UP)
    groups: dict[tuple[int, datetime], list] = {}
    for r in rows:
        groups.setdefault((r["user_id"], r["kickoff"]), []).append(r)
    queued = 0
    for (user_id, kickoff), group in groups.items():
        body, button = _compose(group)
        queued += notifications.enqueue(
            conn, user_id, "reminder", body, f"reminder:{user_id}:{kickoff.isoformat()}",
            payload={"kickoff": kickoff.isoformat()}, button=button)
    return {"queued": queued}


def render_at_send(conn: Connection, user_id: int, payload: dict, now: datetime):
    """The message as it stands now, or None when there is nothing left to remind about."""
    kickoff = datetime.fromisoformat(payload["kickoff"])
    rows = _missing(conn, now, "AND lm.user_id = :user_id AND m.kickoff = :kickoff", user_id=user_id, kickoff=kickoff)
    return _compose(rows) if rows else None
