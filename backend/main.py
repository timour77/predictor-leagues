from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.errors import DomainError
from app.routers import cron, leagues, matches, me, payments

app = FastAPI(title="Predictor Leagues API", version="2.0.0")

# Auth is a per-request header, not a cookie, so credentials are not needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Domain routers.
app.include_router(me.router, prefix="/api", tags=["me"])
app.include_router(matches.router, prefix="/api", tags=["matches"])
app.include_router(leagues.router, prefix="/api", tags=["leagues"])
app.include_router(cron.router, prefix="/api", tags=["cron"])
app.include_router(payments.router, prefix="/api", tags=["payments"])


@app.exception_handler(DomainError)
def domain_error(request: Request, exc: DomainError):
    # Raising rolls back the request transaction (get_conn), so nothing half-done is kept.
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/api/health")
def health():
    return {"status": "ok"}
