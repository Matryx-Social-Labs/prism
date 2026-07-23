"""Phase 2 — relevance gate + classifier/router.

Consumes raw.items. CVE-feed items (NVD, CISA KEV) are relevant by
construction and classified deterministically — no LLM spend. News/RSS
items go through the binary LLM gate, then the classifier. Rejected items
are kept with a reason for audit; relevant items emit classified.items.
"""

import uuid

from classification.schemas import ClassificationResult, GateResult
from classification.shadow_gate import shadow_score
from common import stream
from common.config import get_settings
from common.db import session_scope
from common.llm import structured_chat
from common.logging import get_logger
from common.models import RawItem, Source
from common.observability import fetch_prompt, observe
from common.schemas import ClassifiedItemMessage
from common.taxonomy import prompt_menu, valid_subsector
from ingestion.rss import SPEC_BY_SLUG

logger = get_logger(__name__)

MAX_GATE_CHARS = 4000


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
        gate = await _run_gate(title, body, meta)
        if get_settings().prism_gate_mode == "shadow":
            await _log_shadow_gate(title, body, gate, source_slug, str(raw_item_id))
        classification = None
        if gate.is_relevant:
            classification = await _run_classifier(title, body, source_country, meta)

    # Stamp the state (ISO 3166-2) from a state-edition feed onto the regions, so
    # the feed can tier local(state) -> national. Deterministic from the feed, no LLM.
    if classification is not None and feed_spec is not None and feed_spec.state:
        if feed_spec.state not in classification.regions:
            classification.regions = [*classification.regions, feed_spec.state]

    async with session_scope() as session:
        item = await session.get(RawItem, raw_item_id)
        if item is None or item.relevance != "pending":
            return
        if gate.is_relevant and classification is not None:
            item.relevance = "relevant"
            item.classification = classification.model_dump()
        else:
            item.relevance = "rejected"
            item.rejection_reason = gate.reason

    if gate.is_relevant:
        await stream.publish(
            stream.CLASSIFIED_ITEMS,
            ClassifiedItemMessage(raw_item_id=str(raw_item_id)).model_dump(),
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
    messages = prompt.compile(title=title, body=(body or "(no content — title only)")[:MAX_GATE_CHARS])
    return await structured_chat(
        model=settings.prism_model_gate,
        messages=messages,
        output_model=GateResult,
        trace_name="relevance-gate",
        metadata=meta,
        langfuse_prompt=prompt if prompt.version else None,
    )


async def _run_classifier(
    title: str, body: str | None, source_country: str | None, meta: dict
) -> ClassificationResult:
    settings = get_settings()
    prompt = fetch_prompt("classifier")
    messages = prompt.compile(
        title=title,
        body=(body or "(no content — title only)")[:MAX_GATE_CHARS],
        taxonomy=prompt_menu(),
    )
    result = await structured_chat(
        model=settings.prism_model_classify,
        messages=messages,
        output_model=ClassificationResult,
        trace_name="classifier",
        metadata=meta,
        langfuse_prompt=prompt if prompt.version else None,
    )
    result.subsector = valid_subsector(result.sector, result.subsector)
    if not result.regions and source_country:
        result.regions = [source_country]
    return result


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
