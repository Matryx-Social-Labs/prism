"""Phase 4 — correlation: canonicalize into events, perspectives, impacts.

Consumes enriched.items. Assigns each enriched article to an existing event
(match cascade in clustering.py, trail persisted on event_memberships) or
creates a new one. Upserts entities, rebuilds the event projection, then
runs perspective grouping + impact propagation and emits event.updates.
"""

import json
import uuid

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from common import stream
from common.config import get_settings
from common.countries import gdelt_country_to_iso
from common.db import session_scope
from common.llm import structured_chat
from common.logging import get_logger
from common.models import (
    Article,
    Enrichment,
    Entity,
    Event,
    EventEntity,
    EventMembership,
    Impact,
    Perspective,
    RawItem,
)
from common.observability import fetch_prompt, observe
from common.schemas import EventUpdateMessage
from common.text import slugify
from correlation.briefs import generate_briefs, persist_briefs, primary_lens_for, template_briefs
from correlation.clustering import find_event
from correlation.schemas import CorrelationResult
from correlation.threads import link_event_threads

logger = get_logger(__name__)


@observe(name="correlation-stage")
async def handle_enriched_item(payload: dict) -> None:
    article_id = uuid.UUID(payload["article_id"])
    enrichment_id = uuid.UUID(payload["enrichment_id"])

    async with session_scope() as session:
        enrichment = await session.get(Enrichment, enrichment_id)
        article = await session.get(Article, article_id)
        if enrichment is None or article is None:
            logger.warning("enrichment_or_article_missing", enrichment_id=str(enrichment_id), article_id=str(article_id))
            return
        already = await session.execute(
            select(EventMembership.id).where(EventMembership.article_id == article_id)
        )
        if already.scalar_one_or_none() is not None:
            return  # replay

        raw_item = await session.get(RawItem, article.raw_item_id)
        shared = enrichment.shared_fields or {}
        lens = (enrichment.lens_fields or {}).get("cyber") or {}
        cve_ids = lens.get("cve_ids") or []
        title = raw_item.title if raw_item else "(untitled)"
        url = raw_item.url if raw_item else None
        published_at = raw_item.published_at if raw_item else None
        classification = (raw_item.classification or {}) if raw_item else {}
        cve_record = (enrichment.model or "").startswith("deterministic:")

        embedding = await _first_chunk_embedding(session, article_id)

        match = await find_event(
            session,
            cve_ids=cve_ids,
            url=url,
            title=title,
            published_at=published_at,
            embedding=embedding,
            cve_record=cve_record,
        )

        if match is not None:
            event = await session.get(Event, match.event_id)
            is_new_event = False
        else:
            event = Event(
                id=uuid.uuid4(),
                title=title,
                summary=enrichment.summary,
                sector=classification.get("sector", "other"),
                subsector=classification.get("subsector"),
                regions=shared.get("regions") or classification.get("regions") or [],
                occurred_at=enrichment.occurred_at,
                embedding=embedding,
            )
            session.add(event)
            is_new_event = True

        if event.image_url is None and raw_item is not None and raw_item.image_url:
            event.image_url = raw_item.image_url
        session.add(
            EventMembership(
                event_id=event.id,
                article_id=article_id,
                match_type=match.match_type if match else "new_event",
                match_score=match.match_score if match else None,
                is_survivor=is_new_event,
            )
        )

        await _upsert_entities(session, event.id, shared.get("entities") or [])
        event_id = event.id

    # Rebuild projection + run perspective/impact correlation in fresh scopes
    # so a long LLM call doesn't hold the row transaction open.
    await _rebuild_projection(event_id)
    has_news = await _correlate_event(event_id)
    await _generate_pipeline_briefs(event_id, has_news)
    if has_news:
        try:
            await link_event_threads(event_id)
        except Exception:
            # Threads are additive; never fail the correlation stage over them.
            logger.exception("thread_linking_failed", event_id=str(event_id))

    await stream.publish(stream.EVENT_UPDATES, EventUpdateMessage(event_id=str(event_id)).model_dump())


