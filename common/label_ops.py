"""Running the labeller workspace: the reads and changes behind /admin and
tools/label_admin, in one copy so the dashboard and the command line cannot
drift apart (admin dashboard, phase 2).

Every change takes the founder who made it (`actor`) and writes admin_audit in
the same transaction (common/admin_audit). A missing labeller or batch raises
LookupError; a change the rules refuse (publishing a test a constant strategy
could pass) raises ValueError with the reason.

FOUNDER DECISIONS (2026-09-23): open application with admin approval; a
removed labeller keeps their answers (they are the measurement) and loses
every qualification; nothing here ever shows one labeller's answer to another.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from common.admin_audit import audit
from common.label_scoring import (
    CHECK_WINDOW,
    PASS_MARK,
    QUESTIONS_PER_TEST,
    constant_strategy_scores,
    is_correct,
)

DB = AsyncSession | AsyncConnection
# What an admin can set. `applied` is only ever the applicant's own doing.
STATUSES = ("active", "paused", "removed")
ROUNDS = ("practice", "qualify")


def _json(v: Any) -> Any:
    return json.loads(v) if isinstance(v, str) else v


async def labellers(db: DB) -> list[dict[str, Any]]:
    """Everyone who applied, with what they read and how much they have done."""
    rows = (await db.execute(text(
        """
        SELECT u.email, u.name, l.status, l.languages_read, l.note, l.created_at, l.approved_at, l.approved_by,
               count(r.id) AS answers, max(r.created_at) AS last_answer_at
        FROM labellers l JOIN users u ON u.id = l.user_id
        LEFT JOIN label_invites i ON i.user_id = l.user_id
        LEFT JOIN label_responses r ON r.invite_id = i.id
        GROUP BY u.email, u.name, l.user_id
        ORDER BY l.created_at
        """))).mappings().all()
    return [{**r, "languages_read": list(r["languages_read"])} for r in rows]


async def board(db: DB) -> list[dict[str, Any]]:
    """Every labeller's standing per kind: passed (by test or grant), best score,
    attempts, and accuracy on their last CHECK_WINDOW definite answers to hidden
    checks — the numbers api/routes/labeller.recheck acts on."""
    quals = (await db.execute(text(
        """
        SELECT u.email, l.status, q.user_id, q.kind, q.passed_at, q.best_score, q.attempts, q.granted_by
        FROM labeller_qualifications q JOIN labellers l ON l.user_id = q.user_id JOIN users u ON u.id = q.user_id
        ORDER BY u.email, q.kind
        """))).mappings().all()
    checks = (await db.execute(text(
        """
        SELECT user_id, kind, selected, expected FROM (
            SELECT i.user_id, b.kind, r.selected, t.expected,
                   row_number() OVER (PARTITION BY i.user_id, b.kind ORDER BY r.created_at DESC) AS n
            FROM label_responses r JOIN label_invites i ON i.id = r.invite_id
            JOIN label_tasks t ON t.id = r.task_id JOIN label_batches b ON b.id = t.batch_id
            WHERE i.user_id IS NOT NULL AND b.purpose = 'work' AND t.expected IS NOT NULL
              AND NOT r.unsure AND NOT r.skipped
        ) w WHERE n <= :w
        """), {"w": CHECK_WINDOW})).mappings().all()
    right: Counter = Counter()
    total: Counter = Counter()
    for c in checks:
        k = (c["user_id"], c["kind"])
        total[k] += 1
        right[k] += is_correct({"selected": _json(c["selected"])}, _json(c["expected"]))
    return [
        {"email": q["email"], "status": q["status"], "kind": q["kind"], "passed": q["passed_at"] is not None,
         "passed_at": q["passed_at"], "best_score": q["best_score"], "attempts": q["attempts"],
         "granted_by": q["granted_by"], "checks_right": right[(q["user_id"], q["kind"])],
         "checks_total": total[(q["user_id"], q["kind"])]}
        for q in quals
    ]


async def batches(db: DB) -> list[dict[str, Any]]:
    """Every batch with its progress. `people` counts accounts (or anonymous
    invites) that answered anything — a head count, never what they chose."""
    rows = (await db.execute(text(
        """
        SELECT b.key, b.name, b.kind, b.purpose, b.open, b.listed, b.self_join, b.created_at,
               count(DISTINCT t.id) AS tasks,
               count(DISTINCT t.id) FILTER (WHERE t.languages IS NOT NULL) AS gated,
               count(DISTINCT t.id) FILTER (WHERE r.id IS NOT NULL) AS answered_tasks,
               count(r.id) AS responses,
               count(DISTINCT coalesce(i.user_id::text, i.id::text)) FILTER (WHERE r.id IS NOT NULL) AS people
        FROM label_batches b
        LEFT JOIN label_tasks t ON t.batch_id = b.id
        LEFT JOIN label_responses r ON r.task_id = t.id
        LEFT JOIN label_invites i ON i.id = r.invite_id
        GROUP BY b.id ORDER BY b.created_at DESC
        """))).mappings().all()
    return [dict(r) for r in rows]


async def _batch(db: DB, key: str) -> dict[str, Any]:
    b = (await db.execute(text("SELECT id, key, name, kind, purpose, open FROM label_batches WHERE key = :k"),
                          {"k": key})).mappings().first()
    if b is None:
        raise LookupError(f"no batch with key {key}")
    return dict(b)


async def round_items(db: DB, key: str) -> list[dict[str, Any]]:
    """A practice round's or test's items with their answers and explanations,
    for a founder to read and edit before publishing."""
    b = await _batch(db, key)
    rows = (await db.execute(text(
        "SELECT position, payload, candidates, expected, explanation FROM label_tasks "
        "WHERE batch_id = :b ORDER BY position"), {"b": b["id"]})).mappings().all()
    items = []
    for r in rows:
        payload = _json(r["payload"]) or {}
        expected = _json(r["expected"])
        selected = (expected or {}).get("selected") or []
        if expected is None:
            answer = "no answer"
        elif payload:
            answer = "yes" if selected else "no"
        else:
            answer = f"{len(selected)} of {len(_json(r['candidates']) or [])} ticked"
        items.append({"position": r["position"], "speaker": payload.get("speaker"),
                      "quote": payload.get("quote_text"), "answer": answer, "explanation": r["explanation"] or ""})
    return items


async def check_round(db: DB, key: str) -> dict[str, Any]:
    """Whether a round may be published: every item explained, no constant
    strategy passes, and a test has enough questions to draw from."""
    b = await _batch(db, key)
    tasks = (await db.execute(text("SELECT id, expected, explanation FROM label_tasks WHERE batch_id = :b"),
                              {"b": b["id"]})).mappings().all()
    items = [{"id": str(t["id"]), "expected": _json(t["expected"]) or {}} for t in tasks]
    scores = constant_strategy_scores(items)
    missing = sum(1 for t in tasks if not (t["explanation"] or "").strip())
    reasons = []
    if not tasks:
        reasons.append("it has no items")
    if missing:
        reasons.append(f"{missing} item(s) have no explanation")
    passable = [s for s, v in scores.items() if v >= PASS_MARK]
    if passable:
        reasons.append(f"'{passable[0]}' would pass it without reading")
    if b["purpose"] == "qualify" and len(tasks) < QUESTIONS_PER_TEST:
        reasons.append(f"a test needs at least {QUESTIONS_PER_TEST} items")
    return {"key": key, "name": b["name"], "purpose": b["purpose"], "items": len(tasks), "missing": missing,
            "scores": scores, "ok": not reasons, "reasons": reasons}


async def _user_id(db: DB, email: str) -> Any:
    uid = (await db.execute(text("SELECT id FROM users WHERE lower(email) = lower(:e)"), {"e": email})).scalar()
    if uid is None:
        raise LookupError(f"no Prism account with the email {email}")
    return uid


async def set_status(db: DB, email: str, status: str, actor: str) -> str:
    """Approve (active), pause, or remove. Returns the status it had before."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")
    uid = await _user_id(db, email)
    was = (await db.execute(text("SELECT status FROM labellers WHERE user_id = :u FOR UPDATE"), {"u": uid})).scalar()
    if was is None:
        raise LookupError(f"{email} has not applied at /label")
    await db.execute(text(
        """
        UPDATE labellers SET status = :s,
               approved_at = CASE WHEN :s = 'active' THEN now() ELSE approved_at END,
               approved_by = CASE WHEN :s = 'active' THEN :a ELSE approved_by END
        WHERE user_id = :u
        """), {"s": status, "a": actor, "u": uid})
    if status == "removed":
        # Their answers stay (they are the measurement); what they may do goes.
        await db.execute(text("UPDATE labeller_qualifications SET passed_at = NULL WHERE user_id = :u"), {"u": uid})
    await audit(db, actor, "labeller.status", email, {"from": was, "to": status})
    return was


