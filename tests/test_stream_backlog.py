"""/healthz must report queue depth, and must never fail on it.

The pipeline's characteristic failure is not a stage that dies — it is a stage
that keeps answering while its backlog grows. On 2026-09-03 the gate approved
items ~35x faster than enrichment consumed them and 1,023 relevant articles were
collected, paid for and never enriched, with nothing anywhere reporting it. The
only stream-size code in the repo was STREAM_MAXLEN, which silently DISCARDS
entries at 100k.
"""

import pytest

from common import stream

pytestmark = pytest.mark.asyncio


class FakeRedis:
    def __init__(self, groups: dict | Exception):
        self._groups = groups

    async def xinfo_groups(self, topic):
        if isinstance(self._groups, Exception):
            raise self._groups
        return self._groups[topic]

    async def xpending_range(self, topic, group, min, max, count):
        return [{"time_since_delivered": 45_000}]

    async def xlen(self, topic):
        if isinstance(self._groups, Exception):
            raise self._groups
        return 2 if topic == f"{stream.RAW_ITEMS}.dead" else 0


async def test_reports_waiting_and_pending_per_stage(monkeypatch):
    monkeypatch.setattr(stream, "get_redis", lambda: FakeRedis({
        stream.RAW_ITEMS: [{"name": "classification", "lag": 5800, "pending": 4}],
        stream.CLASSIFIED_ITEMS: [{"name": "enrichment", "lag": 12, "pending": 12}],
        stream.ENRICHED_ITEMS: [{"name": "correlation", "lag": 0, "pending": 1}],
    }))
    out = await stream.backlog()
    # The number that was invisible: 5,800 items nobody has even looked at.
    assert out[stream.RAW_ITEMS] == {
        "waiting": 5800,
        "pending": 4,
        "oldest_pending_ms": 45_000,
        "dead_lettered": 2,
    }
    assert out[stream.CLASSIFIED_ITEMS]["waiting"] == 12
    assert out[stream.CLASSIFIED_ITEMS]["pending"] == 12


async def test_an_unknown_depth_is_minus_one_not_zero(monkeypatch):
    """Absence of evidence must not read as an empty queue. Zero would say
    'nothing is waiting', which is the most reassuring possible lie here."""
    monkeypatch.setattr(stream, "get_redis", lambda: FakeRedis(ConnectionError("redis down")))
    out = await stream.backlog()
    assert all(v["waiting"] == -1 and v["pending"] == -1 for v in out.values())
    assert all(v["dead_lettered"] == -1 for v in out.values())


async def test_a_missing_consumer_group_reads_as_empty_not_as_an_error(monkeypatch):
    """A topic whose group has not been created yet is genuinely empty — the
    worker has not started. That is different from not being able to look."""
    monkeypatch.setattr(stream, "get_redis", lambda: FakeRedis({
        stream.RAW_ITEMS: [],
        stream.CLASSIFIED_ITEMS: [],
        stream.ENRICHED_ITEMS: [],
    }))
    out = await stream.backlog()
    assert out[stream.RAW_ITEMS] == {
        "waiting": 0,
        "pending": 0,
        "oldest_pending_ms": 0,
        "dead_lettered": 2,
    }


async def test_pending_detail_failure_keeps_known_queue_depth(monkeypatch):
    class NoPendingDetail(FakeRedis):
        async def xpending_range(self, *args, **kwargs):
            raise RuntimeError("unsupported")

    monkeypatch.setattr(stream, "get_redis", lambda: NoPendingDetail({
        stream.RAW_ITEMS: [{"name": "classification", "lag": 3, "pending": 1}],
        stream.CLASSIFIED_ITEMS: [],
        stream.ENRICHED_ITEMS: [],
    }))
    out = await stream.backlog()
    assert out[stream.RAW_ITEMS]["waiting"] == 3
    assert out[stream.RAW_ITEMS]["pending"] == 1
    assert out[stream.RAW_ITEMS]["oldest_pending_ms"] == -1
