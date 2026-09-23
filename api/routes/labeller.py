"""The labeller workspace: apply, get approved, see the batches you can do, start one.

GET  /api/v1/labeller/me                    — your application and what you read
POST /api/v1/labeller/apply                 — apply, or change the languages you read
GET  /api/v1/labeller/batches               — listed batches, in your languages, with YOUR progress
POST /api/v1/labeller/batches/{key}/start   — the write credential for one batch
POST /api/v1/labeller/practice/{kind}/start  — a practice round: answer, then see why
POST /api/v1/labeller/qualify/{kind}/start   — a scored test; 90% to pass (phase 3)

api/routes/label.py is the task protocol — one judgement at a time, keyed by a
per-batch invite. This is the signed-in surface in front of it, and it
deliberately does not replace it: starting a batch mints (or returns) an invite
bound to the account, and from there the labeller answers through exactly the
routes a founder's invite link uses. Every response, status, agreement and
compile path in tools/gold_candidates keeps working, untouched.

FOUNDER DECISIONS (2026-09-23): open application, admin approval — `status`
starts `applied` and only tools/label_admin moves it to `active`; tasks are
gated by the languages a labeller reads; and a 90% test per task kind, passed
before any work batch of that kind is offered (common/label_scoring.py).

It never returns another labeller's answer, for the reason label.py gives:
a second opinion that has seen the first is not a second opinion. The dashboard
shows HOW MANY people are on a batch, never what they chose.
"""

from __future__ import annotations

import json
import random
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from common.db import get_db
from common.label_scoring import PASS_MARK, QUESTIONS_PER_TEST, RETAKE_AFTER_HOURS, is_correct
from common.languages import LANGUAGES

router = APIRouter()

MAX_NOTE = 500
# The languages a task may be gated on are the languages Prism ingests.
READABLE = tuple(LANGUAGES)


class Apply(BaseModel):
    languages_read: Annotated[list[str], Field(min_length=1, max_length=len(READABLE))]
    note: Annotated[str, Field(max_length=MAX_NOTE)] = ""


# The language gate, the one copy (label.py's task routes read it too). A task
# is ELIGIBLE when every language it needs is one the labeller reads. NULL task
# `languages` is no gate — every task written before the gate existed — and a
# NULL `:langs` is an anonymous invite, a founder's link, served everything.
ELIGIBLE = ("(CAST(:langs AS text[]) IS NULL OR t.languages IS NULL "
            "OR t.languages <@ CAST(:langs AS text[]))")


async def labeller_row(db: AsyncSession, user_id: uuid.UUID) -> dict | None:
    row = (
        await db.execute(
            text("SELECT status, languages_read, note, created_at FROM labellers WHERE user_id = :u"),
            {"u": str(user_id)},
        )
    ).mappings().first()
    return dict(row) if row else None


async def languages_for_invite(db: AsyncSession, invite_user_id: uuid.UUID | None) -> list[str] | None:
    """The gate for one invite: None for an anonymous invite (a founder's link,
    no gate, exactly as before), the labeller's languages for an account's.

    Raises 403 when the account behind the invite is no longer an active
    labeller — pausing someone must stop their writes, not just hide the
    dashboard from them."""
    if invite_user_id is None:
        return None
    row = await labeller_row(db, invite_user_id)
    if row is None or row["status"] != "active":
        raise HTTPException(status_code=403, detail="this labeller is not active")
    return list(row["languages_read"])


