import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import Connection

from app import bot_commands, config, payments
from app.auth import get_current_user
from app.db import get_conn

router = APIRouter()


def get_bot() -> payments.TelegramBot:
    return payments.TelegramBot(config.BOT_TOKEN)


def require_webhook_secret(
    secret: str = Header(default="", alias="X-Telegram-Bot-Api-Secret-Token"),
) -> None:
    expected = config.TELEGRAM_WEBHOOK_SECRET
    if not expected or not hmac.compare_digest(secret, expected):
        raise HTTPException(401, "Unauthorized")


class TipIn(BaseModel):
    amount: int


@router.post("/tips", status_code=201)
def create_tip(
    body: TipIn,
    user: dict = Depends(get_current_user),
    conn: Connection = Depends(get_conn),
    bot: payments.TelegramBot = Depends(get_bot),
):
    tip = payments.create_tip(conn, bot, user["id"], body.amount)
    return {"invoice_url": tip["invoice_url"]}


@router.post("/telegram/webhook", dependencies=[Depends(require_webhook_secret)])
async def webhook(request: Request, conn: Connection = Depends(get_conn)):
    update = await request.json()
    query = update.get("pre_checkout_query")
    if query:
        # Replying in the webhook response answers within Telegram's 10 s limit without an extra call.
        return payments.pre_checkout_answer(conn, query)
    message = update.get("message") or {}
    if "successful_payment" in message:
        payments.record_payment(conn, message)
        return {"ok": True}
    return bot_commands.reply(message) or {"ok": True}
