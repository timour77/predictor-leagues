from alembic import context
from sqlalchemy import create_engine, pool

from app import config
from app.db import normalize_url

# Migrations use the direct (non-pooled) URL: DDL and advisory locks do not
# survive a transaction-mode pooler.
url = normalize_url(config.DATABASE_URL_DIRECT)
if not url:
    raise SystemExit("DATABASE_URL_DIRECT (or DATABASE_URL) is not set")

if context.is_offline_mode():
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
