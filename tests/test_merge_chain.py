"""A shared storyline link must land on the live story, however many merges deep.

The route followed exactly ONE hop, on the stated assumption that "merges always
point at a canonical". An audit on 2026-07-28 found a two-hop chain among 356
merged rows, so that link resolved to a story that was itself merged — dormant,
superseded, not what the reader should see.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _story(s, sid, slug, *, merged_into=None, label="A story"):
    # status computed here rather than in SQL: a bare :mi used twice (once in a
    # CASE, once cast to uuid) leaves asyncpg unable to infer the parameter type.
    await s.execute(
        text('INSERT INTO stories (id, slug, label, "cast", member_event_ids, sector, '
             "source_count, velocity, status, merged_into) "
             "VALUES (:i,:sl,:lb,'[]'::jsonb,'[]'::jsonb,'politics',1,0,:st,CAST(:mi AS uuid))"),
        {
            "i": str(sid), "sl": slug, "lb": label,
            "st": "dormant" if merged_into else "current",
            "mi": str(merged_into) if merged_into else None,
        },
    )


async def _get(slug):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        return await c.get(f"/api/v1/trending/{slug}")


async def test_a_two_hop_merge_lands_on_the_live_story():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    try:
        async with session_scope() as s:
            await _story(s, c, f"live-{tag}", label="The live story")
            await _story(s, b, f"mid-{tag}", merged_into=c)
            await _story(s, a, f"old-{tag}", merged_into=b)

        r = await _get(f"old-{tag}")
        assert r.status_code == 200
        body = r.json()
        story = body.get("story", body)
        assert story["label"] == "The live story", (
            f"one-hop landed on a merged story instead: {story['label']!r}"
        )
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"),
                            {"i": [str(a), str(b), str(c)]})


async def test_a_single_hop_still_works():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    a, b = uuid.uuid4(), uuid.uuid4()
    try:
        async with session_scope() as s:
            await _story(s, b, f"canon-{tag}", label="Canonical")
            await _story(s, a, f"shared-{tag}", merged_into=b)
        r = await _get(f"shared-{tag}")
        assert r.status_code == 200
        story = r.json().get("story", r.json())
        assert story["label"] == "Canonical"
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"),
                            {"i": [str(a), str(b)]})


async def test_a_merge_cycle_fails_loudly_instead_of_hanging():
    """A `while` here would spin the request thread forever on corrupt data."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    a, b = uuid.uuid4(), uuid.uuid4()
    try:
        async with session_scope() as s:
            await _story(s, a, f"cyc-a-{tag}")
            await _story(s, b, f"cyc-b-{tag}", merged_into=a)
            await s.execute(text("UPDATE stories SET merged_into = :b WHERE id = :a"),
                            {"b": str(b), "a": str(a)})
        r = await _get(f"cyc-a-{tag}")
        assert r.status_code == 500
    finally:
        async with session_scope() as s:
            await s.execute(text("UPDATE stories SET merged_into = NULL WHERE id = ANY(CAST(:i AS uuid[]))"),
                            {"i": [str(a), str(b)]})
            await s.execute(text("DELETE FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"),
                            {"i": [str(a), str(b)]})


# --- the fold decays at ingest speed unless the ATTACH path follows it ---------


async def test_a_new_mention_lands_on_the_canonical_row_not_the_folded_one():
    """The write path, not the read path. `_resolve_entity` followed the fold and
    was only used for impacts; the path that attaches every actor to every event
    stopped at whatever row carried the slug — including one already merged away.

    Measured on production 2026-09-03: 31 mentions pointing at redirected
    entities, all created that day by one ingestion run (RSS, AICC, Directorate of
    Enforcement, AAP). The one-off fold reported success while the graph
    re-fragmented underneath it at ingest speed.
    """
    if not await _db_reachable():
        pytest.skip("no database")
    from correlation.consumer import _follow_merge

    old_id, new_id = uuid.uuid4(), uuid.uuid4()
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO entities (id, slug, name, entity_type) "
                 "VALUES (:i, :sl, 'RSS Canonical', 'organization')"),
            {"i": new_id, "sl": f"canon-{new_id.hex[:8]}"})
        await s.execute(
            text("INSERT INTO entities (id, slug, name, entity_type, merged_into) "
                 "VALUES (:i, :sl, 'RSS Variant', 'organization', :m)"),
            {"i": old_id, "sl": f"variant-{old_id.hex[:8]}", "m": new_id})
        try:
            got = await _follow_merge(s, old_id, new_id)
            assert got == new_id, "a mention would have attached to the folded row"
        finally:
            await s.execute(text("DELETE FROM entities WHERE id IN (:a, :b)"),
                            {"a": old_id, "b": new_id})


async def test_a_two_hop_chain_reaches_the_end():
    """Production carries a real one: CJP -> Cockroach Janta Party -> Cockroach
    Janata Party. Stopping after a single hop lands on a row that is itself dead."""
    if not await _db_reachable():
        pytest.skip("no database")
    from correlation.consumer import _follow_merge

    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with session_scope() as s:
        for eid, merged in ((c, None), (b, c), (a, b)):
            await s.execute(
                text("INSERT INTO entities (id, slug, name, entity_type, merged_into) "
                     "VALUES (:i, :sl, 'chain', 'organization', :m)"),
                {"i": eid, "sl": f"chain-{eid.hex[:8]}", "m": merged})
        try:
            assert await _follow_merge(s, a, b) == c
        finally:
            await s.execute(text("DELETE FROM entities WHERE id IN (:a,:b,:c)"),
                            {"a": a, "b": b, "c": c})


