from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, matches, predictions, leaderboard, competitions, users, leagues

app = FastAPI(title="CM Predictor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(matches.router, prefix="/api/matches", tags=["matches"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["predictions"])
app.include_router(leaderboard.router, prefix="/api/leaderboard", tags=["leaderboard"])
app.include_router(competitions.router, prefix="/api/competitions", tags=["competitions"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(leagues.router, prefix="/api/leagues", tags=["leagues"])


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/bot/webhook")
async def bot_webhook(request: dict):
    """Handle Telegram bot updates — confirm Stars payments automatically."""
    from app.database import execute, fetchone

    msg = request.get("message") or request.get("channel_post")
    if not msg:
        return {"ok": True}

    payment = msg.get("successful_payment")
    if not payment:
        return {"ok": True}

    payload = payment.get("invoice_payload", "")
    charge_id = payment.get("telegram_payment_charge_id", "")

    # payload format: "league:{league_id}:user:{user_id}"
    try:
        parts = payload.split(":")
        league_id = int(parts[1])
        user_id = int(parts[3])
    except (IndexError, ValueError):
        return {"ok": True}

    member = fetchone(
        "SELECT id FROM league_members WHERE league_id=%s AND user_id=%s",
        (league_id, user_id),
    )
    if member:
        execute(
            "UPDATE league_members SET paid=TRUE, telegram_payment_charge_id=%s WHERE id=%s",
            (charge_id, member["id"]),
        )
    else:
        execute(
            "INSERT INTO league_members (league_id, user_id, paid, telegram_payment_charge_id) VALUES (%s,%s,TRUE,%s)",
            (league_id, user_id, charge_id),
        )
    return {"ok": True}


@app.post("/api/admin/recalculate-scores")
def admin_recalculate_scores():
    import traceback
    from app.database import get_conn
    from app.services.scoring import calculate_points
    updated = 0
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """SELECT p.id, p.outcome, p.predicted_score,
                          mr.home_goals, mr.away_goals
                   FROM predictions p
                   JOIN match_results mr ON mr.external_match_id = p.match_id
                   WHERE mr.status = 'FINISHED'
                     AND mr.home_goals IS NOT NULL
                     AND mr.away_goals IS NOT NULL"""
            )
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            for row in rows:
                pts = calculate_points(
                    row["outcome"],
                    row["predicted_score"],
                    row["home_goals"],
                    row["away_goals"],
                )
                cur.execute("UPDATE predictions SET points=%s WHERE id=%s", (pts, row["id"]))
                updated += 1
        return {"status": "ok", "updated": updated}
    except Exception as e:
        return {"status": "error", "detail": str(e), "traceback": traceback.format_exc()}


@app.post("/api/admin/init-db")
def admin_init_db():
    import traceback as tb
    from app.database import init_db
    try:
        init_db()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e), "traceback": tb.format_exc()}
