import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException

from app import config, matchdata
from app.cron import run_tick
from app.db import get_engine

router = APIRouter()


def get_football_client() -> matchdata.FootballDataClient:
    return matchdata.FootballDataClient(config.FOOTBALL_DATA_API_KEY)


def require_cron_secret(authorization: str = Header(default="")) -> None:
    expected = f"Bearer {config.CRON_SECRET}"
    if not config.CRON_SECRET or not hmac.compare_digest(authorization, expected):
        raise HTTPException(401, "Unauthorized")


@router.get("/cron/tick", dependencies=[Depends(require_cron_secret)])
def tick(client: matchdata.FootballDataClient = Depends(get_football_client)):
    def match_sync(conn):
        return matchdata.sync_matches(
            conn, client, datetime.now(timezone.utc), config.MATCHDATA_COMPETITION_IDS
        )

    # Steps from later tickets (League start/Cancellation, Settlement, outbox) go here.
    return run_tick(get_engine(), [("match_sync", match_sync)])
