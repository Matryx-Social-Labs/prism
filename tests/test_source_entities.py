"""An outlet is not an actor in its own coverage.

The extractor faithfully returns the byline, so `prajavani` and `tv9kannada`
became entities. Two measured consequences on production 2026-07-28: `prajavani`
was the single most-shared "entity" across the 139 articles of one over-merged
event — the outlet doing the merging — and `tv9kannada` was the FIRST cast name
on a live trending story, so the product told readers a story was about a TV
channel.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from common.entities import drop_source_names, reset_cache, source_name_slugs

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _seed_source(s, slug, name):
    sid = uuid.uuid4()
    await s.execute(
        text("INSERT INTO sources (id,slug,name,source_type) VALUES (:i,:s,:n,'rss')"),
        {"i": str(sid), "s": slug, "n": name},
    )
    return sid


async def test_outlet_names_are_not_actors():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    sids = []
    try:
        async with session_scope() as s:
            sids.append(await _seed_source(s, f"tv9kannada{tag}", f"TV9 Kannada {tag}"))
            sids.append(await _seed_source(s, f"prajavani{tag}", f"Prajavani {tag}"))
        reset_cache()

        async with session_scope() as s:
            kept = await drop_source_names(
                s,
                [
                    f"TV9 Kannada {tag}",     # the display name, as the extractor emits it
                    f"prajavani{tag}",        # the registry handle
                    "Dharmendra Pradhan",     # a real actor survives
                    "Cockroach Janta Party",
                ],
            )
        assert kept == ["Dharmendra Pradhan", "Cockroach Janta Party"]
    finally:
        reset_cache()
        async with session_scope() as s:
            await s.execute(text("DELETE FROM sources WHERE id = ANY(:i)"), {"i": [str(x) for x in sids]})


async def test_the_filter_is_not_so_greedy_it_eats_real_actors():
    """`The Hindu` must not take `Hindu Mahasabha` with it, and a short source
    handle must not match every word that starts the same way."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    sids = []
    try:
        async with session_scope() as s:
            sids.append(await _seed_source(s, f"thehindu{tag}", f"The Hindu {tag}"))
        reset_cache()
        async with session_scope() as s:
            kept = await drop_source_names(s, ["Hindu Mahasabha", "Hindustan Aeronautics"])
        assert kept == ["Hindu Mahasabha", "Hindustan Aeronautics"]
    finally:
        reset_cache()
        async with session_scope() as s:
            await s.execute(text("DELETE FROM sources WHERE id = ANY(:i)"), {"i": [str(x) for x in sids]})


async def test_cache_survives_repeat_calls_without_requerying_forever():
    if not await _db_reachable():
        pytest.skip("no database")
    reset_cache()
    async with session_scope() as s:
        a = await source_name_slugs(s)
        b = await source_name_slugs(s)
    assert a is b, "the per-process cache is not being reused"
