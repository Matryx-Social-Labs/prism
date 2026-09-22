"""Story-boundary labelling: serve one judgement at a time, store what people say.

POST /api/v1/label/{key}/join     — mint this visitor an invite (the credential)
GET  /api/v1/label/{key}           — batch header + this invite's progress
GET  /api/v1/label/{key}/next      — the next task this invite has not answered
POST /api/v1/label/{key}/answer    — record a judgement
GET  /api/v1/label/{key}/export    — every response, for compiling a gold set

The gold set is what every story-layer decision is measured against, and it was a
one-off literal in a Python file. These routes make growing it a job the product
supports, done by people who do not have a checkout.

TWO CREDENTIALS, DOING DIFFERENT JOBS. The batch key in the URL is a JOIN
capability: it identifies the batch and, if the batch allows it, lets a visitor
mint an invite. The invite token is the WRITE credential, one per person, and it
never appears in a URL — the page keeps it in localStorage and sends it in the
body. A credential in a path leaks through history, Referer headers, server logs
and any shared screenshot; a join capability leaking is a far smaller thing.

IDENTITY IS THE TOKEN, NOT A TYPED NAME, and that is a bug fix rather than
hardening. Responses used to be keyed on (task, typed name) with ON CONFLICT DO
UPDATE, so a second person typing "Ana" silently overwrote the first Ana's
answers — collapsing the two opinions this schema exists to keep apart, and
leaving a gold set that looks entirely normal. A name is now a caption; two
people may share one.

No account, still. The audience is non-technical and a task takes a minute; a
signup wall would cost more labels than it protects, and the endpoints expose only
headlines already public on the site.

WHAT IT DELIBERATELY DOES NOT DO. It never shows one labeller another's answer.
Anchoring is the single failure that would quietly destroy the value of a second
opinion — and a second opinion is the entire reason responses are keyed per person.
"""

import json
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_admin
from common.db import get_db

router = APIRouter()

MAX_LABELLER = 60


class Join(BaseModel):
    # Display only. Two labellers may share it; identity is the issued token.
    name: Annotated[str, Field(max_length=MAX_LABELLER)] = ""


class Answer(BaseModel):
    task_id: uuid.UUID
    token: Annotated[str, Field(min_length=8, max_length=128)]
    # Event ids judged to be the SAME story as the seed. An empty list is a real
    # answer — "none of these" — and is stored as one.
    selected: list[uuid.UUID] = []
    # "I read these and cannot decide" — a claim about the STORY.
    unsure: bool = False
    # "I cannot read this language" — a claim about the LABELLER. Kept apart from
    # `unsure` because conflating them makes a genuinely ambiguous boundary
    # indistinguishable from having asked the wrong person, and the second one is
    # fixed by routing the task to someone else.
    skipped: bool = False
    ms_spent: int | None = None


async def _invite(db: AsyncSession, batch_id, token: str) -> dict:
    """Resolve a write credential, or refuse.

    Scoped to the batch on purpose: a token minted for one batch must not write to
    another, or the batch key would gate reads while leaving every task in the
    database writable by anyone holding any token.
    """
    row = (
        await db.execute(
            text(
                "SELECT id, name, revoked FROM label_invites "
                "WHERE token = :t AND batch_id = :b"
            ),
            {"t": token, "b": batch_id},
        )
    ).mappings().first()
    if row is None or row["revoked"]:
        raise HTTPException(status_code=403, detail="invalid or revoked invite")
    await db.execute(
        text("UPDATE label_invites SET last_seen_at = now() WHERE id = :i"),
        {"i": row["id"]},
    )
    return dict(row)


