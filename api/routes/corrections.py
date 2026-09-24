"""The public corrections log and a record's earlier versions.

A correction is an editorial act recorded by a founder (tools/correct_record.py)
with a reason and a note; the versions are every replaced headline, summary and
reader brief the events trigger kept (migration e7a4c2b9f613). Both are public.
Only the FREE text of a version is served: a paid lens's brief stays paid in
its history too.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import CorrectionOut, CorrectionsResponse, RecordVersion, VersionsResponse
from common.db import get_db

router = APIRouter()

_CORRECTIONS = text(
    "SELECT created_at, reason, note FROM event_corrections WHERE event_id = :e ORDER BY created_at DESC"
)


async def corrections_for(db: AsyncSession, event_id: uuid.UUID) -> list[CorrectionOut]:
    rows = (await db.execute(_CORRECTIONS, {"e": str(event_id)})).mappings().all()
    return [CorrectionOut(created_at=r["created_at"].isoformat(), reason=r["reason"], note=r["note"]) for r in rows]


@router.get("/api/v1/events/{event_id}/versions", response_model=VersionsResponse)
async def versions(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        text(
            "SELECT replaced_at, title, summary, lens_briefs ->> 'reader' AS brief FROM event_revisions "
            "WHERE event_id = :e ORDER BY replaced_at DESC LIMIT 50"
        ),
        {"e": str(event_id)},
    )).mappings().all()
    return VersionsResponse(
        versions=[RecordVersion(replaced_at=r["replaced_at"].isoformat(), title=r["title"], summary=r["summary"],
                                brief=r["brief"]) for r in rows],
        corrections=await corrections_for(db, event_id),
    )


@router.get("/api/v1/corrections", response_model=CorrectionsResponse)
async def corrections(limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        text(
            """
            SELECT c.event_id, c.created_at, c.reason, c.note,
                   COALESCE(e.title, (SELECT r.title FROM event_revisions r WHERE r.event_id = c.event_id
                                      ORDER BY r.replaced_at DESC LIMIT 1)) AS title
            FROM event_corrections c LEFT JOIN events e ON e.id = c.event_id
            ORDER BY c.created_at DESC LIMIT :n
            """
        ),
        {"n": limit},
    )).mappings().all()
    return CorrectionsResponse(corrections=[
        CorrectionOut(event_id=str(r["event_id"]), title=r["title"], created_at=r["created_at"].isoformat(),
                      reason=r["reason"], note=r["note"]) for r in rows
    ])
