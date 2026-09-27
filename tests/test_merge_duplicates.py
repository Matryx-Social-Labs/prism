"""Merging the duplicate backlog: one happening, one record, one address.

In shadow the verified tier recorded, for each article, the existing event Jev
judged it the same happening as (>= 0.85) — and the article founded its own
event anyway. correlation/merge.py folds those events into the one they copy:
members and every row that points at the absorbed event move to the survivor,
the absorbed row stays with `merged_into` set, every list stops serving it, and
its URL answers with a permanent redirect to the survivor.

The shared local database holds other tests' verdicts, so every test here
filters the plan down to the events it made.
"""

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common.db import session_scope
from correlation import merge
from correlation.consumer import _rebuild_projection

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _event(s, title: str, *, minutes_ago: int = 120) -> uuid.UUID:
    """An event founded `minutes_ago`, updated now: the newest-first lists put it
    on their first page. Never stamped in the future — the shared database keeps
    it, and a future stamp would crowd every later test's rows off those pages."""
    eid = uuid.uuid4()
    await s.execute(
        text("INSERT INTO events (id, title, headline_by, summary, sector, subject_path, regions, first_seen_at, last_updated_at) "
             "VALUES (:i, :t, 'prism', :t, 'politics', 'politics', ARRAY['IN'], now() - make_interval(mins => :m), now())"),
        {"i": str(eid), "t": title, "m": minutes_ago},
    )
    return eid


async def _member(s, event_id: uuid.UUID, *, tag: str, match_type: str = "new_event", minutes_ago: int = 0) -> uuid.UUID:
    """One article in an event, from its own outlet, as the consumer writes it."""
    src, raw, art = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await s.execute(text("INSERT INTO sources (id, slug, name, source_type) VALUES (:i, :s, :s, 'rss')"),
                    {"i": str(src), "s": f"m-{tag}-{src.hex[:6]}"})
    await s.execute(
        text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, relevance, published_at) "
             "VALUES (:i, :s, :x, :u, :t, '{}'::jsonb, 'relevant', now() - make_interval(mins => :m))"),
        {"i": str(raw), "s": str(src), "x": raw.hex, "u": f"https://x.example/{raw}", "t": f"report {tag}", "m": minutes_ago},
    )
    await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                         "VALUES (:i, :r, 'x', 'rss', 1)"), {"i": str(art), "r": str(raw)})
    await s.execute(text("INSERT INTO enrichments (id, article_id, summary, event_type) VALUES (:i, :a, :s, 'report')"),
                    {"i": str(uuid.uuid4()), "a": str(art), "s": f"summary {tag} {art.hex[:6]}"})
    await s.execute(
        text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
             "VALUES (:i, :e, :a, :mt, :f)"),
        {"i": str(uuid.uuid4()), "e": str(event_id), "a": str(art), "mt": match_type, "f": match_type == "new_event"},
    )
    return art


async def _verdict(s, article_id: uuid.UUID, event_id: uuid.UUID, noul: float, mode: str = "shadow") -> None:
    await s.execute(
        text("INSERT INTO event_match_verdicts (article_id, event_id, noul, gist_distance, model, mode) "
             "VALUES (:a, :e, :n, 0.05, 'test', :m)"),
        {"a": str(article_id), "e": str(event_id), "n": noul, "m": mode},
    )


async def _pair(tag: str, *, noul: float = 0.93) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """A survivor with its founder, and a later copy whose founder Jev judged
    the same happening in shadow. Returns (survivor, absorbed, copy's founder)."""
    async with session_scope() as s:
        survivor = await _event(s, f"Survivor {tag}")
        await _member(s, survivor, tag=tag, minutes_ago=90)
        absorbed = await _event(s, f"Copy {tag}", minutes_ago=30)
        founder = await _member(s, absorbed, tag=tag, minutes_ago=30)
        await _verdict(s, founder, survivor, noul)
    return survivor, absorbed, founder


