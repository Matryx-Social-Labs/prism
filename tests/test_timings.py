"""Pipeline timings (common/timings.py) and the places that record them: the match
lock (correlation/consumer), Jev's wall time (correlation/verify), the analysis
sweeper's queue age, and dead letters by cause (common/stream).

Timing only: none of these may change what the code does, so each failure case
asserts the original exception still reaches the caller.
"""

import asyncio
import datetime as dt
import time
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
import pytest_asyncio

from common import stream, timings
from common.decisions import ChoiceAnswer, NoulAnswer
from common.stream import get_redis
from correlation import consumer, verify
from tests.test_pipeline_recovery import fresh_redis  # noqa: F401 — a client on this test's loop

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


def test_buckets_are_ordered_as_numbers_not_as_strings():
    # Arrange: as strings "10" < "1000" < "5", so a string sort puts the median in "1000"
    counts = {"5": 1, "10": 1, "1000": 1}

    # Act
    median = timings.quantile(counts, 0.5)

    # Assert
    assert median == 10


def test_a_quantile_in_the_overflow_bucket_is_unknown_not_a_number():
    assert timings.quantile({"5": 1, "inf": 9}, 0.5) is None
    assert timings.quantile({"5": 1, "inf": 9}, 0.05) == 5


def test_no_observations_have_no_quantile():
    assert timings.quantile({}, 0.5) is None


# ── the store ──

async def test_a_day_adds_up_and_a_day_with_no_hash_is_unrecorded(monkeypatch, fresh_redis):  # noqa: F811
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
        {"name": "jev.event-verify", "n": 1, "p50_ms": 300, "p95_ms": 300, "mean_ms": 250.0},
        {"name": "match_lock.wait", "n": 4, "p50_ms": 5, "p95_ms": 1000, "mean_ms": 227.8},
    ]
    assert today["counters"] == [{"name": "dead.raw.items.rebill", "n": 3}]


async def test_a_stalled_redis_costs_at_most_the_write_timeout(monkeypatch):
    """The client has no read timeout, and a write can run under the match lock."""

    class _Stalled:
        def pipeline(self, **_k):
            return self

        def hincrby(self, *_a):
            return None

        def hincrbyfloat(self, *_a):
            return None

        def expire(self, *_a):
            return None

        async def execute(self):
            await asyncio.Event().wait()  # never answers

    monkeypatch.setattr(timings, "get_redis", lambda: _Stalled())
    monkeypatch.setattr(timings, "WRITE_TIMEOUT_S", 0.01)
    await asyncio.wait_for(timings.observe("match_lock.held", 5.0), 2)  # returns, raises nothing


async def test_a_redis_outage_never_costs_the_call(monkeypatch):
    monkeypatch.setattr(timings, "get_redis", lambda: _Broken())
    await timings.observe("match_lock.wait", 12.0)  # must not raise
    await timings.count("jev.event-verify.timeout")  # must not raise


def test_a_day_recorded_before_sums_has_no_mean():
    row = timings._day(dt.date(2001, 1, 1), {"match_lock.wait|5": "2"})["timings"][0]
    assert row == {"name": "match_lock.wait", "n": 2, "p50_ms": 5, "p95_ms": 5, "mean_ms": None}


@pytest.fixture
def log():
    """Every logger.info call, (message, fields), from any module patched with it."""
    seen: list[tuple[str, dict]] = []
    return seen, SimpleNamespace(info=lambda msg, **kw: seen.append((msg, kw)),
                                 warning=lambda *_a, **_k: None, exception=lambda *_a, **_k: None)


async def test_a_timed_block_is_logged_with_its_name_and_ms(monkeypatch, recorded, log):
    seen, logger = log
    monkeypatch.setattr(timings, "logger", logger)
    async with timings.timed("block"):
        await asyncio.sleep(0.01)
    [(msg, kw)] = seen
    assert msg == "timed" and kw["name"] == "block" and kw["ms"] >= 10


async def test_reading_the_days_from_a_stalled_redis_raises_in_bounded_time(monkeypatch):
    class _Stalled:
        def pipeline(self, **_k):
            return self

        def hgetall(self, *_a):
            return None

        async def execute(self):
            await asyncio.Event().wait()  # never answers

    monkeypatch.setattr(timings, "get_redis", lambda: _Stalled())
    monkeypatch.setattr(timings, "READ_TIMEOUT_S", 0.01)
    started = time.perf_counter()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(timings.days(3), 2)
    assert time.perf_counter() - started < 1, "unbounded: only this test's own guard stopped it"


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
        return SimpleNamespace(scalar_one_or_none=lambda: self._attached, scalar=lambda: "0")


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


async def test_a_cancelled_block_is_timed_not_counted_as_an_error_and_still_raised(recorded):
    # Act
    with pytest.raises(asyncio.CancelledError):
        async with timings.timed("block"):
            raise asyncio.CancelledError

    # Assert: a cancellation is the caller's decision, not the block failing
    assert recorded["count"] == []
    assert [name for name, _ms in recorded["observe"]] == ["block"]


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


