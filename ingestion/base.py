"""Shared collector plumbing: source lookup, idempotent persist, watermarks.

Collectors preserve observations exactly as received (raw JSONB), dedupe
within a source on (source_id, external_id), keep a per-source watermark
so scheduled runs fetch only new items, and publish each new raw item to
the raw.items stream.
"""

import html as _html
import re
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from common import stream
from common.db import session_scope
from common.logging import get_logger
from common.models import RawItem, Source
from common.schemas import RawItemEnvelope, RawItemMessage

logger = get_logger(__name__)


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


_TAG = re.compile(r"<[^>]+>")


def clean_text(text: str) -> str:
    """Strip markup, THEN decode entities — in that order, for every collector.

    RSS feeds hand us `&#039;` and friends verbatim, and nothing in the ingest
    path decoded them, so the apostrophe in a headline reached the reader as a
    literal "&#039;". Measured on production: 22 occurrences across 4% of feed
    titles and 5% of storyline developments — and every affected headline was
    Hindi, so it landed squarely on the India-first audience.

    Order matters. Unescaping first would turn `&lt;b&gt;` into a real tag for
    the stripper to eat, silently deleting text the publisher wrote literally.
    Stripping first leaves an escaped tag as visible text, which is what the
    publisher meant; React escapes it again at render, so this is not a way in.

    Applied here rather than in each collector because every one of them —
    rss, nvd, cisa_kev — persists through this function.
    """
    if not text:
        return text
    return _html.unescape(_TAG.sub(" ", text)).strip()


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
                    title=clean_text(env.title)[:2000],
                    body=clean_text(env.body) if env.body else env.body,
                    # The SOURCE knows its language; the collector does not.
                    # ingestion/rss.py stamped language="en" on every envelope
                    # including the Hindi, Tamil and Kannada feeds, so all 1,385
                    # non-Latin production articles were labelled English — and
                    # sources.language had the right answer the whole time.
                    #
                    # Fixed at the persist choke point rather than in rss.py so
                    # it holds for every collector, present and future.
                    language=source.language or env.language,
                    published_at=env.published_at,
                    image_url=env.image_url,
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
