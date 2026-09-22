"""Audit C3/C4: one event per article is a constraint, match-or-create is
serialised on the database, and a replayed message resumes the work a crash
left undone instead of returning."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from common.db import session_scope
from common.models import Article, Enrichment, Event, EventMembership, RawItem, Source
from correlation import consumer


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _seed_article(title: str) -> tuple[uuid.UUID, uuid.UUID]:
    async with session_scope() as s:
        src = Source(id=uuid.uuid4(), slug=f"t-{uuid.uuid4().hex[:8]}", name="t", source_type="rss", country="IN")
        s.add(src)
        await s.flush()
        raw = RawItem(id=uuid.uuid4(), source_id=src.id, external_id=uuid.uuid4().hex, title=title, body="b",
                      observed_at=datetime.now(UTC), raw={}, relevance="relevant",
                      classification={"sector": "politics", "regions": ["IN"]})
        s.add(raw)
        await s.flush()
        art = Article(id=uuid.uuid4(), raw_item_id=raw.id, clean_text="body text " * 30, word_count=60)
        s.add(art)
        await s.flush()
        enr = Enrichment(id=uuid.uuid4(), article_id=art.id, summary="s", shared_fields={"entities": []},
                         lens_fields={}, model="test")
        s.add(enr)
        return art.id, enr.id


async def test_the_database_refuses_an_article_in_two_events():
    if not await _db_reachable():
        pytest.skip("no database")
    article_id, _ = await _seed_article("two events")
    async with session_scope() as s:
        a, b = Event(id=uuid.uuid4(), title="a", sector="politics"), Event(id=uuid.uuid4(), title="b", sector="politics")
        s.add_all([a, b])
        await s.flush()
        s.add(EventMembership(event_id=a.id, article_id=article_id, match_type="new_event"))
        await s.flush()
        s.add(EventMembership(event_id=b.id, article_id=article_id, match_type="entity"))
        with pytest.raises(IntegrityError, match="uq_event_memberships_article"):
            await s.flush()
        await s.rollback()


async def test_a_replayed_message_resumes_instead_of_returning(monkeypatch):
    """First delivery attaches; a redelivery (the stream's answer to any failure
    after the first commit) must not match again but must still rebuild the
    projection and mark the analysis."""
    if not await _db_reachable():
        pytest.skip("no database")
    article_id, enrichment_id = await _seed_article("resume me")
    calls = {"match": 0, "rebuild": 0, "dirty": 0}

    async def rebuild(event_id):
        calls["rebuild"] += 1

    async def dirty(event_id):
        calls["dirty"] += 1

    real_attach = consumer._attach

    async def counting_attach(*a, **k):
        calls["match"] += 1
        return await real_attach(*a, **k)

    monkeypatch.setattr(consumer, "_rebuild_projection", rebuild)
    monkeypatch.setattr(consumer, "mark_event_dirty", dirty)
    monkeypatch.setattr(consumer, "_attach", counting_attach)
    monkeypatch.setattr(consumer, "_first_chunk_embedding", lambda *a, **k: _none())

    payload = {"raw_item_id": "", "article_id": str(article_id), "enrichment_id": str(enrichment_id)}
    await consumer.handle_enriched_item(payload)
    await consumer.handle_enriched_item(payload)  # replay
    assert calls == {"match": 1, "rebuild": 2, "dirty": 2}
    async with session_scope() as s:
        n = (await s.execute(text("SELECT count(*) FROM event_memberships WHERE article_id = :a"), {"a": article_id})).scalar()
    assert n == 1


async def _none():
    return None


async def test_match_or_create_holds_the_advisory_lock():
    """Two consumers serialise on the database, not on a deployment rule."""
    if not await _db_reachable():
        pytest.skip("no database")
    import inspect

    src = inspect.getsource(consumer._attach)
    assert "pg_advisory_xact_lock" in src.split("raw_item = ")[0], "the lock must precede the match"
