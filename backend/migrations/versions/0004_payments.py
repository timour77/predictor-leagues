"""tips, payment_events

Payments module (#14): Tips in Telegram Stars only. The journal is append-only and keyed by
Telegram's charge id, so webhook redeliveries are idempotent. No fee, refund or payout data (ADR 0002).

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tips",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("payload", sa.Text, nullable=False, unique=True),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount > 0", name="tips_amount"),
        sa.CheckConstraint("status IN ('pending','paid')", name="tips_status"),
    )
    op.create_table(
        "payment_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("telegram_payment_charge_id", sa.Text, nullable=False, unique=True),
        sa.Column("provider_payment_charge_id", sa.Text),
        sa.Column("tip_id", sa.BigInteger, sa.ForeignKey("tips.id")),
        sa.Column("telegram_user_id", sa.BigInteger),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("currency", sa.Text, nullable=False),
        sa.Column("raw", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("payment_events")
    op.drop_table("tips")
