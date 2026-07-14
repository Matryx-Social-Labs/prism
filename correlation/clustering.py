"""Candidate retrieval + match scoring for event canonicalization.

Match cascade (strongest first), all persisted in the match trail:
  1. cve_id     — shared CVE identifier (the canonical key for the cyber beachhead)
  2. url_exact  — an article for the same URL already belongs to an event
  3. title_time — trigram title similarity within a time window (pg_trgm)
  4. embedding  — cosine similarity to the event embedding (pgvector)

Identity is never merged: matching links the article to the event; it never
rewrites entities or inflates impact (EduThreat canonicalization rules).
"""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TITLE_SIMILARITY_THRESHOLD = 0.6
EMBEDDING_DISTANCE_THRESHOLD = 0.12  # cosine distance (1 - similarity); near-duplicates only
TIME_WINDOW_DAYS = 4


@dataclass
class Match:
    event_id: uuid.UUID
    match_type: str
    match_score: float


async def find_event(
    session: AsyncSession,
    *,
    cve_ids: list[str],
    url: str | None,
    title: str,
    published_at,
    embedding: list[float] | None,
    cve_record: bool = False,
) -> Match | None:
    if cve_ids:
        match = await _match_by_cve(session, cve_ids)
        if match:
            return match

    # Authoritative CVE records (NVD/KEV) are one-event-per-CVE by
    # construction: distinct CVEs must never merge, and their boilerplate
    # descriptions ("vulnerability in X allows...") make title/embedding
    # similarity meaningless. Identity match or a new event — nothing fuzzy.
    if cve_record:
        return None

    if url:
        match = await _match_by_url(session, url)
        if match:
            return match

    match = await _match_by_title(session, title, published_at)
    if match:
        return match

    if embedding is not None:
        match = await _match_by_embedding(session, embedding, published_at)
        if match:
            return match

    return None


async def _match_by_cve(session: AsyncSession, cve_ids: list[str]) -> Match | None:
    result = await session.execute(
        text(
            """
            SELECT e.id
            FROM events e
            WHERE jsonb_exists_any(e.projection -> 'cyber' -> 'cve_ids',
                                   CAST(:cve_ids AS text[]))
            ORDER BY e.last_updated_at DESC
            LIMIT 1
            """
        ),
        {"cve_ids": cve_ids},
    )
    event_id = result.scalar_one_or_none()
    if event_id:
        return Match(event_id=event_id, match_type="cve_id", match_score=1.0)
    return None


async def _match_by_url(session: AsyncSession, url: str) -> Match | None:
    result = await session.execute(
        text(
            """
            SELECT em.event_id
            FROM event_memberships em
            JOIN articles a ON a.id = em.article_id
            JOIN raw_items ri ON ri.id = a.raw_item_id
            WHERE ri.url = :url
            LIMIT 1
            """
        ),
        {"url": url},
    )
    event_id = result.scalar_one_or_none()
    if event_id:
        return Match(event_id=event_id, match_type="url_exact", match_score=1.0)
    return None


async def _match_by_title(session: AsyncSession, title: str, published_at) -> Match | None:
    result = await session.execute(
        text(
            f"""
            SELECT e.id, similarity(e.title, :title) AS sim
            FROM events e
            WHERE similarity(e.title, :title) >= :threshold
              AND (CAST(:published_at AS timestamptz) IS NULL
                   OR e.last_updated_at >= CAST(:published_at AS timestamptz) - interval '{TIME_WINDOW_DAYS} days')
            ORDER BY sim DESC
            LIMIT 1
            """
        ),
        {"title": title, "threshold": TITLE_SIMILARITY_THRESHOLD, "published_at": published_at},
    )
    row = result.first()
    if row:
        return Match(event_id=row.id, match_type="title_time", match_score=float(row.sim))
    return None


async def _match_by_embedding(
    session: AsyncSession, embedding: list[float], published_at
) -> Match | None:
    vector_literal = "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"
    result = await session.execute(
        text(
            f"""
            SELECT e.id, (e.embedding <=> CAST(:vec AS vector)) AS dist
            FROM events e
            WHERE e.embedding IS NOT NULL
              AND (e.embedding <=> CAST(:vec AS vector)) <= :threshold
              AND (CAST(:published_at AS timestamptz) IS NULL
                   OR e.last_updated_at >= CAST(:published_at AS timestamptz) - interval '{TIME_WINDOW_DAYS} days')
            ORDER BY dist ASC
            LIMIT 1
            """
        ),
        {"vec": vector_literal, "threshold": EMBEDDING_DISTANCE_THRESHOLD, "published_at": published_at},
    )
    row = result.first()
    if row:
        return Match(
            event_id=row.id, match_type="embedding", match_score=1.0 - float(row.dist)
        )
    return None
