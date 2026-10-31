"""Table definitions for query building. The schema itself is owned by Alembic
migrations (backend/migrations); domain modules add their tables here."""
from sqlalchemy import (
    BigInteger, CheckConstraint, Column, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, MetaData,
    Table, Text, func,
)

from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("telegram_id", BigInteger, nullable=False, unique=True),
    Column("username", Text),
    Column("first_name", Text),
    Column("photo_url", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

# MatchData: the app's own copy of football-data.org fixtures. Clients read only from here.
matches = Table(
    "matches",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("external_id", BigInteger, nullable=False, unique=True),
    Column("competition_id", Integer, nullable=False),
    Column("competition_name", Text),
    Column("matchday", Integer),
    Column("home_team", Text, nullable=False),
    Column("away_team", Text, nullable=False),
    Column("home_crest", Text),
    Column("away_crest", Text),
    Column("kickoff", DateTime(timezone=True), nullable=False),
    # football-data.org status stored as-is (SCHEDULED, TIMED, IN_PLAY, PAUSED, FINISHED,
    # POSTPONED, SUSPENDED, CANCELLED, AWARDED); interpretation belongs to Scoring/Settlement.
    Column("status", Text, nullable=False),
    Column("home_goals", Integer),
    Column("away_goals", Integer),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Index("matches_competition_kickoff_idx", "competition_id", "kickoff"),
)

# Round-robin bookkeeping for the match sync step.
competition_sync = Table(
    "competition_sync",
    metadata,
    Column("competition_id", Integer, primary_key=True),
    Column("last_attempt_at", DateTime(timezone=True), nullable=False),
    Column("last_synced_at", DateTime(timezone=True)),
    Column("last_error", Text),
)

# Leagues: private, always free. `status` moves open -> active -> settling -> settled, or
# open -> cancelled; transitions are guarded in app/leagues.py and driven by app/settlement.py.
leagues = Table(
    "leagues",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("name", Text, nullable=False),
    Column("creator_id", BigInteger, ForeignKey("users.id"), nullable=False),
    Column("invite_code", Text, nullable=False, unique=True),
    # The Window: inclusive UTC calendar dates.
    Column("window_start", Date, nullable=False),
    Column("window_end", Date, nullable=False),
    Column("status", Text, nullable=False, server_default="open"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("settled_at", DateTime(timezone=True)),
    Column("matches_scored", Integer),   # set at Settlement
    CheckConstraint("window_end >= window_start", name="leagues_window_order"),
    CheckConstraint(
        "status IN ('open','active','settling','settled','cancelled')", name="leagues_status"
    ),
)

league_competitions = Table(
    "league_competitions",
    metadata,
    Column("league_id", BigInteger, ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True),
    Column("competition_id", Integer, primary_key=True),
)

league_members = Table(
    "league_members",
    metadata,
    Column("league_id", BigInteger, ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", BigInteger, ForeignKey("users.id"), primary_key=True),
    Column("joined_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Index("league_members_user_idx", "user_id"),
)

# One Prediction per Member, League and match: a single exact score (the outcome is derived).
# Withdrawing deletes the row. Rows are only written before the match's Deadline (its kickoff).
predictions = Table(
    "predictions",
    metadata,
    Column("league_id", BigInteger, primary_key=True),
    Column("user_id", BigInteger, primary_key=True),
    Column("match_id", BigInteger, ForeignKey("matches.id"), primary_key=True),
    Column("home_goals", Integer, nullable=False),
    Column("away_goals", Integer, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # Only Members may predict, enforced by the database.
    ForeignKeyConstraint(
        ["league_id", "user_id"],
        ["league_members.league_id", "league_members.user_id"],
        ondelete="CASCADE",
    ),
    CheckConstraint("home_goals BETWEEN 0 AND 99 AND away_goals BETWEEN 0 AND 99", name="predictions_goals"),
    Index("predictions_match_idx", "league_id", "match_id"),
)

# Payments: Tips are voluntary Telegram Stars gifts; nothing is bought and no reward is funded (ADR 0002).
tips = Table(
    "tips",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("users.id"), nullable=False),
    Column("amount", Integer, nullable=False),
    # Opaque id carried in the invoice; Telegram echoes it in pre_checkout_query / successful_payment.
    Column("payload", Text, nullable=False, unique=True),
    Column("status", Text, nullable=False, server_default="pending"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("amount > 0", name="tips_amount"),
    CheckConstraint("status IN ('pending','paid')", name="tips_status"),
)

# Append-only journal of successful_payment updates; UNIQUE charge id makes redelivery a no-op.
payment_events = Table(
    "payment_events",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("telegram_payment_charge_id", Text, nullable=False, unique=True),
    Column("provider_payment_charge_id", Text),
    Column("tip_id", BigInteger, ForeignKey("tips.id")),
    Column("telegram_user_id", BigInteger),
    Column("amount", Integer, nullable=False),
    Column("currency", Text, nullable=False),
    Column("raw", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

# Settlement (#15). `final_standings` fixes the result when a League settles, so later data
# corrections in MatchData cannot change it; `trophies` is the permanent profile mark.
final_standings = Table(
    "final_standings",
    metadata,
    Column("league_id", BigInteger, ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", BigInteger, ForeignKey("users.id"), primary_key=True),
    Column("rank", Integer, nullable=False),
    Column("points", Integer, nullable=False),
    Column("exact", Integer, nullable=False),
)

trophies = Table(
    "trophies",
    metadata,
    Column("league_id", BigInteger, ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", BigInteger, ForeignKey("users.id"), primary_key=True),
    Column("awarded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Index("trophies_user_idx", "user_id"),
)

# Outbox for Telegram bot messages: written inside domain transactions, delivered by the tick.
notifications = Table(
    "notifications",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, ForeignKey("users.id"), nullable=False),
    Column("kind", Text, nullable=False),
    Column("body", Text, nullable=False),
    # Makes enqueueing idempotent, e.g. "league_cancelled:42".
    Column("dedupe_key", Text, nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("sent_at", DateTime(timezone=True)),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("last_error", Text),
)
