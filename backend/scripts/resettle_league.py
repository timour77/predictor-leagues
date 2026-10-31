"""Re-settle one League after the data source corrected a result.

Recomputes the final standings and Trophies from the current match data in one transaction,
with the same logic as Settlement. Settled results are otherwise final.

    python -m scripts.resettle_league LEAGUE_ID [--dry-run] [--notify]
"""
import argparse
import sys
from datetime import datetime, timezone

from app import settlement
from app.errors import DomainError
from scripts._db import direct_engine


def _fmt(s: dict | None) -> str:
    return "-" if s is None else f"#{s['rank']} {s['points']}p {s['exact']}x"


def report(out: dict) -> str:
    lines = [f"{'DRY RUN: ' if out['dry_run'] else ''}League {out['league_id']} \"{out['name']}\""]
    sc = out["matches_scored"]
    if sc["old"] != sc["new"]:
        lines.append(f"matches scored: {sc['old']} -> {sc['new']}")
    for r in out["standings"]:
        if r["old"] != r["new"]:
            lines.append(f"  user {r['user_id']}: {_fmt(r['old'])} -> {_fmt(r['new'])}")
    for u in out["trophies"]["added"]:
        lines.append(f"  trophy added:   user {u}")
    for u in out["trophies"]["removed"]:
        lines.append(f"  trophy removed: user {u}")
    if not out["changed"]:
        lines.append("no changes")
    elif out["dry_run"]:
        lines.append("nothing written (dry run)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("league_id", type=int)
    ap.add_argument("--dry-run", action="store_true", help="print the diff, write nothing")
    ap.add_argument("--notify", action="store_true", help="queue a message to Members whose result changed")
    args = ap.parse_args(argv)
    try:
        with direct_engine().begin() as conn:
            out = settlement.resettle_league(conn, args.league_id, datetime.now(timezone.utc),
                                             dry_run=args.dry_run, notify=args.notify)
    except DomainError as e:
        sys.exit(f"error: {e.detail}")
    print(report(out))


if __name__ == "__main__":
    main()