async def _mine(*ids: uuid.UUID) -> tuple[dict, dict]:
    """The plan, cut down to this test's events: absorbed -> Merge / Skip."""
    async with session_scope() as s:
        merges, skips = await merge.plan(s)
    return ({m.absorbed: m for m in merges if m.absorbed in ids},
            {k.absorbed: k for k in skips if k.absorbed in ids})


async def _scalar(sql: str, **params):
    async with session_scope() as s:
        return (await s.execute(text(sql), {k: str(v) for k, v in params.items()})).scalar()


async def test_a_merge_moves_the_members_and_every_row_that_points_at_the_copy():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    survivor, absorbed, founder = await _pair(tag)
    run = uuid.uuid4()
    reader = uuid.uuid4()
    ent_both, ent_copy = uuid.uuid4(), uuid.uuid4()
    async with session_scope() as s:
        other = await _event(s, f"Unrelated {tag}")
        # A second member of the copy, attached by the LIVE tier against the
        # copy's own founder: judged the same happening, so it may travel.
        live = await _member(s, absorbed, tag=tag, match_type="verified", minutes_ago=10)
        await _verdict(s, live, absorbed, 0.91, mode="live")
        for eid, slug in ((ent_both, f"both-{tag}"), (ent_copy, f"copy-{tag}")):
            await s.execute(text("INSERT INTO entities (id, slug, name, entity_type) VALUES (:i, :s, :s, 'person')"),
                            {"i": str(eid), "s": slug})
        for ev, ent in ((survivor, ent_both), (absorbed, ent_both), (absorbed, ent_copy)):
            await s.execute(text("INSERT INTO event_entities (id, event_id, entity_id, role) VALUES (:i, :e, :n, 'subject')"),
                            {"i": str(uuid.uuid4()), "e": str(ev), "n": str(ent)})
        await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": str(reader), "e": f"{reader.hex}@t.example"})
        # The reader unlocked Markets on BOTH copies, and Cyber on the copy only.
        for ev, lens in ((survivor, "markets"), (absorbed, "markets"), (absorbed, "cyber")):
            await s.execute(text("INSERT INTO lens_unlocks (id, user_id, event_id, lens) VALUES (:i, :u, :e, :l)"),
                            {"i": str(uuid.uuid4()), "u": str(reader), "e": str(ev), "l": lens})
        await s.execute(text("INSERT INTO agent_sessions (id, event_id) VALUES (:i, :e)"),
                        {"i": str(uuid.uuid4()), "e": str(absorbed)})
        await s.execute(text("INSERT INTO event_links (id, from_event_id, to_event_id, relation) VALUES (:i, :a, :b, 'related')"),
                        {"i": str(uuid.uuid4()), "a": str(absorbed), "b": str(other)})
        # A link between the two copies would become a self-loop: it goes.
        await s.execute(text("INSERT INTO event_links (id, from_event_id, to_event_id, relation) VALUES (:i, :a, :b, 'related')"),
                        {"i": str(uuid.uuid4()), "a": str(survivor), "b": str(absorbed)})
        await s.execute(text("INSERT INTO claim_verdicts (event_id, speaker_key, card_hash, verdicts) VALUES (:e, 'k', 'h', '{}'::jsonb)"),
                        {"e": str(absorbed)})
        await s.execute(text("INSERT INTO perspectives (id, event_id, label) VALUES (:i, :e, 'copy framing')"),
                        {"i": str(uuid.uuid4()), "e": str(absorbed)})
        await s.execute(text("INSERT INTO partition_runs (id, status) VALUES (:i, 'superseded')"), {"i": str(run)})
        await s.execute(text("INSERT INTO event_story (run_id, event_id, story_label) VALUES (:r, :e, 7)"),
                        {"r": str(run), "e": str(absorbed)})
        await s.execute(
            text("INSERT INTO stories (id, slug, label, \"cast\", member_event_ids, hero_event_id) "
                 "VALUES (:i, :s, 'x', '[]'::jsonb, CAST(:m AS jsonb), :h)"),
            {"i": str(uuid.uuid4()), "s": f"story-{tag}", "m": json.dumps([str(absorbed), str(other), str(survivor)]),
             "h": str(absorbed)},
        )
    await _rebuild_projection(survivor)
    await _rebuild_projection(absorbed)

    merges, skips = await _mine(absorbed)
    assert absorbed not in skips, skips.get(absorbed)
    assert merges[absorbed].survivor == survivor
    assert await merge.apply(merges[absorbed]) is True

    assert await _scalar("SELECT merged_into FROM events WHERE id = :a", a=absorbed) == survivor
    assert await _scalar("SELECT count(*) FROM event_memberships WHERE event_id = :a", a=absorbed) == 0
    assert await _scalar("SELECT count(*) FROM event_memberships WHERE event_id = :s", s=survivor) == 3
    assert await _scalar("SELECT match_type FROM event_memberships WHERE article_id = :f", f=founder) == "merged"
    assert await _scalar("SELECT projection->>'source_count' FROM events WHERE id = :s", s=survivor) == "3"
    # Entities: the shared one once, the copy's own one carried over.
    assert await _scalar("SELECT count(*) FROM event_entities WHERE event_id = :s", s=survivor) == 2
    assert await _scalar("SELECT count(*) FROM event_entities WHERE event_id = :a", a=absorbed) == 0
    # Paid unlocks follow the record: every lens once, the one paid for twice included.
    assert await _scalar("SELECT string_agg(lens, ',' ORDER BY lens) FROM lens_unlocks WHERE event_id = :s AND user_id = :u",
                         s=survivor, u=reader) == "cyber,markets"
    assert await _scalar("SELECT count(*) FROM lens_unlocks WHERE event_id = :a", a=absorbed) == 0
    assert await _scalar("SELECT count(*) FROM agent_sessions WHERE event_id = :s", s=survivor) == 1
    assert await _scalar("SELECT count(*) FROM event_links WHERE from_event_id = :s AND to_event_id = :o", s=survivor, o=other) == 1
    assert await _scalar("SELECT count(*) FROM event_links WHERE :a IN (from_event_id, to_event_id) "
                         "OR (from_event_id = :s AND to_event_id = :s)", a=absorbed, s=survivor) == 0
    assert await _scalar("SELECT count(*) FROM claim_verdicts WHERE event_id = :s", s=survivor) == 1
    assert await _scalar("SELECT count(*) FROM perspectives WHERE event_id = :a", a=absorbed) == 0
    assert await _scalar("SELECT story_label FROM event_story WHERE run_id = :r AND event_id = :s", r=run, s=survivor) == 7
    story = await _scalar("SELECT jsonb_build_array(member_event_ids, hero_event_id) FROM stories WHERE slug = :t", t=f"story-{tag}")
    assert story == [[str(survivor), str(other)], str(survivor)]
    # The evidence stays where it was written.
    assert await _scalar("SELECT count(*) FROM event_match_verdicts WHERE article_id = :f", f=founder) == 1


