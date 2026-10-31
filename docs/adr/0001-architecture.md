# Vercel + Neon, one cron tick, outbox for payments, Alembic migrations

The rewrite keeps FastAPI + Postgres + React on Vercel Pro with Neon (pooler URL for the app, direct URL for migrations). Scheduled work runs as a single per-minute `/api/cron/tick` endpoint made of idempotent steps (match sync, League start/Cancellation, Settlement, outgoing Telegram notifications) guarded by `CRON_SECRET` and a Postgres transaction-level advisory lock. Settlement writes final standings and Trophies in one DB transaction; Telegram calls (e.g. notifying a Creator of a Cancellation) are made afterwards from a notifications outbox. Schema is managed by Alembic (SQLAlchemy Core + psycopg3), not `init_db()`.

## Considered options

- Railway with an always-on worker (APScheduler, in-process pool): simpler scheduling, but a second platform and cost for a problem Vercel Pro already solves. Kept as the fallback if best-effort cron proves too unreliable.
- Keeping pg8000 + hand-rolled SQL migrations: less to learn, but no pooling or transaction story and a custom migration runner to maintain.

## Consequences

- Vercel cron may skip or duplicate runs and never retries, so every tick step must be safe to repeat and safe to skip.
- Telegram calls cannot join a DB transaction; the outbox gives retries and an audit trail. Payments is limited to Tips and later Paid features (see ADR 0002): payments never fund a reward, so there is no fee, refund or payout flow.
- No HTTP admin surface; operator actions are scripts with direct DB access.
