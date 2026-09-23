"""/admin: people, the switches as the API sees them, and the one control
(admin dashboard, plan phase D; decision D4, 2026-09-23).

GET  /api/v1/admin/people              — every account: plan, activity, labelling
GET  /api/v1/admin/flags               — feature switches, READ-ONLY, as this API process sees them
POST /api/v1/admin/pipeline/trigger    — ask the worker to collect now (audited)

The switches are shown, never set: changing one from here would move flags
from the environment into the database and change how a bad change is rolled
back (D4). They are read from a fixed list, so nothing secret-shaped can ever
reach the page, and they are the API's own view — the worker reads its own
environment, which is how the quote verdicts and X posts run in shadow.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_admin_user
from common import stream, usage
from common.admin_audit import audit
from common.config import get_settings
from common.db import get_db
from common.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)
PRIVATE = {"Cache-Control": "no-store"}

# Setting name → what it does, in the dashboard's words. The only settings the
# page can show; a secret can never be added here by accident because none of
# these are strings.
FLAGS: dict[str, str] = {
    "prism_ingestion_enabled": "Collect new reports",
    "prism_ingest_max_articles": "Stop collecting after this many reports in all (0: no cap)",
    "prism_llm_budget_floor_usd": "Stop collecting below this LLM balance, in dollars (0: no floor)",
    "prism_cve_feeds_enabled": "Collect the CVE security feeds",
    "prism_podcasts_enabled": "Podcast clips: poll, transcribe, match to stories",
    "prism_x_enabled": "Posts from official X accounts",
    "prism_quote_verdicts": "Mark quotes as one statement in two languages, or a translation",
    "prism_headline_tier_threshold": "Match stories across languages by headline (0: off)",
    "prism_veto_enabled": "Check story merges with a model before serving them",
    "prism_ask_guard_enabled": "Screen Ask questions before answering",
    "prism_langfuse_enabled": "Trace model calls in Langfuse",
}
ACTIVE_WINDOW_DAYS = 28


@router.get("/api/v1/admin/people")
async def people(
    response: Response,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
    _: str = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    response.headers.update(PRIVATE)
    since = usage.today() - timedelta(days=ACTIVE_WINDOW_DAYS - 1)
    rows = (await db.execute(text(
        """
        SELECT u.email, u.name, u.profession, u.languages, u.state, u.created_at,
               sub.plan, sub.status AS plan_status, sub.provider,
               (SELECT count(*) FROM user_days d WHERE d.user_id = u.id AND d.day >= :since) AS active_days,
               (SELECT max(d.day) FROM user_days d WHERE d.user_id = u.id) AS last_active,
               l.status AS labeller
        FROM users u
        LEFT JOIN labellers l ON l.user_id = u.id
        LEFT JOIN LATERAL (SELECT plan, status, provider FROM subscriptions s WHERE s.user_id = u.id
                           ORDER BY s.created_at DESC LIMIT 1) sub ON true
        ORDER BY u.created_at DESC LIMIT :n OFFSET :o
        """), {"since": since, "n": limit, "o": offset})).mappings().all()
    total = (await db.execute(text("SELECT count(*) FROM users"))).scalar() or 0
    return {"total": total, "active_window_days": ACTIVE_WINDOW_DAYS,
            "people": [{**r, "languages": list(r["languages"] or [])} for r in rows]}


@router.get("/api/v1/admin/flags")
async def flags(response: Response, _: str = Depends(require_admin_user)):
    response.headers.update(PRIVATE)
    s = get_settings()
    return {"seen_by": "api", "flags": [
        {"name": name.upper(), "value": getattr(s, name), "does": does} for name, does in FLAGS.items()]}


@router.post("/api/v1/admin/pipeline/trigger")
async def trigger(actor: str = Depends(require_admin_user), db: AsyncSession = Depends(get_db)):
    """The same signal as the token-guarded /admin/pipeline/run, from a founder's
    account and recorded against them. The worker still decides: with
    collection switched off it does nothing."""
    # Record first, commit, then publish. The worker is in Redis and the record
    # in Postgres, so the two cannot share a transaction; this order means a
    # failure can leave a record of a request that did not go out, never a run
    # nobody recorded (review, 2026-09-23).
    await audit(db, actor, "pipeline.run", "ingestion")
    await db.commit()
    await stream.publish(stream.ADMIN_TRIGGERS, {"requested_by": actor})
    logger.info("admin_trigger_published", actor=actor)
    return {"status": "the worker will collect on its next read of the queue",
            "collecting": get_settings().prism_ingestion_enabled}
