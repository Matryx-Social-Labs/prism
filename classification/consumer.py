"""Phase 2 — relevance gate + classifier/router.

Consumes raw.items. CVE-feed items (NVD, CISA KEV) are relevant by
construction and classified deterministically — no LLM spend. News/RSS
items go through the binary LLM gate, then the classifier. Rejected items
are kept with a reason for audit; relevant items emit classified.items.
"""

import uuid

from classification.schemas import ClassificationResult, GateResult
from common import stream
from common.config import get_settings
from common.db import session_scope
from common.llm import structured_chat
from common.logging import get_logger
from common.models import RawItem, Source
from common.observability import fetch_prompt, observe
from common.schemas import ClassifiedItemMessage

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

    if source_type == "cve_feed":
        classification = _classify_cve_feed(source_slug, title, body)
        gate = GateResult(is_relevant=True, reason="Authoritative CVE feed record")
    else:
        gate = await _run_gate(title, body, meta)
        classification = None
        if gate.is_relevant:
            classification = await _run_classifier(title, body, source_country, meta)

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
    messages = prompt.compile(title=title, body=(body or "(no content — title only)")[:MAX_GATE_CHARS])
    result = await structured_chat(
        model=settings.prism_model_classify,
        messages=messages,
        output_model=ClassificationResult,
        trace_name="classifier",
        metadata=meta,
        langfuse_prompt=prompt if prompt.version else None,
    )
    if not result.regions and source_country:
        result.regions = [source_country]
    return result


def _classify_cve_feed(source_slug: str, title: str, body: str | None) -> ClassificationResult:
    """Deterministic classification for structured CVE records."""
    fast_lane = source_slug == "cisa_kev"  # KEV = actively exploited → time-critical
    return ClassificationResult(
        sector="cybersecurity",
        regions=[],
        language="en",
        role_interests=["cyber_grc"],
        route="fast_lane" if fast_lane else "standard",
        confidence=1.0,
    )