async def test_star_resolution_points_every_copy_at_a_record_that_is_not_itself_a_copy():
    """B copies C, A copies B: A goes to C, never to B."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    async with session_scope() as s:
        c = await _event(s, f"C {tag}")
        await _member(s, c, tag=tag, minutes_ago=90)
        b = await _event(s, f"B {tag}", minutes_ago=60)
        await _verdict(s, await _member(s, b, tag=tag, minutes_ago=60), c, 0.9)
        a = await _event(s, f"A {tag}", minutes_ago=30)
        await _verdict(s, await _member(s, a, tag=tag, minutes_ago=30), b, 0.95)

    merges, _ = await _mine(a, b)
    assert {k: m.survivor for k, m in merges.items()} == {a: c, b: c}
    assert merges[a].via == b
    for m in sorted(merges.values(), key=lambda m: str(m.absorbed)):
        assert await merge.apply(m)
    assert await _scalar("SELECT count(*) FROM events WHERE id IN (:a, :b) AND merged_into = :c", a=a, b=b, c=c) == 2
    assert await _scalar("SELECT count(*) FROM event_memberships WHERE event_id = :c", c=c) == 3


async def test_a_later_run_repoints_what_an_earlier_run_merged_into_a_new_copy():
    """A was merged into B; B later turns out to copy C. A must end at C."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    async with session_scope() as s:
        c = await _event(s, f"C {tag}")
        await _member(s, c, tag=tag, minutes_ago=90)
        b = await _event(s, f"B {tag}", minutes_ago=60)
        b_founder = await _member(s, b, tag=tag, minutes_ago=60)
        a = await _event(s, f"A {tag}", minutes_ago=30)
        await _verdict(s, await _member(s, a, tag=tag, minutes_ago=30), b, 0.95)
    first, _ = await _mine(a)
    assert await merge.apply(first[a])
    async with session_scope() as s:
        await _verdict(s, b_founder, c, 0.9)
    second, _ = await _mine(a, b)
    assert set(second) == {b}
    assert await merge.apply(second[b])
    assert await _scalar("SELECT merged_into FROM events WHERE id = :a", a=a) == c


