"""P0-3: "What <name> said" on the entity page.

A quote is the entity's only when its speaker, punctuation and spaces folded
away, IS the entity's name or a many-word alias: "D.K. Shivakumar" is
dk-shivakumar; a bare "Reddy" is nobody's. And nothing is printed that the
record's own story page would not print: the checks are group_claims's.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from api.routes.entity import _quoted_records, entity_quotes, speaker_keys
from common.db import session_scope

QUOTE = "We will complete the metro line to the airport by next year."
UNQUOTED = "the metro line will be finished before the monsoon"
INVENTED = "We have never promised anything to the people of Bengaluru."
BODY = (
    f"Bengaluru: Deputy Chief Minister D.K. Shivakumar said, “{QUOTE}” "
    f"Officials said {UNQUOTED}. The opposition disagreed."
)
REDDY_QUOTE = "The farmers of this district will get their water this season."
REDDY_BODY = f"Nalgonda: Reddy told reporters, “{REDDY_QUOTE}” The meeting ended at noon."
PUBLISHED = datetime(2026, 9, 24, 6, 0, tzinfo=UTC)


def _row(body: str, claims: list[dict], article: str = "a1") -> dict:
    return {"article_id": article, "source_name": "Deccan Herald", "url": f"https://dh.test/{article}",
            "url_canonical": None, "published_at": PUBLISHED, "lang": "en", "claims": claims, "clean_text": body}


def _claim(speaker: str, quote: str) -> dict:
    return {"speaker": speaker, "quote_text": quote}


def test_dotted_initials_are_the_same_person_as_the_entity():
    keys = speaker_keys("DK Shivakumar", [])
    quotes, _ = entity_quotes([("e1", "Metro", [_row(BODY, [_claim("D.K. Shivakumar", QUOTE)])])], keys)
    assert [q.quote_text for q in quotes] == [QUOTE]
    assert quotes[0].event_id == "e1" and quotes[0].source_index == 1


def test_a_surname_alone_never_matches():
    keys = speaker_keys("Chinna Reddy", ["Reddy"])
    assert keys == {"chinnareddy"}, "a one-word alias of a longer name is a surname, never a match"
    quotes, _ = entity_quotes([("e1", "Water", [_row(REDDY_BODY, [_claim("Reddy", REDDY_QUOTE)])])], keys)
    assert quotes == []


def test_a_quote_the_article_does_not_hold_in_quotation_marks_is_dropped():
    claims = [_claim("D.K. Shivakumar", QUOTE), _claim("D.K. Shivakumar", UNQUOTED), _claim("D.K. Shivakumar", INVENTED)]
    quotes, _ = entity_quotes([("e1", "Metro", [_row(BODY, claims)])], speaker_keys("DK Shivakumar", []))
    assert [q.quote_text for q in quotes] == [QUOTE]


def test_the_same_words_on_two_records_are_one_quote_newest_record_kept():
    row = _row(BODY, [_claim("D.K. Shivakumar", QUOTE)])
    quotes, _ = entity_quotes([("new", "Metro", [row]), ("old", "Metro again", [{**row, "article_id": "a2"}])],
                              speaker_keys("DK Shivakumar", []))
    assert [q.event_id for q in quotes] == ["new"]


# ── Through the route: the SQL pre-filter, the counts, and the empty case ──

async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


# Out of the feed's window: the shared test database serves the feed tests too.
_LONG_AGO = datetime.now(UTC) - timedelta(days=60)


async def _seed(name: str, body: str, claims: list[dict]) -> str:
    """An entity named `name` on one served record with one English article."""
    slug, event, raw_item, article = f"t-{uuid.uuid4().hex[:10]}", uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with session_scope() as s:
        source = (await s.execute(
            text("INSERT INTO sources (id, slug, name, source_type) VALUES (gen_random_uuid(), :s, 'Deccan Herald', 'rss') RETURNING id"),
            {"s": slug})).scalar_one()
        await s.execute(text("INSERT INTO entities (id, slug, name, entity_type) VALUES (gen_random_uuid(), :s, :n, 'person')"),
                        {"s": slug, "n": name})
        await s.execute(
            text("INSERT INTO events (id, title, sector, regions, last_updated_at, projection) "
                 "VALUES (:i, 'Metro', 'politics', ARRAY['IN'], :at, CAST(:p AS jsonb))"),
            {"i": str(event), "at": _LONG_AGO, "p": json.dumps({"source_slugs": ["the_hindu"]})})
        await s.execute(
            text("INSERT INTO event_entities (id, event_id, entity_id, role) "
                 "SELECT gen_random_uuid(), :e, id, 'subject' FROM entities WHERE slug = :s"),
            {"e": str(event), "s": slug})
        await s.execute(
            text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, relevance, language, published_at) "
                 "VALUES (:i, :s, :x, :u, 't', '{}'::jsonb, 'relevant', 'en', :p)"),
            {"i": str(raw_item), "s": str(source), "x": raw_item.hex, "u": f"https://dh.test/{raw_item.hex}", "p": PUBLISHED})
        await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                             "VALUES (:i, :r, :t, 'direct', 30)"), {"i": str(article), "r": str(raw_item), "t": body})
        await s.execute(
            text("INSERT INTO enrichments (id, article_id, event_type, summary, sentiment, shared_fields, lens_fields, "
                 "raw_model_output, model) VALUES (gen_random_uuid(), :a, 'other', 's', 0, CAST(:sf AS jsonb), "
                 "'{}'::jsonb, '{}'::jsonb, 'test')"),
            {"a": str(article), "sf": json.dumps({"claims": claims})})
        await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
                             "VALUES (gen_random_uuid(), :e, :a, 'new_event', true)"), {"e": str(event), "a": str(article)})
    return slug


async def _get(slug: str) -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/api/v1/entity/{slug}")
    assert r.status_code == 200
    return r.json()


async def test_the_entity_page_carries_its_checked_quotes():
    if not await _db_reachable():
        pytest.skip("no database")
    role = {"speaker_role": "Deputy Chief Minister"}  # stored by faithful_role, the article's own words
    slug = await _seed("DK Shivakumar", BODY, [{**_claim("D.K. Shivakumar", QUOTE), **role}, _claim("D.K. Shivakumar", INVENTED)])
    body = await _get(slug)
    assert [q["quote_text"] for q in body["quotes"]] == [QUOTE]
    assert (body["quote_count"], body["reported_count"], body["quoted_records"], body["quotes_window"]) == (1, 0, 1, 1)
    assert body["quotes"][0]["source_index"] == 1 and body["quotes"][0]["event_title"] == "Metro"
    assert body["role"] == "Deputy Chief Minister"


async def test_the_sql_filter_never_reads_a_record_for_a_surname():
    if not await _db_reachable():
        pytest.skip("no database")
    slug = await _seed("Chinna Reddy", REDDY_BODY, [_claim("Reddy", REDDY_QUOTE)])
    async with session_scope() as s:
        ent = (await s.execute(text("SELECT id, name FROM entities WHERE slug = :s"), {"s": slug})).mappings().one()
        assert await _quoted_records(s, ent["id"], speaker_keys(ent["name"], [])) == []
    assert (await _get(slug))["quotes"] == []


async def test_no_checked_quote_is_an_empty_section():
    """The speaker is theirs, the words are not in the article's quotation marks:
    nothing to print, and every count says so."""
    if not await _db_reachable():
        pytest.skip("no database")
    slug = await _seed("DK Shivakumar", BODY, [_claim("D.K. Shivakumar", INVENTED), _claim("D.K. Shivakumar", UNQUOTED)])
    body = await _get(slug)
    assert body["quotes"] == []
    assert (body["quote_count"], body["reported_count"], body["quoted_records"]) == (0, 0, 0)
    assert body["role"] is None
