"""The labeller workspace: apply, get approved, see the batches you can do, start one.

GET  /api/v1/labeller/me                    — your application and what you read
POST /api/v1/labeller/apply                 — apply, or change the languages you read
GET  /api/v1/labeller/batches               — listed batches, in your languages, with YOUR progress
POST /api/v1/labeller/batches/{key}/start   — the write credential for one batch

api/routes/label.py is the task protocol — one judgement at a time, keyed by a
per-batch invite. This is the signed-in surface in front of it, and it
deliberately does not replace it: starting a batch mints (or returns) an invite
bound to the account, and from there the labeller answers through exactly the
routes a founder's invite link uses. Every response, status, agreement and
compile path in tools/gold_candidates keeps working, untouched.

FOUNDER DECISIONS (2026-09-23): open application, admin approval — `status`
starts `applied` and only tools/label_admin moves it to `active`; tasks are
gated by the languages a labeller reads; the qualification gate arrives with the
tests (plan phase 3).

It never returns another labeller's answer, for the reason label.py gives:
a second opinion that has seen the first is not a second opinion. The dashboard
shows HOW MANY people are on a batch, never what they chose.
"""

from __future__ import annotations

import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from common.db import get_db
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
        return {"status": row["status"] if row else "none", "ready": [], "done": []}
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
                WHERE b.listed AND b.open
                ORDER BY b.created_at DESC
                """
            ),
            {"u": str(user_id), "langs": list(row["languages_read"])},
        )
    ).mappings().all()
    shaped = [
        {"key": r["key"], "name": r["name"], "kind": r["kind"], "notes": r["notes"] or "",
         "eligible": r["eligible"], "answered": r["answered"], "labellers": r["labellers"]}
        for r in rows if r["eligible"] > 0
    ]
    return {
        "status": "active",
        "ready": [b for b in shaped if b["answered"] < b["eligible"]],
        "done": [b for b in shaped if b["answered"] >= b["eligible"]],
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
            text("SELECT id, open FROM label_batches WHERE key = :k AND listed"), {"k": key}
        )
    ).mappings().first()
    if batch is None:
        raise HTTPException(status_code=404, detail="no such batch")
    if not batch["open"]:
        raise HTTPException(status_code=409, detail="batch is closed")
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
            text("SELECT token, revoked FROM label_invites WHERE batch_id = :b AND user_id = :u"),
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
            ON CONFLICT (batch_id, user_id) WHERE user_id IS NOT NULL DO NOTHING
            """
        ),
        {"i": uuid.uuid4(), "t": secrets.token_urlsafe(24), "b": batch["id"],
         # The display name on responses (read by the admin tools). The email's
         # local part when the account never gave a name.
         "n": (who["name"] or who["email"].split("@", 1)[0])[:60], "u": str(user_id)},
    )
    token = (
        await db.execute(
            text("SELECT token FROM label_invites WHERE batch_id = :b AND user_id = :u"),
            {"b": batch["id"], "u": str(user_id)},
        )
    ).scalar_one()
    return {"token": token}
