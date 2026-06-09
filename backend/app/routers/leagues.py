import secrets
import requests
from fastapi import APIRouter, HTTPException, Depends

from app.models import (
    CreateLeagueRequest, LeagueResponse, LeagueMemberEntry,
    JoinLeagueResponse, ConfirmPaymentRequest,
)
from app.database import fetchone, fetchall, execute
from app.routers.auth import get_current_user
from app.utils.config import BOT_TOKEN

router = APIRouter()


def _bot_post(method: str, payload: dict) -> dict:
    resp = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        json=payload,
        timeout=10,
    )
    return resp.json()


def _league_row_to_response(row: dict, current_user_id: int) -> LeagueResponse:
    return LeagueResponse(
        id=row["id"],
        name=row["name"],
        creator_id=row["creator_id"],
        invite_code=row["invite_code"],
        entry_fee=row["entry_fee"],
        competition_id=row["competition_id"],
        status=row["status"],
        member_count=row["member_count"],
        prize_pool=row["entry_fee"] * row["member_count"],
        is_member=row["is_member"],
        is_creator=row["creator_id"] == current_user_id,
    )


@router.post("", response_model=LeagueResponse)
def create_league(body: CreateLeagueRequest, current_user: dict = Depends(get_current_user)):
    if len(body.name.strip()) < 2:
        raise HTTPException(400, "League name too short")
    if body.entry_fee < 0:
        raise HTTPException(400, "Entry fee cannot be negative")

    invite_code = secrets.token_urlsafe(8)
    league_id = execute(
        """INSERT INTO leagues (name, creator_id, invite_code, entry_fee, competition_id)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (body.name.strip(), current_user["user_id"], invite_code, body.entry_fee, 2000),
    )
    # Creator joins automatically as paid member
    execute(
        "INSERT INTO league_members (league_id, user_id, paid) VALUES (%s, %s, TRUE)",
        (league_id, current_user["user_id"]),
    )
    row = fetchone(
        """SELECT l.*, COUNT(lm.id) as member_count,
                  EXISTS(SELECT 1 FROM league_members WHERE league_id=l.id AND user_id=%s) as is_member
           FROM leagues l LEFT JOIN league_members lm ON lm.league_id = l.id
           WHERE l.id = %s GROUP BY l.id""",
        (current_user["user_id"], league_id),
    )
    return _league_row_to_response(row, current_user["user_id"])


@router.get("/my", response_model=list[LeagueResponse])
def my_leagues(current_user: dict = Depends(get_current_user)):
    rows = fetchall(
        """SELECT l.*, COUNT(lm.id) as member_count,
                  EXISTS(SELECT 1 FROM league_members WHERE league_id=l.id AND user_id=%s) as is_member
           FROM leagues l
           JOIN league_members lm2 ON lm2.league_id = l.id AND lm2.user_id = %s
           LEFT JOIN league_members lm ON lm.league_id = l.id
           GROUP BY l.id ORDER BY l.created_at DESC""",
        (current_user["user_id"], current_user["user_id"]),
    )
    return [_league_row_to_response(r, current_user["user_id"]) for r in rows]


@router.get("/{invite_code}", response_model=LeagueResponse)
def get_league(invite_code: str, current_user: dict = Depends(get_current_user)):
    row = fetchone(
        """SELECT l.*, COUNT(lm.id) as member_count,
                  EXISTS(SELECT 1 FROM league_members WHERE league_id=l.id AND user_id=%s) as is_member
           FROM leagues l LEFT JOIN league_members lm ON lm.league_id = l.id
           WHERE l.invite_code = %s GROUP BY l.id""",
        (current_user["user_id"], invite_code),
    )
    if not row:
        raise HTTPException(404, "League not found")
    return _league_row_to_response(row, current_user["user_id"])


@router.post("/{invite_code}/join", response_model=JoinLeagueResponse)
def join_league(invite_code: str, current_user: dict = Depends(get_current_user)):
    league = fetchone("SELECT * FROM leagues WHERE invite_code = %s", (invite_code,))
    if not league:
        raise HTTPException(404, "League not found")

    already = fetchone(
        "SELECT id, paid FROM league_members WHERE league_id = %s AND user_id = %s",
        (league["id"], current_user["user_id"]),
    )
    if already and already["paid"]:
        return JoinLeagueResponse(status="joined")

    if league["entry_fee"] == 0:
        if not already:
            execute(
                "INSERT INTO league_members (league_id, user_id, paid) VALUES (%s, %s, TRUE)",
                (league["id"], current_user["user_id"]),
            )
        else:
            execute(
                "UPDATE league_members SET paid=TRUE WHERE id=%s", (already["id"],)
            )
        return JoinLeagueResponse(status="joined")

    # Paid league — create Telegram Stars invoice link
    if not BOT_TOKEN:
        raise HTTPException(500, "Bot token not configured")

    user = fetchone("SELECT telegram_id FROM users WHERE id=%s", (current_user["user_id"],))
    if not user or not user.get("telegram_id"):
        raise HTTPException(400, "Telegram account required for paid leagues")

    result = _bot_post("createInvoiceLink", {
        "title": league["name"],
        "description": f"Вступительный взнос в лигу «{league['name']}»",
        "payload": f"league:{league['id']}:user:{current_user['user_id']}",
        "currency": "XTR",
        "prices": [{"label": "Взнос", "amount": league["entry_fee"]}],
    })
    if not result.get("ok"):
        raise HTTPException(500, f"Telegram error: {result.get('description')}")

    # Reserve unpaid seat
    if not already:
        execute(
            "INSERT INTO league_members (league_id, user_id, paid) VALUES (%s, %s, FALSE) ON CONFLICT DO NOTHING",
            (league["id"], current_user["user_id"]),
        )

    return JoinLeagueResponse(status="invoice_sent", invoice_url=result["result"])


@router.post("/confirm-payment", response_model=JoinLeagueResponse)
def confirm_payment(body: ConfirmPaymentRequest, current_user: dict = Depends(get_current_user)):
    """Called by frontend after successful Telegram Stars payment."""
    member = fetchone(
        "SELECT id FROM league_members WHERE league_id=%s AND user_id=%s",
        (body.league_id, current_user["user_id"]),
    )
    if not member:
        execute(
            "INSERT INTO league_members (league_id, user_id, paid, telegram_payment_charge_id) VALUES (%s,%s,TRUE,%s)",
            (body.league_id, current_user["user_id"], body.telegram_payment_charge_id),
        )
    else:
        execute(
            "UPDATE league_members SET paid=TRUE, telegram_payment_charge_id=%s WHERE id=%s",
            (body.telegram_payment_charge_id, member["id"]),
        )
    return JoinLeagueResponse(status="joined")


@router.get("/{invite_code}/leaderboard", response_model=list[LeagueMemberEntry])
def league_leaderboard(invite_code: str, current_user: dict = Depends(get_current_user)):
    league = fetchone("SELECT * FROM leagues WHERE invite_code = %s", (invite_code,))
    if not league:
        raise HTTPException(404, "League not found")

    rows = fetchall(
        """SELECT u.id as user_id, u.username, u.photo_url,
                  COALESCE(SUM(p.points), 0) as total_points,
                  COALESCE(SUM(CASE WHEN p.points = 1 THEN 1 ELSE 0 END), 0) as correct_outcomes,
                  COALESCE(SUM(CASE WHEN p.points >= 3 THEN 1 ELSE 0 END), 0) as correct_scores
           FROM league_members lm
           JOIN users u ON u.id = lm.user_id
           LEFT JOIN predictions p ON p.user_id = u.id AND p.competition_id = %s
           WHERE lm.league_id = %s AND lm.paid = TRUE
           GROUP BY u.id, u.username, u.photo_url
           ORDER BY total_points DESC, u.username""",
        (league["competition_id"], league["id"]),
    )
    return [
        LeagueMemberEntry(
            user_id=r["user_id"],
            username=r["username"],
            photo_url=r.get("photo_url"),
            total_points=r["total_points"],
            correct_outcomes=r["correct_outcomes"],
            correct_scores=r["correct_scores"],
            rank=i + 1,
        )
        for i, r in enumerate(rows)
    ]