async def add(db: DB, email: str, languages: list[str], actor: str) -> None:
    """Make an existing Prism account an active labeller without an application."""
    if not languages:
        raise ValueError("choose at least one language they read")
    uid = await _user_id(db, email)
    await db.execute(text(
        """
        INSERT INTO labellers (user_id, languages_read, status, note, approved_at, approved_by)
        VALUES (:u, CAST(:l AS text[]), 'active', 'added by an admin', now(), :a)
        ON CONFLICT (user_id) DO UPDATE
          SET languages_read = EXCLUDED.languages_read, status = 'active',
              approved_at = now(), approved_by = EXCLUDED.approved_by
        """), {"u": uid, "l": languages, "a": actor})
    await audit(db, actor, "labeller.add", email, {"languages": languages})


async def qualify(db: DB, email: str, kind: str, granted: bool, actor: str) -> None:
    """Grant a kind without a test (recorded as a grant, never as a score), or
    withdraw it. Only kinds that have batches exist."""
    if not (await db.execute(text("SELECT 1 FROM label_batches WHERE kind = :k LIMIT 1"), {"k": kind})).first():
        raise ValueError(f"there is no task kind {kind!r}")
    uid = await _user_id(db, email)
    if not (await db.execute(text("SELECT 1 FROM labellers WHERE user_id = :u"), {"u": uid})).first():
        raise LookupError(f"{email} has not applied at /label")
    if granted:
        await db.execute(text(
            """
            INSERT INTO labeller_qualifications (user_id, kind, passed_at, granted_by)
            VALUES (:u, :k, now(), :a)
            ON CONFLICT (user_id, kind) DO UPDATE
              SET passed_at = coalesce(labeller_qualifications.passed_at, now()), granted_by = :a
            """), {"u": uid, "k": kind, "a": actor})
    else:
        await db.execute(text("UPDATE labeller_qualifications SET passed_at = NULL WHERE user_id = :u AND kind = :k"),
                         {"u": uid, "k": kind})
    await audit(db, actor, "labeller.grant" if granted else "labeller.revoke", email, {"kind": kind})


