"""The classification stage's own moving parts: no feed-state stamp, the body
cap, and the write that must be idempotent under stream replay."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from classification import consumer
from classification.decide import MAX_GATE_CHARS, body_for_prompt
from classification.schemas import ClassificationResult, GateResult
from common.config import get_settings
from common.db import session_scope
from common.decisions import ChoiceAnswer, Decisions, NoulAnswer
from common.models import RawItem, Source


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


@pytest.mark.asyncio
async def test_a_state_editions_item_the_classifier_called_national_stays_national(monkeypatch):
    """Prajavani's whole-site feed is Karnataka's; a national bank strike it
    carried was stamped IN-KA over the classifier's 'national' (audit
    2026-09-27: 4.7% of state tags wrong). A state is the classifier's to
    choose, never the feed's."""
    if not await _db_reachable():
        pytest.skip("no database")
    item_id = await _seed()
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO sources (id, slug, name, source_type, country) "
                 "VALUES (gen_random_uuid(), 'prajavani', 'Prajavani', 'rss', 'IN') ON CONFLICT (slug) DO NOTHING")
        )
        await s.execute(
            text("UPDATE raw_items SET source_id = (SELECT id FROM sources WHERE slug = 'prajavani') WHERE id = :id"),
            {"id": item_id},
        )

    async def gate_and_classify(*a, **k):
        return GateResult(is_relevant=True, reason="news"), ClassificationResult(sector="business", regions=["IN"])

    async def publish(topic, message):
        return "1-0"

    monkeypatch.setattr(consumer, "_gate_and_classify", gate_and_classify)
    monkeypatch.setattr(consumer.stream, "publish", publish)
    await consumer.handle_raw_item({"raw_item_id": str(item_id)})
    assert (await _row(item_id)).classification["regions"] == ["IN"]
