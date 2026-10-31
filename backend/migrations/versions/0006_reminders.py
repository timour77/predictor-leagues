"""reminders: users.reminders_enabled, notifications payload and inline button

Prediction Reminders (#31).

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("reminders_enabled", sa.Boolean, nullable=False, server_default=sa.true()))
    op.add_column("notifications", sa.Column("payload", JSONB))
    op.add_column("notifications", sa.Column("button_text", sa.Text))
    op.add_column("notifications", sa.Column("button_url", sa.Text))


def downgrade() -> None:
    op.drop_column("notifications", "button_url")
    op.drop_column("notifications", "button_text")
    op.drop_column("notifications", "payload")
    op.drop_column("users", "reminders_enabled")
