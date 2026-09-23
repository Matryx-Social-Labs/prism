"""/admin: running the labeller workspace (admin dashboard, phase 2).

GET  /api/v1/admin/labellers                       — everyone who applied, and each one's standing per kind
POST /api/v1/admin/labellers/status                — approve (active), pause, or remove
POST /api/v1/admin/labellers/add                   — an existing account, active without applying
POST /api/v1/admin/labellers/qualify               — grant a kind without a test, or withdraw it
GET  /api/v1/admin/batches                         — every batch with its progress
POST /api/v1/admin/batches/{key}/listed            — show on the labeller dashboard (closes anonymous join)
POST /api/v1/admin/batches/{key}/open              — open or close; opening a round publishes it, if it passes the check
POST /api/v1/admin/batches/{key}/languages         — fill in what each task needs its labeller to read
GET  /api/v1/admin/batches/{key}/items             — a round's items, answers, explanations and publish check
PUT  /api/v1/admin/batches/{key}/explanations      — save edited explanations

Every route is guarded by api/deps.require_admin_user and every change goes
through common/label_ops — the same functions tools/label_admin runs — which
writes admin_audit against the founder in the same transaction.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_admin_user
from common import label_ops
from common.db import get_db
from common.languages import LANGUAGES

router = APIRouter()

Email = Annotated[str, Field(min_length=3, max_length=320)]
Kind = Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[a-z_]+$")]
MAX_EXPLANATION = 2000


class StatusChange(BaseModel):
    email: Email
    status: Literal["active", "paused", "removed"]


class AddLabeller(BaseModel):
    email: Email
    languages_read: Annotated[list[str], Field(min_length=1, max_length=len(LANGUAGES))]


class Qualification(BaseModel):
    email: Email
    kind: Kind
    granted: bool


class Flag(BaseModel):
    on: bool


class Explanation(BaseModel):
    position: Annotated[int, Field(ge=0)]
    explanation: Annotated[str, Field(max_length=MAX_EXPLANATION)]


class Explanations(BaseModel):
    edits: Annotated[list[Explanation], Field(min_length=1, max_length=500)]


async def _run(change):
    """A missing labeller or batch is a 404; a change the rules refuse is a 409
    with the reason. get_db rolls the change back with its audit row, or
    commits both."""
    try:
        return await change
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/api/v1/admin/labellers")
async def list_labellers(_: str = Depends(require_admin_user), db: AsyncSession = Depends(get_db)):
    return {"labellers": await label_ops.labellers(db), "board": await label_ops.board(db),
            "languages": list(LANGUAGES)}


@router.post("/api/v1/admin/labellers/status")
async def change_status(body: StatusChange, actor: str = Depends(require_admin_user),
                        db: AsyncSession = Depends(get_db)):
    was = await _run(label_ops.set_status(db, body.email, body.status, actor))
    return {"email": body.email, "from": was, "to": body.status}


@router.post("/api/v1/admin/labellers/add")
async def add_labeller(body: AddLabeller, actor: str = Depends(require_admin_user),
                       db: AsyncSession = Depends(get_db)):
    # Only languages Prism ingests, as /label's own form allows.
    langs = sorted({code for code in body.languages_read if code in LANGUAGES})
    await _run(label_ops.add(db, body.email, langs, actor))
    return {"email": body.email, "status": "active"}


@router.post("/api/v1/admin/labellers/qualify")
async def change_qualification(body: Qualification, actor: str = Depends(require_admin_user),
                               db: AsyncSession = Depends(get_db)):
    await _run(label_ops.qualify(db, body.email, body.kind, body.granted, actor))
    return {"email": body.email, "kind": body.kind, "granted": body.granted}


@router.get("/api/v1/admin/batches")
async def list_batches(_: str = Depends(require_admin_user), db: AsyncSession = Depends(get_db)):
    return {"batches": await label_ops.batches(db)}


@router.post("/api/v1/admin/batches/{key}/listed")
async def list_batch(key: str, body: Flag, actor: str = Depends(require_admin_user),
                     db: AsyncSession = Depends(get_db)):
    await _run(label_ops.set_listed(db, key, body.on, actor))
    return {"key": key, "listed": body.on}


@router.post("/api/v1/admin/batches/{key}/open")
async def open_batch(key: str, body: Flag, actor: str = Depends(require_admin_user),
                     db: AsyncSession = Depends(get_db)):
    await _run(label_ops.set_open(db, key, body.on, actor))
    return {"key": key, "open": body.on}


@router.post("/api/v1/admin/batches/{key}/languages")
async def gate_batch(key: str, actor: str = Depends(require_admin_user), db: AsyncSession = Depends(get_db)):
    return {"key": key, "gated": await _run(label_ops.gate_languages(db, key, actor))}


@router.get("/api/v1/admin/batches/{key}/items")
async def batch_items(key: str, _: str = Depends(require_admin_user), db: AsyncSession = Depends(get_db)):
    try:
        return {"items": await label_ops.round_items(db, key), "check": await label_ops.check_round(db, key)}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/api/v1/admin/batches/{key}/explanations")
async def save_explanations(key: str, body: Explanations, actor: str = Depends(require_admin_user),
                            db: AsyncSession = Depends(get_db)):
    saved = await _run(label_ops.save_explanations(
        db, key, [(e.position, e.explanation) for e in body.edits], actor))
    return {"key": key, "saved": saved, "check": await label_ops.check_round(db, key)}
