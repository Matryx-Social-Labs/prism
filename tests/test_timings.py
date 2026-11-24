"""Pipeline timings (common/timings.py) and the places that record them: the match
lock (correlation/consumer), Jev's wall time (correlation/verify), the analysis
sweeper's queue age, and dead letters by cause (common/stream).

Timing only: none of these may change what the code does, so each failure case
asserts the original exception still reaches the caller.
"""

import asyncio
import datetime as dt
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from common import stream, timings
from common.decisions import ChoiceAnswer, NoulAnswer
from common.stream import get_redis
from correlation import consumer, verify

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _redis_up() -> bool:
    try:
        await get_redis().ping()
        return True
    except Exception:  # noqa: BLE001
        return False


class _Broken:
    def pipeline(self, **_k):
        raise ConnectionError("redis down")


@pytest.fixture
def recorded(monkeypatch):
    """What the instrumented code sent to timings, in order."""
    seen: dict[str, list] = {"observe": [], "count": []}

    async def observe(name, ms):
        seen["observe"].append((name, ms))

    async def count(name, n=1):
        seen["count"].append((name, n))

    monkeypatch.setattr(timings, "observe", observe)
    monkeypatch.setattr(timings, "count", count)
    return seen


# ── buckets and quantiles ──

def test_a_duration_lands_in_the_first_bucket_at_or_above_it():
    assert timings.bucket(0) == "1"
    assert timings.bucket(1) == "1"
    assert timings.bucket(1.01) == "2"
    assert timings.bucket(6000) == "7000"
    assert timings.bucket(86_400_000) == "86400000"
    assert timings.bucket(86_400_001) == "inf"


def test_a_quantile_is_the_upper_bound_of_the_bucket_that_holds_it():
    counts = {"10": 50, "100": 45, "1000": 5}
    assert timings.quantile(counts, 0.5) == 10
    assert timings.quantile(counts, 0.95) == 100
    assert timings.quantile(counts, 0.96) == 1000


def test_a_quantile_in_the_overflow_bucket_is_unknown_not_a_number():
    assert timings.quantile({"5": 1, "inf": 9}, 0.5) is None
    assert timings.quantile({"5": 1, "inf": 9}, 0.05) == 5


def test_no_observations_have_no_quantile():
    assert timings.quantile({}, 0.5) is None


# ── the store ──

async def test_a_day_adds_up_and_a_day_with_no_hash_is_unrecorded(monkeypatch):
    if not await _redis_up():
        pytest.skip("no redis")
    day = dt.date(2001, 1, 1) + dt.timedelta(days=uuid.uuid4().int % 3000)  # a day no one else writes
    monkeypatch.setattr(timings, "_today", lambda: day)
    await get_redis().delete(timings._key(day))
    try:
        for ms in (3, 4, 4, 900):
            await timings.observe("match_lock.wait", ms)
        await timings.observe("jev.event-verify", 250)
        await timings.count("dead.raw.items.rebill")
        await timings.count("dead.raw.items.rebill", 2)
        [today, before] = await timings.days(2, today=day)
    finally:
        await get_redis().delete(timings._key(day))
    assert before == {"day": (day - dt.timedelta(days=1)).isoformat(), "recorded": False, "timings": [], "counters": []}
    assert today["recorded"] is True
    assert today["timings"] == [
        {"name": "jev.event-verify", "n": 1, "p50_ms": 300, "p95_ms": 300},
        {"name": "match_lock.wait", "n": 4, "p50_ms": 5, "p95_ms": 1000},
    ]
    assert today["counters"] == [{"name": "dead.raw.items.rebill", "n": 3}]


async def test_a_redis_outage_never_costs_the_call(monkeypatch):
    monkeypatch.setattr(timings, "get_redis", lambda: _Broken())
    await timings.observe("match_lock.wait", 12.0)  # must not raise
    await timings.count("jev.event-verify.timeout")  # must not raise


# ── the match lock ──

def _payload() -> dict:
    return {"article_id": str(uuid.uuid4()), "enrichment_id": str(uuid.uuid4())}


class _Session:
    """Enough of an AsyncSession for handle_enriched_item: the membership query
    answers `attached`, the lock statement takes `lock_s`."""

    def __init__(self, attached, lock_s: float = 0.02):
        self.info: dict = {}
        self._attached = attached
        self._lock_s = lock_s

    async def get(self, _model, _id):
        return SimpleNamespace(shared_fields={}, lens_fields={})

    async def execute(self, stmt, *_a):
        if "pg_advisory_xact_lock" in str(stmt):
            await asyncio.sleep(self._lock_s)
        return SimpleNamespace(scalar_one_or_none=lambda: self._attached)


