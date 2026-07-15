"""Prism serving layer — /api/v1 REST + SSE (docs: api/README.md).

Shared by the Next.js web app now and the React Native app later.
"""

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent.questions import suggested_questions
from agent.rag import answer_stream, ensure_session
from common import stream
from common.config import get_settings
from common.db import get_db
from common.lenses import LENSES, get_lens
from common.logging import get_logger, setup_logging
from correlation.briefs import available_lenses, generate_briefs, persist_briefs
from personalization.ranking import score_event

setup_logging()
logger = get_logger(__name__)

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
    tickers: list[str]
    catalyst: str | None
    price_impact_direction: str | None
    last_updated_at: str
    score: float


class FeedResponse(BaseModel):
    items: list[FeedItem]
    lens: str


class LensOut(BaseModel):
    slug: str
    name: str
    tagline: str


class LensesResponse(BaseModel):
    lenses: list[LensOut]
    default: str


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
    lens_briefs: dict[str, str]
    available_lenses: list[str]
    sources: list[SourceRef]
    perspectives: list[PerspectiveOut]
    impacts: list[ImpactOut]


class BriefResponse(BaseModel):
    lens: str
    brief: str | None
    cached: bool


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


@app.get("/api/v1/lenses", response_model=LensesResponse)
async def get_lenses():
    return LensesResponse(
        lenses=[
            LensOut(slug=lens.slug, name=lens.name, tagline=lens.tagline)
            for lens in LENSES.values()
        ],
        default="cyber_grc",
    )


@app.get("/api/v1/feed", response_model=FeedResponse)
async def get_feed(
    lens: str | None = None,
    sector: str | None = None,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    active_lens = get_lens(lens)
    # Explicit ?sector= wins; otherwise the lens's sector defaults apply.
    sectors = [sector] if sector else active_lens.sectors
    # Candidate window is per-sector so a high-churn sector (thousands of
    # CVE updates a day) can't evict everyone else's news before ranking.
    rows = (
        await db.execute(
            text(
                """
                SELECT id, title, summary, sector, projection,
                       last_updated_at, occurred_at
                FROM (
                    SELECT e.*, ROW_NUMBER() OVER (
                        PARTITION BY e.sector ORDER BY e.last_updated_at DESC
                    ) AS rn
                    FROM events e
                    WHERE (CAST(:sectors AS text[]) IS NULL
                           OR e.sector = ANY(CAST(:sectors AS text[])))
                ) windowed
                WHERE rn <= 120
                """
            ),
            {"sectors": sectors or None},
        )
    ).mappings().all()

    cve_only_sources = {"nvd", "cisa_kev"}
    items: list[FeedItem] = []
    for row in rows:
        projection = row["projection"] or {}
        # Raw database records (no news coverage) only surface for lenses
        # that want them (cyber/GRC); they're noise for readers and traders.
        slugs = set(projection.get("source_slugs") or [])
        if slugs and slugs <= cve_only_sources and not active_lens.include_cve_records:
            continue
        cyber = projection.get("cyber") or {}
        finance = projection.get("finance") or {}
        cvss = cyber.get("cvss") or {}
        kev = bool((cyber.get("exploitation") or {}).get("kev_listed"))
        # Recency = when the event happened, not when we ingested it —
        # otherwise a backfill makes years-old records look breaking.
        occurred = row["occurred_at"]
        reference_time = (
            datetime.combine(occurred, datetime.min.time(), tzinfo=UTC)
            if occurred
            else row["last_updated_at"]
        )
        score = score_event(
            lens=active_lens,
            reference_time=reference_time,
            projection=projection,
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
                tickers=(finance.get("tickers") or [])[:4],
                catalyst=finance.get("catalyst"),
                price_impact_direction=(finance.get("price_impact") or {}).get("direction"),
                last_updated_at=row["last_updated_at"].isoformat(),
                score=score,
            )
        )
    items.sort(key=lambda i: i.score, reverse=True)
    return FeedResponse(items=items[:limit], lens=active_lens.slug)


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

    projection = event["projection"] or {}
    return EventDetail(
        id=str(event["id"]),
        title=event["title"],
        summary=event["summary"],
        sector=event["sector"],
        regions=event["regions"] or [],
        occurred_at=event["occurred_at"].isoformat() if event["occurred_at"] else None,
        last_updated_at=event["last_updated_at"].isoformat(),
        projection=event["projection"],
        lens_briefs=projection.get("lens_briefs") or {},
        available_lenses=available_lenses(projection),
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


# On-demand lens briefs: any lens on any story — this is what lets a cyber
# professional pull the cyber read of a war, or a trader the market read of
# a breach. Generated once, cached on the event projection. Single-flight
# per (event, lens) so a burst of viewers costs one LLM call.
_brief_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


@app.get("/api/v1/events/{event_id}/brief", response_model=BriefResponse)
async def get_brief(event_id: uuid.UUID, lens: str, db: AsyncSession = Depends(get_db)):
    if lens not in LENSES:
        raise HTTPException(status_code=422, detail=f"unknown lens '{lens}'")
    row = (
        await db.execute(
            text("SELECT projection FROM events WHERE id = :eid"), {"eid": str(event_id)}
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="event not found")

    cached = ((row["projection"] or {}).get("lens_briefs") or {}).get(lens)
    if cached:
        return BriefResponse(lens=lens, brief=cached, cached=True)

    lock = _brief_locks[f"{event_id}:{lens}"]
    async with lock:
        # Re-check under the lock — another request may have generated it.
        row = (
            await db.execute(
                text("SELECT projection FROM events WHERE id = :eid"), {"eid": str(event_id)}
            )
        ).mappings().first()
        cached = ((row["projection"] or {}).get("lens_briefs") or {}).get(lens)
        if cached:
            return BriefResponse(lens=lens, brief=cached, cached=True)

        briefs = await generate_briefs(event_id, [lens])
        await persist_briefs(event_id, briefs)
        return BriefResponse(lens=lens, brief=briefs.get(lens), cached=False)


@app.get("/api/v1/events/{event_id}/questions", response_model=QuestionsResponse)
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
    # Ingestion runs in the worker; the API only signals it. Running
    # collectors in-process doubled GDELT load and starved API workers.
    await stream.publish(stream.ADMIN_TRIGGERS, {"requested_by": "admin-endpoint"})
    logger.info("admin_trigger_published")
    return {"status": "ingestion trigger queued for worker"}
