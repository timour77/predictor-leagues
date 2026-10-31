import os

from dotenv import load_dotenv

load_dotenv()

# Pooled (Neon pooler) URL used by the app at runtime.
DATABASE_URL = os.getenv("DATABASE_URL", "")
# Direct (non-pooled) URL used by Alembic and scripts; falls back to DATABASE_URL.
DATABASE_URL_DIRECT = os.getenv("DATABASE_URL_DIRECT") or DATABASE_URL
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
# Mini Apps keep the launch-time initData for the whole session, so allow a day.
INIT_DATA_MAX_AGE_SECONDS = int(os.getenv("INIT_DATA_MAX_AGE_SECONDS", "86400"))
# Shared secret Vercel Cron sends as `Authorization: Bearer <CRON_SECRET>`.
CRON_SECRET = os.getenv("CRON_SECRET", "")
# football-data.org competitions to keep in sync (default: the free-tier set).
MATCHDATA_COMPETITION_IDS = [
    int(x) for x in os.getenv(
        "MATCHDATA_COMPETITION_IDS",
        "2000,2001,2002,2003,2013,2014,2015,2016,2017,2018,2019,2021",
    ).split(",") if x.strip()
]
