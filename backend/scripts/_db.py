from sqlalchemy import create_engine, pool

from app import config
from app.db import normalize_url


def direct_engine():
    """Engine on the direct (non-pooled) URL, for operator actions."""
    return create_engine(normalize_url(config.DATABASE_URL_DIRECT), poolclass=pool.NullPool)
