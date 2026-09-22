"""The classification stage's own moving parts: the feed-state stamp, the body
cap, and the write that must be idempotent under stream replay."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from classification import consumer
from classification.consumer import _apply_feed_state
from classification.decide import MAX_GATE_CHARS, body_for_prompt
from classification.schemas import ClassificationResult, GateResult
from common.config import get_settings
from common.db import session_scope
from common.decisions import ChoiceAnswer, Decisions, NoulAnswer
from common.models import RawItem, Source
from ingestion.rss import FeedSpec


def _cls(regions: list[str]) -> ClassificationResult:
    return ClassificationResult(sector="politics", regions=regions)


def test_a_state_feed_stamps_its_state_on_a_national_indian_item():
    spec = FeedSpec(slug="x", url="u", state="IN-KA")
    before = _cls(["IN"])
    after = _apply_feed_state(before, spec)
    assert after.regions == ["IN", "IN-KA"]
    assert before.regions == ["IN"], "the input must not be mutated"


@pytest.mark.parametrize("regions", [["IN", "IN-MH"], ["US"], ["IN", "US"]])
def test_the_stamp_yields_to_the_article(regions):
    spec = FeedSpec(slug="x", url="u", state="IN-KA")
    assert _apply_feed_state(_cls(regions), spec).regions == regions


def test_no_stamp_without_a_state_feed():
    assert _apply_feed_state(_cls(["IN"]), None).regions == ["IN"]
    assert _apply_feed_state(_cls(["IN"]), FeedSpec(slug="x", url="u")).regions == ["IN"]


def test_body_for_prompt_caps_and_names_the_empty_case():
    assert body_for_prompt(None) == "(no content — title only)"
    assert body_for_prompt("") == "(no content — title only)"
    assert len(body_for_prompt("x" * (MAX_GATE_CHARS + 500))) == MAX_GATE_CHARS


# ── the decisions modes ──────────────────────────────────────────────────────


def _jev(event=0.9, sector_conf=0.97):
    return Decisions(answers={
        "event": NoulAnswer(noul=event), "not_news": NoulAnswer(noul=0.05),
        "sector": ChoiceAnswer(choice="sports", confidence=sector_conf, probabilities={}),
        "subsector": ChoiceAnswer(choice="sports/cricket", confidence=0.9, probabilities={}),
        "indian_state": ChoiceAnswer(choice="none", confidence=1, probabilities={}),
        "country": ChoiceAnswer(choice="IN", confidence=1, probabilities={}),
        "language": ChoiceAnswer(choice="en", confidence=1, probabilities={}),
        "cyber": NoulAnswer(noul=0.0), "markets": NoulAnswer(noul=0.0), "fast_lane": NoulAnswer(noul=0.0),
    })


class _Calls:
    def __init__(self, monkeypatch, *, jev=None, jev_error=None):
        self.gate = self.classify = self.decide = 0
        self.shadow_logs: list[dict] = []

        async def gate(*a, **k):
            self.gate += 1
            return GateResult(is_relevant=True, reason="llm")

        async def classify(*a, **k):
            self.classify += 1
            return ClassificationResult(sector="politics", regions=["IN"])

        async def decide(*a, **k):
            self.decide += 1
            if jev_error:
                raise jev_error
            return jev

        monkeypatch.setattr(consumer, "_run_gate", gate)
        monkeypatch.setattr(consumer, "_run_classifier", classify)
        monkeypatch.setattr(consumer, "decide", decide)
        monkeypatch.setattr(consumer, "_log_decision_shadow", lambda **kw: self.shadow_logs.append(kw))


async def _run(mode: str, monkeypatch, **calls_kw) -> tuple[_Calls, GateResult, ClassificationResult | None]:
    monkeypatch.setattr(get_settings(), "prism_decisions_mode", mode)
    monkeypatch.setattr(get_settings(), "prism_gate_mode", "off")
    calls = _Calls(monkeypatch, **calls_kw)
    gate, cls = await consumer._gate_and_classify("t", "b", "IN", {"stage": "classification"})
    return calls, gate, cls


async def test_off_never_asks_jev(monkeypatch):
    calls, gate, cls = await _run("off", monkeypatch, jev=_jev())
    assert (calls.decide, calls.gate, calls.classify) == (0, 1, 1)
    assert cls.sector == "politics"


async def test_shadow_asks_both_logs_the_pair_and_keeps_the_llm_answer(monkeypatch):
    calls, gate, cls = await _run("shadow", monkeypatch, jev=_jev())
    assert (calls.decide, calls.gate, calls.classify) == (1, 1, 1)
    assert cls.sector == "politics", "shadow must not change the outcome"
    assert len(calls.shadow_logs) == 1
    assert calls.shadow_logs[0]["llm_classification"].sector == "politics"
    assert calls.shadow_logs[0]["jev_classification"].sector == "sports"


async def test_shadow_survives_a_jev_failure(monkeypatch):
    calls, gate, cls = await _run("shadow", monkeypatch, jev_error=ConnectionError("down"))
    assert (calls.gate, calls.classify) == (1, 1) and cls.sector == "politics"
    assert calls.shadow_logs == []


async def test_live_answers_from_jev_alone(monkeypatch):
    calls, gate, cls = await _run("live", monkeypatch, jev=_jev())
    assert (calls.decide, calls.gate, calls.classify) == (1, 0, 0)
    assert (cls.sector, cls.subsector) == ("sports", "cricket")


async def test_live_falls_back_to_the_llm_under_the_confidence_floor(monkeypatch):
    monkeypatch.setattr(get_settings(), "prism_decisions_min_confidence", 0.6)
    calls, gate, cls = await _run("live", monkeypatch, jev=_jev(sector_conf=0.4))
    assert (calls.decide, calls.gate, calls.classify) == (1, 1, 1)
    assert cls.sector == "politics"
    assert len(calls.shadow_logs) == 1, "a fallback still records the pair"


async def test_an_answer_that_fits_no_record_is_a_jev_failure_not_a_lost_item(monkeypatch):
    """The alpha endpoint answering outside our vocabulary must read as Jev being
    down: shadow keeps the LLM's answer, live falls back to it."""
    unmappable = _jev()
    unmappable.answers["sector"] = ChoiceAnswer(choice="not-a-sector", confidence=1, probabilities={})
    calls, gate, cls = await _run("shadow", monkeypatch, jev=unmappable)
    assert cls.sector == "politics" and calls.shadow_logs == []
    calls, gate, cls = await _run("live", monkeypatch, jev=unmappable)
    assert (calls.gate, calls.classify) == (1, 1) and cls.sector == "politics"


