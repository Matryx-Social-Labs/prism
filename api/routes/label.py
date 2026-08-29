"""Story-boundary labelling: serve one judgement at a time, store what people say.

GET  /api/v1/label/{key}          — batch header + this labeller's progress
GET  /api/v1/label/{key}/next     — the next task this labeller has not answered
POST /api/v1/label/{key}/answer   — record a judgement
GET  /api/v1/label/{key}/export   — every response, for compiling a gold set

The gold set is what every story-layer decision is measured against, and it was a
one-off literal in a Python file. These routes make growing it a job the product
supports, done by people who do not have a checkout.

ACCESS IS THE BATCH KEY, NOT AN ACCOUNT. The audience is non-technical and a task
takes a minute; a signup wall would cost more labels than it protects. The key is
unguessable, the endpoints expose only headlines already public on the site, and
the write path can do nothing but attach a judgement to a task that already exists.
An account would be theatre over a link people will paste to each other anyway.

WHAT IT DELIBERATELY DOES NOT DO. It never shows one labeller another's answer.
Anchoring is the single failure that would quietly destroy the value of a second
opinion — and a second opinion is the entire reason responses are keyed per person.
"""

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db

router = APIRouter()

MAX_LABELLER = 60


class Answer(BaseModel):
    task_id: uuid.UUID
    labeller: Annotated[str, Field(min_length=1, max_length=MAX_LABELLER)]
    # Event ids judged to be the SAME story as the seed. An empty list is a real
    # answer — "none of these" — and is stored as one.
    selected: list[uuid.UUID] = []
    unsure: bool = False
    ms_spent: int | None = None