async def _first_chunk_embedding(session, article_id: uuid.UUID) -> list[float] | None:
    result = await session.execute(
        text(
            "SELECT embedding FROM article_chunks WHERE article_id = :aid ORDER BY chunk_index LIMIT 1"
        ),
        {"aid": str(article_id)},
    )
    row = result.first()
    if row and row.embedding is not None:
        raw = row.embedding
        if isinstance(raw, str):
            return json.loads(raw)
        return list(raw)
    return None


async def _upsert_entities(session, event_id: uuid.UUID, entities: list[dict]) -> None:
    for extracted in entities[:15]:
        name = (extracted.get("name") or "").strip()
        if not name:
            continue
        slug = slugify(name)
        stmt = (
            pg_insert(Entity)
            .values(
                id=uuid.uuid4(),
                slug=slug,
                name=name,
                entity_type=extracted.get("type", "organization"),
            )
            .on_conflict_do_nothing(index_elements=["slug"])
            .returning(Entity.id)
        )
        result = await session.execute(stmt)
        entity_id = result.scalar_one_or_none()
        if entity_id is None:
            existing = await session.execute(select(Entity.id).where(Entity.slug == slug))
            entity_id = existing.scalar_one_or_none()
        if entity_id is None:
            continue
        link = (
            pg_insert(EventEntity)
            .values(
                id=uuid.uuid4(),
                event_id=event_id,
                entity_id=entity_id,
                role=extracted.get("role", "affected"),
            )
            .on_conflict_do_nothing(
                index_elements=["event_id", "entity_id", "role"]
            )
        )
        await session.execute(link)