async def set_listed(db: DB, key: str, on: bool, actor: str) -> str:
    """Show a batch on the labeller dashboard, or take it off. Listing also
    closes anonymous self-join: a listed batch is reached only through an
    approved account, and api/routes/label.py refuses /join on it."""
    name = (await db.execute(text(
        "UPDATE label_batches SET listed = :on, self_join = CASE WHEN :on THEN false ELSE self_join END "
        "WHERE key = :k RETURNING name"), {"k": key, "on": on})).scalar()
    if name is None:
        raise LookupError(f"no batch with key {key}")
    await audit(db, actor, "batch.list" if on else "batch.unlist", key)
    return name


async def set_open(db: DB, key: str, on: bool, actor: str) -> None:
    """Open or close a batch. Opening a practice round or a test is publishing
    it, and is refused while check_round finds a reason not to."""
    b = await _batch(db, key)
    if on and b["purpose"] in ROUNDS:
        verdict = await check_round(db, key)
        if not verdict["ok"]:
            raise ValueError("not publishable: " + "; ".join(verdict["reasons"]))
    await db.execute(text("UPDATE label_batches SET open = :on WHERE id = :b"), {"on": on, "b": b["id"]})
    await audit(db, actor, "batch.open" if on else "batch.close", key)


async def save_explanations(db: DB, key: str, edits: list[tuple[int, str]], actor: str) -> int:
    b = await _batch(db, key)
    for position, explanation in edits:
        await db.execute(text("UPDATE label_tasks SET explanation = :x WHERE batch_id = :b AND position = :p"),
                         {"x": explanation, "b": b["id"], "p": position})
    await audit(db, actor, "batch.explanations", key, {"edited": len(edits)})
    return len(edits)


async def gate_languages(db: DB, key: str, actor: str) -> dict[str, int]:
    """Fill in what each task needs its labeller to read: every article
    language on the events it shows, plus English for Prism's own headline, or
    a claim task's own `language`. A task written before the gate has NULL
    languages, which means shown to everyone. Returns a tally by need."""
    b = await _batch(db, key)
    tasks = (await db.execute(text("SELECT id, seed_event_id, candidates, payload FROM label_tasks WHERE batch_id = :b"),
                              {"b": b["id"]})).mappings().all()
    event_ids = {str(t["seed_event_id"]) for t in tasks if t["seed_event_id"]}
    for t in tasks:
        event_ids |= {c["id"] for c in _json(t["candidates"]) or []}
    langs_of = {
        str(r["event_id"]): set(r["langs"])
        for r in (await db.execute(text(
            """
            SELECT m.event_id, array_agg(DISTINCT ri.language) FILTER (WHERE ri.language IS NOT NULL) AS langs
            FROM event_memberships m JOIN articles a ON a.id = m.article_id
            JOIN raw_items ri ON ri.id = a.raw_item_id
            WHERE m.event_id = ANY(CAST(:ids AS uuid[])) GROUP BY m.event_id
            """), {"ids": sorted(event_ids)})).mappings().all()
        if r["langs"]
    }
    tally: Counter = Counter()
    for t in tasks:
        payload = _json(t["payload"])
        if payload is not None:
            need = {payload.get("language") or "en"}
        else:
            # Prism's own headline is English on every event, so English is always needed.
            need = {"en"}
            for eid in [str(t["seed_event_id"])] + [c["id"] for c in _json(t["candidates"]) or []]:
                need |= langs_of.get(eid, set())
        await db.execute(text("UPDATE label_tasks SET languages = CAST(:l AS text[]) WHERE id = :i"),
                         {"l": sorted(need), "i": t["id"]})
        tally["+".join(sorted(need))] += 1
    await audit(db, actor, "batch.languages", key, {"tasks": len(tasks)})
    return dict(tally.most_common())