async def _batch(db: AsyncSession, key: str) -> dict:
    row = (
        await db.execute(
            text("SELECT id, name, notes, open FROM label_batches WHERE key = :k"),
            {"k": key},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="no such batch")
    return dict(row)


@router.get("/api/v1/label/{key}")
async def batch_header(key: str, labeller: str = "", db: AsyncSession = Depends(get_db)):
    """Batch name, instructions, and how far THIS labeller has got.

    `done` counts this person's answers, not everyone's: with several people on one
    batch a shared counter would tell someone they were nearly finished when they
    had barely started.
    """
    b = await _batch(db, key)
    total = (
        await db.execute(
            text("SELECT count(*) FROM label_tasks WHERE batch_id = :b"), {"b": b["id"]}
        )
    ).scalar_one()
    done = 0
    if labeller.strip():
        done = (
            await db.execute(
                text(
                    "SELECT count(*) FROM label_responses r "
                    "JOIN label_tasks t ON t.id = r.task_id "
                    "WHERE t.batch_id = :b AND r.labeller = :l"
                ),
                {"b": b["id"], "l": labeller.strip()[:MAX_LABELLER]},
            )
        ).scalar_one()
    return {
        "name": b["name"], "notes": b["notes"], "open": b["open"],
        "total": total, "done": done,
    }


@router.get("/api/v1/label/{key}/next")
async def next_task(key: str, labeller: str = "", db: AsyncSession = Depends(get_db)):
    """The lowest-numbered task this labeller has not answered.

    Deterministic order rather than random: someone working a batch in a stable
    order can stop and resume, and two people on one batch converge on the same
    tasks, which is what produces comparable second opinions.
    """
    b = await _batch(db, key)
    if not b["open"]:
        return {"task": None, "closed": True}
    who = labeller.strip()[:MAX_LABELLER]
    row = (
        await db.execute(
            text(
                """
                SELECT t.id, t.position, t.sector, t.candidates, t.seed_event_id
                FROM label_tasks t
                WHERE t.batch_id = :b
                  AND NOT EXISTS (
                    SELECT 1 FROM label_responses r
                    WHERE r.task_id = t.id AND r.labeller = :l
                  )
                ORDER BY t.position
                LIMIT 1
                """
            ),
            {"b": b["id"], "l": who},
        )
    ).mappings().first()
    if row is None:
        return {"task": None, "closed": False}

    ids = [row["seed_event_id"]] + [uuid.UUID(c["id"]) for c in row["candidates"]]
    events = {
        str(r["id"]): dict(r)
        for r in (
            await db.execute(
                text(
                    """
                    SELECT e.id, e.title,
                           coalesce(e.occurred_at, e.first_seen_at) AS at,
                           (SELECT count(*) FROM event_memberships m WHERE m.event_id = e.id)
                             AS source_count,
                           (SELECT array_agg(en.name ORDER BY en.name)
                            FROM event_entities ee JOIN entities en ON en.id = ee.entity_id
                            WHERE ee.event_id = e.id
                              AND en.entity_type IN ('person','organization')) AS actors
                    FROM events e WHERE e.id = ANY(:ids)
                    """
                ),
                {"ids": ids},
            )
        ).mappings().all()
    }

    def shape(eid: str, signals: list[str] | None = None) -> dict:
        e = events.get(eid) or {}
        return {
            "id": eid,
            "title": e.get("title") or "",
            "at": e["at"].isoformat() if e.get("at") else None,
            "source_count": e.get("source_count") or 0,
            "actors": (e.get("actors") or [])[:4],
            "signals": signals or [],
        }

    return {
        "task": {
            "id": str(row["id"]),
            "position": row["position"],
            "sector": row["sector"],
            "seed": shape(str(row["seed_event_id"])),
            "candidates": [shape(c["id"], c.get("signals")) for c in row["candidates"]],
        },
        "closed": False,
    }


@router.post("/api/v1/label/{key}/answer")
async def answer(key: str, body: Answer, db: AsyncSession = Depends(get_db)):
    """Record a judgement. Re-answering the same task UPDATES rather than appends.

    Someone who changes their mind should leave one opinion, not two — otherwise a
    single person's second thoughts look like agreement between two people, which is
    the one thing this table exists to measure honestly.
    """
    b = await _batch(db, key)
    if not b["open"]:
        raise HTTPException(status_code=409, detail="batch is closed")
    owned = (
        await db.execute(
            text("SELECT 1 FROM label_tasks WHERE id = :t AND batch_id = :b"),
            {"t": body.task_id, "b": b["id"]},
        )
    ).first()
    if owned is None:
        # A task id from another batch must not be writable through this key.
        raise HTTPException(status_code=404, detail="task not in this batch")

    await db.execute(
        text(
            """
            INSERT INTO label_responses (id, task_id, labeller, selected, unsure, ms_spent)
            VALUES (:id, :t, :l, CAST(:sel AS jsonb), :u, :ms)
            ON CONFLICT (task_id, labeller) DO UPDATE
              SET selected = EXCLUDED.selected, unsure = EXCLUDED.unsure,
                  ms_spent = EXCLUDED.ms_spent, created_at = now()
            """
        ),
        {
            "id": uuid.uuid4(), "t": body.task_id,
            "l": body.labeller.strip()[:MAX_LABELLER],
            "sel": json.dumps([str(x) for x in body.selected]),
            "u": body.unsure, "ms": body.ms_spent,
        },
    )
    return {"ok": True}


@router.get("/api/v1/label/{key}/export")
async def export(key: str, db: AsyncSession = Depends(get_db)):
    """Every response in the batch, for compiling a gold set offline.

    Returns each labeller separately rather than a merged verdict. Merging IS a
    judgement — how many people must concur, what to do with `unsure` — and it
    belongs in the tool that builds the gold set, where it can be written down and
    argued with, not buried in a serializer.
    """
    b = await _batch(db, key)
    rows = (
        await db.execute(
            text(
                """
                SELECT t.position, t.seed_event_id, t.sector, t.candidates,
                       r.labeller, r.selected, r.unsure, r.ms_spent
                FROM label_tasks t
                LEFT JOIN label_responses r ON r.task_id = t.id
                WHERE t.batch_id = :b
                ORDER BY t.position, r.labeller
                """
            ),
            {"b": b["id"]},
        )
    ).mappings().all()
    return {
        "batch": b["name"],
        "responses": [
            {
                "position": r["position"],
                "seed": str(r["seed_event_id"]),
                "sector": r["sector"],
                "candidates": r["candidates"],
                "labeller": r["labeller"],
                "selected": r["selected"],
                "unsure": r["unsure"],
                "ms_spent": r["ms_spent"],
            }
            for r in rows
        ],
    }
