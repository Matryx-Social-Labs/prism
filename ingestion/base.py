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
from common.urls import CANONICAL_URL_VERSION, canonicalize_url

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
        prepared: list[tuple[RawItemEnvelope, Source, str | None]] = []
        canonical_by_source: dict[uuid.UUID, set[str]] = {}
        for env in envelopes:
            if env.source_slug not in source_cache:
                source_cache[env.source_slug] = await get_source(session, env.source_slug)
            source = source_cache[env.source_slug]
            url_canonical = canonicalize_url(env.url)
            prepared.append((env, source, url_canonical))
            if url_canonical:
                canonical_by_source.setdefault(source.id, set()).add(url_canonical)

        # ``external_id`` is a feed observation, not a reliable document key.
        # BBC has changed only its URL fragment as an article moves through the
        # feed (#0 -> #2 -> #5), which used to create a new raw item each time.
        # Canonical URL is the document identity within one source. Keep
        # cross-source observations because they are useful provenance, but do
        # not send the same source document through the pipeline repeatedly.
        seen_documents: set[tuple[uuid.UUID, str]] = set()
        for source_id, urls in canonical_by_source.items():
            existing = await session.execute(
                select(RawItem.url_canonical).where(
                    RawItem.source_id == source_id,
                    RawItem.url_canonical.in_(urls),
                )
            )
            seen_documents.update(
                (source_id, canonical)
                for canonical in existing.scalars()
                if canonical
            )

        for env, source, url_canonical in prepared:
            document_key = (source.id, url_canonical) if url_canonical else None
            if document_key and document_key in seen_documents:
                continue
            if document_key:
                # Also dedupe two unstable ids for one URL inside this batch.
                seen_documents.add(document_key)
            stmt = (
                pg_insert(RawItem)
                .values(
                    id=uuid.uuid4(),
                    source_id=source.id,
                    external_id=env.external_id,
                    url=env.url,
                    url_canonical=url_canonical,
                    url_canonical_version=CANONICAL_URL_VERSION if url_canonical else None,
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
