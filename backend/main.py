from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import me

app = FastAPI(title="Predictor Leagues API", version="2.0.0")

# Auth is a per-request header, not a cookie, so credentials are not needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Domain routers (Leagues, Predictions, Payments, cron tick) are added by #12-#15.
app.include_router(me.router, prefix="/api", tags=["me"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
