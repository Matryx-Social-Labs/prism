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


async def _add_member(s, event_id, *, title, summary, source_id, minutes_ago=0):
    """One article joining an event, as the correlation consumer writes it.

    `minutes_ago` is not decoration. Without it every member inserted in one
    transaction shares a published_at AND a created_at — Postgres evaluates now()
    at transaction start — so nothing ordered them and this test asserted on a
    coin flip. It failed 5/5 on one run and passed 5/5 on another with no code
    change between.
    """
    raw_id, art_id = uuid.uuid4(), uuid.uuid4()
    await s.execute(
        text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, "
             "relevance, published_at) "
             "VALUES (:i, :s, :x, :u, :t, '{}'::jsonb, 'relevant', "
             "now() - make_interval(mins => :m))"),
        {"i": str(raw_id), "s": str(source_id), "x": str(raw_id), "u": f"http://x/{raw_id}",
         "t": title, "m": minutes_ago},
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
                minutes_ago=120,  # the founder: oldest article
                title="AAIB explains to SC why the crash report is delayed",
                summary="Aircraft Accident Investigation Bureau informs the Supreme Court.",
                source_id=src))
            # A later member. In production this was a WRONG merge sharing only
            # the entity "Supreme Court", but the bug does not need a wrong merge
            # — any later member with different content produced the mismatch.
            created.append(await _add_member(
                s, eid,
                minutes_ago=5,  # a later member
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


async def test_single_origin_means_one_masthead_not_one_country():
    """"Single-origin" warns a reader that only one newsroom is carrying this and
    nobody has corroborated it. It was computed as `len(origins) == 1` where
    origins are source COUNTRIES, so on an India-first feed it fired on 97% of
    multi-article events (1,039 of 1,070) — a warning on almost everything, which
    is a warning about nothing.

    Two same-country outlets covering one story is exactly the corroboration the
    flag exists to say is MISSING, so it must not fire there.
    """
    if not await _db_reachable():
        pytest.skip("no database")

    eid = uuid.uuid4()
    src_a, src_b = uuid.uuid4(), uuid.uuid4()
    created = []
    try:
        async with session_scope() as s:
            # Two DIFFERENT mastheads, same country.
            for sid, slug, pub in ((src_a, "a", "Alpha Times"), (src_b, "b", "Beta Herald")):
                await s.execute(
                    text("INSERT INTO sources (id, slug, name, source_type, country, publisher) "
                         "VALUES (:i, :s, :n, 'rss', 'IN', :p)"),
                    {"i": str(sid), "s": f"{slug}-{eid.hex[:8]}", "n": pub, "p": pub},
                )
            await s.execute(
                text("INSERT INTO events (id, title, summary, sector, regions, last_updated_at) "
                     "VALUES (:i, :t, :su, 'politics', CAST(:r AS text[]), now())"),
                {"i": str(eid), "t": "Flood relief operations begin",
                 "su": "Relief operations began.", "r": ["IN"]},
            )
            created.append(await _add_member(
                s, eid, title="Flood relief operations begin",
                summary="Relief operations began.", source_id=src_a))
            created.append(await _add_member(
                s, eid, title="Relief teams deployed after flooding",
                summary="Teams were deployed.", source_id=src_b))

        await _rebuild_projection(eid)
        async with session_scope() as s:
            proj = (await s.execute(
                text("SELECT projection FROM events WHERE id = :i"), {"i": str(eid)}
            )).scalar_one()

        cov = proj["coverage"]
        assert cov["single_origin"] is False, (
            "two independent mastheads corroborate each other — flagging this "
            "single-origin is what made the warning fire on 97% of stories"
        )
        # The country breakdown is still reported; it just no longer drives the flag.
        assert cov["origins"] == {"IN": 2}
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": str(eid)})
            for raw_id, art_id in created:
                await s.execute(text("DELETE FROM enrichments WHERE article_id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM raw_items WHERE id = :r"), {"r": str(raw_id)})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})
            await s.execute(text("DELETE FROM sources WHERE id = ANY(:ids)"),
                            {"ids": [str(src_a), str(src_b)]})