async def test_live_falls_back_to_the_llm_when_jev_is_down(monkeypatch):
    calls, gate, cls = await _run("live", monkeypatch, jev_error=ConnectionError("down"))
    assert (calls.gate, calls.classify) == (1, 1) and cls.sector == "politics"


# ── the write path, against Postgres ────────────────────────────────────────


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _seed(relevance: str = "pending") -> uuid.UUID:
    async with session_scope() as s:
        src = Source(id=uuid.uuid4(), slug=f"t-{uuid.uuid4().hex[:8]}", name="t", source_type="rss", country="IN")
        s.add(src)
        await s.flush()
        item = RawItem(
            id=uuid.uuid4(), source_id=src.id, external_id=uuid.uuid4().hex, title="t", body="b",
            observed_at=datetime.now(UTC), raw={}, relevance=relevance,
        )
        s.add(item)
        return item.id


async def _row(item_id: uuid.UUID) -> RawItem:
    async with session_scope() as s:
        row = await s.get(RawItem, item_id)
        s.expunge(row)
        return row


@pytest.mark.asyncio
async def test_a_relevant_item_is_written_once_and_published_once(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    item_id = await _seed()
    published: list[dict] = []

    async def gate(*a, **k):
        return GateResult(is_relevant=True, reason="yes")

    async def classify(*a, **k):
        return ClassificationResult(sector="politics", regions=["IN"])

    async def publish(topic, message):
        published.append(message)
        return "1-0"

    monkeypatch.setattr(consumer, "_run_gate", gate)
    monkeypatch.setattr(consumer, "_run_classifier", classify)
    monkeypatch.setattr(consumer.stream, "publish", publish)

    await consumer.handle_raw_item({"raw_item_id": str(item_id)})
    row = await _row(item_id)
    assert row.relevance == "relevant"
    assert row.classification["sector"] == "politics"
    assert row.classified_at is not None
    assert len(published) == 1

    await consumer.handle_raw_item({"raw_item_id": str(item_id)})  # stream replay
    assert len(published) == 1, "a replayed message must not publish twice"


@pytest.mark.asyncio
async def test_a_rejected_item_keeps_the_reason_and_stays_quiet(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    item_id = await _seed()
    published: list[dict] = []

    async def gate(*a, **k):
        return GateResult(is_relevant=False, reason="an opinion column")

    async def publish(topic, message):
        published.append(message)
        return "1-0"

    monkeypatch.setattr(consumer, "_run_gate", gate)
    monkeypatch.setattr(consumer.stream, "publish", publish)

    await consumer.handle_raw_item({"raw_item_id": str(item_id)})
    row = await _row(item_id)
    assert (row.relevance, row.rejection_reason, row.classification) == ("rejected", "an opinion column", None)
    assert published == []


@pytest.mark.asyncio
async def test_an_item_settled_by_another_worker_mid_call_is_not_overwritten(monkeypatch):
    """Two workers can hold the same pending item across the LLM call; the
    second write must lose, not flip a settled row."""
    if not await _db_reachable():
        pytest.skip("no database")
    item_id = await _seed()
    published: list[dict] = []

    async def gate(*a, **k):
        async with session_scope() as s:  # the other worker settles it while we wait on the model
            await s.execute(
                text("UPDATE raw_items SET relevance = 'rejected', rejection_reason = 'first' WHERE id = :id"),
                {"id": item_id},
            )
        return GateResult(is_relevant=True, reason="second")

    async def classify(*a, **k):
        return ClassificationResult(sector="politics")

    async def publish(topic, message):
        published.append(message)
        return "1-0"

    monkeypatch.setattr(consumer, "_run_gate", gate)
    monkeypatch.setattr(consumer, "_run_classifier", classify)
    monkeypatch.setattr(consumer.stream, "publish", publish)

    await consumer.handle_raw_item({"raw_item_id": str(item_id)})
    row = await _row(item_id)
    assert (row.relevance, row.rejection_reason) == ("rejected", "first")
    assert published == []
