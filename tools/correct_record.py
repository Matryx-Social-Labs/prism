"""Record a correction on a record: the public corrections log (api/routes/corrections.py).

    uv run python -m tools.correct_record --list                         # the newest corrections
    uv run python -m tools.correct_record --event ID --reason prism_error \\
        --note "The headline said 14 were injured; the reports say 12." --by founder@x.com            # dry run
    uv run python -m tools.correct_record --event ID --reason source_correction --note "..." --by X --apply

A correction is an editorial act, so it names who made it (--by, recorded in
admin_audit in the same transaction) and says why in words a reader sees:
  source_correction — the outlet corrected its own report
  prism_error       — Prism got it wrong
Fix the record first (or let the pipeline rewrite it); the previous version is
already kept by the events trigger and is shown beside the correction. Reads
production read-only unless --apply.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

import asyncpg

REASONS = ("source_correction", "prism_error")


async def main() -> int:
    from tools.snapshot_l2 import _prod_url

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--event", type=uuid.UUID)
    ap.add_argument("--reason", choices=REASONS)
    ap.add_argument("--note", help="what was wrong and what is right, 10-600 characters, shown to readers")
    ap.add_argument("--by", help="who is making the correction (recorded)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--db", metavar="URL", help="target database (default: production)")
    a = ap.parse_args()
    c = await asyncpg.connect(a.db or _prod_url(), timeout=60)
    try:
        if a.list:
            for r in await c.fetch("SELECT created_at, event_id, reason, note, actor FROM event_corrections "
                                   "ORDER BY created_at DESC LIMIT 30"):
                print(f"  {r['created_at']:%Y-%m-%d %H:%M}  {r['event_id']}  {r['reason']:17}  {r['actor']}: {r['note']}")
            return 0
        if not (a.event and a.reason and a.note and a.by):
            ap.error("--event, --reason, --note and --by are all required to record a correction")
        if not 10 <= len(a.note) <= 600:
            ap.error("--note must be 10-600 characters: it is what a reader sees")
        title = await c.fetchval("SELECT title FROM events WHERE id = $1", a.event)
        if title is None:
            ap.error(f"no record {a.event}")
        print(f"  record: {title}\n  reason: {a.reason}\n  note:   {a.note}\n  by:     {a.by}")
        if not a.apply:
            print("DRY RUN: add --apply to publish this correction.")
            return 0
        async with c.transaction():
            await c.execute("INSERT INTO event_corrections (event_id, reason, note, actor) VALUES ($1, $2, $3, $4)",
                            a.event, a.reason, a.note, a.by)
            await c.execute("INSERT INTO admin_audit (actor, action, target, detail) VALUES ($1, 'record.correct', $2, "
                            "jsonb_build_object('reason', $3::text, 'note', $4::text))",
                            a.by, str(a.event), a.reason, a.note)
        print("  published: the record now shows it, and /corrections lists it.")
        return 0
    finally:
        await c.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
