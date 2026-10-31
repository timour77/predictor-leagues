# Operator scripts

There is no HTTP admin surface: operator actions are scripts with direct DB access.
Run from `backend/` with `.env` (or the environment) providing `DATABASE_URL_DIRECT`:

```bash
python -m scripts.db_status
```

New scripts use `scripts/_db.py:direct_engine()`.

## Re-settle a League

Settlement is final, except when the data source corrects a result afterwards. Then the operator
recomputes that League's final standings and Trophies from the current match data (same logic as
Settlement, one transaction, safe to repeat):

```bash
python -m scripts.resettle_league 42 --dry-run   # print the rank/points/Trophy diff, write nothing
python -m scripts.resettle_league 42             # apply
python -m scripts.resettle_league 42 --notify    # apply and queue a message to Members whose result changed
```

Only `settled` Leagues are accepted (anything else exits with an error). Members are not told
unless `--notify` is given; the message goes through the usual outbox on the next tick.

## Launch: webhook, refunds, data deletion

```bash
python -m scripts.set_webhook [--test-env] [--drop-pending]   # setWebhook + print getWebhookInfo
python -m scripts.refund_tip TELEGRAM_PAYMENT_CHARGE_ID       # refundStarPayment, then mark the Tip refunded
python -m scripts.delete_user TELEGRAM_ID                     # erase one user's personal data
```

`set_webhook` and `refund_tip` need `BOT_TOKEN`; `set_webhook` also needs `TELEGRAM_WEBHOOK_SECRET` and
`PUBLIC_URL`. Add `--test-env` (or `TELEGRAM_TEST_ENV=1`) to talk to Telegram's test server, where a
test bot and test Stars live. Find a charge id with
`SELECT telegram_payment_charge_id, amount, telegram_user_id FROM payment_events ORDER BY id DESC;`.