async def test_single_origin_DOES_fire_for_one_masthead_across_its_own_feeds():
    """The counterpart, and the reason this counts publishers rather than source
    slugs: The Hindu syndicates one story across six regional feeds. Six slugs,
    one newsroom, no corroboration — the flag must still fire."""
    if not await _db_reachable():
        pytest.skip("no database")

    eid = uuid.uuid4()
    src_a, src_b = uuid.uuid4(), uuid.uuid4()
    created = []
    try:
        async with session_scope() as s:
            # Two feeds, ONE publisher — the thehindu / thehindu_kerala shape.
            for sid, slug in ((src_a, "main"), (src_b, "kerala")):
                await s.execute(
                    text("INSERT INTO sources (id, slug, name, source_type, country, publisher) "
                         "VALUES (:i, :s, :n, 'rss', 'IN', 'One Masthead')"),
                    {"i": str(sid), "s": f"{slug}-{eid.hex[:8]}", "n": slug},
                )
            await s.execute(
                text("INSERT INTO events (id, title, summary, sector, regions, last_updated_at) "
                     "VALUES (:i, :t, :su, 'politics', CAST(:r AS text[]), now())"),
                {"i": str(eid), "t": "Only one newsroom has this",
                 "su": "A single newsroom reported it.", "r": ["IN"]},
            )
            created.append(await _add_member(
                s, eid, title="Only one newsroom has this",
                summary="A single newsroom reported it.", source_id=src_a))
            created.append(await _add_member(
                s, eid, title="Only one newsroom has this (regional edition)",
                summary="A single newsroom reported it.", source_id=src_b))

        await _rebuild_projection(eid)
        async with session_scope() as s:
            proj = (await s.execute(
                text("SELECT projection FROM events WHERE id = :i"), {"i": str(eid)}
            )).scalar_one()

        assert proj["coverage"]["single_origin"] is True, (
            "two feeds of the same masthead are not corroboration"
        )
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": str(eid)})
            for raw_id, art_id in created:
                await s.execute(text("DELETE FROM enrichments WHERE article_id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM raw_items WHERE id = :r"), {"r": str(raw_id)})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})
            await s.execute(text("DELETE FROM sources WHERE id = ANY(:ids)"),
                            {"ids": [str(src_a), str(src_b)]})


def test_the_member_ordering_has_a_deterministic_tiebreaker():
    """`ORDER BY em.created_at` alone is not a total order, and the tie is real.

    created_at defaults to now(), which Postgres evaluates at TRANSACTION start,
    so every member written in one transaction shares a timestamp exactly.
    event_memberships.id is a uuid4 and orders nothing. summaries[0] is what
    becomes the event summary, so an unstable sort silently swaps in a later
    member's summary and reintroduces the headline/summary mismatch #135 fixed.

    This is a SOURCE assertion rather than a behavioural one, deliberately. The
    behavioural test above passes with the tiebreaker removed — on a small table
    Postgres returns heap order, which happens to be insertion order — so it
    cannot detect the bug. Asserting the query shape can. Same reasoning as
    test_the_model_column_is_not_hardcoded_to_a_provider.

    (This test was itself flaky before the fix: it inserted both members with
    published_at = now() inside one transaction, so nothing ordered them and it
    asserted on a coin flip — 5/5 failures on one run, 5/5 passes on another,
    with no code change in between.)
    """
    import inspect

    import correlation.consumer as mod

    src = inspect.getsource(mod)
    assert "ORDER BY em.created_at\n" not in src, (
        "member ordering must not rely on created_at alone — it ties inside a transaction"
    )
    assert src.count("ORDER BY em.created_at, ri.published_at NULLS LAST, a.id") == 2, (
        "both member queries need the same deterministic order"
    )