def _story_assign():
    from correlation import stories

    rec = SimpleNamespace(id=uuid.uuid4(), at=dt.datetime(2026, 1, 1), title="t", summary=None)
    return stories, stories._judge(rec, ["story"])


def _entity_variant():
    from correlation import variants

    name = SimpleNamespace(name="a", kind="person")
    pair = SimpleNamespace(variant=name, survivor=name, variant_seen="x", survivor_seen="y")
    return variants, variants.judge([pair])


@pytest.mark.parametrize(("call", "kind"), [(_story_assign, "jev.story-assign"),
                                            (_entity_variant, "jev.entity-variant")])
async def test_every_judge_call_is_timed_under_its_kind(monkeypatch, recorded, call, kind):
    boom = ValueError("no answer")

    async def broken(*_a, **_k):
        raise boom

    module, pending = call()
    monkeypatch.setattr(module, "decide", broken)
    with pytest.raises(ValueError) as caught:
        await pending
    assert caught.value is boom
    assert [name for name, _ in recorded["observe"]] == [kind]


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


async def test_queue_age_is_observed_only_for_what_this_sweeper_claimed(monkeypatch, recorded, log):
    import time

    logged, logger = log
    monkeypatch.setattr(consumer, "logger", logger)
    now = time.time()
    mine, theirs = str(uuid.uuid4()), str(uuid.uuid4())
    monkeypatch.setattr(consumer, "get_redis", lambda: _Dirty({mine: now - 30, theirs: now - 60}, frozenset({theirs})))

    async def analyze(_eid):
        return None

    monkeypatch.setattr(consumer, "analyze_event_now", analyze)
    assert await consumer.run_due_analyses() == 1
    [(name, ms)] = recorded["observe"]
    assert name == "analysis.queue_age" and 30_000 <= ms < 40_000
    assert logged == [("analysis_claimed", {"event_id": mine, "queue_age_ms": round(ms, 1)})]


async def test_the_queue_reports_what_is_due_and_how_long_it_waited(monkeypatch, fresh_redis):  # noqa: F811
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


# ── re-bills: a raw item's extraction paid for twice ──

class _Crash(Exception):
    """The worker killed between the paid extraction and the insert (a deploy)."""


async def _extract_and_crash(monkeypatch, rid) -> None:
    import enrichment.consumer as ec

    async def crash(_chunks):
        raise _Crash

    monkeypatch.setattr(ec, "embed_texts", crash)
    with pytest.raises(_Crash):
        await ec.handle_classified_item({"raw_item_id": str(rid)})


@pytest_asyncio.fixture(loop_scope="session")
async def raw_item(monkeypatch, fresh_redis):  # noqa: F811
    """A relevant raw item the stubbed extractor will pay for; its paid mark removed after."""
    from tests import test_enrichment_text_guard as guard

    if not await guard._db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    async with guard.session_scope() as s:
        sid = await guard._source(s, tag)
        rid = await guard._raw(s, sid, f"https://example.test/{tag}/rebill", guard.STORY_TITLE, guard.FEED_BODY)
    guard._stub_pipeline(monkeypatch, guard.FEED_BODY * 6)
    yield rid
    try:
        await get_redis().delete(f"extract:paid:{rid}")
    except Exception:  # noqa: BLE001 — the Redis-down case never set it
        pass
    await guard._purge(sid)


async def test_a_crash_redelivery_that_pays_again_is_a_rebill(monkeypatch, recorded, raw_item):
    """REGRESSION: the redelivered item found no article, paid again, inserted
    fine, and nothing counted it."""
    if not await _redis_up():
        pytest.skip("no redis")
    await _extract_and_crash(monkeypatch, raw_item)
    assert recorded["count"] == [], "a first extraction is not a re-bill"
    await _extract_and_crash(monkeypatch, raw_item)
    assert recorded["count"] == [("extract.rebill", 1)]


async def test_reusing_an_extraction_is_never_a_rebill(monkeypatch, recorded, raw_item):
    import enrichment.consumer as ec

    async def reused(_url):
        return "the text", {"shared": {"headline_summary": "already extracted"}}, "openrouter:test"

    async def never(**_k):
        raise AssertionError("paid for a reused extraction")

    monkeypatch.setattr(ec, "_extraction_for_same_url", reused)
    monkeypatch.setattr(ec, "structured_chat", never)
    for _ in range(2):
        await _extract_and_crash(monkeypatch, raw_item)
    assert recorded["count"] == []


async def test_a_redis_outage_neither_fails_the_extraction_nor_counts_a_rebill(monkeypatch, recorded, raw_item):
    class _Down:
        async def set(self, *_a, **_k):
            raise ConnectionError("redis down")

    monkeypatch.setattr(timings, "get_redis", lambda: _Down())
    for _ in range(2):
        await _extract_and_crash(monkeypatch, raw_item)  # reaches the crash after the mark: nothing raised by it
    assert recorded["count"] == []
