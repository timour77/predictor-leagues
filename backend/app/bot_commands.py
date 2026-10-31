"""Bot commands answered in the webhook response (no extra API call, nothing stored).

/paysupport, /terms and /support are required of Stars sellers by Telegram's Live Checklist.
"""
from app import config

COMMANDS = {}


def command(fn):
    COMMANDS[fn.__name__] = fn
    return fn


def _page(path: str) -> str:
    return f"{config.PUBLIC_URL}{path}"


def _contact() -> str:
    return config.SUPPORT_CONTACT or "the developer"


@command
def start() -> dict:
    return {
        "text": "Predict match scores with friends in private Leagues. Joining is always free.",
        "reply_markup": {"inline_keyboard": [[{"text": "Play", "web_app": {"url": _page("/")}}]]},
    }


@command
def help() -> dict:
    return {"text": (
        "Predictor Leagues: predict exact scores, compete with friends, win Trophies.\n\n"
        "/start - open the app\n/support - contact the developer\n/paysupport - help with a tip\n"
        "/terms - terms of use\n/privacy - privacy policy"
    )}


@command
def support() -> dict:
    return {"text": f"Questions or problems? Contact {_contact()}. "
                    "Telegram support and @botsupport cannot help with this app."}


@command
def paysupport() -> dict:
    return {"text": (
        f"Tip problems or refund requests: contact {_contact()} and include the date and amount. "
        "Telegram support and @botsupport cannot help with Star purchases made here. "
        "Tips are voluntary; a refund returns the Stars in full."
    )}


@command
def terms() -> dict:
    return {"text": f"Terms of use: {_page('/terms')}"}


@command
def privacy() -> dict:
    return {"text": f"Privacy policy: {_page('/privacy')}"}


def reply(message: dict) -> dict | None:
    """sendMessage webhook response for a command in a private chat, else None."""
    chat = message.get("chat") or {}
    text = message.get("text") or ""
    if chat.get("type") != "private" or not text.startswith("/"):
        return None
    name = text.split()[0][1:].split("@")[0].lower()
    handler = COMMANDS.get(name)
    if handler is None:
        return None
    return {"method": "sendMessage", "chat_id": chat["id"], **handler()}
