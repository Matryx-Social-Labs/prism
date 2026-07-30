"""Event routes: detail, on-demand lens brief, suggested questions, Ask (SSE).

The on-demand brief is where the read-time paywall gate will attach (freemium
PR2). The single-flight lock below is in-process only — PR2 replaces it with a
Redis lock so it holds across API replicas.
"""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent.questions import suggested_questions
from agent.rag import answer_stream, ensure_session
from api.schemas import (
    AskRequest,
    BriefResponse,
    EntityOut,
    EventDetail,
    ImpactOut,
    PerspectiveOut,
    QuestionsResponse,
    SourceRef,
)
from common.db import get_db
from common.lenses import LENSES
from common.locks import single_flight
from common.logging import get_logger
from correlation.briefs import available_lenses, generate_briefs, persist_briefs

logger = get_logger(__name__)
router = APIRouter()


@router.get("/api/v1/events/{event_id}", response_model=EventDetail)
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    event = (
        await db.execute(
            text(
                """
                SELECT id, title, summary, sector, subsector, image_url, regions,
                       occurred_at, last_updated_at, projection
                FROM events WHERE id = :eid
                """
            ),
            {"eid": str(event_id)},
        )
    ).mappings().first()
    if event is None:
        raise HTTPException(status_code=404, detail="event not found")

    sources = (
        await db.execute(
            text(
                """
                SELECT a.id AS article_id, s.name AS source_name, s.slug AS source_slug,
                       s.reliability ->> 'funding' AS funding,
                       ri.url, ri.title, ri.published_at,
                       e.shared_fields -> 'stance' ->> 'label' AS stance
                FROM event_memberships em
                JOIN articles a ON a.id = em.article_id
                JOIN raw_items ri ON ri.id = a.raw_item_id
                JOIN sources s ON s.id = ri.source_id
                LEFT JOIN enrichments e ON e.article_id = a.id
                WHERE em.event_id = :eid
                ORDER BY ri.published_at DESC NULLS LAST
                """
            ),
            {"eid": str(event_id)},
        )
    ).mappings().all()

    perspectives = (
        await db.execute(
            text(
                """
                SELECT label, stance, origin_country, summary, member_articles
                FROM perspectives WHERE event_id = :eid ORDER BY created_at
                """
            ),
            {"eid": str(event_id)},
        )
    ).mappings().all()

    impacts = (
        await db.execute(
            text(
                """
                SELECT i.id, i.effect, i.direction, i.horizon, i.confidence,
                       i.parent_impact_id,
                       COALESCE(en.name, i.provenance ->> 'entity_name') AS entity_name
                FROM impacts i
                LEFT JOIN entities en ON en.id = i.entity_id
                WHERE i.event_id = :eid
                ORDER BY i.created_at
                """
            ),
            {"eid": str(event_id)},
        )
    ).mappings().all()

    entities = (
        await db.execute(
            text(
                """
                SELECT en.name, en.entity_type, ee.role
                FROM event_entities ee
                JOIN entities en ON en.id = ee.entity_id
                WHERE ee.event_id = :eid
                ORDER BY (ee.role = 'affected') DESC, en.name
                LIMIT 12
                """
            ),
            {"eid": str(event_id)},
        )
    ).mappings().all()

    # No story_timeline() call here: the arc belongs to /trending/{slug}, which
    # builds it from the story's frozen member set. Serving it from here as well
    # meant two member sets for one story. Dropping it also takes a Redis lookup
    # and a partition/BFS assembly off the most-viewed route.
    projection = event["projection"] or {}
    return EventDetail(
        id=str(event["id"]),
        title=event["title"],
        summary=event["summary"],
        sector=event["sector"],
        subsector=event["subsector"],
        image_url=event["image_url"],
        regions=event["regions"] or [],
        occurred_at=event["occurred_at"].isoformat() if event["occurred_at"] else None,
        last_updated_at=event["last_updated_at"].isoformat(),
        projection=event["projection"],
        lens_briefs=projection.get("lens_briefs") or {},
        lens_points=projection.get("lens_points") or {},
        available_lenses=available_lenses(projection, event["sector"]),
        coverage=projection.get("coverage"),
        entities=[
            EntityOut(name=e["name"], entity_type=e["entity_type"], role=e["role"]) for e in entities
        ],
        sources=[
            SourceRef(
                article_id=str(s["article_id"]),
                source_name=s["source_name"],
                source_slug=s["source_slug"],
                url=s["url"],
                title=s["title"],
                published_at=s["published_at"].isoformat() if s["published_at"] else None,
                stance=s["stance"],
                funding=s["funding"],
            )
            for s in sources
        ],
        perspectives=[
            PerspectiveOut(
                label=p["label"],
                stance=p["stance"],
                origin_country=p["origin_country"],
                summary=p["summary"],
                article_ids=[str(a) for a in (p["member_articles"] or [])],
            )
            for p in perspectives
        ],
        impacts=[
            ImpactOut(
                id=str(i["id"]),
                entity_name=i["entity_name"],
                effect=i["effect"],
                direction=i["direction"],
                horizon=i["horizon"],
                confidence=i["confidence"],
                parent_impact_id=str(i["parent_impact_id"]) if i["parent_impact_id"] else None,
            )
            for i in impacts
        ],
    )


