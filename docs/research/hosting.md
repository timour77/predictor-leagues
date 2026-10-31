# Can Vercel host scheduled Settlement and the bot webhook?

Research for issue #6. Sources checked 2026-10-31. Every claim links to the page that owns it.

## Bottom line

**Yes, on Vercel Pro ($20/month). Not on Hobby.**

- **Hobby can't do it.** Cron jobs there run at most once per day, with ±59 min timing. Hobby is also limited to non-commercial use, and this app sells paid leagues for Telegram Stars.
- **Pro meets every requirement.** Cron can run every minute and fires within the scheduled minute. Functions run up to 800 s. Fluid compute (the default) supports Python and keeps instances warm.
- **The Telegram webhook works on either plan.** It is an ordinary HTTPS route. The only tight deadline is the 10 s limit for answering `pre_checkout_query`. The backend doesn't handle that update yet (see Side findings).
- **Postgres is the real risk, and it comes from the code, not from Vercel.** `get_conn()` opens a new TLS connection with pg8000 for every query and never pools. Three fixes:
  - point `POSTGRES_URL` at the Neon `-pooler` host
  - reuse one connection per request
  - optionally keep a small module-level pool, since Fluid reuses instances
- **Write the cron jobs to be idempotent and to take a lock.** Vercel cron delivery is best effort: it can skip a run or deliver the same run twice, and it never retries a failure.
- **No need to move off Vercel.** Railway and Fly.io are good fallbacks if we later want a long-running worker, such as APScheduler (already in `backend/requirements.txt`). Railway is the simpler and cheaper of the two. Fly's built-in scheduler is too coarse for this.

## Comparison

| | Vercel Hobby | **Vercel Pro** | Railway Hobby | Fly.io |
|---|---|---|---|---|
| Base price | $0 | $20/month, credit-based included usage | $5/month incl. $5 usage | Pay-as-you-go, no free tier |
| Commercial use | **No** (non-commercial only) | Yes | Yes | Yes |
| Scheduler | Vercel Cron, **once per day**, ±59 min | Vercel Cron, **every minute**, fires within the minute | Cron service, **≥5 min** apart, "can vary by a few minutes"; or an always-on worker | `--schedule` is only hourly/daily/weekly/monthly and can't target a clock time; run supercronic or APScheduler in an always-on Machine instead |
| Max run time per job | 300 s | 800 s (1800 s beta) | Unlimited (process) | Unlimited (process) |
| Missed / duplicate runs | Best effort, may skip or duplicate, no retry | Same | Skips a run if the previous one is still running | Depends on our scheduler |
| Cold starts | Fluid: bytecode + pre-warming on prod | Same | None if always-on; "small delay"/502 if Serverless sleep is on | None if always-on; some delay if auto-stop is on |
| Postgres pooling | Per-instance pool + external pooler (Neon `-pooler`) | Same | Plain long-lived pool in process | Plain long-lived pool in process |
| Approx. cost for API + worker | $0 (not allowed for this app) | $20 | ~$5–10 (two small services) + DB | ~$4–7 (2 × shared-cpu-1x 256–512 MB) + DB (Managed PG from $38) |

## Detail

### 1. Scheduled jobs (result polling, Settlement, Cancellation refunds)

