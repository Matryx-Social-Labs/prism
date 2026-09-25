"""Search route over HTTP — keyword match on title/summary, recency order.

Drives the real FastAPI app via httpx/ASGITransport against a live Postgres.
Skips without a database.
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


async def _seed(title: str, summary: str, sector: str) -> uuid.UUID:
    eid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO events (id, title, summary, sector) VALUES (:i, :t, :s, :sec)"),
            {"i": str(eid), "t": title, "s": summary, "sec": sector},
        )
    return eid


async def test_search_matches_title_and_summary():
    if not await _db_reachable():
        pytest.skip("no database — run `docker compose up -d postgres`")
    tag = uuid.uuid4().hex[:8]
    e_title = await _seed(f"Zephyron-{tag} raises Series B", "Funding news", "business")
    e_summary = await _seed("A quiet day in markets", f"analysts cite Zephyron-{tag} exposure", "finance")
    e_miss = await _seed("Unrelated cricket result", "no keyword here", "sports")
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            # too-short query is rejected by validation
            assert (await ac.get("/api/v1/search", params={"q": "a"})).status_code == 422

            got = {i["id"] for i in (await ac.get("/api/v1/search", params={"q": tag})).json()["items"]}
            assert str(e_title) in got  # matched in title
            assert str(e_summary) in got  # matched in summary
            assert str(e_miss) not in got  # no keyword → excluded

            # empty result set is a clean empty list, not an error
            assert (await ac.get("/api/v1/search", params={"q": "zzz-no-such-" + tag})).json()["items"] == []
    finally:
        async with session_scope() as s:
            await s.execute(
                text("DELETE FROM events WHERE id = ANY(:ids)"),
                {"ids": [str(e_title), str(e_summary), str(e_miss)]},
            )


# --- the index that keeps this route off a full table scan ----------------------
# Measured on production before migration c8a3f5d21b74: Seq Scan, ~100ms per query
# over 19,356 events, growing linearly. The route's leading-wildcard ILIKE cannot
# use a btree, so it needs GIN over trigrams.
#
# This asserts the SCHEMA rather than a query plan on purpose. The local test
# database holds a couple of hundred rows, where Postgres correctly prefers a
# sequential scan whatever indexes exist — so an EXPLAIN assertion here would fail
# for a reason that has nothing to do with the thing being tested.


async def test_search_columns_have_trigram_indexes():
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        rows = await s.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'events' AND indexdef ILIKE '%gin_trgm_ops%'"
            )
        )
        defs = " ".join(r[0] for r in rows.all())
    assert "title" in defs, "events.title has no trigram index; search full-scans"
    assert "summary" in defs, "events.summary has no trigram index; search full-scans"


async def test_search_still_matches_inside_a_word():
    """Substring semantics are the reason this used ILIKE and not tsvector. A
    lexeme index would quietly stop matching mid-word, which is a product change,
    not a performance one — so it is pinned here."""
    if not await _db_reachable():
        pytest.skip("no database")
    token = uuid.uuid4().hex[:10]
    await _seed(f"Prefix{token}Suffix headline", "body", "politics")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.get("/api/v1/search", params={"q": token})
    assert r.status_code == 200
    assert any(token in i["title"] for i in r.json()["items"]), (
        "a mid-word substring stopped matching — search semantics changed"
    )


# --- the names the search page offers --------------------------------------------
# The start screen offers "In the news now": the cast of the trending stories. A
# cast name need not appear in any headline or summary — on 2026-09-25, 4 of the 6
# names offered ("Nanavati Hospital", "Mahesh Bhatt", …) returned no records.


async def _cast(event_id: uuid.UUID, name: str) -> None:
    async with session_scope() as s:
        ent_id = (await s.execute(
            text("INSERT INTO entities (id, slug, name, entity_type) VALUES (:i, :s, :n, 'organization') RETURNING id"),
            {"i": str(uuid.uuid4()), "s": name.lower().replace(" ", "-"), "n": name},
        )).scalar_one()
        await s.execute(
            text("INSERT INTO event_entities (id, event_id, entity_id, role) VALUES (:i, :e, :n, 'subject')"),
            {"i": str(uuid.uuid4()), "e": str(event_id), "n": str(ent_id)},
        )


async def test_search_finds_a_record_by_a_name_in_its_cast_only():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    eid = await _seed("Actor dies at 56 after cancer battle", "The actor died in Mumbai.", "entertainment")
    await _cast(eid, f"Nanavati{tag} Hospital")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        got = {i["id"] for i in (await ac.get("/api/v1/search", params={"q": f"Nanavati{tag} Hospital"})).json()["items"]}
    assert str(eid) in got, "a name in the record's cast found nothing — the search chips go blank"


# --- the row's photograph is never an outlet's fallback art -----------------------
# REGRESSION: the feed filtered placeholder photos and search did not, so a search
# row showed Prajavani's `prajavani_fallback_image.webp` — a logo on 141 reports —
# that the opened story (which filters) did not show.


async def _report(event_id: uuid.UUID, image_url: str, url: str, first: bool = False) -> None:
    from datetime import UTC, datetime

    async with session_scope() as s:
        src_id = (await s.execute(
            text("INSERT INTO sources (id, slug, name, source_type, country) VALUES (:i, :s, 't', 'rss', 'IN') RETURNING id"),
            {"i": str(uuid.uuid4()), "s": f"t-{uuid.uuid4().hex[:8]}"},
        )).scalar_one()
        raw_id = (await s.execute(
            text("INSERT INTO raw_items (id, source_id, external_id, url, title, body, observed_at, raw, relevance, image_url) "
                 "VALUES (:i, :src, :x, :u, 't', 'b', :now, '{}', 'relevant', :img) RETURNING id"),
            {"i": str(uuid.uuid4()), "src": str(src_id), "x": uuid.uuid4().hex, "u": url, "now": datetime.now(UTC), "img": image_url},
        )).scalar_one()
        art_id = (await s.execute(
            text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) VALUES (:i, :r, 'x', 'direct', 1) RETURNING id"),
            {"i": str(uuid.uuid4()), "r": str(raw_id)},
        )).scalar_one()
        await s.execute(
            text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) VALUES (:i, :e, :a, 'new_event', :f)"),
            {"i": str(uuid.uuid4()), "e": str(event_id), "a": str(art_id), "f": first},
        )
        if first:
            await s.execute(text("UPDATE events SET image_url = :img WHERE id = :e"), {"img": image_url, "e": str(event_id)})


async def test_search_never_shows_a_fallback_image_as_the_rows_photo():
    if not await _db_reachable():
        pytest.skip("no database")
    from common import images

    images._placeholders = (0.0, frozenset())  # the set is cached for five minutes
    tag = uuid.uuid4().hex[:8]
    fallback = f"https://media.example/{tag}/fallback_image.webp"
    own = f"https://media.example/{tag}/the-match.jpg"
    # The fallback sits on four DIFFERENT articles (no hash: the fetch failed, as
    # for 16% of reports), so it is furniture; the story's own photo is on one.
    hit = await _seed(f"Hockey{tag} team records big win", "India beat Sri Lanka", "sports")
    await _report(hit, fallback, f"https://news.example/{tag}/0", first=True)
    for n in range(1, 4):
        other = await _seed(f"Unrelated {tag} {n}", "x", "sports")
        await _report(other, fallback, f"https://news.example/{tag}/{n}", first=True)
    real = await _seed(f"Hockey{tag} semifinal preview", "x", "sports")
    await _report(real, own, f"https://news.example/{tag}/own", first=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        rows = {i["id"]: i for i in (await ac.get("/api/v1/search", params={"q": f"Hockey{tag}"})).json()["items"]}
    assert rows[str(hit)]["image_url"] is None, "the outlet's fallback art was served as the story's photo"
    assert rows[str(real)]["image_url"] == own, "a story's own photograph must still show"