def _scope(session, commit_s: float):
    @asynccontextmanager
    async def scope():
        yield session
        await asyncio.sleep(commit_s)  # the commit, still under the lock

    return scope


@pytest.fixture
def downstream(monkeypatch):
    async def nothing(*_a, **_k):
        return None

    for name in ("_rebuild_projection", "persist_briefs", "mark_event_dirty", "reconcile_on_attach"):
        monkeypatch.setattr(consumer, name, nothing)


async def test_the_lock_is_held_until_the_transaction_ends(monkeypatch, recorded, downstream):
    session = _Session(attached=None)
    monkeypatch.setattr(consumer, "session_scope", _scope(session, commit_s=0.05))

    async def attach(s, *_a):
        await consumer._take_match_lock(s)
        return uuid.uuid4(), True

    monkeypatch.setattr(consumer, "_attach", attach)
    await consumer.handle_enriched_item(_payload())
    got = dict(recorded["observe"])
    assert set(got) == {"match_lock.wait", "match_lock.held"}
    assert got["match_lock.wait"] >= 20
    assert got["match_lock.held"] >= 50, "held must include the commit, which releases the lock"


async def test_a_failed_attach_still_records_the_hold_and_raises_unchanged(monkeypatch, recorded, downstream):
    session = _Session(attached=None)
    monkeypatch.setattr(consumer, "session_scope", _scope(session, commit_s=0))
    boom = RuntimeError("match failed")

    async def attach(s, *_a):
        await consumer._take_match_lock(s)
        raise boom

    monkeypatch.setattr(consumer, "_attach", attach)
    with pytest.raises(RuntimeError) as caught:
        await consumer.handle_enriched_item(_payload())
    assert caught.value is boom
    assert [name for name, _ in recorded["observe"]] == ["match_lock.wait", "match_lock.held"]


async def test_a_replayed_message_takes_no_lock_and_records_nothing(monkeypatch, recorded, downstream):
    monkeypatch.setattr(consumer, "session_scope", _scope(_Session(attached=uuid.uuid4()), commit_s=0))
    await consumer.handle_enriched_item(_payload())
    assert recorded["observe"] == []


async def test_attach_takes_the_lock_through_the_timed_helper():
    class _StopAfterLock(_Session):
        async def get(self, _model, _id):
            raise LookupError("stop after the lock")

    session = _StopAfterLock(attached=None, lock_s=0)
    with pytest.raises(LookupError):
        await consumer._attach(session, SimpleNamespace(raw_item_id=uuid.uuid4()), None, {}, uuid.uuid4(), [])
    assert "match_lock" in session.info


async def test_a_real_session_carries_the_lock_timing():
    from sqlalchemy.ext.asyncio import AsyncSession

    assert AsyncSession().info == {}, "session.info is where the lock's numbers ride"


async def test_the_lock_statement_is_what_is_timed():
    session = _Session(attached=None, lock_s=0.03)
    await consumer._take_match_lock(session)
    wait_ms, acquired = session.info["match_lock"]
    assert wait_ms >= 30 and acquired > 0


# ── Jev ──

def _candidate() -> verify.Candidate:
    return verify.Candidate(uuid.uuid4(), 0.1)


async def test_a_jev_call_is_timed_under_its_kind(monkeypatch, recorded):
    c = _candidate()

    async def decide(*_a, **_k):
        return SimpleNamespace(answers={"same_1": NoulAnswer(noul=0.9)}, model="jev", usage=SimpleNamespace(cost=0.0))

    monkeypatch.setattr(verify, "decide", decide)
    await verify.judge_story(article_id=uuid.uuid4(), block="a", candidates=[c], blocks={c.event_id: "e"}, follows=False)
    assert [name for name, _ in recorded["observe"]] == ["jev.event-verify"]
    assert recorded["count"] == []


async def test_a_jev_timeout_is_timed_counted_and_still_raised(monkeypatch, recorded):
    async def slow(*_a, **_k):
        await asyncio.sleep(1)

    monkeypatch.setattr(verify, "decide", slow)
    monkeypatch.setattr(verify, "VERIFY_TIMEOUT_S", 0.01)
    with pytest.raises(TimeoutError):
        await verify.judge_ledes(article_id=uuid.uuid4(), report="a", record="b")
    assert [name for name, _ in recorded["observe"]] == ["jev.event-escalate"]
    assert recorded["count"] == [("jev.event-escalate.timeout", 1)]


async def test_a_jev_error_is_timed_counted_and_still_raised(monkeypatch, recorded):
    c = _candidate()
    boom = ValueError("bad answer")

    async def broken(*_a, **_k):
        raise boom

    monkeypatch.setattr(verify, "decide", broken)
    with pytest.raises(ValueError) as caught:
        await verify.judge_story(article_id=uuid.uuid4(), block="a", candidates=[c], blocks={c.event_id: "e"})
    assert caught.value is boom
    assert [name for name, _ in recorded["observe"]] == ["jev.story-verify"]
    assert recorded["count"] == [("jev.story-verify.error", 1)]