async def _rebuild_projection(event_id: uuid.UUID) -> None:
    """Merge member enrichments into the served projection.

    Never merge identity, never inflate impact: lens fields are merged
    field-by-field preferring authoritative sources (NVD for CVSS, KEV for
    exploitation); disclosed values are attributed once.
    """
    async with session_scope() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT e.shared_fields, e.lens_fields, e.summary, e.event_type, s.slug AS source_slug,
                           s.country AS source_country,
                           ri.raw ->> 'sourcecountry' AS gdelt_country,
                           ri.classification AS classification
                    FROM event_memberships em
                    JOIN articles a ON a.id = em.article_id
                    JOIN enrichments e ON e.article_id = a.id
                    JOIN raw_items ri ON ri.id = a.raw_item_id
                    JOIN sources s ON s.id = ri.source_id
                    WHERE em.event_id = :eid
                    ORDER BY em.created_at
                    """
                ),
                {"eid": str(event_id)},
            )
        ).mappings().all()
        if not rows:
            return

        cyber: dict = {}
        finance: dict = {}
        summaries: list[str] = []
        event_types: list[str] = []
        source_slugs: list[str] = []
        role_interests: set[str] = set()
        origins: dict[str, int] = {}
        unknown_origins = 0
        for row in rows:
            source_slugs.append(row["source_slug"])
            role_interests.update((row["classification"] or {}).get("role_interests") or [])
            origin = row["source_country"] or gdelt_country_to_iso(row["gdelt_country"])
            if origin:
                origins[origin] = origins.get(origin, 0) + 1
            else:
                unknown_origins += 1
            if row["summary"]:
                summaries.append(row["summary"])
            if row["event_type"]:
                event_types.append(row["event_type"])
            row_finance = (row["lens_fields"] or {}).get("finance") if row["lens_fields"] else None
            if row_finance:
                for ticker in row_finance.get("tickers") or []:
                    finance.setdefault("tickers", [])
                    if ticker not in finance["tickers"]:
                        finance["tickers"].append(ticker)
                if row_finance.get("sector") and not finance.get("sector"):
                    finance["sector"] = row_finance["sector"]
                if row_finance.get("catalyst") and not finance.get("catalyst"):
                    finance["catalyst"] = row_finance["catalyst"]
                # Prefer the highest-confidence price read; never average —
                # a disclosed read is attributed once (no impact inflation).
                pi = row_finance.get("price_impact")
                if pi and (pi.get("confidence") or 0) >= (
                    (finance.get("price_impact") or {}).get("confidence") or 0
                ):
                    finance["price_impact"] = pi
            row_lens = (row["lens_fields"] or {}).get("cyber") if row["lens_fields"] else None
            if not row_lens:
                continue
            slug = row["source_slug"]
            for cve in row_lens.get("cve_ids") or []:
                cyber.setdefault("cve_ids", [])
                if cve not in cyber["cve_ids"]:
                    cyber["cve_ids"].append(cve)
            if row_lens.get("cvss") and (slug == "nvd" or not cyber.get("cvss")):
                if row_lens["cvss"].get("score") is not None:
                    cyber["cvss"] = row_lens["cvss"]
            if row_lens.get("exploitation") and (slug == "cisa_kev" or not cyber.get("exploitation")):
                if any(v is not None for v in row_lens["exploitation"].values()):
                    cyber["exploitation"] = row_lens["exploitation"]
            if row_lens.get("affected") and len(row_lens["affected"]) > len(cyber.get("affected", [])):
                cyber["affected"] = row_lens["affected"]
            if row_lens.get("remediation") and any(
                v is not None for v in row_lens["remediation"].values()
            ):
                cyber.setdefault("remediation", row_lens["remediation"])
            for cm in row_lens.get("control_mapping") or []:
                cyber.setdefault("control_mapping", [])
                if cm not in cyber["control_mapping"]:
                    cyber["control_mapping"].append(cm)
            for cwe in row_lens.get("weakness") or []:
                cyber.setdefault("weakness", [])
                if cwe not in cyber["weakness"]:
                    cyber["weakness"].append(cwe)

        event = await session.get(Event, event_id)
        if event is None:
            return
        # Prefer a news-article summary (readable) over raw CVE text when present.
        event.summary = summaries[-1] if summaries else event.summary
        event.projection = {
            "event_type": max(set(event_types), key=event_types.count) if event_types else None,
            "source_count": len(rows),
            "source_slugs": sorted(set(source_slugs)),
            "role_interests": sorted(role_interests),
            # Origin-country distribution of the coverage — the axis Prism
            # measures balance on (vs. Ground News' US left/right axis).
            "coverage": {
                "origins": origins,
                "unknown": unknown_origins,
                "single_origin": len(origins) == 1 and len(rows) >= 2,
            },
            "cyber": cyber or None,
            "finance": finance or None,
        }
        event.last_updated_at = func.now()


async def _correlate_event(event_id: uuid.UUID) -> None:
    """Perspective grouping + impact propagation over the event's members."""
    async with session_scope() as session:
        members = (
            await session.execute(
                text(
                    """
                    SELECT a.id AS article_id, e.summary, e.shared_fields,
                           s.name AS source_name, s.country AS source_country,
                           s.slug AS source_slug
                    FROM event_memberships em
                    JOIN articles a ON a.id = em.article_id
                    JOIN enrichments e ON e.article_id = a.id
                    JOIN raw_items ri ON ri.id = a.raw_item_id
                    JOIN sources s ON s.id = ri.source_id
                    WHERE em.event_id = :eid
                    ORDER BY em.created_at
                    """
                ),
                {"eid": str(event_id)},
            )
        ).mappings().all()
        event = await session.get(Event, event_id)
        event_summary = event.summary if event else ""
    if not members:
        return False

    settings = get_settings()
    has_news = any(m["source_slug"] not in ("nvd", "cisa_kev") for m in members)

    if has_news:
        article_lines = []
        for m in members:
            stance = ((m["shared_fields"] or {}).get("stance") or {})
            article_lines.append(
                f"- id={m['article_id']} source={m['source_name']} country={m['source_country'] or '?'} "
                f"stance={stance.get('label') or 'unknown'} summary={m['summary'] or '(none)'}"
            )
        prompt = fetch_prompt("perspective-impact")
        messages = prompt.compile(event_summary=event_summary or "(no summary)", articles="\n".join(article_lines))
        result = await structured_chat(
            model=settings.prism_model_correlate,
            messages=messages,
            output_model=CorrelationResult,
            trace_name="perspective-impact",
            metadata={"stage": "correlation", "event_id": str(event_id)},
            langfuse_prompt=prompt if prompt.version else None,
        )
    else:
        result = _deterministic_correlation(members)

    valid_article_ids = {str(m["article_id"]) for m in members}
    async with session_scope() as session:
        # Idempotent rebuild: perspectives/impacts are derived data.
        await session.execute(delete(Perspective).where(Perspective.event_id == event_id))
        await session.execute(delete(Impact).where(Impact.event_id == event_id))

        for group in result.perspectives:
            member_ids = [uuid.UUID(a) for a in group.article_ids if a in valid_article_ids]
            session.add(
                Perspective(
                    event_id=event_id,
                    label=group.label[:200],
                    origin_country=group.origin_country,
                    stance=group.stance,
                    member_articles=member_ids or None,
                    summary=group.summary,
                )
            )

        impact_ids: list[uuid.UUID] = []
        for imp in result.impacts[:20]:
            impact_id = uuid.uuid4()
            parent_id = None
            if imp.parent_index is not None and 0 <= imp.parent_index < len(impact_ids):
                parent_id = impact_ids[imp.parent_index]
            entity_id = await _resolve_entity(session, imp.entity)
            session.add(
                Impact(
                    id=impact_id,
                    event_id=event_id,
                    entity_id=entity_id,
                    effect=imp.effect[:200],
                    direction=imp.direction,
                    horizon=imp.horizon,
                    confidence=imp.confidence,
                    parent_impact_id=parent_id,
                    provenance={"entity_name": imp.entity},
                )
            )
            impact_ids.append(impact_id)

    return has_news


