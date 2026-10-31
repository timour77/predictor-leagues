"""Table definitions for query building. The schema itself is owned by Alembic
migrations (backend/migrations); domain modules add their tables here."""
from sqlalchemy import BigInteger, Column, DateTime, MetaData, Table, Text, func

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