async def test_nothing_asked_of_jev_records_nothing(recorded):
    await verify.judge_story(article_id=uuid.uuid4(), block="a", candidates=[_candidate()], blocks={})
    assert recorded == {"observe": [], "count": []}


async def test_a_lede_reading_is_timed_as_an_escalation(monkeypatch, recorded):
    async def decide(*_a, **_k):
        answer = ChoiceAnswer(choice="same", confidence=0.9, probabilities={"same": 0.9, "follow_up": 0.05})
        return SimpleNamespace(answers={"relation": answer}, model="jev", usage=SimpleNamespace(cost=0.0))

    monkeypatch.setattr(verify, "decide", decide)
    await verify.judge_ledes(article_id=uuid.uuid4(), report="a", record="b")
    assert [name for name, _ in recorded["observe"]] == ["jev.event-escalate"]


# ── the analysis sweeper ──

class _Dirty:
    """A sorted set of due analyses; `taken` were claimed by another sweeper."""

    def __init__(self, scores: dict[str, float], taken: frozenset = frozenset()):
        self.scores, self.taken = scores, taken

    async def zrangebyscore(self, _key, lo, hi, start=0, num=None, withscores=False):
        due = sorted((s, m) for m, s in self.scores.items() if lo <= s <= hi)
        return [(m, s) for s, m in due] if withscores else [m for _, m in due]

    async def zrem(self, _key, member):
        return 0 if member in self.taken else 1

    async def zadd(self, *_a, **_k):
        return 1


async def test_queue_age_is_observed_only_for_what_this_sweeper_claimed(monkeypatch, recorded):
    import time

    now = time.time()
    mine, theirs = str(uuid.uuid4()), str(uuid.uuid4())
    monkeypatch.setattr(consumer, "get_redis", lambda: _Dirty({mine: now - 30, theirs: now - 60}, frozenset({theirs})))

    async def analyze(_eid):
        return None

    monkeypatch.setattr(consumer, "analyze_event_now", analyze)
    assert await consumer.run_due_analyses() == 1
    [(name, ms)] = recorded["observe"]
    assert name == "analysis.queue_age" and 30_000 <= ms < 40_000


async def test_the_queue_reports_what_is_due_and_how_long_it_waited(monkeypatch):
    if not await _redis_up():
        pytest.skip("no redis")
    import time

    key = f"test.dirty.{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(consumer, "DIRTY_KEY", key)
    r = get_redis()
    now = time.time()
    try:
        assert await consumer.analysis_queue() == {"due": 0, "oldest_due_age_s": None}
        await r.zadd(key, {"a": now - 12, "b": now - 3, "c": now + 90})
        q = await consumer.analysis_queue()
    finally:
        await r.delete(key)
    assert q["due"] == 2 and 12 <= q["oldest_due_age_s"] < 20


async def test_an_unreadable_queue_is_absent_not_empty(monkeypatch):
    monkeypatch.setattr(consumer, "get_redis", lambda: _Broken())
    assert await consumer.analysis_queue() is None


# ── dead letters ──

class _Stream:
    def __init__(self):
        self.dead: list[tuple[str, dict]] = []

    async def xpending_range(self, *_a, **_k):
        return [{"times_delivered": 1}]

    async def xadd(self, topic, fields, **_k):
        self.dead.append((topic, fields))

    def pipeline(self, **_k):
        raise ConnectionError("not needed")


async def test_a_lost_insert_race_is_counted_as_a_rebill(recorded):
    exc = Exception('duplicate key value violates unique constraint "uq_articles_raw_item"')
    await stream._dead_letter(_Stream(), "classified.items", "enrichment", "1-0", {"data": "{}"}, exc)
    assert recorded["count"] == [("dead.classified.items.rebill", 1)]


async def test_any_other_dead_letter_is_counted_by_its_class(recorded):
    await stream._dead_letter(_Stream(), "raw.items", "classification", "1-0", {"data": "{}"}, KeyError("x"))
    assert recorded["count"] == [("dead.raw.items.KeyError", 1)]


async def test_a_broken_counter_never_stops_the_dead_letter(monkeypatch):
    monkeypatch.setattr(timings, "get_redis", lambda: _Broken())
    r = _Stream()
    await stream._dead_letter(r, "raw.items", "classification", "1-0", {"data": "{}"}, KeyError("x"))
    assert [topic for topic, _ in r.dead] == ["raw.items.dead"]
