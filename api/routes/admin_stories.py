"""/admin/stories: what /trending leads with, set by a founder.

GET    /api/v1/admin/stories              — pinned, running and listed stories (or a search by headline)
POST   /api/v1/admin/stories/{slug}/pin   — pin a story for N days (audited)
DELETE /api/v1/admin/stories/{slug}/pin   — unpin it (audited)

A pin puts a story at the head of /trending, ahead of the running stories, and
keeps it listed while the pin holds even if it has gone quiet. It never changes
what is in the story.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_admin_user
from common.admin_audit import audit
from common.db import get_db

router = APIRouter()
PRIVATE = {"Cache-Control": "no-store"}
LISTED = 60
PIN_DAYS_MAX = 30

_COLUMNS = """
    st.slug, st.label, st.status, st.source_count, st.velocity, st.last_updated_at, st.pinned_until,
    st.scope IS NOT NULL AS running, coalesce(st.pinned_until > now(), false) AS pinned,
    jsonb_array_length(st.member_event_ids) AS developments
"""


class Pin(BaseModel):
    days: Annotated[int, Field(ge=1, le=PIN_DAYS_MAX)] = 7


def _out(r) -> dict:
    d = dict(r)
    for k in ("last_updated_at", "pinned_until"):
        d[k] = d[k].isoformat() if d[k] else None
    return d


@router.get("/api/v1/admin/stories")
async def list_stories(
    response: Response,
    q: Annotated[str, Query(max_length=120)] = "",
    _: str = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """The pinned and running stories, then what /trending lists, in its order;
    with `q`, the served stories whose headline holds it, newest first."""
    response.headers.update(PRIVATE)
    served = "st.merged_into IS NULL AND st.status <> 'shadow' AND st.anchor_event_id IS NOT NULL"
    if q.strip():
        rows = (await db.execute(
            text(f"SELECT {_COLUMNS} FROM stories st WHERE {served} AND st.label ILIKE :q "
                 "ORDER BY st.last_updated_at DESC LIMIT :n"),
            {"q": f"%{q.strip()}%", "n": LISTED})).mappings().all()
    else:
        rows = (await db.execute(
            text(f"SELECT {_COLUMNS} FROM stories st WHERE {served} "
                 "AND (st.status = 'active' OR st.pinned_until > now() OR st.scope IS NOT NULL) "
                 "ORDER BY coalesce(st.pinned_until > now(), false) DESC, (st.scope IS NOT NULL) DESC, "
                 "st.velocity DESC, st.source_count DESC LIMIT :n"),
            {"n": LISTED})).mappings().all()
    return {"stories": [_out(r) for r in rows], "pin_days_max": PIN_DAYS_MAX}


async def _set_pin(db: AsyncSession, slug: str, days: int | None):
    row = (await db.execute(
        text(f"UPDATE stories st SET pinned_until = CASE WHEN CAST(:d AS int) IS NULL THEN NULL "
             f"ELSE now() + make_interval(days => CAST(:d AS int)) END "
             f"WHERE st.slug = :s AND st.merged_into IS NULL AND st.status <> 'shadow' RETURNING {_COLUMNS}"),
        {"d": days, "s": slug})).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="No story with that address is being served")
    return row


@router.post("/api/v1/admin/stories/{slug}/pin")
async def pin(slug: str, body: Pin, actor: str = Depends(require_admin_user), db: AsyncSession = Depends(get_db)):
    row = await _set_pin(db, slug, body.days)
    await audit(db, actor, "story.pin", slug, {"days": body.days})
    await db.commit()
    return _out(row)


@router.delete("/api/v1/admin/stories/{slug}/pin")
async def unpin(slug: str, actor: str = Depends(require_admin_user), db: AsyncSession = Depends(get_db)):
    row = await _set_pin(db, slug, None)
    await audit(db, actor, "story.unpin", slug)
    await db.commit()
    return _out(row)
