"""The one pair judge behind the clip judge and the X post judge: cached pairs
are not re-asked, uncached pairs are judged concurrently and written in one
batched round trip, and a failed verdict costs only its own pair."""

import asyncio
import uuid

import pytest

from common import pair_judge
from common.config import get_settings
from common.decisions import ChoiceAnswer, Decisions
from common.pair_judge import PairJudge, Verdict, judge_pairs


class FakeRows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeSession:
    """Routes each statement by what it reads from; records what it writes."""

    def __init__(self, cached, stories, rights):
        self.cached, self.stories, self.rights = cached, stories, rights
        self.inserts: list = []

    async def execute(self, stmt, params=None):
        sql = str(stmt)
        if sql.startswith("INSERT"):
            self.inserts.append(params)
            return FakeRows([])
        if "FROM verdict_cache" in sql:
            return FakeRows(self.cached)
        if "FROM events" in sql:
            return FakeRows(self.stories)
        raise AssertionError(f"unexpected statement: {sql[:60]}")


async def _fetch_right(db, ids):
    return {i: f"PASSAGE:\n{db.rights[i]}" for i in ids if i in db.rights}


JUDGE = PairJudge(
    system="judge it",
    criteria={"event": "this one", "topic": "near it", "unrelated": "no"},
    cache_table="verdict_cache",
    right_column="right_id",
    right_sql_type="uuid",
    fetch_right=_fetch_right,
    trace_name="test-judge",
    log_event="test_judged",
)


def _make(n_uncached: int, cached: dict | None = None):
    ev = uuid.uuid4()
    rights = {uuid.uuid4(): f"passage {i}" for i in range(n_uncached)}
    cached = cached or {}
    db = FakeSession(
        cached=[(ev, r, v) for r, v in cached.items()],
        stories=[(ev, "Headline", "First. Second. Third.", "21 Sep 10:00")],
        rights=rights,
    )
    pairs = [(ev, r) for r in list(cached) + list(rights)]
    return ev, db, pairs


def test_cached_pairs_are_not_asked_again(monkeypatch):
    ev, db, pairs = _make(0, cached={uuid.uuid4(): "event"})
    calls = []

    async def no_chat(**kw):
        calls.append(kw)
        return Verdict(about="event")

    monkeypatch.setattr(pair_judge, "structured_chat", no_chat)
    out = asyncio.run(judge_pairs(db, JUDGE, pairs))
    assert out == {pairs[0]: "event"}
    assert calls == [] and db.inserts == []


def test_uncached_pairs_are_judged_concurrently_and_written_once(monkeypatch):
    ev, db, pairs = _make(6)
    in_flight, peak = 0, 0

    async def slow_chat(**kw):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        assert kw["messages"][1]["content"].startswith("STORY headline: Headline\n")
        return Verdict(about="topic")

    monkeypatch.setattr(pair_judge, "structured_chat", slow_chat)
    out = asyncio.run(judge_pairs(db, JUDGE, pairs))
    assert all(out[p] == "topic" for p in pairs)
    assert peak > 1, "pairs were judged one at a time"
    assert peak <= pair_judge.JUDGE_CONCURRENCY
    assert len(db.inserts) == 1 and len(db.inserts[0]) == 6, "verdicts must go in one executemany"


def test_a_failed_verdict_costs_only_its_pair(monkeypatch):
    ev, db, pairs = _make(3)
    bad = pairs[1][1]

    async def flaky_chat(**kw):
        if db.rights[bad] in kw["messages"][1]["content"]:
            raise ConnectionError("boom")
        return Verdict(about="event")

    monkeypatch.setattr(pair_judge, "structured_chat", flaky_chat)
    out = asyncio.run(judge_pairs(db, JUDGE, pairs))
    assert pairs[1] not in out
    assert out[pairs[0]] == "event" and out[pairs[2]] == "event"
    assert len(db.inserts[0]) == 2


def test_empty_input_touches_nothing():
    db = FakeSession([], [], {})
    assert asyncio.run(judge_pairs(db, JUDGE, [])) == {}
    assert db.inserts == []


@pytest.mark.parametrize("about", ["event", "topic", "unrelated"])
def test_verdict_vocabulary(about):
    assert Verdict(about=about).about == about


def test_on_jev_the_verdict_is_the_choice_and_the_cache_names_the_model(monkeypatch):
    ev, db, pairs = _make(2)
    monkeypatch.setattr(get_settings(), "prism_judge_backend", "decide")
    seen = []

    async def fake_decide(state, questions, **kw):
        seen.append((state, questions))
        return Decisions(answers={"about": ChoiceAnswer(choice="event", confidence=0.9, probabilities={})})

    async def no_chat(**kw):
        raise AssertionError("the LLM must not be asked on the decide backend")

    monkeypatch.setattr(pair_judge, "decide", fake_decide)
    monkeypatch.setattr(pair_judge, "structured_chat", no_chat)
    out = asyncio.run(judge_pairs(db, JUDGE, pairs))
    assert all(v == "event" for v in out.values())
    state, questions = seen[0]
    assert state["story"].startswith("STORY headline:") and state["text"].startswith("PASSAGE:")
    assert questions["about"].criteria == JUDGE.criteria
    assert {row["m"] for row in db.inserts[0]} == {get_settings().prism_model_decide}
