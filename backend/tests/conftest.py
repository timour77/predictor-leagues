import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
BOT_TOKEN = "123456:TEST-TOKEN"

# Integration tests need a throwaway Postgres: TEST_DATABASE_URL=postgresql://...
# (the schema is dropped and rebuilt with Alembic, so never point it at real data).
TEST_DB = os.getenv("TEST_DATABASE_URL")
os.environ["BOT_TOKEN"] = BOT_TOKEN
if TEST_DB:
    os.environ["DATABASE_URL"] = TEST_DB
    os.environ["DATABASE_URL_DIRECT"] = TEST_DB
sys.path.insert(0, str(BACKEND))


@pytest.fixture(scope="session")
def migrated_db():
    if not TEST_DB:
        pytest.skip("TEST_DATABASE_URL not set")
    from sqlalchemy import create_engine, text

    from app.db import normalize_url

    engine = create_engine(normalize_url(TEST_DB))
    with engine.begin() as c:
        c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    engine.dispose()
    subprocess.run(["alembic", "upgrade", "head"], cwd=BACKEND, check=True)
    return TEST_DB


@pytest.fixture
def client(migrated_db):
    from fastapi.testclient import TestClient

    from main import app

    return TestClient(app)
