"""leagues, league_competitions, league_members, predictions

Leagues and Predictions modules (#13). Always free: no fee or pool columns (ADR 0002).

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leagues",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("creator_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("invite_code", sa.Text, nullable=False, unique=True),
        sa.Column("window_start", sa.Date, nullable=False),
        sa.Column("window_end", sa.Date, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("window_end >= window_start", name="leagues_window_order"),
        sa.CheckConstraint(
            "status IN ('open','active','settling','settled','cancelled')", name="leagues_status"
        ),
    )
    op.create_table(
        "league_competitions",
        sa.Column("league_id", sa.BigInteger, sa.ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("competition_id", sa.Integer, primary_key=True),
    )
    op.create_table(
        "league_members",
        sa.Column("league_id", sa.BigInteger, sa.ForeignKey("leagues.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("league_members_user_idx", "league_members", ["user_id"])
    op.create_table(
        "predictions",
        sa.Column("league_id", sa.BigInteger, primary_key=True),
        sa.Column("user_id", sa.BigInteger, primary_key=True),
        sa.Column("match_id", sa.BigInteger, sa.ForeignKey("matches.id"), primary_key=True),
        sa.Column("home_goals", sa.Integer, nullable=False),
        sa.Column("away_goals", sa.Integer, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["league_id", "user_id"],
            ["league_members.league_id", "league_members.user_id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("home_goals BETWEEN 0 AND 99 AND away_goals BETWEEN 0 AND 99", name="predictions_goals"),
    )
    op.create_index("predictions_match_idx", "predictions", ["league_id", "match_id"])


def downgrade() -> None:
    op.drop_index("predictions_match_idx", table_name="predictions")
    op.drop_table("predictions")
    op.drop_index("league_members_user_idx", table_name="league_members")
    op.drop_table("league_members")
    op.drop_table("league_competitions")
    op.drop_table("leagues")
