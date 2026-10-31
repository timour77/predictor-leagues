# Launch checklist: Telegram Mini App with Stars tips

Researched 2026-10-31 for issue #24. Every claim cites a Telegram first-party page (fetched that day). Items marked **(unverified)** were not stated on a primary page and should be checked in the BotFather UI.

Context: React frontend + FastAPI on one Vercel domain; `POST /api/telegram/webhook` checks `X-Telegram-Bot-Api-Secret-Token`; Stars (XTR) are used only for voluntary Tips via `createInvoiceLink`; Leagues are free.

## Part 1. Operator checklist (in order)

Placeholders: `$TOKEN` = bot token, `$SECRET` = value of `TELEGRAM_WEBHOOK_SECRET`, `$DOMAIN` = production Vercel domain.

### Phase A. Test environment dry run (do this first, with a throwaway bot)

1. **Log in to the Telegram test server** with a new test account. iOS: tap Settings icon 10 times > Accounts > Login to another account > Test. Desktop: Settings, Shift+Alt+right-click "Add Account" > Test Server. macOS: click Settings icon 10 times, Cmd+click "Add Account". The test environment is separate, so you need a new account and a new bot. Source: https://core.telegram.org/bots/features#testing-your-bot, https://core.telegram.org/bots/webapps#testing-mini-apps
2. **Create a test bot** with @BotFather on the test server (`/newbot`). Source: https://core.telegram.org/bots/features#botfather
3. **Point a Vercel Preview deployment at it**: set `BOT_TOKEN` (test bot token) and `TELEGRAM_WEBHOOK_SECRET` in the Preview environment. initData for test-environment users is verified under the test bot token; the Ed25519 key for third-party verification differs for test vs production (see https://core.telegram.org/bots/webapps#validating-data-for-third-party-use).
4. **Call the Bot API with the `/test/` path segment**; there is no separate host:
   ```
   curl -sS "https://api.telegram.org/bot$TEST_TOKEN/test/setWebhook" \
     -d url="https://<preview-domain>/api/telegram/webhook" \
     -d secret_token="$SECRET" \
     -d 'allowed_updates=["message","pre_checkout_query"]'
   ```
   **Backend gotcha:** `backend/app/payments.py` `TelegramBot` must build URLs as `https://api.telegram.org/bot<token>/test/<method>` when running against the test server, otherwise `createInvoiceLink` will hit production with a test token and fail. Add an env flag (e.g. `TELEGRAM_TEST_ENV=1`). Source: https://core.telegram.org/bots/features#creating-a-bot-in-the-test-environment
5. **Set the menu button / Main Mini App on the test bot**, open the app, tip with test Stars, confirm `pre_checkout_query` is answered and `successful_payment` is recorded. "You can freely test payments in Telegram Stars by connecting your bot to Telegram's dedicated test environment." Source: https://core.telegram.org/bots/payments-stars#testing-payments
6. **Exercise refund**: `refundStarPayment` with `user_id` + the stored `telegram_payment_charge_id`. Source: https://core.telegram.org/bots/api/methods/refundstarpayment

Test-environment caveats: HTTP (no TLS) URLs are allowed for the Mini App only there, and flood limits are not raised (may be stricter). Source: https://core.telegram.org/bots/features#dedicated-test-environment

### Phase B. Production bot

7. **Secure the owner account**: enable 2-step verification on the Telegram account that owns the bot (recommended in the live checklist; losing the account can terminate the app and strand Stars). Source: https://core.telegram.org/bots/payments-stars#live-checklist, https://telegram.org/tos/bot-developers
8. **Create the production bot**: @BotFather `/newbot`. Username must end in `bot` and cannot be changed. Save the token as `BOT_TOKEN` in Vercel Production env (never commit it; tokens must not be public). Source: https://core.telegram.org/bots/features#botfather, https://telegram.org/tos/bot-developers
9. **Generate and store `TELEGRAM_WEBHOOK_SECRET`**: 1-256 chars from `A-Z a-z 0-9 _ -` only. E.g. `openssl rand -hex 32` (hex is valid). Add to Vercel Production env, then redeploy so the function sees it. Source: https://core.telegram.org/bots/api/methods/setwebhook
10. **Deploy and confirm HTTPS on `$DOMAIN`**: Mini App URL and webhook must be HTTPS (webhook: TLS 1.2+, valid cert chain, IPv4 reachable, port 443/80/88/8443). Vercel's default certificate satisfies this. Source: https://core.telegram.org/bots/webhooks
11. **Register the webhook**:
    ```
    curl -sS "https://api.telegram.org/bot$TOKEN/setWebhook" \
      -d url="https://$DOMAIN/api/telegram/webhook" \
      -d secret_token="$SECRET" \
      -d 'allowed_updates=["message","pre_checkout_query"]' \
      -d drop_pending_updates=true
    ```
    `allowed_updates` is a JSON-serialized list; omitting it keeps any previous setting. `pre_checkout_query` is required: payment is cancelled if not answered within 10 s. Source: https://core.telegram.org/bots/api/methods/setwebhook, https://core.telegram.org/bots/api/methods/answerprecheckoutquery
12. **Verify the webhook**: `curl -sS "https://api.telegram.org/bot$TOKEN/getWebhookInfo"`. Expect `url` set, `last_error_message` absent, `allowed_updates` as set, `pending_update_count` near 0. Also confirm a request without the secret header gets 401. Source: https://core.telegram.org/bots/api#getwebhookinfo
13. **Set up the Main Mini App** in @BotFather (`/mybots` > bot > Bot Settings > Configure Mini App, or `t.me/botfather?startapp`). Enter the production URL `https://$DOMAIN/`. This adds a "Launch app" button to the bot profile, enables `https://t.me/<bot>?startapp` links and is a prerequisite for Mini App Store featuring. Exact BotFather prompt wording **(unverified)**; the docs only describe the outcome. Source: https://core.telegram.org/bots/webapps#launching-the-main-mini-app
14. **Menu button** (so users get an "Open" button in the chat): BotFather `/setmenubutton` (or Bot Settings > Menu Button), or the default via API:
    ```
    curl -sS "https://api.telegram.org/bot$TOKEN/setChatMenuButton" \
      -d 'menu_button={"type":"web_app","text":"Play","web_app":{"url":"https://'$DOMAIN'/"}}'
    ```
    Source: https://core.telegram.org/bots/webapps#launching-mini-apps-from-the-menu-button, https://core.telegram.org/bots/api/methods/setchatmenubutton
15. **Direct link (named app, optional)**: `https://t.me/<bot>/<appname>?startapp=<param>` needs a short app name registered in BotFather (`/newapp`). The `/newapp` command is **not** described on the fetched pages **(unverified)**; the Main Mini App link `https://t.me/<bot>?startapp=<param>` needs no short name and is the simpler choice. `mode=compact` opens half height. The `startapp` value arrives as `start_param` / `tgWebAppStartParam` (usable for league invite deep links). Source: https://core.telegram.org/bots/webapps#direct-link-mini-apps
16. **Bot profile**: `/setname`, `/setdescription` (max 512 chars), `/setabouttext` (max 120), `/setuserpic`, and upload Mini App media previews (screenshots/videos) from the bot profile page; Mini App splash screen under Bot Settings > Configure Mini App > Configure Splash Screen. Source: https://core.telegram.org/bots/features#botfather
17. **Set bot commands** (`/setcommands` in BotFather) for the compliance commands in Part 2: `help`, `support`, `paysupport`, `terms`, `privacy`. Source: https://core.telegram.org/bots/features#commands
18. **Privacy policy**: publish a policy URL and register it via @BotFather (required if Telegram's Standard Privacy Policy does not cover what you store; this app stores Telegram ids, usernames, predictions, tip records). The exact BotFather command/field name was not on the fetched pages **(unverified)**. Source: https://telegram.org/tos/bot-developers (Privacy Policy section)
19. **Smoke-test in production**: open the Main Mini App from a second account, confirm initData auth works (`auth_date` within `INIT_DATA_MAX_AGE_SECONDS`), make a minimum Tip yourself, confirm Stars deducted and `successful_payment` recorded, then refund it with `refundStarPayment`. Source: https://core.telegram.org/bots/payments-stars
20. **Stars payout (later)**: Stars received stay Telegram property; payouts go through Fragment (1 Star = 0.013 USD reward value, "up to 21 days" before Stars become available, Stars expire 3 years after receipt). Thresholds/KYC are on Fragment, not covered by the fetched Telegram pages **(unverified)**. Source: https://telegram.org/tos/bot-developers (Stars and Digital Goods)
21. **Promotion/listing**: nothing to submit. Per Telegram, bots that **enable a main Mini App and accept Stars** may be featured in the Mini App Store; media previews and following the design guidelines raise the chance. Bots with a main Mini App appear in the Apps tab of search for users who have launched them. Source: https://core.telegram.org/bots/webapps#launching-the-main-mini-app, https://core.telegram.org/bots/webapps#design-guidelines

## Part 2. Policy requirements and notes

### Stars rules that apply to us
- Digital goods/services inside Telegram must be sold only in Stars (`XTR`); `provider_token` empty; `prices` has exactly one item; `payload` 1-128 bytes; title 1-32, description 1-255 chars. Source: https://core.telegram.org/bots/api/methods/createinvoicelink
- Tips are a voluntary Stars payment, so they stay on the compliant path. Leagues are free and should stay free; digital goods sold in another currency or via a third-party provider can get the app removed. Source: https://core.telegram.org/bots/payments-stars#faq, https://telegram.org/tos/bot-developers (Payments)
- Pre-checkout: answer `pre_checkout_query` within 10 s; deliver only after `successful_payment`; store `telegram_payment_charge_id` (needed for refunds). Source: https://core.telegram.org/bots/payments-stars
- Replying with `{"method": "answerPreCheckoutQuery", ...}` in the webhook HTTP response is supported, but "It's not possible to know that such a request was successful"; our `pre_checkout_answer` does this. Vercel cold start plus the DB lookup must stay well under 10 s. Source: https://core.telegram.org/bots/api#making-requests-when-getting-updates
- A non-2xx webhook response is retried then dropped, so return 200 for ignored updates (the handler does). Source: https://core.telegram.org/bots/api/methods/setwebhook

### Required commands and legal surface (Live Checklist)
| Requirement | Source wording | Needed by us? |
|---|---|---|
| `/paysupport` | "must be able to respond to the command `/paysupport` and process user requests regarding payment issues" | Yes (we take payments, even tips) |
| `/terms` (or equivalent) with agreement before purchase | "make sure your bot can respond to a /terms command ... users must confirm that they have read and agree to your terms before they make the purchase" | Yes. Add a terms link and confirmation line in the tip UI before opening the invoice |
| `/support` (or other clear channel) | Users need a clear way to contact you; tell users Telegram support and @botsupport cannot help with purchases | Yes |
| Privacy policy | "must be bound by a privacy policy that is easily accessible"; own policy via @BotFather if the Standard one is not enough | Yes |
| Refund path | Unfulfillable orders must be returned in full "via the Bot API with no penalty"; disputes are on the developer | Yes, keep a `refundStarPayment` runbook |
| Backups of payment data | "Use backups to make sure that you don't lose data about your users' payments" | Neon backups/PITR |
| Agree to ToS + Bot Platform Developer Terms | accept as bot owner | Yes |

Sources: https://core.telegram.org/bots/payments-stars#live-checklist, https://telegram.org/tos/bot-developers, https://core.telegram.org/bots/payments-stars#faq (disputes)

Penalties for ignoring disputes: Star debits, removal, a public SCAM label, termination. Refunds are deducted from the developer's balance. Source: https://telegram.org/tos/bot-developers (Refunds and Support)

### Data handling duties (Bot Developer Terms)
Collect only what is needed; delete user data on request or when no longer needed (we need a deletion path); encrypt user data at rest and keep it apart from keys; tokens/secrets are confidential; the app needs its own branding and must not imitate Telegram. Source: https://telegram.org/tos/bot-developers

### Mini Apps Terms (user-facing)
Telegram shares user id, public name, username, photo, language and IP with the Mini App; the service provider (us) is responsible for data users give us and for availability, refunds and disputes. Source: https://telegram.org/tos/mini-apps. That page says nothing on Stars, gambling or listing rules; no separate App Center application process was found on primary pages.

### Other platform facts
- Webhook IPs (if you ever allowlist): 149.154.160.0/20 and 91.108.4.0/22, may change; prefer the secret header (we do). Source: https://core.telegram.org/bots/webhooks
- Webhook and `getUpdates` are mutually exclusive. Source: setWebhook page.
- initData verification (HMAC keyed `WebAppData` + bot token, check `auth_date`) is what `app.auth` implements. Source: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
- Load `https://telegram.org/js/telegram-web-app.js` in `<head>` before other scripts. Source: https://core.telegram.org/bots/webapps#initializing-mini-apps

## Part 3. Code/config gaps found in this repo (origin/main at time of research)

1. **No `/paysupport`, `/terms`, `/support` handlers**: the webhook only handles `pre_checkout_query` and `successful_payment`. `allowed_updates` already includes `message`, so add replies (e.g. webhook-response `sendMessage`) for these commands, plus `/start`, `/help`, `/privacy`.
2. **No privacy policy or terms pages/URLs** and no consent line in the tip flow.
3. **No refund tooling**: add an operator script wrapping `refundStarPayment` with the stored `telegram_payment_charge_id`.
4. **Test-server support**: `TelegramBot` needs the `/test/` URL segment option (step 4), plus a documented Preview env.
5. **No setup script**: add `scripts/set_webhook.py` doing steps 11-12 reproducibly (secret from env).
6. **User data deletion** path for the Bot Developer Terms.
7. `.env.example` comment on `TELEGRAM_WEBHOOK_SECRET` should state the allowed charset (`A-Za-z0-9_-`, 1-256).
8. Confirm `record_payment` is idempotent on `telegram_payment_charge_id` (Telegram retries non-2xx).
