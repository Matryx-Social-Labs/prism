"""Audit H9/H10: every way an item can fall out of the pipeline has a way back.

The third requeue gap (an enriched article that never reached an event) and the
dead-letter redrive, which had a writer and no reader since the streams existed.
"""

import json
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common import stream
from common.db import session_scope
from common.models import Article, Enrichment, Event, EventMembership, RawItem, Source
from ingestion.runner import requeue_stalled
from tools import redrive_dead


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _seed_enriched(*, attached: bool, minutes_old: int) -> uuid.UUID:
    """An article with an enrichment, optionally already attached to an event."""
    async with session_scope() as s:
        src = Source(id=uuid.uuid4(), slug=f"t-{uuid.uuid4().hex[:8]}", name="t", source_type="rss")
        s.add(src)
        await s.flush()
        raw = RawItem(id=uuid.uuid4(), source_id=src.id, external_id=uuid.uuid4().hex, title="t",
                      observed_at=datetime.now(UTC), raw={}, relevance="relevant")
        s.add(raw)
        await s.flush()
        art = Article(id=uuid.uuid4(), raw_item_id=raw.id, clean_text="x " * 40, word_count=40)
        s.add(art)
        await s.flush()
        enr = Enrichment(id=uuid.uuid4(), article_id=art.id, summary="s", shared_fields={}, model="test")
        s.add(enr)
        await s.flush()
        if attached:
            ev = Event(id=uuid.uuid4(), title="e", sector="politics")
            s.add(ev)
            await s.flush()
            s.add(EventMembership(event_id=ev.id, article_id=art.id, match_type="new_event"))
        await s.execute(
            text("UPDATE enrichments SET created_at = now() - make_interval(mins => :m) WHERE id = :id"),
            {"m": minutes_old, "id": enr.id},
        )
        return art.id


async def test_an_enriched_article_that_never_reached_an_event_is_re_driven(monkeypatch):
    """The gap no row announces: classification says done, enrichment says done,
    and only the missing membership knows the publish never landed."""
    if not await _db_reachable():
        pytest.skip("no database")
    stranded = await _seed_enriched(attached=False, minutes_old=30)
    attached = await _seed_enriched(attached=True, minutes_old=30)
    fresh = await _seed_enriched(attached=False, minutes_old=1)
    published: list[tuple[str, dict]] = []

    async def capture(topic, message):
        published.append((topic, message))
        return "1-0"

    monkeypatch.setattr(stream, "publish", capture)
    await requeue_stalled()

    enriched = [m for t, m in published if t == stream.ENRICHED_ITEMS]
    ids = {m["article_id"] for m in enriched}
    assert str(stranded) in ids
    assert str(attached) not in ids, "an attached article must not be re-driven"
    assert str(fresh) not in ids, "a fresh one is still in flight on the stream"
    assert all({"raw_item_id", "article_id", "enrichment_id"} <= m.keys() for m in enriched)


def test_recovery_is_scheduled_outside_the_ingestion_switch():
    """It used to run inside run_all, so the cost brake also switched off the
    only thing that re-drives stranded items."""
    import inspect

    from ingestion import runner
    from worker import __main__ as worker_main

    assert "requeue_stalled" not in inspect.getsource(runner.run_all)
    assert 'id="requeue"' in inspect.getsource(worker_main.main)


# ── H10: the dead letters have a reader ──────────────────────────────────────


@pytest.fixture
def fresh_redis():
    """Drop the cached client so this test builds one on its own loop.

    `common.stream._redis` is a module global bound to the loop that created
    it, so the second Redis test in a file inherits a client whose loop has
    closed: its ping raises and the test SKIPS — green, having run nothing.
    That is the failure shape `tests/conftest.py` exists to prevent for
    Postgres. Dropped synchronously and not awaited closed: an async teardown
    here interleaves with conftest's engine disposal and errors the DB tests
    in this same file.
    """
    stream._redis = None
    yield
    stream._redis = None


async def _redis_reachable() -> bool:
    try:
        await stream.get_redis().ping()
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"redis unreachable: {type(exc).__name__}: {exc}")
        return False


async def test_a_dead_letter_can_be_listed_shown_and_re_driven(monkeypatch, fresh_redis):
    if not await _redis_reachable():
        pytest.skip("no redis")
    r = stream.get_redis()
    topic = f"test.redrive.{uuid.uuid4().hex[:8]}"
    dead = f"{topic}.dead"
    payload = {"raw_item_id": str(uuid.uuid4())}
    await r.xadd(dead, {"data": json.dumps(payload), "entry_id": "1-1", "deliveries": "5",
                        "error": "LlmQuotaError: quota exhausted"})
    try:
        entries = await redrive_dead.read_dead(dead, 10)
        assert len(entries) == 1 and json.loads(entries[0][1]["data"]) == payload

        published: list[tuple[str, dict]] = []

        async def capture(t, m):
            published.append((t, m))
            return "1-0"

        monkeypatch.setattr(stream, "publish", capture)

        # A dry run touches nothing.
        assert await redrive_dead.redrive([dead], 10, None, apply=False) == 1
        assert published == [] and await r.xlen(dead) == 1

        # A filter that does not match leaves it alone.
        assert await redrive_dead.redrive([dead], 10, "SomeOtherError", apply=True) == 0
        assert await r.xlen(dead) == 1

        assert await redrive_dead.redrive([dead], 10, "LlmQuotaError", apply=True) == 1
        assert published == [(topic, payload)], "the ORIGINAL payload, to the live topic"
        assert await r.xlen(dead) == 0, "and the dead entry is gone once the publish returned"
    finally:
        await r.delete(dead)


async def test_a_dead_payload_that_is_not_json_is_skipped_not_crashed(monkeypatch, fresh_redis):
    if not await _redis_reachable():
        pytest.skip("no redis")
    r = stream.get_redis()
    dead = f"test.redrive.{uuid.uuid4().hex[:8]}.dead"
    await r.xadd(dead, {"data": "not json at all", "error": "ValueError: x"})
    try:
        monkeypatch.setattr(stream, "publish", lambda *a, **k: None)
        assert await redrive_dead.redrive([dead], 10, None, apply=True) == 0
        assert await r.xlen(dead) == 1, "kept for inspection rather than dropped"
    finally:
        await r.delete(dead)


def test_every_stream_is_covered_by_the_redrive_tool():
    assert set(redrive_dead.dead_topics()) == {f"{t}.dead" for t, _ in stream.TOPIC_GROUPS}
