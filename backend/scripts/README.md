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