**Vercel cron limits per plan.** Every plan allows 100 cron jobs per project. Hobby allows a minimum interval of "Once per day" and per-hour precision (±59 min). Pro and Enterprise allow "Once per minute" with per-minute precision. A Hobby cron expression that runs more often than daily "will fail deployment." ([Cron usage & pricing](https://vercel.com/docs/cron-jobs/usage-and-pricing))

Polling results every few minutes therefore requires Pro. Pro accuracy: "the expression `5 8 * * *` would trigger an invocation between `08:05:00` and `08:05:59`." ([Managing cron jobs](https://vercel.com/docs/cron-jobs/manage-cron-jobs#cron-jobs-accuracy))

**Duration.** Cron jobs get the same limits as functions ([Managing cron jobs](https://vercel.com/docs/cron-jobs/manage-cron-jobs#cron-job-duration)):

- Hobby: 300 s default and maximum.
- Pro: 300 s default and 800 s maximum. An extended 1800 s maximum is in beta and requires a per-function `maxDuration`.

([Functions limits](https://vercel.com/docs/functions/limitations#max-duration))

Settling one matchday (a few queries per league) fits easily within these limits.

**Reliability semantics.** All of the following come from [Managing cron jobs](https://vercel.com/docs/cron-jobs/manage-cron-jobs):

- "Vercel will not retry an invocation if a cron job fails."
- "Cron job delivery is best effort … your function does not execute, and no runtime log is created for that scheduled run."
- "Cron delivery can also occasionally invoke the same scheduled run more than once."
- If a run outlasts its interval, "Vercel can trigger a second instance while the first is still running."
- Vercel's recommendation is to use locks *and* "idempotent reconciliation".
- Cron requests can be authenticated with a `CRON_SECRET` env var, which Vercel sends as `Authorization: Bearer …`.
- Cron requests don't follow redirects.

**What this means for Settlement and refunds:**

- Each job should be a *reconciliation*, not a single event. For example: "settle every finished match not yet settled" and "refund every Cancelled paid membership not yet refunded".
- A missed tick is then caught up by the next one.
- Mark each item done in the same transaction that does the work, for example a `settled_at` column, or a stored `refund` result keyed by `telegram_payment_charge_id`.
- Prevent overlapping runs with `pg_try_advisory_xact_lock(...)` or `SELECT … FOR UPDATE SKIP LOCKED`. Don't use session-level advisory locks. They don't survive PgBouncer transaction mode (see §3).
- Stars refunds (`refundStarPayment`) are external side effects. Record the attempt before calling the API and the result after, so a duplicate run can't refund twice.

**Free workaround and why we shouldn't rely on it.** An external pinger such as a GitHub Actions `schedule` can call a protected endpoint on Hobby. However:

- "The shortest interval … is once every 5 minutes."
- Runs "can be delayed during periods of high loads."
- "some queued jobs may be dropped."
- ([GitHub Actions events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows))

This also leaves the Hobby commercial-use restriction in place. It's acceptable only as a stopgap before monetization.

**Vercel-native worker option.** Vercel Daemons (beta, all plans) run a long-lived container, including Python and Celery beat. In beta they run in production only, and Hobby quotas stop them when exhausted. ([Vercel Daemons guide](https://vercel.com/kb/guide/vercel-daemons)) This is unnecessary for jobs that fit in a cron tick; Vercel's own guide points schedule-only work to Cron Jobs.

### 2. Telegram bot webhook

- The webhook is a normal POST route (`/api/bot/webhook` in `backend/main.py`), rewritten to `api/index.py` by `vercel.json`. Nothing about it is plan-specific.
- Telegram retries any response that is not 2XX and will "give up after a reasonable amount of attempts". `max_connections` can be 1–100 (default 40). ([Bot API: setWebhook](https://core.telegram.org/bots/api#setwebhook)) So the handler must be idempotent: the same `successful_payment` may arrive twice. The current `UPDATE … SET paid=TRUE` already is.
- Webhook and `getUpdates` are "two mutually exclusive ways of receiving updates" ([Bot API: Getting updates](https://core.telegram.org/bots/api#getting-updates)). No long-polling worker is needed on Vercel.
- **Hard deadline:** "The Bot API must receive an answer within 10 seconds after the pre-checkout query was sent." ([Bot API: answerPreCheckoutQuery](https://core.telegram.org/bots/api#answerprecheckoutquery))
  - On Fluid compute, cold starts are reduced by "function pre-warming on production deployments", and Python bundles ship precompiled `.pyc` bytecode. ([Fluid compute](https://vercel.com/docs/fluid-compute), [Python runtime](https://vercel.com/docs/functions/runtimes/python))
  - A cold FastAPI start plus a couple of Postgres round trips should fit well under 10 s.
  - The biggest controllable cost is the per-query TLS connect to Postgres (§3).

### 3. Postgres connections

**Current state.** `backend/app/database.py` `_connect()` opens a fresh pg8000 TLS connection inside `get_conn()`, and `fetchone`/`execute` each call `get_conn()`. One API request that runs N queries therefore makes N TCP+TLS+auth handshakes. This causes two problems:

- Added latency on every request.
- Bursts of connections at the database.

**What Vercel offers.**

- Fluid compute runs "multiple invocations [that] share a single function instance" for Python. ([Fluid compute](https://vercel.com/docs/fluid-compute#optimized-concurrency))
- So a module-level pool *is* reused across requests on the same instance.
- Vercel's pooling guide recommends the following ([Connection pooling with functions](https://vercel.com/kb/guide/connection-pooling-with-functions)):
  - create the pool globally
  - use a short idle timeout (~5 s)
  - "Don't set max pool size to 1"
  - use an external pooler
- The `attachDatabasePool` helper, which closes idle connections before an instance suspends, is shown only for Node (`@vercel/functions`). No Python equivalent is documented.
- Without such a helper, connections from suspended instances simply get dropped. A server-side pooler absorbs that.
- Each instance has a limit of 1,024 file descriptors shared across concurrent executions, including DB sockets. ([Functions limits](https://vercel.com/docs/functions/limitations#file-descriptors))

**Neon pooler** (the likely DB behind `POSTGRES_URL` from the Vercel Marketplace):

- Add `-pooler` to the endpoint hostname to get PgBouncer in transaction mode.
- Up to 10,000 client connections. The pool size is 0.9 × `max_connections` per user/db.
- Recommended for "serverless functions and connection-per-request workloads".
- **Not supported:** session state (`SET`, `LISTEN/NOTIFY`, session advisory locks, temp tables) and SQL-level `PREPARE`/`EXECUTE`.
- **Supported:** protocol-level prepared statements.
- Use the direct (non-pooler) URL for migrations / `init_db()`.
- ([Neon connection pooling](https://neon.com/docs/connect/connection-pooling))

**Recommended changes (small, do before adding cron):**

1. Use the `-pooler` connection string for the app and keep a direct URL for `init_db`/migrations.
2. Open one connection per request (FastAPI dependency) or per cron run, not one per query.
3. Optionally keep a tiny module-level pool with a short idle timeout, per Vercel's guidance.
4. Use transaction-scoped locks (`pg_try_advisory_xact_lock`, `FOR UPDATE SKIP LOCKED`) for job exclusivity.

Assumption to verify: pg8000's DB-API `execute()` uses the unnamed extended-protocol statement and no SQL `PREPARE`, so it should work behind PgBouncer transaction mode. Not checked against pg8000 source in this research.

### 4. Alternatives

**Railway** ([pricing](https://railway.com/pricing), [cron jobs](https://docs.railway.com/reference/cron-jobs), [app sleeping](https://docs.railway.com/reference/app-sleeping))

- Hobby costs $5/month and includes $5 of usage. Usage is ≈ $20 per vCPU-month and $10 per GB-month, billed per second.
- Free plan: $1/month of usage, 0.5 GB per service.
- Cron services must be "at least 5 minutes apart". Timing "can vary by a few minutes". If the previous run is still going, Railway "will skip the new cron job". The process must exit.
- Alternatively, run the FastAPI web service plus an always-on worker with APScheduler and an ordinary in-process connection pool. That design has no pooling problems and no cold starts.
- Optional Serverless sleep kicks in after 5–10 min without outbound traffic. The first request may then see a "small delay" or a 502. Don't enable it for the webhook service.

**Fly.io** ([pricing](https://docs.fly.io/about/pricing), [fly machine run](https://fly.io/docs/machines/flyctl/fly-machine-run/), [background workers](https://fly.io/learn/background-workers/))

- No free tier for new orgs; the trial is 2 h of runtime or 7 days.
- shared-cpu-1x costs $2.19 (256 MB), $3.69 (512 MB) or $6.70 (1 GB) per month if always on.
- Managed Postgres starts at $38/month. Neon could be kept instead.
- Built-in scheduled Machines only support "hourly, daily, weekly, monthly", measured from creation time. That's useless for every-few-minutes polling. Fly's own guide says to run a scheduler process instead, for example supercronic or APScheduler in an always-on Machine.
- More operations work than Railway (Dockerfile/fly.toml, regions), with no advantage for this app.

## Side findings (out of scope, worth a ticket)

- **Stars checkout will hang.** `backend/main.py` `bot_webhook` only handles `message.successful_payment`. There is no `pre_checkout_query` handler and no call to `answerPreCheckoutQuery` anywhere in `backend/`. Telegram requires that answer within 10 s before it charges the user, so paid league joins can't complete until it's added.
- `bot_webhook` doesn't verify the `X-Telegram-Bot-Api-Secret-Token` header (set via `setWebhook secret_token`), so anyone can POST a fake `successful_payment`. ([Bot API: setWebhook](https://core.telegram.org/bots/api#setwebhook))
- `apscheduler` is in `backend/requirements.txt`. An in-process scheduler won't run reliably on Vercel functions, because instances suspend between requests. Use Vercel Cron, or move to an always-on worker.
