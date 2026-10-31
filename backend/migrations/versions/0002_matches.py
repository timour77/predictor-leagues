"""matches and competition_sync

MatchData module (#12): the app's own copy of football-data.org fixtures.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "matches",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("competition_id", sa.Integer, nullable=False),
        sa.Column("competition_name", sa.Text),
        sa.Column("matchday", sa.Integer),
        sa.Column("home_team", sa.Text, nullable=False),
        sa.Column("away_team", sa.Text, nullable=False),
        sa.Column("home_crest", sa.Text),
        sa.Column("away_crest", sa.Text),
        sa.Column("kickoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("home_goals", sa.Integer),
        sa.Column("away_goals", sa.Integer),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("matches_competition_kickoff_idx", "matches", ["competition_id", "kickoff"])
    op.create_table(
        "competition_sync",
        sa.Column("competition_id", sa.Integer, primary_key=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text),
    )


def downgrade() -> None:
    op.drop_table("competition_sync")
    op.drop_index("matches_competition_kickoff_idx", table_name="matches")
    op.drop_table("matches")
