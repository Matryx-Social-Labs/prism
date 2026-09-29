"""tools/repair_attaches: a follow-up the entity tier swept into a record leaves it,
founds its own record at the time it first arrived, and is linked back as a later
development — and the record it left is put back as it was without it."""

import datetime as dt
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text

import correlation.verify as verify
from common.config import get_settings
from common.db import session_scope
from common.decisions import Decisions, NoulAnswer
from tests.test_verified_tier import _db_reachable
from tools import repair_attaches

pytestmark = pytest.mark.asyncio(loop_scope="session")

WHEN = dt.datetime.now(dt.UTC) - dt.timedelta(days=60)  # out of the feed's way (test_geo)
FOUNDER = "Father demands arrests in IIT-Bombay suicide case"
FOLLOW_UP = "Father demands arrests in IIT-Bombay suicide case, parents begin hunger strike"


async def _article(s, *, source, title, image, entity=None):
    rid, aid = uuid.uuid4(), uuid.uuid4()
    await s.execute(
        text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, relevance, published_at, image_url) "
             "VALUES (:i, :s, :x, :u, :t, '{}'::jsonb, 'relevant', :w, :img)"),
        {"i": str(rid), "s": str(source), "x": rid.hex, "u": f"https://repair.test/{rid}", "t": title, "w": WHEN, "img": image},
    )
    await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                         "VALUES (:i, :r, :t, 'direct', 9)"), {"i": str(aid), "r": str(rid), "t": title})
    await s.execute(text("INSERT INTO enrichments (id, article_id, summary, event_type, shared_fields) "
                         "VALUES (:i, :a, :t, 'report', '{}'::jsonb)"), {"i": str(uuid.uuid4()), "a": str(aid), "t": title})
    if entity:
        await s.execute(text("INSERT INTO article_entities (id, article_id, entity_id, role) VALUES (:i, :a, :e, 'actor')"),
                        {"i": str(uuid.uuid4()), "a": str(aid), "e": str(entity)})
    return aid


@pytest_asyncio.fixture(loop_scope="session")
async def swept():
    """A record and the follow-up the entity tier swept into it, with the image
    and an actor that came only with the follow-up."""
    if not await _db_reachable():
        pytest.skip("no database")
    src, event, actor = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO sources (id, slug, name, source_type) VALUES (:i, :s, :s, 'rss')"),
                        {"i": str(src), "s": f"repair-{src.hex[:8]}"})
        await s.execute(text("INSERT INTO entities (id, slug, name, entity_type) VALUES (:i, :s, :s, 'person')"),
                        {"i": str(actor), "s": f"hunger-striker-{actor.hex[:6]}"})
        await s.execute(
            text("INSERT INTO events (id, title, summary, sector, first_seen_at, last_updated_at, image_url) "
                 "VALUES (:i, :t, :t, 'civic', :w, :w, 'https://img.test/follow-up.jpg')"),
            {"i": str(event), "t": FOUNDER, "w": WHEN},
        )
        founder = await _article(s, source=src, title=FOUNDER, image=None)
        follow = await _article(s, source=src, title=FOLLOW_UP, image="https://img.test/follow-up.jpg", entity=actor)
        membership = uuid.uuid4()
        await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor, created_at) "
                             "VALUES (:m, :e, :f, 'new_event', true, :w), (:i, :e, :a, 'entity_overlap', false, :w)"),
                        {"m": str(uuid.uuid4()), "i": str(membership), "e": str(event), "f": str(founder),
                         "a": str(follow), "w": WHEN})
        await s.execute(text("INSERT INTO event_entities (id, event_id, entity_id, role) VALUES (:i, :e, :n, 'actor')"),
                        {"i": str(uuid.uuid4()), "e": str(event), "n": str(actor)})
    row = {"membership": membership, "event_id": event, "article_id": follow, "attached_at": WHEN}
    yield row, src, actor
    async with session_scope() as s:
        events = [str(e) for e in (await s.execute(
            text("SELECT DISTINCT event_id FROM event_memberships WHERE article_id = ANY(CAST(:a AS uuid[]))"),
            {"a": [str(founder), str(follow)]})).scalars().all()] + [str(event)]
        await s.execute(text("DELETE FROM event_links WHERE to_event_id = ANY(CAST(:e AS uuid[])) "
                             "OR from_event_id = ANY(CAST(:e AS uuid[]))"), {"e": events})
        await s.execute(text("DELETE FROM event_match_verdicts WHERE article_id = :a"), {"a": str(follow)})
        await s.execute(text("DELETE FROM event_memberships WHERE event_id = ANY(CAST(:e AS uuid[]))"), {"e": events})
        await s.execute(text("DELETE FROM event_entities WHERE event_id = ANY(CAST(:e AS uuid[]))"), {"e": events})
        await s.execute(text("DELETE FROM article_entities WHERE entity_id = :n"), {"n": str(actor)})
        await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"), {"e": events})
        await s.execute(text("DELETE FROM enrichments WHERE article_id = ANY(CAST(:a AS uuid[]))"), {"a": [str(founder), str(follow)]})
        await s.execute(text("DELETE FROM articles WHERE id = ANY(CAST(:a AS uuid[]))"), {"a": [str(founder), str(follow)]})
        await s.execute(text("DELETE FROM raw_items WHERE source_id = :s"), {"s": str(src)})
        await s.execute(text("DELETE FROM sources WHERE id = :s"), {"s": str(src)})
        await s.execute(text("DELETE FROM entities WHERE id = :n"), {"n": str(actor)})


