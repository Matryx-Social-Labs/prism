"""Phase 2 — relevance gate + classifier/router.

Consumes raw.items. CVE-feed items (NVD, CISA KEV) are relevant by
construction and classified deterministically — no LLM spend. News/RSS
items go through the binary LLM gate, then the classifier — or, with
prism_decisions_mode, through one typed Jev call that answers both
(classification/decide.py): `shadow` runs it beside the LLM pair and logs the
two verdicts, `live` lets it answer. Rejected items are kept with a reason for
audit; relevant items emit classified.items.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import update

from classification.decide import (
    QUESTIONS,
    QUESTIONS_VERSION,
    body_for_prompt,
    decided_confidence,
    state_for,
    to_results,
)
from classification.schemas import ClassificationResult, GateResult
from classification.shadow_gate import shadow_score
from common import stream
from common.config import get_settings
from common.db import session_scope
from common.decisions import decide
from common.llm import REASONING_OFF, structured_chat
from common.logging import get_logger
from common.models import RawItem, Source
from common.observability import fetch_prompt, observe
from common.schemas import ClassifiedItemMessage
from common.taxonomy import prompt_menu, valid_subsector
from ingestion.rss import SPEC_BY_SLUG, FeedSpec

logger = get_logger(__name__)



@observe(name="classification-stage")
async def handle_raw_item(payload: dict) -> None:
    raw_item_id = uuid.UUID(payload["raw_item_id"])

    async with session_scope() as session:
        item = await session.get(RawItem, raw_item_id)
        if item is None:
            logger.warning("raw_item_missing", raw_item_id=str(raw_item_id))
            return
        if item.relevance != "pending":
            return  # already processed (stream replay)
        source = await session.get(Source, item.source_id)
        source_slug = source.slug if source else "unknown"
        source_type = source.source_type if source else "unknown"
        source_country = source.country if source else None
        title, body = item.title, item.body

    meta = {"stage": "classification", "source_slug": source_slug, "raw_item_id": str(raw_item_id)}

    feed_spec = SPEC_BY_SLUG.get(source_slug)
    if source_type == "cve_feed":
        classification = _classify_cve_feed(source_slug, title, body)
        gate = GateResult(is_relevant=True, reason="Authoritative CVE feed record")
    elif feed_spec is not None and feed_spec.sector is not None:
        # Single-topic feed: sector known by construction — no LLM spend.
        classification = ClassificationResult(
            sector=feed_spec.sector,
            subsector=feed_spec.subsector,
            regions=[source_country] if source_country else [],
            language="en",
            role_interests=["markets"] if feed_spec.sector in ("finance", "business") else [],
            route="standard",
            confidence=0.8,
        )
        gate = GateResult(is_relevant=True, reason=f"Single-topic {feed_spec.sector} feed")
    else:
        gate, classification = await _gate_and_classify(title, body, source_country, meta)

    if classification is not None:
        classification = _apply_feed_state(classification, feed_spec)

    relevant = gate.is_relevant and classification is not None
    values = (
        {"relevance": "relevant", "classification": classification.model_dump()}
        if relevant
        else {"relevance": "rejected", "rejection_reason": gate.reason}
    )
    # One conditional UPDATE, not a re-SELECT then ORM flush: the row is only
    # written if it is still pending, so a replayed message or a second worker
    # that held the same item across the model call cannot flip a settled row.
    async with session_scope() as session:
        result = await session.execute(
            update(RawItem)
            .where(RawItem.id == raw_item_id, RawItem.relevance == "pending")
            .values(classified_at=datetime.now(UTC), **values)
        )
        settled_here = result.rowcount == 1

    if relevant and settled_here:
        await stream.publish(
            stream.CLASSIFIED_ITEMS,
            ClassifiedItemMessage(raw_item_id=str(raw_item_id)).model_dump(),
        )


def _apply_feed_state(classification: ClassificationResult, feed_spec: FeedSpec | None) -> ClassificationResult:
    """Stamp the state (ISO 3166-2) from a state-edition feed onto the regions, so
    the feed can tier local(state) -> national. Deterministic from the feed, no
    LLM — but only where the feed's state can be the story's: not when the
    classifier already placed the event in a state, and not when the article
    is about another country. Prajavani's whole-site feed is IN-KA and printed
    the US Senate's Russia-sanctions bill; the stamp put it under Karnataka
    (founder, 2026-09-20)."""
    if feed_spec is None or not feed_spec.state:
        return classification
    if feed_spec.state in classification.regions or not feed_state_applies(classification.regions):
        return classification
    return classification.model_copy(update={"regions": [*classification.regions, feed_spec.state]})


async def _gate_and_classify(
    title: str, body: str | None, source_country: str | None, meta: dict
) -> tuple[GateResult, ClassificationResult | None]:
    """The gate and the classifier, by whichever prism_decisions_mode says.

    `off`: the LLM pair. `shadow`: Jev beside the pair, both verdicts logged,
    the pair's answer kept. `live`: Jev's answer, unless it is under the
    confidence floor or Jev is down — then the pair answers and the two are
    still logged, so the floor can be tuned from what it excluded."""
    settings = get_settings()
    mode = settings.prism_decisions_mode
    decided: tuple[GateResult, ClassificationResult | None, float] | None = None
    if mode in ("shadow", "live"):
        try:
            answers = await decide(
                state_for(title, body), QUESTIONS, trace_name="gate-classify",
                metadata={**meta, "questions_version": QUESTIONS_VERSION},
            )
            # Mapped inside the guard: an answer that does not fit our records is
            # a Jev failure like any other, not a lost article.
            decided = (*to_results(answers, source_country=source_country), decided_confidence(answers))
        except Exception as exc:  # noqa: BLE001 — shadow must not break the stage; live falls back to the pair
            logger.warning("decision_failed", error_type=type(exc).__name__, error=str(exc)[:200], mode=mode,
                           raw_item_id=meta.get("raw_item_id"))
    if decided is not None and mode == "live" and decided[2] >= settings.prism_decisions_min_confidence:
        return decided[0], decided[1]

    gate = await _run_gate(title, body, meta)
    if settings.prism_gate_mode == "shadow":
        await _log_shadow_gate(title, body, gate, meta.get("source_slug", ""), meta.get("raw_item_id", ""))
    classification = await _run_classifier(title, body, source_country, meta) if gate.is_relevant else None
    if decided is not None:
        _log_decision_shadow(
            jev_gate=decided[0], jev_classification=decided[1], jev_confidence=decided[2],
            llm_gate=gate, llm_classification=classification, meta=meta,
        )
    return gate, classification


def _log_decision_shadow(
    *, jev_gate: GateResult, jev_classification: ClassificationResult | None, jev_confidence: float,
    llm_gate: GateResult, llm_classification: ClassificationResult | None, meta: dict,
) -> None:
    """One line per item with both verdicts side by side; the agreement table
    that decides `live` and its confidence floor is grepped from these."""
    j, l = jev_classification, llm_classification  # noqa: E741 — j/l read as jev/llm
    logger.info(
        "decision_shadow",
        raw_item_id=meta.get("raw_item_id"),
        source_slug=meta.get("source_slug"),
        language=(l or j).language if (l or j) else None,
        jev_confidence=round(jev_confidence, 3),
        gate_agree=jev_gate.is_relevant == llm_gate.is_relevant,
        jev_relevant=jev_gate.is_relevant,
        llm_relevant=llm_gate.is_relevant,
        jev_reason=jev_gate.reason,
        sector_agree=(j.sector == l.sector) if (j and l) else None,
        jev_sector=j.sector if j else None,
        llm_sector=l.sector if l else None,
        subsector_agree=(j.subsector == l.subsector) if (j and l) else None,
        state_agree=({r for r in j.regions if "-" in r} == {r for r in l.regions if "-" in r}) if (j and l) else None,
        jev_regions=j.regions if j else None,
        llm_regions=l.regions if l else None,
        route_agree=(j.route == l.route) if (j and l) else None,
        lenses_agree=(sorted(j.role_interests) == sorted(l.role_interests)) if (j and l) else None,
        language_agree=(j.language == l.language) if (j and l) else None,
    )


async def _log_shadow_gate(
    title: str, body: str | None, gate: GateResult, source_slug: str, raw_item_id: str
) -> None:
    """Shadow mode: log the embedding relevance score next to the LLM decision so
    the score band can be calibrated before embeddings ever filter. Behavior-neutral.

    The broad `except` is deliberate: shadow scoring is observability-only and must
    never break ingestion. It logs the failure with context rather than swallowing.
    """
    try:
        score = await shadow_score(title, body)
        logger.info(
            "shadow_gate",
            score=round(score, 4),
            llm_relevant=gate.is_relevant,
            source_slug=source_slug,
            raw_item_id=raw_item_id,
        )
    except Exception as exc:  # noqa: BLE001 — shadow path must not break the pipeline
        logger.warning("shadow_gate_failed", error=str(exc), raw_item_id=raw_item_id)


async def _run_gate(title: str, body: str | None, meta: dict) -> GateResult:
    settings = get_settings()
    prompt = fetch_prompt("relevance-gate")
    messages = prompt.compile(title=title, body=body_for_prompt(body))
    return await structured_chat(
        model=settings.prism_model_gate,
        messages=messages,
        output_model=GateResult,
        trace_name="relevance-gate",
        max_tokens=1500,
        reasoning=REASONING_OFF,
        metadata=meta,
        langfuse_prompt=prompt if prompt.version else None,
    )


async def _run_classifier(
    title: str, body: str | None, source_country: str | None, meta: dict
) -> ClassificationResult:
    settings = get_settings()
    prompt = fetch_prompt("classifier")
    messages = prompt.compile(title=title, body=body_for_prompt(body), taxonomy=prompt_menu())
    result = await structured_chat(
        model=settings.prism_model_classify,
        messages=messages,
        output_model=ClassificationResult,
        trace_name="classifier",
        max_tokens=1500,
        reasoning=REASONING_OFF,
        metadata=meta,
        langfuse_prompt=prompt if prompt.version else None,
    )
    return result.model_copy(update={
        "subsector": valid_subsector(result.sector, result.subsector),
        "regions": result.regions or ([source_country] if source_country else []),
    })


def feed_state_applies(regions: list[str]) -> bool:
    """A feed's state stamp holds only when nothing says otherwise: the
    classifier named no state of its own, and no foreign country is involved."""
    if any(r.startswith("IN-") for r in regions):
        return False
    return all(r == "IN" for r in regions)


def _classify_cve_feed(source_slug: str, title: str, body: str | None) -> ClassificationResult:
    """Deterministic classification for structured CVE records."""
    fast_lane = source_slug == "cisa_kev"  # KEV = actively exploited → time-critical
    return ClassificationResult(
        sector="cybersecurity",
        subsector="vulnerabilities",
        regions=[],
        language="en",
        role_interests=["cyber"],
        route="fast_lane" if fast_lane else "standard",
        confidence=1.0,
    )
