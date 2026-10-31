"""tip refunds: tips.status 'refunded', payment_events.refunded_at

Launch readiness (#29): Telegram requires a refund path for Stars purchases.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("tips_status", "tips", type_="check")
    op.create_check_constraint("tips_status", "tips", "status IN ('pending','paid','refunded')")
    op.add_column("payment_events", sa.Column("refunded_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("payment_events", "refunded_at")
    op.drop_constraint("tips_status", "tips", type_="check")
    op.create_check_constraint("tips_status", "tips", "status IN ('pending','paid')")