async def _read_cached_brief(db: AsyncSession, event_id: uuid.UUID, lens: str) -> BriefResponse | None:
    row = (
        await db.execute(
            text("SELECT projection FROM events WHERE id = :eid"), {"eid": str(event_id)}
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")
    projection = row["projection"] or {}
    cached = (projection.get("lens_briefs") or {}).get(lens)
    if cached:
        points = (projection.get("lens_points") or {}).get(lens) or []
        return BriefResponse(lens=lens, brief=cached, points=points, cached=True)
    return None


# On-demand lens briefs: any lens on any story — this is what lets a cyber
# professional pull the cyber read of a war, or a trader the market read of a
# breach. Generated once, cached on the event projection. A Redis single-flight
# per (event, lens) holds across API replicas so a burst of viewers (and, once
# the paywall lands, a burst of sample-spenders) costs exactly one LLM call.
@router.get("/api/v1/events/{event_id}/brief", response_model=BriefResponse)
async def get_brief(event_id: uuid.UUID, lens: str, db: AsyncSession = Depends(get_db)):
    if lens not in LENSES:
        raise HTTPException(status_code=422, detail=f"unknown lens '{lens}'")
    cached = await _read_cached_brief(db, event_id, lens)
    if cached:
        return cached

    async with single_flight(f"brief:{event_id}:{lens}"):
        # Past the single-flight barrier, re-read: the leader may have just
        # filled the cache while we waited. If it's still empty, generate — that
        # covers the leader and the fallback case where the leader stalled/died.
        cached = await _read_cached_brief(db, event_id, lens)
        if cached:
            return cached
        try:
            briefs = await generate_briefs(event_id, [lens])
            await persist_briefs(event_id, briefs)
            read = briefs.get(lens) or {}
        except Exception:
            # The brief is an on-demand LLM synthesis. If the model is unavailable
            # (quota exhausted, timeout), return an empty brief so the story page
            # shows "the <lens> read isn't available yet" — never a 500.
            logger.warning("brief_unavailable", event_id=str(event_id), lens=lens, exc_info=True)
            read = {}
        return BriefResponse(
            lens=lens, brief=read.get("text"), points=read.get("points") or [], cached=False
        )


@router.get("/api/v1/events/{event_id}/questions", response_model=QuestionsResponse)
async def get_questions(
    event_id: uuid.UUID, lens: str | None = None, db: AsyncSession = Depends(get_db)
):
    row = (
        await db.execute(
            text("SELECT projection FROM events WHERE id = :eid"), {"eid": str(event_id)}
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")
    return QuestionsResponse(questions=suggested_questions(row["projection"], lens))


@router.post("/api/v1/events/{event_id}/ask")
async def ask(event_id: uuid.UUID, body: AskRequest, db: AsyncSession = Depends(get_db)):
    exists = (
        await db.execute(text("SELECT 1 FROM events WHERE id = :eid"), {"eid": str(event_id)})
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail="event not found")
    question = body.question.strip()
    if not question or len(question) > 2000:
        raise HTTPException(status_code=422, detail="question must be 1-2000 characters")

    session_id = await ensure_session(
        event_id, uuid.UUID(body.session_id) if body.session_id else None
    )

    async def sse():
        yield f"event: session\ndata: {json.dumps({'session_id': str(session_id)})}\n\n"
        async for chunk in answer_stream(event_id=event_id, session_id=session_id, question=question):
            yield f"event: {chunk['type']}\ndata: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