async def _generate_pipeline_briefs(event_id: uuid.UUID, has_news: bool) -> None:
    """Hybrid brief strategy at pipeline time (regenerated on new members).

    News events: one LLM call for the general brief + the event's primary
    lens. Other lenses are generated on demand by the API and cached.
    CVE-record-only events: composed template briefs, zero LLM cost.
    """
    async with session_scope() as session:
        row = (
            await session.execute(
                text("SELECT sector, summary, projection FROM events WHERE id = :eid"),
                {"eid": str(event_id)},
            )
        ).mappings().first()
    if row is None:
        return
    projection = row["projection"] or {}

    try:
        if not has_news:
            briefs = template_briefs(projection, row["summary"])
        else:
            lenses = ["general"]
            primary = primary_lens_for(row["sector"])
            if primary != "general":
                lenses.append(primary)
            briefs = await generate_briefs(event_id, lenses)
        await persist_briefs(event_id, briefs)
    except Exception:
        # Briefs are additive; never fail the correlation stage over them.
        logger.exception("pipeline_briefs_failed", event_id=str(event_id))


def _deterministic_correlation(members) -> CorrelationResult:
    """CVE-record-only events: advisory framing + impacts from enrichment."""
    from correlation.schemas import CorrelatedImpact, PerspectiveGroup

    impacts: list[CorrelatedImpact] = []
    seen: set[tuple[str, str]] = set()
    for m in members:
        for imp in ((m["shared_fields"] or {}).get("impacts") or [])[:5]:
            key = (imp.get("entity", ""), imp.get("effect", ""))
            if key in seen:
                continue
            seen.add(key)
            impacts.append(
                CorrelatedImpact(
                    entity=imp.get("entity", "affected systems"),
                    effect=imp.get("effect", "patch_required"),
                    direction=imp.get("direction", "negative"),
                    horizon=imp.get("horizon", "days"),
                    confidence=float(imp.get("confidence", 0.8)),
                )
            )
    return CorrelationResult(
        perspectives=[
            PerspectiveGroup(
                label="Advisory record",
                stance="neutral",
                origin_country="US",
                article_ids=[str(m["article_id"]) for m in members],
                summary="Authoritative vulnerability database records (NVD / CISA KEV).",
            )
        ],
        impacts=impacts,
    )


async def _resolve_entity(session, name: str) -> uuid.UUID | None:
    slug = slugify(name)
    result = await session.execute(select(Entity.id).where(Entity.slug == slug))
    return result.scalar_one_or_none()