async def test_a_copy_holding_articles_nobody_judged_the_same_is_reported_not_merged():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    survivor, absorbed, _ = await _pair(tag)
    async with session_scope() as s:
        # Joined the copy on shared actors: never put to Jev.
        await _member(s, absorbed, tag=tag, match_type="entity_overlap", minutes_ago=5)
    merges, skips = await _mine(absorbed)
    assert absorbed not in merges
    assert skips[absorbed].candidate == survivor
    assert "entity_overlap" in skips[absorbed].reason

    # And apply refuses a pair whose copy changed after it was planned.
    stale = merge.Merge(absorbed=absorbed, survivor=survivor, noul=0.93, via=None)
    assert await merge.apply(stale) is False
    assert await _scalar("SELECT merged_into FROM events WHERE id = :a", a=absorbed) is None


async def test_below_the_floor_is_not_a_merge():
    if not await _db_reachable():
        pytest.skip("no database")
    _, absorbed, _ = await _pair(uuid.uuid4().hex[:8], noul=0.84)
    merges, skips = await _mine(absorbed)
    assert absorbed not in merges and absorbed not in skips


async def test_merging_twice_is_a_no_op():
    if not await _db_reachable():
        pytest.skip("no database")
    survivor, absorbed, _ = await _pair(uuid.uuid4().hex[:8])
    merges, _ = await _mine(absorbed)
    assert await merge.apply(merges[absorbed]) is True
    assert await merge.apply(merges[absorbed]) is False
    again, skips = await _mine(absorbed, survivor)
    assert again == {} and skips == {}
    assert await _scalar("SELECT count(*) FROM event_memberships WHERE event_id = :s", s=survivor) == 2


