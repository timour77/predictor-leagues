# Operator scripts

There is no HTTP admin surface: operator actions are scripts with direct DB access.
Run from `backend/` with `.env` (or the environment) providing `DATABASE_URL_DIRECT`:

```bash
python -m scripts.db_status
```

New scripts use `scripts/_db.py:direct_engine()`.
