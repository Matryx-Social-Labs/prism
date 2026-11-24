"""requeue_stalled must not add another copy of an item that is still queued.

During a backlog a "stalled" item (by the database's account) is usually just
waiting its turn on the stream. Each ten-minute pass used to publish another copy,
and two copies of one item in enrichment is one extraction paid for twice.
"""

import json
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from common import stream
from common.db import session_scope
from common.models import RawItem, Source
from ingestion import runner
from tests.test_pipeline_recovery import (  # noqa: F401
    _db_reachable,
    _redis_reachable,
    _seed_enriched,
    fresh_redis,
)

GROUP = "g"


def _entry(raw_item_id: str) -> dict:
    return {"data": json.dumps({"raw_item_id": raw_item_id})}


@pytest.fixture
async def topic(fresh_redis):  # noqa: F811
    if not await _redis_reachable():
        pytest.skip("no redis")
    name = f"test.unacked.{uuid.uuid4().hex[:8]}"
    yield name
    await stream.get_redis().delete(name)


async def test_undelivered_and_delivered_unacked_count_and_acked_does_not(topic):
    # Arrange: one acked, one delivered but unacked, one never delivered
    r = stream.get_redis()
    await r.xgroup_create(topic, GROUP, id="0", mkstream=True)
    for rid in ("acked", "in-flight", "waiting"):
        await r.xadd(topic, _entry(rid))
    delivered = await r.xreadgroup(GROUP, "c", {topic: ">"}, count=2)
    first_id = delivered[0][1][0][0]
    await r.xack(topic, GROUP, first_id)

    # Act
    ids = await stream.unacked_raw_item_ids(topic, GROUP)

    # Assert
    assert ids == {"in-flight", "waiting"}


async def test_a_group_that_does_not_exist_yet_has_consumed_nothing(topic):
    r = stream.get_redis()
    await r.xadd(topic, _entry("a"))
    await r.xgroup_create(topic, "someone-else", id="$")
    assert await stream.unacked_raw_item_ids(topic, GROUP) == {"a"}


async def test_a_stream_that_does_not_exist_holds_nothing(topic):
    assert await stream.unacked_raw_item_ids(topic, GROUP) == set()


async def test_an_entry_that_does_not_parse_is_ignored(topic):
    r = stream.get_redis()
    await r.xgroup_create(topic, GROUP, id="0", mkstream=True)
    for fields in ({"data": "not json"}, {"data": "[1]"}, {"other": "x"}, _entry("ok")):
        await r.xadd(topic, fields)
    await r.xreadgroup(GROUP, "c", {topic: ">"}, count=2)  # two of them pending, two waiting
    assert await stream.unacked_raw_item_ids(topic, GROUP) == {"ok"}


async def test_more_entries_than_one_page_are_all_read(topic, monkeypatch):
    # Arrange: pages of 3 over 7 pending and 7 waiting entries
    monkeypatch.setattr(stream, "_PAGE", 3)
    r = stream.get_redis()
    await r.xgroup_create(topic, GROUP, id="0", mkstream=True)
    for i in range(14):
        await r.xadd(topic, _entry(str(i)))
    await r.xreadgroup(GROUP, "c", {topic: ">"}, count=7)

    # Act / Assert
    assert await stream.unacked_raw_item_ids(topic, GROUP) == {str(i) for i in range(14)}


# ── requeue_stalled ──────────────────────────────────────────────────────────


async def _seed_pending(minutes_old: int = 30) -> str:
    async with session_scope() as s:
        src = Source(id=uuid.uuid4(), slug=f"t-{uuid.uuid4().hex[:8]}", name="t", source_type="rss")
        s.add(src)
        await s.flush()
        raw = RawItem(id=uuid.uuid4(), source_id=src.id, external_id=uuid.uuid4().hex, title="t",
                      observed_at=datetime.now(UTC), raw={}, relevance="pending")
        s.add(raw)
        await s.flush()
        await s.execute(text("UPDATE raw_items SET created_at = now() - make_interval(mins => :m) WHERE id = :id"),
                        {"m": minutes_old, "id": raw.id})
        return str(raw.id)


async def _requeue(monkeypatch, unacked) -> list[tuple[str, dict]]:
    published: list[tuple[str, dict]] = []

    async def capture(t, m):
        published.append((t, m))
        return "1-0"

    monkeypatch.setattr(stream, "publish", capture)
    monkeypatch.setattr(stream, "unacked_raw_item_ids", unacked)
    await runner.requeue_stalled()
    return published


async def test_an_item_still_queued_is_not_republished_and_one_that_is_not_is(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    # Arrange: two stalled at each of two stages, one of each still on its topic
    queued, lost = await _seed_pending(), await _seed_pending()
    queued_art, lost_art = await _seed_enriched(attached=False, minutes_old=30), await _seed_enriched(
        attached=False, minutes_old=30)
    async with session_scope() as s:
        queued_enr = str((await s.execute(text("SELECT raw_item_id FROM articles WHERE id = :a"),
                                          {"a": queued_art})).scalar_one())
    asked: list[tuple[str, str]] = []

    async def unacked(topic, group):
        asked.append((topic, group))
        return {stream.RAW_ITEMS: {queued}, stream.ENRICHED_ITEMS: {queued_enr}}.get(topic, set())

    # Act
    published = await _requeue(monkeypatch, unacked)

    # Assert
    raw = {m["raw_item_id"] for t, m in published if t == stream.RAW_ITEMS}
    enriched = {m["article_id"] for t, m in published if t == stream.ENRICHED_ITEMS}
    assert lost in raw and queued not in raw
    assert str(lost_art) in enriched and str(queued_art) not in enriched
    # Each topic asked of the group that consumes it, and only where something stalled.
    assert {(stream.RAW_ITEMS, "classification"), (stream.ENRICHED_ITEMS, "correlation")} <= set(asked)
    assert set(asked) <= set(stream.TOPIC_GROUPS)


async def test_when_redis_cannot_say_everything_stalled_is_republished(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    stalled = await _seed_pending()
    warnings: list[str] = []
    monkeypatch.setattr(runner.logger, "warning", lambda name, **kw: warnings.append(name))

    async def down(topic, group):
        raise ConnectionError("redis down")

    published = await _requeue(monkeypatch, down)

    assert stalled in {m["raw_item_id"] for t, m in published if t == stream.RAW_ITEMS}
    assert "queued_items_unknown" in warnings


async def test_nothing_stalled_asks_redis_nothing(monkeypatch):
    async def none_stalled(limit):
        return [], [], []

    asked: list[str] = []

    async def unacked(topic, group):  # recorded, not raised: _still_queued swallows errors
        asked.append(topic)
        return set()

    monkeypatch.setattr(runner, "_stalled", none_stalled)
    assert await _requeue(monkeypatch, unacked) == []
    assert asked == []


async def test_a_hung_handler_stops_renewing_its_claim(monkeypatch):
    # Arrange: sleep returns at once, so only the bound can end the loop
    claims: list[str] = []

    class R:
        async def xclaim(self, *a, **kw):
            claims.append("x")

    async def no_sleep(_s):
        # An unbounded loop never yields here, so it is stopped by count, not by a clock.
        if len(claims) > 10 * stream.HEARTBEAT_MAX_S:
            raise AssertionError("the heartbeat never stops")

    monkeypatch.setattr(stream.asyncio, "sleep", no_sleep)

    # Act
    await stream._heartbeat(R(), "t", "g", "c", "1-1")

    # Assert
    assert len(claims) == stream.HEARTBEAT_MAX_S // stream.HEARTBEAT_S