async def test_a_swept_in_follow_up_founds_its_own_record_linked_back(monkeypatch, swept):
    row, _, actor = swept
    monkeypatch.setattr(get_settings(), "prism_event_verify", "confirm")

    async def jev(state, questions, **_):  # the record's founder: not the same happening, a later development
        return Decisions(answers={k: NoulAnswer(noul=0.1 if k.startswith("same") else 0.92) for k in questions},
                         model="typesafe/jev-test")

    monkeypatch.setattr(verify, "decide", jev)
    landed, founded = await repair_attaches.move(row, 0.1, 0.92)
    assert founded and landed != row["event_id"]

    async with session_scope() as s:
        new = (await s.execute(text("SELECT first_seen_at, last_updated_at FROM events WHERE id = :e"),
                               {"e": str(landed)})).one()
        assert new.first_seen_at == WHEN and new.last_updated_at == WHEN, "a repaired record is not news"
        joined = (await s.execute(text("SELECT created_at FROM event_memberships WHERE article_id = :a"),
                                  {"a": str(row["article_id"])})).scalar_one()
        assert joined == WHEN, "trending counts a membership's created_at as recent coverage"
        link = (await s.execute(text("SELECT method FROM event_links WHERE from_event_id = :f AND to_event_id = :t"),
                                {"f": str(row["event_id"]), "t": str(landed)})).scalar_one()
        assert link == "verified"
        left = (await s.execute(text("SELECT image_url FROM events WHERE id = :e"), {"e": str(row["event_id"])})).scalar_one()
        assert left is None, "the image came with the follow-up and left with it"
        actors = (await s.execute(text("SELECT count(*) FROM event_entities WHERE event_id = :e AND entity_id = :n"),
                                  {"e": str(row["event_id"]), "n": str(actor)})).scalar_one()
        assert actors == 0
        same = (await s.execute(text("SELECT noul FROM event_match_verdicts WHERE article_id = :a AND event_id = :e"),
                                {"a": str(row["article_id"]), "e": str(row["event_id"])})).scalar_one()
        assert same < get_settings().prism_event_verify_min, "why it left is on record"

    assert await repair_attaches.move(row, 0.1, 0.92) is None, "idempotent: a moved membership is not moved twice"


async def test_bands_read_like_the_verifier():
    assert [repair_attaches.band(p) for p in (0.9, 0.85, 0.6, 0.2, 0.05)] == [
        "same", "same", "likely same", "likely different", "different"]
