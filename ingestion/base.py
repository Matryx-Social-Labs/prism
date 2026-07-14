"""Shared collector plumbing: source lookup, idempotent persist, watermarks.

Collectors preserve observations exactly as received (raw JSONB), dedupe
within a source on (source_id, external_id), keep a per-source watermark
so scheduled runs fetch only new items, and publish each new raw item to
the raw.items stream.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from common import stream
from common.db import session_scope
from common.models import RawItem, Source
from common.schemas import RawItemEnvelope, RawItemMessage

logger = logging.getLogger(__name__)


async def get_source(session: AsyncSession, slug: str) -> Source:
    result = await session.execute(select(Source).where(Source.slug == slug))
    source = result.scalar_one_or_none()
    if source is None:
        raise RuntimeError(f"source '{slug}' not seeded — run ingestion.seed first")
    return source


async def get_watermark(slug: str) -> dict:
    async with session_scope() as session:
        source = await get_source(session, slug)
        return dict(source.watermark or {})


async def set_watermark(slug: str, watermark: dict) -> None:
    async with session_scope() as session:
        source = await get_source(session, slug)
        source.watermark = watermark


async def persist_envelopes(envelopes: list[RawItemEnvelope]) -> int:
    """Insert new raw items (idempotent) and publish each to raw.items.

    Returns the number of newly inserted items.
    """
    if not envelopes:
        return 0

    new_ids: list[uuid.UUID] = []
    async with session_scope() as session:
        source_cache: dict[str, Source] = {}
        for env in envelopes:
            if env.source_slug not in source_cache:
                source_cache[env.source_slug] = await get_source(session, env.source_slug)
            source = source_cache[env.source_slug]

            stmt = (
                pg_insert(RawItem)
                .values(
                    id=uuid.uuid4(),
                    source_id=source.id,
                    external_id=env.external_id,
                    url=env.url,
                    title=env.title[:2000],
                    body=env.body,
                    language=env.language,
                    published_at=env.published_at,
                    raw=env.raw,
                    relevance="pending",
                )
                .on_conflict_do_nothing(index_elements=["source_id", "external_id"])
                .returning(RawItem.id)
            )
            result = await session.execute(stmt)
            inserted = result.scalar_one_or_none()
            if inserted is not None:
                new_ids.append(inserted)

    for raw_item_id in new_ids:
        await stream.publish(stream.RAW_ITEMS, RawItemMessage(raw_item_id=str(raw_item_id)).model_dump())

    return len(new_ids)