async def test_every_table_that_points_at_events_is_moved_or_deliberately_left():
    """A table added later that references events must be decided here, or a
    merge would silently strand its rows on the absorbed record."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        tables = set((await s.execute(text(
            "SELECT DISTINCT c.conrelid::regclass::text FROM pg_constraint c "
            "WHERE c.contype = 'f' AND c.confrelid = 'events'::regclass AND c.conrelid <> 'events'::regclass"
        ))).scalars())
    assert tables <= merge.HANDLED_TABLES, tables - merge.HANDLED_TABLES


async def test_merged_records_leave_every_list_and_their_address_redirects():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    survivor, absorbed, _ = await _pair(tag)
    ent = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("UPDATE events SET title = :t WHERE id IN (:a, :s)"),
                        {"t": f"Zyxwv{tag} bridge collapse", "a": str(absorbed), "s": str(survivor)})
        await s.execute(text("INSERT INTO entities (id, slug, name, entity_type) VALUES (:i, :s, :s, 'person')"),
                        {"i": str(ent), "s": f"cast-{tag}"})
        for ev in (survivor, absorbed):
            await s.execute(text("INSERT INTO event_entities (id, event_id, entity_id, role) VALUES (:i, :e, :n, 'subject')"),
                            {"i": str(uuid.uuid4()), "e": str(ev), "n": str(ent)})
    await _rebuild_projection(survivor)
    await _rebuild_projection(absorbed)
    async with session_scope() as s:
        # Served before the merge: two outlets, so the records sitemap offers it.
        await s.execute(text("UPDATE events SET projection = projection || CAST(:p AS jsonb), "
                             "last_updated_at = now() WHERE id = :a"),
                        {"p": json.dumps({"source_slugs": [f"a-{tag}", f"b-{tag}"]}), "a": str(absorbed)})

    async def listed(ac) -> dict[str, set[str]]:
        async def ids(url, key="items", **params):
            body = (await ac.get(url, params=params)).json()
            return {str(r.get("id")) for r in body[key]}
        return {
            "feed": await ids("/api/v1/feed", sector="politics", limit=100),
            "search": await ids("/api/v1/search", q=f"Zyxwv{tag}"),
            "subject": await ids("/api/v1/subject/politics", key="stories", limit=60),
            "entity": await ids(f"/api/v1/entity/cast-{tag}", key="records"),
            "sitemap": await ids("/api/v1/sitemap/records", key="records"),
        }

    # A redirect only means something if the list served the copy beforehand.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        before = await listed(ac)
    assert all(str(absorbed) in got for got in before.values()), before

    merges, _ = await _mine(absorbed)
    assert await merge.apply(merges[absorbed])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        after = await listed(ac)
        assert {k for k, got in after.items() if str(absorbed) in got} == set()
        assert str(survivor) in after["search"]

        r = await ac.get(f"/api/v1/events/{absorbed}")
        assert r.status_code == 308
        assert r.headers["location"] == f"/api/v1/events/{survivor}"
        r = await ac.get(f"/api/v1/events/{absorbed}/brief", params={"lens": "markets"})
        assert r.status_code == 308
        assert r.headers["location"] == f"/api/v1/events/{survivor}/brief?lens=markets"
        assert (await ac.get(f"/api/v1/events/{survivor}")).status_code == 200


async def test_a_new_article_never_matches_a_merged_record():
    """The absorbed row keeps its title and vector; the cascade must not hand
    new coverage to a record nobody can open."""
    if not await _db_reachable():
        pytest.skip("no database")
    from common.config import get_settings
    from correlation import clustering

    tag = uuid.uuid4().hex[:8]
    survivor, absorbed, _ = await _pair(tag)
    dim = get_settings().prism_embed_dim
    vec = [0.0] * dim
    vec[hash(tag) % dim] = 1.0
    async with session_scope() as s:
        await s.execute(text("UPDATE events SET title = :t, embedding = CAST(:v AS vector) WHERE id = :a"),
                        {"t": f"Qwrtp{tag} flood toll rises", "v": str(vec), "a": str(absorbed)})
    merges, _ = await _mine(absorbed)
    assert await merge.apply(merges[absorbed])
    async with session_scope() as s:
        by_title = await clustering._match_by_title(s, f"Qwrtp{tag} flood toll rises", None)
        by_vector = await clustering._match_by_embedding(s, vec, None)
    assert by_title is None or by_title.event_id != absorbed
    assert by_vector is None or by_vector.event_id != absorbed


async def test_the_story_partition_never_sees_a_merged_record():
    """The partition loads its window from the events table directly; a merged
    record there would be a member-less node the Leiden pass could still place."""
    if not await _db_reachable():
        pytest.skip("no database")
    from correlation.partition import _load_nodes, _window

    survivor, absorbed, _ = await _pair(uuid.uuid4().hex[:8])
    merges, _ = await _mine(absorbed)
    assert await merge.apply(merges[absorbed])
    async with session_scope() as s:
        nodes = await _load_nodes(s)
    assert str(survivor) in nodes and str(absorbed) not in nodes
    assert _window("last_updated_at").endswith(" AND merged_into IS NULL")
