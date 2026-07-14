"""Prism serving layer — /api/v1 REST + SSE (docs: api/README.md).

Shared by the Next.js web app now and the React Native app later.
"""

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent.questions import suggested_questions
from agent.rag import answer_stream, ensure_session
from common.config import get_settings
from common.db import get_db
from ingestion.runner import run_all
from personalization.ranking import score_event

logger = logging.getLogger(__name__)

app = FastAPI(title="Prism API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ──────────────────────────────────────────────────────────


class FeedItem(BaseModel):
    id: str
    title: str
    summary: str | None
    sector: str | None
    event_type: str | None
    source_count: int
    cvss_score: float | None
    cvss_severity: str | None
    kev_listed: bool
    cve_ids: list[str]
    last_updated_at: str
    score: float


class FeedResponse(BaseModel):
    items: list[FeedItem]


class SourceRef(BaseModel):
    article_id: str
    source_name: str
    source_slug: str
    url: str | None
    title: str
    published_at: str | None
    stance: str | None


class PerspectiveOut(BaseModel):
    label: str
    stance: str | None
    origin_country: str | None
    summary: str | None
    article_ids: list[str]


class ImpactOut(BaseModel):
    id: str
    entity_name: str | None
    effect: str
    direction: str | None
    horizon: str | None
    confidence: float | None
    parent_impact_id: str | None


class EventDetail(BaseModel):
    id: str
    title: str
    summary: str | None
    sector: str | None
    regions: list[str]
    occurred_at: str | None
    last_updated_at: str
    projection: dict | None
    sources: list[SourceRef]
    perspectives: list[PerspectiveOut]
    impacts: list[ImpactOut]


class QuestionsResponse(BaseModel):
    questions: list[str]


class AskRequest(BaseModel):
    question: str
    session_id: str | None = None


# ── Endpoints ────────────────────────────────────────────────────────


@app.get("/healthz")
async def healthz(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/v1/feed", response_model=FeedResponse)
async def get_feed(
    sector: str | None = None,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    where = "WHERE (CAST(:sector AS text) IS NULL OR e.sector = CAST(:sector AS text))"
    rows = (
        await db.execute(
            text(
                f"""
                SELECT e.id, e.title, e.summary, e.sector, e.projection,
                       e.last_updated_at, e.occurred_at
                FROM events e
                {where}
                ORDER BY e.last_updated_at DESC
                LIMIT 200
                """
            ),
            {"sector": sector},
        )
    ).mappings().all()

    items: list[FeedItem] = []
    for row in rows:
        projection = row["projection"] or {}
        cyber = projection.get("cyber") or {}
        cvss = cyber.get("cvss") or {}
        exploitation = cyber.get("exploitation") or {}
        kev = bool(exploitation.get("kev_listed"))
        # Recency = when the event happened, not when we ingested it —
        # otherwise a backfill makes years-old records look breaking.
        occurred = row["occurred_at"]
        reference_time = (
            datetime.combine(occurred, datetime.min.time(), tzinfo=UTC)
            if occurred
            else row["last_updated_at"]
        )
        score = score_event(
            last_updated_at=reference_time,
            cvss_score=cvss.get("score"),
            kev_listed=kev,
            source_count=projection.get("source_count", 1),
        )
        items.append(
            FeedItem(
                id=str(row["id"]),
                title=row["title"],
                summary=row["summary"],
                sector=row["sector"],
                event_type=projection.get("event_type"),
                source_count=projection.get("source_count", 1),
                cvss_score=cvss.get("score"),
                cvss_severity=cvss.get("severity"),
                kev_listed=kev,
                cve_ids=(cyber.get("cve_ids") or [])[:4],
                last_updated_at=row["last_updated_at"].isoformat(),
                score=score,
            )
        )
    items.sort(key=lambda i: i.score, reverse=True)
    return FeedResponse(items=items[:limit])


@app.get("/api/v1/events/{event_id}", response_model=EventDetail)
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    event = (
        await db.execute(
            text(
                """
                SELECT id, title, summary, sector, regions, occurred_at,
                       last_updated_at, projection
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

    return EventDetail(
        id=str(event["id"]),
        title=event["title"],
        summary=event["summary"],
        sector=event["sector"],
        regions=event["regions"] or [],
        occurred_at=event["occurred_at"].isoformat() if event["occurred_at"] else None,
        last_updated_at=event["last_updated_at"].isoformat(),
        projection=event["projection"],
        sources=[
            SourceRef(
                article_id=str(s["article_id"]),
                source_name=s["source_name"],
                source_slug=s["source_slug"],
                url=s["url"],
                title=s["title"],
                published_at=s["published_at"].isoformat() if s["published_at"] else None,
                stance=s["stance"],
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


@app.get("/api/v1/events/{event_id}/questions", response_model=QuestionsResponse)
async def get_questions(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(
            text("SELECT projection FROM events WHERE id = :eid"), {"eid": str(event_id)}
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")
    return QuestionsResponse(questions=suggested_questions(row["projection"]))


@app.post("/api/v1/events/{event_id}/ask")
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


@app.post("/api/v1/admin/pipeline/run")
async def trigger_pipeline(x_admin_token: str = Header(default="")):
    if x_admin_token != settings.prism_admin_token:
        raise HTTPException(status_code=403, detail="invalid admin token")
    task = asyncio.create_task(run_all())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"status": "ingestion started"}


_background_tasks: set[asyncio.Task] = set()
