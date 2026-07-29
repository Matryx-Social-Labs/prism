"""Corroboration counts mastheads, not feeds.

The Hindu ships six RSS feeds — national plus Tamil Nadu, Kerala, Karnataka,
Andhra Pradesh and Telangana — and republishes the same article across them.
Measured on production 2026-07-28, 666 articles in that family share a
byte-identical body. Counting DISTINCT source slug meant one newsroom filing one
story could report up to SIX independent sources.

That number is the product's central claim — the ledger rail prints it, and the
single-origin flag exists to warn when sourcing is narrow. Inflating it by
syndication is the precise failure that flag is meant to catch.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from correlation.trending import _community_facts

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _article_from(s, event_id, slug, publisher, tag):
    """One source -> raw_item -> article -> membership in `event_id`."""
    sid, rid, aid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await s.execute(
        text("INSERT INTO sources (id,slug,name,source_type,publisher) "
             "VALUES (:i,:s,:n,'rss',:p)"),
        {"i": str(sid), "s": f"{slug}-{tag}", "n": slug, "p": f"{publisher}-{tag}"},
    )
    await s.execute(
        text("INSERT INTO raw_items (id,source_id,external_id,title,raw,relevance) "
             "VALUES (:i,:s,:e,'a headline','{}'::jsonb,'relevant')"),
        {"i": str(rid), "s": str(sid), "e": f"ext-{aid}"},
    )
    await s.execute(
        text("INSERT INTO articles (id,raw_item_id,clean_text,retrieval_tier,word_count) "
             "VALUES (:i,:r,'the same syndicated body','rss',4)"),
        {"i": str(aid), "r": str(rid)},
    )
    await s.execute(
        text("INSERT INTO event_memberships (id,event_id,article_id,match_type,is_survivor) "
             "VALUES (:i,:e,:a,'embedding',false)"),
        {"i": str(uuid.uuid4()), "e": str(event_id), "a": str(aid)},
    )
    return sid, rid, aid


async def _facts(event_id):
    async with session_scope() as s:
        return await _community_facts(s, [str(event_id)])


async def test_one_masthead_across_six_feeds_counts_once():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    eid = uuid.uuid4()
    made = []
    try:
        async with session_scope() as s:
            await s.execute(
                text("INSERT INTO events (id,title,sector,last_updated_at) "
                     "VALUES (:i,'a syndicated story','politics',now())"),
                {"i": str(eid)},
            )
            for edition in ("thehindu", "thehindu_kerala", "thehindu_karnataka",
                            "thehindu_andhra", "thehindu_telangana", "thehindu_tamilnadu"):
                made.append(await _article_from(s, eid, edition, "thehindu", tag))

        facts = await _facts(eid)
        assert facts["total_sources"] == 1, (
            f"six editions of one masthead reported as {facts['total_sources']} sources"
        )
    finally:
        await _teardown(eid, made)


async def test_genuinely_independent_outlets_still_each_count():
    """The guard must not flatten real corroboration into 1."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    eid = uuid.uuid4()
    made = []
    try:
        async with session_scope() as s:
            await s.execute(
                text("INSERT INTO events (id,title,sector,last_updated_at) "
                     "VALUES (:i,'a real story','politics',now())"),
                {"i": str(eid)},
            )
            for outlet in ("thehindu", "ndtv", "timesofindia"):
                made.append(await _article_from(s, eid, outlet, outlet, tag))

        facts = await _facts(eid)
        assert facts["total_sources"] == 3
    finally:
        await _teardown(eid, made)


async def _teardown(eid, made):
    async with session_scope() as s:
        await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": str(eid)})
        await s.execute(text("DELETE FROM articles WHERE id = ANY(CAST(:i AS uuid[]))"),
                        {"i": [str(a) for _, _, a in made]})
        await s.execute(text("DELETE FROM raw_items WHERE id = ANY(CAST(:i AS uuid[]))"),
                        {"i": [str(r) for _, r, _ in made]})
        await s.execute(text("DELETE FROM sources WHERE id = ANY(CAST(:i AS uuid[]))"),
                        {"i": [str(x) for x, _, _ in made]})
        await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})
