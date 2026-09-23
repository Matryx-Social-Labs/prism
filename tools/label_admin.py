"""Run the labeller workspace from the command line — the same operations as /admin.

    uv run python -m tools.label_admin --pending                  # applications waiting on you
    uv run python -m tools.label_admin --labellers                # everyone, with status and languages
    uv run python -m tools.label_admin --board                    # per kind: passed, attempts, live check accuracy
    uv run python -m tools.label_admin --batches                  # every batch with its progress
    uv run python -m tools.label_admin --approve a@x.com b@y.com  # applied|paused|removed -> active
    uv run python -m tools.label_admin --pause a@x.com            # stops their writes at once
    uv run python -m tools.label_admin --remove a@x.com           # stops them and withdraws every kind; answers kept
    uv run python -m tools.label_admin --add a@x.com en,kn        # an existing account, active without applying
    uv run python -m tools.label_admin --list KEY                 # show a batch on the dashboard
    uv run python -m tools.label_admin --unlist KEY
    uv run python -m tools.label_admin --languages KEY            # fill in what each task needs read
    uv run python -m tools.label_admin --qualify a@x.com event_identity   # qualify by hand, no test
    uv run python -m tools.label_admin --revoke a@x.com event_identity

FOUNDER DECISION (2026-09-23): open application, ADMIN APPROVAL. Anyone with a
Prism account can apply at /label; nobody is served a task until an admin
approves them. The labels these people produce become the measurement every
quality gate is judged on, so letting a stranger write into it on the strength
of a form was the one option ruled out.

`--languages` exists because a task written before the gate has NULL
languages, which means "shown to everyone" — correct for a founder's link, wrong
for a Kannada seed served to someone who reads only Hindi.

`--qualify` is for a kind that has no test yet — the cross-language task's
first labellers ARE the answer key its test will be built from — and for
people whose judgement the founders already trust. It is recorded as a grant
(`granted_by`), never as a score, so it can always be told apart from a pass.

Every change is written to admin_audit against `--by` (common/label_ops is the
one copy of these operations; /admin calls the same functions). Writes to
PRODUCTION by default (it is an admin tool — every command here is a deliberate
act); --db points it anywhere else.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy.ext.asyncio import create_async_engine

from common import label_ops
from tools.snapshot_l2 import _prod_url


def _pct(v: float | None) -> str:
    return f"{v:.0%}" if v is not None else "-"


async def _read(conn, a: argparse.Namespace) -> bool:
    if a.pending or a.labellers:
        rows = [r for r in await label_ops.labellers(conn) if not a.pending or r["status"] == "applied"]
        if not rows:
            print("  nobody here")
        for r in rows:
            print(f"  {r['status']:8} {r['email']:34} reads {','.join(r['languages_read']):14} {r['answers']:5} answers")
            if a.pending and r["note"]:
                print(f"      “{r['note'][:200]}”")
    elif a.board:
        for r in await label_ops.board(conn):
            how = "granted" if r["granted_by"] else f"best {_pct(r['best_score'])}"
            live = f"checks {r['checks_right']}/{r['checks_total']}" if r["checks_total"] else "no checks yet"
            print(f"  {r['email']:34} {r['status']:8} {r['kind']:18} {'PASSED' if r['passed'] else 'not passed':10} "
                  f"{how:10} {r['attempts']} attempts  {live}")
    elif a.batches:
        for b in await label_ops.batches(conn):
            flags = ",".join(f for f, on in (("open", b["open"]), ("listed", b["listed"]), ("self-join", b["self_join"])) if on)
            print(f"  {b['key']:14} {b['purpose']:8} {b['kind']:18} {b['answered_tasks']:4}/{b['tasks']:<4} "
                  f"{b['people']:3} people  {flags:22} {b['name'][:40]}")
    else:
        return False
    return True


async def _write(conn, a: argparse.Namespace) -> bool:
    for flag, status in (("approve", "active"), ("pause", "paused"), ("remove", "removed")):
        for email in getattr(a, flag) or []:
            was = await label_ops.set_status(conn, email, status, a.by)
            print(f"  {email:34} {was} -> {status}")
    if a.add:
        await label_ops.add(conn, a.add[0], [x.strip() for x in a.add[1].split(",") if x.strip()], a.by)
        print(f"  {a.add[0]} is an active labeller reading {a.add[1]}")
    if a.list or a.unlist:
        name = await label_ops.set_listed(conn, a.list or a.unlist, bool(a.list), a.by)
        print(f"  {name!r} is {'listed on' if a.list else 'removed from'} the labeller dashboard")
    if a.languages:
        tally = await label_ops.gate_languages(conn, a.languages, a.by)
        print(f"  {sum(tally.values())} tasks gated: " + ", ".join(f"{k} {v}" for k, v in tally.items()))
    for flag, granted in (("qualify", True), ("revoke", False)):
        if getattr(a, flag):
            email, kind = getattr(a, flag)
            await label_ops.qualify(conn, email, kind, granted, a.by)
            print(f"  {email} {'qualified for' if granted else 'no longer qualified for'} {kind} by {a.by}")
    return any(getattr(a, f) for f in ("approve", "pause", "remove", "add", "list", "unlist", "languages", "qualify", "revoke"))


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for flag in ("pending", "labellers", "board", "batches"):
        ap.add_argument(f"--{flag}", action="store_true")
    for flag in ("approve", "pause", "remove"):
        ap.add_argument(f"--{flag}", nargs="+", metavar="EMAIL")
    ap.add_argument("--add", nargs=2, metavar=("EMAIL", "LANGS"))
    ap.add_argument("--list", metavar="KEY")
    ap.add_argument("--unlist", metavar="KEY")
    ap.add_argument("--languages", metavar="KEY")
    ap.add_argument("--qualify", nargs=2, metavar=("EMAIL", "KIND"))
    ap.add_argument("--revoke", nargs=2, metavar=("EMAIL", "KIND"))
    ap.add_argument("--by", default="founder", help="recorded as approved_by / granted_by and in admin_audit")
    ap.add_argument("--db", metavar="URL", help="target database (default: production)")
    a = ap.parse_args()
    url = (a.db or _prod_url()).replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url, connect_args={"timeout": 60})
    try:
        # One transaction per run: a change and its audit row commit together,
        # and a refused change leaves nothing behind.
        async with engine.begin() as conn:
            if await _read(conn, a) or await _write(conn, a):
                return 0
        ap.print_help()
        return 2
    except (LookupError, ValueError) as e:
        print(f"  refused: {e}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
