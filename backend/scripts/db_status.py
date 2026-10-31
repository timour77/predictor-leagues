"""Print the applied migration revision and row counts."""
from sqlalchemy import text

from scripts._db import direct_engine

with direct_engine().connect() as conn:
    print("revision:", conn.execute(text("SELECT version_num FROM alembic_version")).scalar())
    print("users:", conn.execute(text("SELECT count(*) FROM users")).scalar())
