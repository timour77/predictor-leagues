"""settlement: final_standings, trophies, notifications outbox, leagues.settled_at

Settlement and Cancellation (#15).

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leagues", sa.Column("settled_at", sa.DateTime(timezone=True)))
    op.add_column("leagues", sa.Column("matches_scored", sa.Integer))
    op.create_table(
        "final_standings",
        sa.Column("league_id", sa.BigInteger, sa.ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("points", sa.Integer, nullable=False),
        sa.Column("exact", sa.Integer, nullable=False),
    )
    op.create_table(
        "trophies",
        sa.Column("league_id", sa.BigInteger, sa.ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("trophies_user_idx", "trophies", ["user_id"])
    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("dedupe_key", sa.Text, nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_index("trophies_user_idx", table_name="trophies")
    op.drop_table("trophies")
    op.drop_table("final_standings")
    op.drop_column("leagues", "matches_scored")
    op.drop_column("leagues", "settled_at")
