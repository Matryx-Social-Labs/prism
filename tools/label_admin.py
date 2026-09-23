"""Run the labeller workspace: who applied, who is approved, which batches are listed.

    uv run python -m tools.label_admin --pending                  # applications waiting on you
    uv run python -m tools.label_admin --labellers                # everyone, with status and languages
    uv run python -m tools.label_admin --board                    # per kind: passed, attempts, live check accuracy
    uv run python -m tools.label_admin --approve a@x.com b@y.com  # applied|paused -> active
    uv run python -m tools.label_admin --pause a@x.com            # stops their writes at once
    uv run python -m tools.label_admin --list KEY                 # show a batch on the dashboard
    uv run python -m tools.label_admin --unlist KEY
    uv run python -m tools.label_admin --languages KEY            # fill in what each task needs read
    uv run python -m tools.label_admin --qualify a@x.com event_identity   # qualify by hand, no test

FOUNDER DECISION (2026-09-23): open application, ADMIN APPROVAL. Anyone with a
Prism account can apply at /label; nobody is served a task until this tool
approves them. The labels these people produce become the measurement every
quality gate is judged on, so letting a stranger write into it on the strength
of a form was the one option ruled out.

`--languages` exists because a task written before the gate has NULL
languages, which means "shown to everyone" — correct for a founder's link, wrong
for a Kannada seed served to someone who reads only Hindi. It fills them in
from the events a task shows (every article's language, plus English for the
Prism headline above each) or from a claim task's own `language`.

`--qualify` is for a kind that has no test yet — the cross-language task's
first labellers ARE the answer key its test will be built from — and for
people whose judgement the founders already trust. It is recorded as a grant
(`granted_by`), never as a score, so it can always be told apart from a pass.

Writes to PRODUCTION by default (it is an admin tool — every command here is a
deliberate act); --db points it anywhere else.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import asyncpg

from tools.snapshot_l2 import _prod_url


async def _conn(url: str | None) -> asyncpg.Connection:
    return await asyncpg.connect(url or _prod_url(), timeout=60)


async def pending(c: asyncpg.Connection) -> None:
    rows = await c.fetch(
        """
        SELECT u.email, u.name, l.languages_read, l.note, l.created_at
        FROM labellers l JOIN users u ON u.id = l.user_id
        WHERE l.status = 'applied' ORDER BY l.created_at
        """)
    if not rows:
        print("  no applications waiting")
    for r in rows:
        print(f"  {r['email']:34} {r['name'] or '':20} reads {','.join(r['languages_read']):14} "
              f"applied {r['created_at']:%d %b %H:%M}")
        if r["note"]:
            print(f"      “{r['note'][:200]}”")


async def labellers(c: asyncpg.Connection) -> None:
    for r in await c.fetch(
        """
        SELECT u.email, l.status, l.languages_read, l.approved_at, l.approved_by,
               (SELECT count(*) FROM label_responses r JOIN label_invites i ON i.id = r.invite_id
                WHERE i.user_id = l.user_id) AS answers
        FROM labellers l JOIN users u ON u.id = l.user_id ORDER BY l.status, u.email
        """):
        print(f"  {r['status']:8} {r['email']:34} reads {','.join(r['languages_read']):14} "
              f"{r['answers']:5} answers")


async def board(c: asyncpg.Connection) -> None:
    """Every labeller's standing per kind: passed (by test or grant), best score,
    attempts, and accuracy on the last 20 definite answers to hidden checks —
    the numbers api/routes/labeller.recheck acts on."""
    from common.label_scoring import CHECK_WINDOW, is_correct

    for r in await c.fetch(
        """
        SELECT u.email, l.status, q.kind, q.passed_at, q.best_score, q.attempts, q.granted_by, q.user_id
        FROM labellers l JOIN users u ON u.id = l.user_id
        LEFT JOIN labeller_qualifications q ON q.user_id = l.user_id
        ORDER BY u.email, q.kind
        """):
        if r["kind"] is None:
            print(f"  {r['email']:34} {r['status']:8} (no kinds yet)")
            continue
        checks = await c.fetch(
            """
            SELECT r.selected, t.expected FROM label_responses r
            JOIN label_invites i ON i.id = r.invite_id JOIN label_tasks t ON t.id = r.task_id
            JOIN label_batches b ON b.id = t.batch_id
            WHERE i.user_id = $1 AND b.kind = $2 AND b.purpose = 'work' AND t.expected IS NOT NULL
              AND NOT r.unsure AND NOT r.skipped
            ORDER BY r.created_at DESC LIMIT $3
            """, r["user_id"], r["kind"], CHECK_WINDOW)
        right = sum(is_correct({"selected": json.loads(x["selected"]) if isinstance(x["selected"], str) else x["selected"]},
                               json.loads(x["expected"]) if isinstance(x["expected"], str) else x["expected"]) for x in checks)
        how = "granted" if r["granted_by"] else (f"best {r['best_score']:.0%}" if r["best_score"] is not None else "-")
        live = f"checks {right}/{len(checks)}" if checks else "no checks yet"
        print(f"  {r['email']:34} {r['status']:8} {r['kind']:18} {'PASSED' if r['passed_at'] else 'not passed':10} "
              f"{how:10} {r['attempts']} attempts  {live}")


async def set_status(c: asyncpg.Connection, emails: list[str], status: str, by: str) -> None:
    for email in emails:
        done = await c.fetchval(
            """
            UPDATE labellers l SET status = $2,
                   approved_at = CASE WHEN $2 = 'active' THEN now() ELSE l.approved_at END,
                   approved_by = CASE WHEN $2 = 'active' THEN $3 ELSE l.approved_by END
            FROM users u WHERE u.id = l.user_id AND lower(u.email) = lower($1)
            RETURNING u.email
            """, email, status, by)
        print(f"  {email:34} {'-> ' + status if done else 'NOT FOUND — they must apply at /label first'}")


async def listed(c: asyncpg.Connection, key: str, on: bool) -> None:
    # Listing also closes anonymous self-join: a listed batch is reached only
    # through an approved account, and api/routes/label.py refuses /join on it.
    # Doing both here keeps the row honest for anything that reads self_join.
    name = await c.fetchval(
        "UPDATE label_batches SET listed = $2, self_join = CASE WHEN $2 THEN false ELSE self_join END "
        "WHERE key = $1 RETURNING name", key, on)
    if name is None:
        raise SystemExit(f"no batch with key {key}")
    print(f"  {name!r} is {'listed on' if on else 'removed from'} the labeller dashboard")


async def languages(c: asyncpg.Connection, key: str) -> None:
    bid = await c.fetchval("SELECT id FROM label_batches WHERE key = $1", key)
    if bid is None:
        raise SystemExit(f"no batch with key {key}")
    tasks = await c.fetch(
        "SELECT id, seed_event_id, candidates, payload FROM label_tasks WHERE batch_id = $1", bid)
    event_ids = {t["seed_event_id"] for t in tasks if t["seed_event_id"]}
    for t in tasks:
        cands = t["candidates"] if isinstance(t["candidates"], list) else json.loads(t["candidates"] or "[]")
        event_ids |= {c_["id"] for c_ in cands}
    langs_of = {
        str(r["event_id"]): set(r["langs"])
        for r in await c.fetch(
            """
            SELECT m.event_id, array_agg(DISTINCT ri.language) FILTER (WHERE ri.language IS NOT NULL) AS langs
            FROM event_memberships m JOIN articles a ON a.id = m.article_id
            JOIN raw_items ri ON ri.id = a.raw_item_id
            WHERE m.event_id = ANY($1::uuid[]) GROUP BY m.event_id
            """, [str(e) for e in event_ids])
        if r["langs"]
    }
    updates = []
    for t in tasks:
        if t["payload"] is not None:
            payload = t["payload"] if isinstance(t["payload"], dict) else json.loads(t["payload"])
            need = {payload.get("language") or "en"}
        else:
            cands = t["candidates"] if isinstance(t["candidates"], list) else json.loads(t["candidates"] or "[]")
            # Prism's own headline is English on every event, so English is always needed.
            need = {"en"}
            for eid in [str(t["seed_event_id"])] + [c_["id"] for c_ in cands]:
                need |= langs_of.get(eid, set())
        updates.append((t["id"], sorted(need)))
    await c.executemany("UPDATE label_tasks SET languages = $2 WHERE id = $1", updates)
    tally: dict[str, int] = {}
    for _, need in updates:
        tally["+".join(need)] = tally.get("+".join(need), 0) + 1
    print(f"  {len(updates)} tasks gated: " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items(), key=lambda x: -x[1])))


async def qualify(c: asyncpg.Connection, email: str, kind: str, by: str) -> None:
    uid = await c.fetchval("SELECT l.user_id FROM labellers l JOIN users u ON u.id = l.user_id "
                           "WHERE lower(u.email) = lower($1)", email)
    if uid is None:
        raise SystemExit(f"{email} has not applied at /label")
    await c.execute(
        """
        INSERT INTO labeller_qualifications (user_id, kind, passed_at, granted_by)
        VALUES ($1, $2, now(), $3)
        ON CONFLICT (user_id, kind) DO UPDATE
          SET passed_at = coalesce(labeller_qualifications.passed_at, now()), granted_by = $3
        """, uid, kind, by)
    print(f"  {email} qualified for {kind} by {by} (a grant, not a test score)")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pending", action="store_true")
    ap.add_argument("--labellers", action="store_true")
    ap.add_argument("--board", action="store_true")
    ap.add_argument("--approve", nargs="+", metavar="EMAIL")
    ap.add_argument("--pause", nargs="+", metavar="EMAIL")
    ap.add_argument("--list", metavar="KEY")
    ap.add_argument("--unlist", metavar="KEY")
    ap.add_argument("--languages", metavar="KEY")
    ap.add_argument("--qualify", nargs=2, metavar=("EMAIL", "KIND"))
    ap.add_argument("--by", default="founder", help="recorded as approved_by")
    ap.add_argument("--db", metavar="URL", help="target database (default: production)")
    a = ap.parse_args()
    c = await _conn(a.db)
    try:
        if a.pending:
            await pending(c)
        elif a.labellers:
            await labellers(c)
        elif a.board:
            await board(c)
        elif a.approve:
            await set_status(c, a.approve, "active", a.by)
        elif a.pause:
            await set_status(c, a.pause, "paused", a.by)
        elif a.list:
            await listed(c, a.list, True)
        elif a.unlist:
            await listed(c, a.unlist, False)
        elif a.languages:
            await languages(c, a.languages)
        elif a.qualify:
            await qualify(c, a.qualify[0], a.qualify[1], a.by)
        else:
            ap.print_help()
            return 2
        return 0
    finally:
        await c.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