async def test_a_cycle_stops_instead_of_hanging_the_consumer():
    """A -> B -> A must terminate. This runs inside the correlation consumer, so a
    loop here stalls the whole pipeline rather than failing one article.

    HONEST LIMIT: this passes with the `seen` check removed too, because
    `range(_MAX_ENTITY_MERGE_HOPS)` already bounds the walk — the cycle guard makes
    it stop SOONER and on a more sensible row, not stop at all. The bound is what
    protects the consumer; the guard is defence in depth. Recorded so nobody reads
    this as pinning the guard."""
    if not await _db_reachable():
        pytest.skip("no database")
    from correlation.consumer import _follow_merge

    a, b = uuid.uuid4(), uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO entities (id, slug, name, entity_type) "
                             "VALUES (:i, :sl, 'cyc', 'organization')"),
                        {"i": a, "sl": f"cyc-{a.hex[:8]}"})
        await s.execute(text("INSERT INTO entities (id, slug, name, entity_type, merged_into) "
                             "VALUES (:i, :sl, 'cyc', 'organization', :m)"),
                        {"i": b, "sl": f"cyc-{b.hex[:8]}", "m": a})
        await s.execute(text("UPDATE entities SET merged_into = :m WHERE id = :i"),
                        {"m": b, "i": a})
        try:
            assert await _follow_merge(s, a, b) in (a, b)
        finally:
            await s.execute(text("UPDATE entities SET merged_into = NULL WHERE id IN (:a,:b)"),
                            {"a": a, "b": b})
            await s.execute(text("DELETE FROM entities WHERE id IN (:a,:b)"), {"a": a, "b": b})


async def test_the_ATTACH_path_follows_the_fold_not_just_the_read_path():
    """The production bug, driven through `_upsert_entities` itself.

    `_resolve_entity` followed the fold and was only used for impacts. The path
    that attaches every actor to every event looked the slug up and used whatever
    row it found — including one already merged away. Testing `_follow_merge` in
    isolation does NOT catch that: the helper was correct, the call site was
    missing. A mutation replacing the call with `existing[0]` passed every test
    until this one.
    """
    if not await _db_reachable():
        pytest.skip("no database")
    from correlation.consumer import _upsert_entities

    tag = uuid.uuid4().hex[:8]
    name = f"Zeta Variant {tag}"                     # slugifies to the folded row
    old_id, new_id, ev, art = (uuid.uuid4() for _ in range(4))
    from common.text import entity_slug

    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO entities (id, slug, name, entity_type) "
                 "VALUES (:i, :sl, :n, 'organization')"),
            {"i": new_id, "sl": f"zeta-canon-{tag}", "n": f"Zeta Canonical {tag}"})
        await s.execute(
            text("INSERT INTO entities (id, slug, name, entity_type, merged_into) "
                 "VALUES (:i, :sl, :n, 'organization', :m)"),
            {"i": old_id, "sl": entity_slug(name), "n": name, "m": new_id})
        await s.execute(
            text("INSERT INTO events (id, title, first_seen_at, last_updated_at) "
                 "VALUES (:i, 'attach test', '2019-01-01', '2019-01-01')"), {"i": ev})
        # article_entities has an FK to articles, so the row has to be real.
        src, raw = uuid.uuid4(), uuid.uuid4()
        await s.execute(
            text("INSERT INTO sources (id,slug,name,source_type) VALUES (:i,:s,:s,'rss')"),
            {"i": src, "s": f"attach-{tag}"})
        await s.execute(
            text("INSERT INTO raw_items (id,source_id,external_id,url,title,raw,relevance) "
                 "VALUES (:i,:s,:e,:u,'t','{}'::jsonb,'relevant')"),
            {"i": raw, "s": src, "e": f"ext-{tag}", "u": f"https://example.test/{tag}"})
        await s.execute(
            text("INSERT INTO articles (id,raw_item_id,clean_text,retrieval_tier,word_count) "
                 "VALUES (:i,:r,'body','body',1)"), {"i": art, "r": raw})
    try:
        async with session_scope() as s:
            await _upsert_entities(s, ev, [{"name": name, "type": "organization"}], art)
        async with session_scope() as s:
            landed = (await s.execute(
                text("SELECT entity_id FROM event_entities WHERE event_id = :e"), {"e": ev}
            )).scalars().all()
        assert landed == [new_id], (
            f"the mention attached to the FOLDED row {old_id} instead of {new_id} — "
            "canonicalization decays at ingest speed"
        )
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_entities WHERE event_id = :e"), {"e": ev})
            await s.execute(text("DELETE FROM article_entities WHERE entity_id IN (:a,:b)"),
                            {"a": old_id, "b": new_id})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": ev})
            await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": art})
            await s.execute(
                text("DELETE FROM raw_items WHERE url = :u"),
                {"u": f"https://example.test/{tag}"})
            await s.execute(text("DELETE FROM sources WHERE slug = :s"), {"s": f"attach-{tag}"})
            await s.execute(text("DELETE FROM entities WHERE id IN (:a,:b)"),
                            {"a": old_id, "b": new_id})