@router.get("/api/v1/labeller/me")
async def me(user_id: uuid.UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = await labeller_row(db, user_id)
    return {
        "status": row["status"] if row else "none",
        "languages_read": list(row["languages_read"]) if row else [],
        "note": (row or {}).get("note") or "",
        "languages_available": [
            {"code": lang.code, "name": lang.name, "native": lang.native} for lang in LANGUAGES.values()
        ],
    }


@router.post("/api/v1/labeller/apply")
async def apply(body: Apply, user_id: uuid.UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Apply, or update the languages you read. Never changes `status`: applying
    again cannot promote an applicant, and an approved labeller changing their
    languages stays approved."""
    langs = sorted({code for code in body.languages_read if code in READABLE})
    if not langs:
        raise HTTPException(status_code=422, detail="choose at least one language you read")
    await db.execute(
        text(
            """
            INSERT INTO labellers (user_id, languages_read, note)
            VALUES (:u, CAST(:l AS text[]), :n)
            ON CONFLICT (user_id) DO UPDATE
              SET languages_read = EXCLUDED.languages_read, note = EXCLUDED.note
            """
        ),
        {"u": str(user_id), "l": langs, "n": body.note.strip() or None},
    )
    row = await labeller_row(db, user_id)
    return {"status": row["status"], "languages_read": list(row["languages_read"])}


@router.get("/api/v1/labeller/batches")
async def batches(user_id: uuid.UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Listed, open batches with at least one task in this labeller's languages,
    split into the ones with work left and the ones they have finished. Progress
    is THEIR answers over THEIR eligible tasks; `labellers` is a head count."""
    row = await labeller_row(db, user_id)
    if row is None or row["status"] != "active":
        return {"status": row["status"] if row else "none", "ready": [], "done": [], "kinds": []}
    rows = (
        await db.execute(
            text(
                f"""
                SELECT b.key, b.name, b.kind, b.notes,
                       (SELECT count(*) FROM label_tasks t
                        WHERE t.batch_id = b.id AND {ELIGIBLE}) AS eligible,
                       (SELECT count(*) FROM label_responses r
                        JOIN label_tasks t ON t.id = r.task_id
                        JOIN label_invites i ON i.id = r.invite_id
                        WHERE t.batch_id = b.id AND i.user_id = :u AND {ELIGIBLE}) AS answered,
                       (SELECT count(DISTINCT r.invite_id) FROM label_responses r
                        JOIN label_tasks t ON t.id = r.task_id
                        WHERE t.batch_id = b.id) AS labellers
                FROM label_batches b
                WHERE b.listed AND b.open AND b.purpose = 'work'
                ORDER BY b.created_at DESC
                """
            ),
            {"u": str(user_id), "langs": list(row["languages_read"])},
        )
    ).mappings().all()
    kinds = await kind_status(db, user_id, list(row["languages_read"]), {r["kind"] for r in rows if r["eligible"]})
    qualified = {k["kind"] for k in kinds if k["qualified"]}
    shaped = [
        {"key": r["key"], "name": r["name"], "kind": r["kind"], "notes": r["notes"] or "",
         "eligible": r["eligible"], "answered": r["answered"], "labellers": r["labellers"]}
        for r in rows if r["eligible"] > 0 and r["kind"] in qualified
    ]
    return {
        "status": "active",
        "ready": [b for b in shaped if b["answered"] < b["eligible"]],
        "done": [b for b in shaped if b["answered"] >= b["eligible"]],
        "kinds": kinds,
    }


@router.post("/api/v1/labeller/batches/{key}/start")
async def start(key: str, user_id: uuid.UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """This account's write credential for one batch — minted once, returned
    thereafter. The page stores it exactly as it stores a founder's invite link,
    and answers through label.py's routes."""
    row = await labeller_row(db, user_id)
    if row is None or row["status"] != "active":
        raise HTTPException(status_code=403, detail="your application has not been approved yet")
    batch = (
        await db.execute(
            text("SELECT id, open, kind FROM label_batches WHERE key = :k AND listed AND purpose = 'work'"),
            {"k": key},
        )
    ).mappings().first()
    if batch is None:
        raise HTTPException(status_code=404, detail="no such batch")
    if not batch["open"]:
        raise HTTPException(status_code=409, detail="batch is closed")
    if not await is_qualified(db, user_id, batch["kind"]):
        raise HTTPException(status_code=403, detail="pass this task's test first")
    eligible = (
        await db.execute(
            text(f"SELECT count(*) FROM label_tasks t WHERE t.batch_id = :b AND {ELIGIBLE}"),
            {"b": batch["id"], "langs": list(row["languages_read"])},
        )
    ).scalar_one()
    if not eligible:
        raise HTTPException(status_code=403, detail="no tasks in the languages you read")

    existing = (
        await db.execute(
            text("SELECT token, revoked FROM label_invites WHERE batch_id = :b AND user_id = :u AND attempt = 0"),
            {"b": batch["id"], "u": str(user_id)},
        )
    ).mappings().first()
    if existing is not None:
        if existing["revoked"]:
            raise HTTPException(status_code=403, detail="your access to this batch was revoked")
        return {"token": existing["token"]}

    who = (
        await db.execute(text("SELECT name, email FROM users WHERE id = :u"), {"u": str(user_id)})
    ).mappings().one()
    # ON CONFLICT, then read back: two taps on Start arrive together, both see
    # no invite, and without this the second one is a unique-index 500.
    await db.execute(
        text(
            """
            INSERT INTO label_invites (id, token, batch_id, name, user_id)
            VALUES (:i, :t, :b, :n, :u)
            ON CONFLICT (batch_id, user_id, attempt) WHERE user_id IS NOT NULL DO NOTHING
            """
        ),
        {"i": uuid.uuid4(), "t": secrets.token_urlsafe(24), "b": batch["id"],
         # The display name on responses (read by the admin tools). The email's
         # local part when the account never gave a name.
         "n": (who["name"] or who["email"].split("@", 1)[0])[:60], "u": str(user_id)},
    )
    token = (
        await db.execute(
            text("SELECT token FROM label_invites WHERE batch_id = :b AND user_id = :u AND attempt = 0"),
            {"b": batch["id"], "u": str(user_id)},
        )
    ).scalar_one()
    return {"token": token}


# ── Practice and qualification (plan phase 3) ───────────────────────────────


async def is_qualified(db: AsyncSession, user_id: uuid.UUID, kind: str) -> bool:
    return bool((
        await db.execute(
            text("SELECT 1 FROM labeller_qualifications WHERE user_id = :u AND kind = :k AND passed_at IS NOT NULL"),
            {"u": str(user_id), "k": kind},
        )
    ).first())


async def _round_batch(db: AsyncSession, kind: str, purpose: str) -> dict | None:
    """The open practice or qualification batch for a kind, newest first."""
    row = (
        await db.execute(
            text("SELECT id, key FROM label_batches WHERE kind = :k AND purpose = :p AND open "
                 "ORDER BY created_at DESC LIMIT 1"),
            {"k": kind, "p": purpose},
        )
    ).mappings().first()
    return dict(row) if row else None


async def kind_status(db: AsyncSession, user_id: uuid.UUID, langs: list[str], work_kinds: set[str]) -> list[dict]:
    """Per task kind that has work in your languages, or a test: are you
    qualified, can you practise, can you take the test now, when can you retake."""
    rounds = (
        await db.execute(
            text(f"""
                SELECT b.kind, b.purpose,
                       (SELECT count(*) FROM label_tasks t WHERE t.batch_id = b.id AND {ELIGIBLE}) AS eligible
                FROM label_batches b WHERE b.open AND b.purpose IN ('practice', 'qualify')
            """),
            {"langs": langs},
        )
    ).mappings().all()
    quals = {
        r["kind"]: dict(r)
        for r in (await db.execute(
            text("SELECT kind, passed_at, best_score, attempts, last_attempt_at FROM labeller_qualifications "
                 "WHERE user_id = :u"), {"u": str(user_id)},
        )).mappings().all()
    }
    kinds = sorted(work_kinds | {r["kind"] for r in rounds} | {k for k, q in quals.items() if q["passed_at"]})
    out = []
    for kind in kinds:
        q = quals.get(kind) or {}
        practice = any(r["kind"] == kind and r["purpose"] == "practice" and r["eligible"] for r in rounds)
        test_items = max((r["eligible"] for r in rounds if r["kind"] == kind and r["purpose"] == "qualify"), default=0)
        retake_at = None
        if not q.get("passed_at") and q.get("last_attempt_at"):
            due = q["last_attempt_at"] + timedelta(hours=RETAKE_AFTER_HOURS)
            retake_at = due.isoformat() if due > datetime.now(UTC) else None
        out.append({
            "kind": kind,
            "qualified": bool(q.get("passed_at")),
            "best_score": q.get("best_score"),
            "attempts": q.get("attempts") or 0,
            "can_practise": practice,
            # A test needs enough items IN YOUR LANGUAGES to be a test.
            "can_test": test_items >= QUESTIONS_PER_TEST and not q.get("passed_at") and retake_at is None,
            "retake_at": retake_at,
            "has_work": kind in work_kinds,
        })
    return out


async def _new_attempt(db: AsyncSession, batch_id: Any, user_id: uuid.UUID, task_ids: list[Any] | None) -> str:
    who = (
        await db.execute(text("SELECT name, email FROM users WHERE id = :u"), {"u": str(user_id)})
    ).mappings().one()
    attempt = (
        await db.execute(
            text("SELECT coalesce(max(attempt), 0) + 1 FROM label_invites WHERE batch_id = :b AND user_id = :u"),
            {"b": batch_id, "u": str(user_id)},
        )
    ).scalar_one()
    token = secrets.token_urlsafe(24)
    await db.execute(
        text("INSERT INTO label_invites (id, token, batch_id, name, user_id, attempt, task_ids) "
             "VALUES (:i, :t, :b, :n, :u, :a, CAST(:ids AS uuid[]))"),
        {"i": uuid.uuid4(), "t": token, "b": batch_id, "n": (who["name"] or who["email"].split("@", 1)[0])[:60],
         "u": str(user_id), "a": attempt, "ids": [str(x) for x in task_ids] if task_ids is not None else None},
    )
    return token


async def _unfinished(db: AsyncSession, batch_id: Any, user_id: uuid.UUID) -> str | None:
    """An attempt this account started and did not finish: resumed, never re-drawn,
    so leaving halfway cannot be used to shop for easier questions."""
    return (
        await db.execute(
            text("SELECT token FROM label_invites WHERE batch_id = :b AND user_id = :u AND attempt > 0 "
                 "AND finished_at IS NULL AND NOT revoked ORDER BY attempt DESC LIMIT 1"),
            {"b": batch_id, "u": str(user_id)},
        )
    ).scalar_one_or_none()


async def _active(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    row = await labeller_row(db, user_id)
    if row is None or row["status"] != "active":
        raise HTTPException(status_code=403, detail="your application has not been approved yet")
    return list(row["languages_read"])


@router.post("/api/v1/labeller/practice/{kind}/start")
async def start_practice(kind: str, user_id: uuid.UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """A practice round: every practice item in your languages, with the expected
    answer and the reason shown after each. Unlimited; a finished round starts a
    fresh one."""
    await _active(db, user_id)
    batch = await _round_batch(db, kind, "practice")
    if batch is None:
        raise HTTPException(status_code=404, detail="no practice for this task yet")
    token = await _unfinished(db, batch["id"], user_id) or await _new_attempt(db, batch["id"], user_id, None)
    return {"key": batch["key"], "token": token}


@router.post("/api/v1/labeller/qualify/{kind}/start")
async def start_test(kind: str, user_id: uuid.UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """A scored attempt: QUESTIONS_PER_TEST items drawn at random from the kind's
    pool in your languages, no feedback until the end, 90% to pass, a fresh draw
    after RETAKE_AFTER_HOURS if you do not."""
    langs = await _active(db, user_id)
    if await is_qualified(db, user_id, kind):
        raise HTTPException(status_code=409, detail="you have already passed this test")
    batch = await _round_batch(db, kind, "qualify")
    if batch is None:
        raise HTTPException(status_code=404, detail="no test for this task yet")
    resumed = await _unfinished(db, batch["id"], user_id)
    if resumed:
        return {"key": batch["key"], "token": resumed}
    last = (
        await db.execute(
            text("SELECT last_attempt_at FROM labeller_qualifications WHERE user_id = :u AND kind = :k"),
            {"u": str(user_id), "k": kind},
        )
    ).scalar_one_or_none()
    if last and last + timedelta(hours=RETAKE_AFTER_HOURS) > datetime.now(UTC):
        raise HTTPException(status_code=429, detail=f"you can retake this test after {RETAKE_AFTER_HOURS} hours")
    pool = [r[0] for r in (
        await db.execute(
            text(f"SELECT t.id FROM label_tasks t WHERE t.batch_id = :b AND {ELIGIBLE}"),
            {"b": batch["id"], "langs": langs},
        )
    ).all()]
    if len(pool) < QUESTIONS_PER_TEST:
        raise HTTPException(status_code=409, detail="not enough test questions in your languages yet")
    draw = random.SystemRandom().sample(pool, QUESTIONS_PER_TEST)
    return {"key": batch["key"], "token": await _new_attempt(db, batch["id"], user_id, draw)}


async def finish_attempt(db: AsyncSession, batch: dict, invite: dict) -> dict:
    """Score a practice or qualification attempt once every task in it is
    answered. Written ONCE (the UPDATE ... WHERE finished_at IS NULL is the
    guard): a refresh, a second tab or a retried request re-reads the result,
    it never records the attempt twice."""
    rows = (
        await db.execute(
            text("""
                SELECT t.position, t.expected, t.explanation, t.payload,
                       (SELECT e.title FROM events e WHERE e.id = t.seed_event_id) AS seed_title,
                       r.selected, r.unsure, r.skipped
                FROM label_tasks t
                JOIN label_responses r ON r.task_id = t.id AND r.invite_id = :i
                WHERE t.batch_id = :b
                  AND (CAST(:subset AS uuid[]) IS NULL OR t.id = ANY(CAST(:subset AS uuid[])))
                ORDER BY t.position
            """),
            {"i": invite["id"], "b": batch["id"], "subset": _ids(invite.get("task_ids"))},
        )
    ).mappings().all()
    rows = [{**r, "expected": _json(r["expected"]), "payload": _json(r["payload"]),
             "selected": _json(r["selected"]) or []} for r in rows]
    right = sum(is_correct(r, r["expected"]) for r in rows)
    total = len(rows)
    score = right / total if total else 0.0
    passed = total > 0 and score >= PASS_MARK
    won = (
        await db.execute(
            text("UPDATE label_invites SET finished_at = now(), score = :s WHERE id = :i AND finished_at IS NULL "
                 "RETURNING id"),
            {"s": score, "i": invite["id"]},
        )
    ).first()
    if won and batch["purpose"] == "qualify" and invite.get("user_id"):
        await db.execute(
            text("""
                INSERT INTO labeller_qualifications (user_id, kind, passed_at, best_score, attempts, last_attempt_at)
                VALUES (:u, :k, CASE WHEN :p THEN now() END, :s, 1, now())
                ON CONFLICT (user_id, kind) DO UPDATE SET
                  attempts = labeller_qualifications.attempts + 1,
                  last_attempt_at = now(),
                  best_score = GREATEST(labeller_qualifications.best_score, EXCLUDED.best_score),
                  passed_at = coalesce(labeller_qualifications.passed_at, EXCLUDED.passed_at)
            """),
            {"u": str(invite["user_id"]), "k": batch["kind"], "p": passed, "s": score},
        )
    # The reasons for the ones missed — only now, when the attempt can no
    # longer be changed (plan phase 3).
    missed = [
        {"position": r["position"], "about": _about(r), "explanation": r["explanation"] or ""}
        for r in rows if not is_correct(r, r["expected"])
    ]
    return {"right": right, "total": total, "score": round(score, 4), "passed": passed,
            "pass_mark": PASS_MARK, "missed": missed, "purpose": batch["purpose"]}


def feedback(task: dict, answer: dict) -> dict:
    """What a PRACTICE answer earns straight away: right or wrong, the expected
    answer, and why. Never called for a qualification attempt."""
    expected = _json(task.get("expected"))
    return {"correct": is_correct(answer, expected), "expected": expected.get("selected") or [],
            "explanation": task.get("explanation") or ""}


def _json(value: Any) -> Any:
    """JSONB as Python — the driver hands back text on some paths (label.py
    guards the same way), and a str here would silently mark everything wrong."""
    if isinstance(value, str):
        return json.loads(value)
    return value if value is not None else {}


def _ids(value: Any) -> list[str] | None:
    return [str(x) for x in value] if value is not None else None


def _about(row: Any) -> str:
    payload = row["payload"]
    if isinstance(payload, dict) and payload.get("quote_text"):
        return f"{payload.get('speaker', '')}: “{payload['quote_text'][:140]}”"
    return row["seed_title"] or ""
