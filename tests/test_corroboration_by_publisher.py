"""Corroboration counts OUTLETS (mastheads), never articles (audit P0 #8).

`projection.source_count` was `len(rows)`, the member articles. One outlet
re-filing a story, or carrying it on three section feeds, read as three outlets
corroborating it: event 73342608 (five Indian Express articles, one newsroom)
led the front page as the most-corroborated record. In the live window 148 of
1,200 events overstated it and 84 passed as multi-source with one publisher.
The count drives the ranking boost, the chart order, the one-source style and
"Top of the record" (`source_count > 1`), so it is the same unit /sources
counts: distinct publishers, The Times of India's city desks included.
"""

import json
import uuid

import pytest
from sqlalchemy import text

from common.db import session_scope
from correlation.consumer import _rebuild_projection
from tests.test_projection_summary import _add_member, _db_reachable
from tools.backfill_source_count import recount

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _event_from(feeds: list[tuple[str, str]], per_feed: int, projection: dict | None = None):
    """An event whose members come from `feeds` (slug, publisher), `per_feed` articles each."""
    eid = uuid.uuid4()
    srcs = {slug: uuid.uuid4() for slug, _ in feeds}
    created = []
    async with session_scope() as s:
        for slug, pub in feeds:
            await s.execute(
                text("INSERT INTO sources (id, slug, name, source_type, country, publisher) "
                     "VALUES (:i, :s, :s, 'rss', 'IN', :p)"),
                {"i": str(srcs[slug]), "s": f"{slug}-{eid.hex[:8]}", "p": pub},
            )
        await s.execute(
            text("INSERT INTO events (id, title, summary, sector, regions, last_updated_at, projection) "
                 "VALUES (:i, 'Minister slapped at rally', 'A minister was slapped.', 'politics', "
                 "CAST(:r AS text[]), now(), CAST(:p AS jsonb))"),
            {"i": str(eid), "r": ["IN"], "p": json.dumps(projection) if projection else None},
        )
        for slug, _ in feeds:
            for k in range(per_feed):
                created.append(await _add_member(
                    s, eid, title=f"Minister slapped ({slug} {k})", summary="A minister was slapped.",
                    source_id=srcs[slug], minutes_ago=len(created)))
    return eid, list(srcs.values()), created


async def _drop(eid, srcs, created):
    async with session_scope() as s:
        await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": str(eid)})
        for raw_id, art_id in created:
            await s.execute(text("DELETE FROM enrichments WHERE article_id = :a"), {"a": str(art_id)})
            await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": str(art_id)})
            await s.execute(text("DELETE FROM raw_items WHERE id = :r"), {"r": str(raw_id)})
        await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})
        await s.execute(text("DELETE FROM sources WHERE id = ANY(:ids)"), {"ids": [str(x) for x in srcs]})


async def _projection(eid) -> dict:
    async with session_scope() as s:
        return (await s.execute(text("SELECT projection FROM events WHERE id = :i"), {"i": str(eid)})).scalar_one()


@pytest.mark.parametrize(
    ("feeds", "per_feed", "outlets"),
    [
        # Five reports, one newsroom: the record that led the front page.
        ([("indianexpress", "indianexpress")], 5, 1),
        # One masthead's section feeds are one outlet, however many there are.
        ([("ie_india", "indianexpress"), ("ie_cities", "indianexpress")], 2, 1),
        # The Times of India and The Times of India — Delhi: one masthead.
        ([("toi", "timesofindia"), ("toi_delhi", "timesofindia")], 1, 1),
        # ...and a second masthead is the corroboration the count exists for.
        ([("toi", "timesofindia"), ("toi_delhi", "timesofindia"), ("hindu", "thehindu")], 1, 2),
    ],
)
async def test_source_count_is_distinct_publishers_not_articles(feeds, per_feed, outlets):
    if not await _db_reachable():
        pytest.skip("no database")
    eid, srcs, created = await _event_from(feeds, per_feed)
    try:
        await _rebuild_projection(eid)
        proj = await _projection(eid)
        assert proj["source_count"] == outlets, (
            f"{len(created)} articles from {outlets} outlet(s) counted as {proj['source_count']}: "
            "one newsroom re-filing is not corroboration, and source_count > 1 is what "
            "puts a record in Top of the record"
        )
    finally:
        await _drop(eid, srcs, created)


async def test_backfill_recounts_a_stale_article_count_only_with_apply():
    if not await _db_reachable():
        pytest.skip("no database")
    stale = {"source_count": 5, "lens_briefs": {"reader": "Kept."}}
    eid, srcs, created = await _event_from([("indianexpress", "indianexpress")], 5, projection=stale)
    try:
        async with session_scope() as s:
            changes = await recount(s, apply=False)
        assert (5, 1) in [(old, new) for i, old, new in changes if i == eid]
        assert (await _projection(eid))["source_count"] == 5, "the dry run wrote"

        async with session_scope() as s:
            await recount(s, apply=True)
        proj = await _projection(eid)
        assert proj["source_count"] == 1
        assert proj["lens_briefs"] == {"reader": "Kept."}, "the backfill writes one key, nothing else"

        async with session_scope() as s:
            assert [c for c in await recount(s, apply=False) if c[0] == eid] == [], "a rerun has nothing to do"
    finally:
        await _drop(eid, srcs, created)
