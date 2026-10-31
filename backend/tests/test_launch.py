import pytest
from sqlalchemy import text

from app import bot_commands, config, payments
from app.db import get_engine
from scripts import delete_user, refund_tip
from tests.test_payments import SECRET, WH, new_tip, paid, pay, rows, wh, USER  # noqa: F401
from tests.test_api import header


def msg(text_, chat_type="private", chat_id=8001):
    return {"update_id": 5, "message": {"chat": {"id": chat_id, "type": chat_type},
                                        "from": {"id": 8001}, "text": text_}}


@pytest.fixture
def urls(monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_URL", "https://app.example")
    monkeypatch.setattr(config, "SUPPORT_CONTACT", "@owner")


# --- bot commands ---

@pytest.mark.parametrize("cmd", ["/help", "/support", "/paysupport", "/terms", "/privacy", "/start"])
def test_command_replies_with_sendmessage_to_the_chat(pay, urls, cmd):
    r = pay.post(WH, json=msg(cmd), headers=wh())
    body = r.json()
    assert r.status_code == 200
    assert body["method"] == "sendMessage" and body["chat_id"] == 8001 and body["text"]


def test_terms_and_privacy_link_to_the_pages(pay, urls):
    assert "https://app.example/terms" in pay.post(WH, json=msg("/terms"), headers=wh()).json()["text"]
    assert "https://app.example/privacy" in pay.post(WH, json=msg("/privacy"), headers=wh()).json()["text"]


def test_paysupport_names_the_contact_and_says_telegram_cannot_help(pay, urls):
    t = pay.post(WH, json=msg("/paysupport"), headers=wh()).json()["text"]
    assert "@owner" in t and "@botsupport" in t


def test_start_opens_the_mini_app(pay, urls):
    b = pay.post(WH, json=msg("/start"), headers=wh()).json()
    assert b["reply_markup"]["inline_keyboard"][0][0]["web_app"]["url"] == "https://app.example/"


def test_start_with_a_param_still_opens_the_app(pay, urls):
    assert pay.post(WH, json=msg("/start join_abc"), headers=wh()).json()["method"] == "sendMessage"


def test_command_with_bot_suffix_is_recognised(pay, urls):
    assert pay.post(WH, json=msg("/help@some_bot"), headers=wh()).json()["method"] == "sendMessage"


def test_unknown_text_and_group_chats_get_no_reply(pay, urls):
    assert pay.post(WH, json=msg("hello"), headers=wh()).json() == {"ok": True}
    assert pay.post(WH, json=msg("/help", chat_type="group"), headers=wh()).json() == {"ok": True}


def test_every_registered_command_has_a_handler():
    assert set(bot_commands.COMMANDS) == {"start", "help", "support", "paysupport", "terms", "privacy"}


# --- test server ---

def test_bot_urls_use_production_by_default(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_TEST_ENV", False)
    assert payments.TelegramBot("T").method_url("x") == "https://api.telegram.org/botT/x"


def test_bot_urls_use_test_path_segment_when_flagged(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_TEST_ENV", True)
    assert payments.TelegramBot("T").method_url("x") == "https://api.telegram.org/botT/test/x"


def test_outbox_send_message_uses_test_server_too(monkeypatch):
    from app import telegram
    monkeypatch.setattr(config, "TELEGRAM_TEST_ENV", True)
    seen = {}

    class R:
        def raise_for_status(self): pass
    monkeypatch.setattr(telegram.requests, "post", lambda url, **kw: seen.setdefault("url", url) and R())
    telegram.send_message(1, "hi")
    assert "/test/sendMessage" in seen["url"]


# --- refunds ---

class RefundBot:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def refund_star_payment(self, user_id, charge_id):
        self.calls.append((user_id, charge_id))
        if self.fail:
            raise RuntimeError("CHARGE_ALREADY_REFUNDED")


def paid_tip(pay, charge="tg-charge-1"):
    t = new_tip(pay)
    pay.post(WH, json=paid(t["payload"], charge=charge), headers=wh())
    return t


def test_refund_calls_telegram_and_marks_tip_refunded(pay):
    paid_tip(pay)
    bot = RefundBot()
    with get_engine().begin() as c:
        refund_tip.refund(c, bot, "tg-charge-1")
    assert bot.calls == [(8001, "tg-charge-1")]
    assert rows("SELECT status FROM tips")[0]["status"] == "refunded"
    assert rows("SELECT refunded_at FROM payment_events")[0]["refunded_at"] is not None


def test_refund_twice_is_refused_without_calling_telegram(pay):
    paid_tip(pay)
    bot = RefundBot()
    with get_engine().begin() as c:
        refund_tip.refund(c, bot, "tg-charge-1")
    with pytest.raises(refund_tip.RefundError):
        with get_engine().begin() as c:
            refund_tip.refund(c, bot, "tg-charge-1")
    assert len(bot.calls) == 1


def test_refund_unknown_charge_is_an_error(pay):
    with pytest.raises(refund_tip.RefundError):
        with get_engine().begin() as c:
            refund_tip.refund(c, RefundBot(), "nope")


def test_refund_leaves_tip_paid_when_telegram_fails(pay):
    paid_tip(pay)
    with pytest.raises(RuntimeError):
        with get_engine().begin() as c:
            refund_tip.refund(c, RefundBot(fail=True), "tg-charge-1")
    assert rows("SELECT status FROM tips")[0]["status"] == "paid"


def test_refunded_tip_cannot_be_paid_again_via_precheckout(pay):
    t = paid_tip(pay)
    with get_engine().begin() as c:
        refund_tip.refund(c, RefundBot(), "tg-charge-1")
    from tests.test_payments import pre_checkout
    assert pay.post(WH, json=pre_checkout(t["payload"]), headers=wh()).json()["ok"] is False


def test_refund_star_payment_request_shape(monkeypatch):
    seen = {}

    class R:
        def json(self): return {"ok": True, "result": True}
    monkeypatch.setattr(payments.requests, "post", lambda url, json, timeout: seen.update(url=url, json=json) or R())
    payments.TelegramBot("T").refund_star_payment(7, "ch")
    assert seen["url"].endswith("/refundStarPayment") and seen["json"] == {"user_id": 7, "telegram_payment_charge_id": "ch"}


# --- data deletion ---

def test_delete_user_erases_personal_data_but_keeps_payment_records(pay):
    paid_tip(pay)
    with get_engine().begin() as c:
        c.execute(text("INSERT INTO notifications (user_id, kind, body, dedupe_key) "
                       "SELECT id, 'k', 'b', 'd1' FROM users"))
    with get_engine().begin() as c:
        out = delete_user.delete_user(c, 8001)
    u = rows("SELECT * FROM users")[0]
    assert u["username"] is None and u["photo_url"] is None
    assert u["first_name"] == "Deleted user" and u["telegram_id"] != 8001
    assert rows("SELECT 1 FROM notifications") == []
    assert rows("SELECT 1 FROM predictions") == []
    assert len(rows("SELECT 1 FROM payment_events")) == 1
    assert out["deleted"] is True


def test_delete_user_unknown_is_a_noop(pay):
    with get_engine().begin() as c:
        assert delete_user.delete_user(c, 999)["deleted"] is False


def test_deleted_user_gets_a_fresh_account_on_return(pay):
    paid_tip(pay)
    with get_engine().begin() as c:
        delete_user.delete_user(c, 8001)
    assert pay.post("/api/tips", json={"amount": 5}, headers=header(USER)).status_code == 201
    assert len(rows("SELECT 1 FROM users")) == 2


# --- set_webhook ---

def test_set_webhook_params_and_secret_charset():
    from scripts import set_webhook
    p = set_webhook.params("https://d.example", "ab_C-9")
    assert p["url"] == "https://d.example/api/telegram/webhook" and p["secret_token"] == "ab_C-9"
    assert p["allowed_updates"] == ["message", "pre_checkout_query"]
    for bad in ["", "has space", "x" * 257, "dot.dot"]:
        with pytest.raises(ValueError):
            set_webhook.params("https://d.example", bad)
    with pytest.raises(ValueError):
        set_webhook.params("http://d.example", "ok")
