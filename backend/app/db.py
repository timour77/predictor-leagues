"""SQLAlchemy Core engine and the per-request connection dependency."""
from functools import lru_cache
from typing import Iterator

from sqlalchemy import Connection, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from app import config


def normalize_url(url: str) -> str:
    """Accept postgres:// and postgresql:// URLs; force the psycopg3 driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    # Neon's pooler (pgbouncer, transaction mode) owns pooling, so no client-side
    # pool, and server-side prepared statements must be off.
    return create_engine(
        normalize_url(config.DATABASE_URL),
        poolclass=NullPool,
        connect_args={"prepare_threshold": None},
    )


def get_conn() -> Iterator[Connection]:
    """FastAPI dependency: one connection and one transaction per request.

    Commits when the handler returns, rolls back if it raises.
    """
    with get_engine().begin() as conn:
        yield conn
