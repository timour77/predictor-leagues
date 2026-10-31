"""Table definitions for query building. The schema itself is owned by Alembic
migrations (backend/migrations); domain modules add their tables here."""
from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, MetaData, Table, Text, func

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
