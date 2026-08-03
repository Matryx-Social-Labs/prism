"""The headline and the summary must describe the same article.

An event's title is copied from its FOUNDING article when the event is created
and never changes. Its summary was being taken from whichever article joined most
recently, so for any event with more than one member the two described different
pieces of news. Measured on production before the fix: 830 of 1,054 multi-member
events, 79%.

It was worst exactly where a reader looks first. The lead story on the feed read
"AAIB explains to SC why AI171 crash report is getting delayed" above a summary
about a seafarer missing in the Black Sea, because one late member had wrongly
merged on the shared entity "Supreme Court". One bad merge at the tail replaced
the whole event's summary.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from correlation.consumer import _rebuild_projection


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        # Narrow on purpose. A bare `except Exception` here reports every failure
        # as "no database", which turns a broken test into a silent skip — and a
        # skip reads as a pass in CI.
        return False


async def _add_member(s, event_id, *, title, summary, source_id):
    """One article joining an event, as the correlation consumer writes it."""
    raw_id, art_id = uuid.uuid4(), uuid.uuid4()
    await s.execute(
        text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, "
             "relevance, published_at) "
             "VALUES (:i, :s, :x, :u, :t, '{}'::jsonb, 'relevant', now())"),
        {"i": str(raw_id), "s": str(source_id), "x": str(raw_id), "u": f"http://x/{raw_id}", "t": title},
    )
    await s.execute(
        text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
             "VALUES (:i, :r, :c, 'rss', 12)"),
        {"i": str(art_id), "r": str(raw_id), "c": title},
    )
    await s.execute(
        text("INSERT INTO enrichments (id, article_id, summary, event_type) "
             "VALUES (:i, :a, :s, 'report')"),
        {"i": str(uuid.uuid4()), "a": str(art_id), "s": summary},
    )
    await s.execute(
        text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
             "VALUES (:i, :e, :a, 'entity_overlap', false)"),
        {"i": str(uuid.uuid4()), "e": str(event_id), "a": str(art_id)},
    )
    return raw_id, art_id


async def test_the_summary_comes_from_the_founder_not_the_newest_member():
    if not await _db_reachable():
        pytest.skip("no database")

    eid = uuid.uuid4()
    src = uuid.uuid4()
    created = []
    try:
        async with session_scope() as s:
            await s.execute(
                text("INSERT INTO sources (id, slug, name, source_type) VALUES (:i, :s, :n, 'rss')"),
                {"i": str(src), "s": f"t-{eid.hex[:8]}", "n": "test"},
            )
            await s.execute(
                text("INSERT INTO events (id, title, summary, sector, regions, last_updated_at) "
                     "VALUES (:i, :t, :su, 'politics', CAST(:r AS text[]), now())"),
                {"i": str(eid), "t": "AAIB explains to SC why the crash report is delayed",
                 "su": "Aircraft Accident Investigation Bureau informs the Supreme Court.",
                 "r": ["IN"]},
            )
            # The founder — the article the TITLE was copied from.
            created.append(await _add_member(
                s, eid,
                title="AAIB explains to SC why the crash report is delayed",
                summary="Aircraft Accident Investigation Bureau informs the Supreme Court.",
                source_id=src))
            # A later member. In production this was a WRONG merge sharing only
            # the entity "Supreme Court", but the bug does not need a wrong merge
            # — any later member with different content produced the mismatch.
            created.append(await _add_member(
                s, eid,
                title="SC directs MEA to trace seafarer missing after Black Sea attack",
                summary="The Supreme Court directed the Ministry of External Affairs to "
                        "locate an Indian seafarer missing in the Black Sea.",
                source_id=src))

        await _rebuild_projection(eid)

        async with session_scope() as s:
            row = (await s.execute(
                text("SELECT title, summary FROM events WHERE id = :i"), {"i": str(eid)}
            )).mappings().first()

        assert "Aircraft Accident Investigation Bureau" in row["summary"], (
            "the summary must describe the same article as the headline"
        )
        assert "seafarer" not in row["summary"], (
            "the newest member's summary replaced the founder's — the reader sees a "
            "headline about one story over a summary about another"
        )
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": str(eid)})
            for raw_id, art_id in created:
                await s.execute(text("DELETE FROM enrichments WHERE article_id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM raw_items WHERE id = :r"), {"r": str(raw_id)})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})
            await s.execute(text("DELETE FROM sources WHERE id = :s"), {"s": str(src)})