async def _batch(db: AsyncSession, key: str) -> dict:
    row = (
        await db.execute(
            text("SELECT id, name, notes, open, self_join, kind FROM label_batches WHERE key = :k"),
            {"k": key},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="no such batch")
    return dict(row)


@router.post("/api/v1/label/{key}/join")
async def join(key: str, body: Join, db: AsyncSession = Depends(get_db)):
    """Mint this visitor their own write credential.

    This is what lets ONE link be shared with a group while every person still gets
    a distinct identity — no name to collide, and nothing for the labeller to copy
    or keep track of. `self_join` off means invites must be minted deliberately
    instead, for a batch where who answers matters.
    """
    b = await _batch(db, key)
    if not b["open"]:
        raise HTTPException(status_code=409, detail="batch is closed")
    if not b["self_join"]:
        raise HTTPException(status_code=403, detail="this batch is invite-only")
    token = secrets.token_urlsafe(24)
    await db.execute(
        text("INSERT INTO label_invites (id, token, batch_id, name) "
             "VALUES (:i, :t, :b, :n)"),
        {"i": uuid.uuid4(), "t": token, "b": b["id"],
         "n": body.name.strip()[:MAX_LABELLER] or None},
    )
    return {"token": token}


@router.get("/api/v1/label/{key}")
async def batch_header(
    key: str,
    token: str = Header("", alias="X-Label-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Batch name, instructions, and how far THIS labeller has got.

    `done` counts this invite's answers, not everyone's: with several people on one
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
    name = ""
    if token:
        inv = await _invite(db, b["id"], token)
        name = inv["name"] or ""
        done = (
            await db.execute(
                text(
                    "SELECT count(*) FROM label_responses r "
                    "JOIN label_tasks t ON t.id = r.task_id "
                    "WHERE t.batch_id = :b AND r.invite_id = :i"
                ),
                {"b": b["id"], "i": inv["id"]},
            )
        ).scalar_one()
    return {
        "name": b["name"], "notes": b["notes"], "open": b["open"],
        "self_join": b["self_join"], "labeller": name, "kind": b["kind"],
        "total": total, "done": done,
    }


@router.get("/api/v1/label/{key}/next")
async def next_task(
    key: str,
    token: str = Header("", alias="X-Label-Token"),
    db: AsyncSession = Depends(get_db),
):
    """The lowest-numbered task this invite has not answered.

    Deterministic order rather than random: someone working a batch in a stable
    order can stop and resume, and two people on one batch converge on the same
    tasks, which is what produces comparable second opinions.
    """
    b = await _batch(db, key)
    if not b["open"]:
        return {"task": None, "closed": True}
    inv = await _invite(db, b["id"], token)
    row = (
        await db.execute(
            text(
                """
                SELECT t.id, t.position, t.sector, t.candidates, t.seed_event_id, t.payload
                FROM label_tasks t
                WHERE t.batch_id = :b
                  AND NOT EXISTS (
                    SELECT 1 FROM label_responses r
                    WHERE r.task_id = t.id AND r.invite_id = :i
                  )
                ORDER BY t.position
                LIMIT 1
                """
            ),
            {"b": b["id"], "i": inv["id"]},
        )
    ).mappings().first()
    if row is None:
        return {"task": None, "closed": False}

    # A claim task carries everything it needs in `payload` — no events to join.
    # Returning early keeps the story query off a path where seed_event_id is NULL.
    if row["payload"] is not None:
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return {
            "task": {"id": str(row["id"]), "position": row["position"],
                     "kind": "claim_attribution", "claim": payload},
            "closed": False,
        }

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
                              AND en.entity_type IN ('person','organization')) AS actors,
                           (SELECT ri.title FROM event_memberships m JOIN articles a ON a.id = m.article_id
                            JOIN raw_items ri ON ri.id = a.raw_item_id
                            WHERE m.event_id = e.id ORDER BY m.is_survivor DESC, ri.published_at LIMIT 1) AS native_title,
                           (SELECT ri.language FROM event_memberships m JOIN articles a ON a.id = m.article_id
                            JOIN raw_items ri ON ri.id = a.raw_item_id
                            WHERE m.event_id = e.id ORDER BY m.is_survivor DESC, ri.published_at LIMIT 1) AS language
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
            # What the founding outlet actually printed, in its own language;
            # the title above is Prism's English headline. A same-event
            # judgement across languages needs both.
            "native_title": e.get("native_title") or "",
            "language": e.get("language") or "",
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
    inv = await _invite(db, b["id"], body.token)
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
            INSERT INTO label_responses
              (id, task_id, invite_id, labeller, selected, unsure, skipped, ms_spent)
            VALUES (:id, :t, :inv, :l, CAST(:sel AS jsonb), :u, :sk, :ms)
            ON CONFLICT (task_id, invite_id) DO UPDATE
              SET selected = EXCLUDED.selected, unsure = EXCLUDED.unsure,
                  skipped = EXCLUDED.skipped,
                  ms_spent = EXCLUDED.ms_spent, created_at = now()
            """
        ),
        {
            "id": uuid.uuid4(), "t": body.task_id, "inv": inv["id"],
            "l": inv["name"] or "anonymous",
            "sel": json.dumps([str(x) for x in body.selected]),
            "u": body.unsure, "sk": body.skipped, "ms": body.ms_spent,
        },
    )
    return {"ok": True}


@router.get("/api/v1/label/{key}/export", dependencies=[Depends(require_admin)])
async def export(
    key: str,
    db: AsyncSession = Depends(get_db),
):
    """Every response in the batch, for compiling a gold set offline. ADMIN ONLY.

    The batch key is a JOIN capability — it is meant to be pasted into a message
    and forwarded, and it reaches whoever the recipient forwards it to. Letting it
    also read back every labeller's answers made it a bearer credential for the
    whole dataset, which is not what anyone hands out when they share a link.

    Reading answers is also the one operation that could quietly corrupt the gold
    set rather than merely add noise to it: a labeller who can see what others
    chose is no longer an independent opinion, and independence is the entire
    reason responses are keyed per person.

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
                       r.labeller, r.selected, r.unsure, r.skipped, r.ms_spent
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
                "skipped": r["skipped"],
                "ms_spent": r["ms_spent"],
            }
            for r in rows
        ],
    }
