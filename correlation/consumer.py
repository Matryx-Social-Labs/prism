"""Phase 4 — correlation: canonicalize into events, perspectives, impacts.

Consumes enriched.items. Assigns each enriched article to an existing event
(match cascade in clustering.py, trail persisted on event_memberships) or
creates a new one. Upserts entities, rebuilds the event projection, then
runs perspective grouping + impact propagation and emits event.updates.
"""

import json
import time
import uuid

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from common.config import get_settings
from common.countries import gdelt_country_to_iso
from common.db import session_scope
from common.entities import drop_source_names, source_name_slugs
from common.llm import structured_chat
from common.logging import get_logger
from common.models import (
    Article,
    ArticleEntity,
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
from common.stream import get_redis
from common.text import entity_slug
from correlation.briefs import persist_briefs, primary_lens_for, template_briefs
from correlation.clustering import find_event
from correlation.schemas import CorrelationResult, EventAnalysis
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
        # The outlet is not an actor in its own coverage: left in, `prajavani` was
        # the most-shared "entity" across a 139-article over-merge, i.e. the thing
        # doing the merging.
        entity_names = [e["name"] for e in (shared.get("entities") or []) if e.get("name")]
        entity_slugs = [entity_slug(n) for n in await drop_source_names(session, entity_names)]

        match = await find_event(
            session,
            cve_ids=cve_ids,
            url=url,
            title=title,
            published_at=published_at,
            embedding=embedding,
            entity_slugs=entity_slugs or None,
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

        # State codes (ISO 3166-2, e.g. IN-KA) from a state-edition feed must
        # survive into the event's regions — even when a new event's shared
        # extraction returned only country-level regions, or an existing event
        # was matched — so the feed can tier local(state) -> national.
        state_codes = [r for r in (classification.get("regions") or []) if "-" in r]
        if state_codes:
            merged = list(event.regions or [])
            merged += [c for c in state_codes if c not in merged]
            if merged != list(event.regions or []):
                event.regions = merged

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

        await _upsert_entities(session, event.id, shared.get("entities") or [], article_id)
        event_id = event.id

    # Real-time path: rebuild the served projection (fast, DB-only) and publish so
    # the feed reflects the new coverage immediately — before any LLM runs.
    await _rebuild_projection(event_id)
    # Defer the expensive per-story analysis (perspectives/impacts/briefs/threads)
    # to the debounced sweeper: a burst of coverage for one story then costs a
    # single analysis pass, off the ingest hot path.
    await mark_event_dirty(event_id)


# ── Deferred analysis: real-time attach above, debounced LLM analysis here ──

DIRTY_KEY = "dirty:events"
ANALYSIS_DEBOUNCE_S = 90  # coalesce a burst of coverage for one story into one pass
ANALYSIS_RETRY_BACKOFF_S = 300  # re-queue a failed analysis this far out (self-heals credit stalls)
SWEEP_BATCH = 20


async def mark_event_dirty(event_id: uuid.UUID) -> None:
    """Schedule a debounced analysis. Leading debounce (NX): the first article
    schedules it ANALYSIS_DEBOUNCE_S out; later coverage in the window rides the
    same pass (the sweeper re-reads all members at fire time)."""
    try:
        await get_redis().zadd(DIRTY_KEY, {str(event_id): time.time() + ANALYSIS_DEBOUNCE_S}, nx=True)
    except Exception:  # noqa: BLE001 — never fail ingest on the dirty-mark
        logger.exception("mark_event_dirty_failed", event_id=str(event_id))


async def run_due_analyses() -> int:
    """Drain events whose debounce has elapsed and analyze each once."""
    redis = get_redis()
    now = time.time()
    due = await redis.zrangebyscore(DIRTY_KEY, 0, now, start=0, num=SWEEP_BATCH)
    done = 0
    for raw in due:
        eid = raw.decode() if isinstance(raw, (bytes, bytearray)) else raw
        if not await redis.zrem(DIRTY_KEY, eid):
            continue  # another sweeper claimed it
        try:
            await analyze_event_now(uuid.UUID(eid))
            done += 1
        except Exception:
            logger.exception("deferred_analysis_failed", event_id=eid)
            # The event was already claimed (zrem above), so a transient failure — LLM
            # timeout, or credits exhausted mid-run — would otherwise leave it PERMANENTLY
            # un-analyzed (no perspectives/briefs) unless a new member happens to join.
            # Re-queue with backoff so it retries and self-heals when the LLM recovers.
            # ponytail: unbounded retry every ANALYSIS_RETRY_BACKOFF_S; add a cap only if a
            # poison event ever loops (the deferred_analysis_failed log will show it).
            try:
                await redis.zadd(DIRTY_KEY, {eid: now + ANALYSIS_RETRY_BACKOFF_S}, nx=True)
            except Exception:
                logger.exception("analysis_requeue_failed", event_id=eid)
    return done


async def analyze_event_now(event_id: uuid.UUID) -> None:
    """The deferred work: perspectives/impacts/briefs + thread linking + republish."""
    has_news, ran_llm = await _analyze_event(event_id)
    if has_news and ran_llm:
        try:
            await link_event_threads(event_id)
        except Exception:
            # Threads are additive; never fail analysis over them.
            logger.exception("thread_linking_failed", event_id=str(event_id))


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


async def _upsert_entities(
    session, event_id: uuid.UUID, entities: list[dict], article_id: uuid.UUID
) -> None:
    blocked = await source_name_slugs(session)
    for extracted in entities[:15]:
        name = (extracted.get("name") or "").strip()
        if not name:
            continue
        # Filtered here as well as at the gate: an outlet that reaches the graph
        # becomes a cast name, and `tv9kannada` led a live trending story.
        if entity_slug(name) in blocked:
            continue
        slug = entity_slug(name)
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
        # Both links, written together. The event-level one is what the rest of
        # the product reads; the article-level one is what the matcher weighs, so
        # an actor named by one absorbed article cannot speak for the whole event.
        await session.execute(
            pg_insert(ArticleEntity)
            .values(
                id=uuid.uuid4(),
                article_id=article_id,
                entity_id=entity_id,
                role=extracted.get("role", "affected"),
            )
            .on_conflict_do_nothing(index_elements=["article_id", "entity_id"])
        )
        link = (
            pg_insert(EventEntity)
            .values(
                id=uuid.uuid4(),
                event_id=event_id,
                entity_id=entity_id,
                role=extracted.get("role", "affected"),
            )
            .on_conflict_do_nothing(
                index_elements=["event_id", "entity_id"]
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
                           s.country AS source_country, s.language AS source_language,
                           s.publisher AS source_publisher,
                           ri.title AS article_title, ri.published_at AS published_at,
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
        # Distinct MASTHEADS, which is what 'single-origin' means to a reader:
        # one newsroom telling this, nobody corroborating it. Publisher rather
        # than source slug so The Hindu's six regional feeds count once.
        publishers: set[str] = set()
        # When the NEWS happened, as distinct from when Prism noticed it.
        latest_published: object = None
        languages: set[str] = set()
        best_headline: dict[str, dict] = {}  # lang -> most-recent member headline
        for row in rows:
            source_slugs.append(row["source_slug"])
            role_interests.update((row["classification"] or {}).get("role_interests") or [])
            # Per-language display headline: the cluster stays cross-language; the
            # feed renders each reader the headline in their preferred language (or
            # falls back to English). Keep the most recent title per language.
            lang = row["source_language"]
            if lang:
                languages.add(lang)
                title = row["article_title"]
                if title:
                    pub = row["published_at"]
                    cur = best_headline.get(lang)
                    if cur is None or (
                        pub is not None and (cur["_pub"] is None or pub > cur["_pub"])
                    ):
                        best_headline[lang] = {
                            "lang": lang,
                            "title": title,
                            "source_slug": row["source_slug"],
                            "published_at": pub.isoformat() if pub else None,
                            "_pub": pub,
                        }
            publishers.add(row["source_publisher"] or row["source_slug"])
            if row["published_at"] and (
                latest_published is None or row["published_at"] > latest_published
            ):
                latest_published = row["published_at"]
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
        # The FOUNDER's summary, not the newest member's.
        #
        # `rows` is ordered by em.created_at, so summaries[-1] was whichever
        # article joined most recently — while the title is copied from the
        # founding article at creation and never changes. Those are different
        # articles for any event with more than one member, so the headline and
        # the summary underneath it described different pieces of news. Measured
        # on production: 830 of 1,054 multi-member events, 79%.
        #
        # It is worst exactly where a reader notices. The lead story on the feed
        # read "AAIB explains to SC why AI171 crash report is getting delayed"
        # over a summary about a seafarer missing in the Black Sea, because one
        # late member had wrongly merged on the shared entity "Supreme Court".
        # One bad merge at the tail replaced the whole event's summary; the
        # founder's own summary ("Aircraft Accident Investigation Bureau informs
        # Supreme Court") matched its headline perfectly.
        #
        # Coherence beats freshness here: a headline and a summary about the same
        # article is the product's basic promise, and a stale-but-matching summary
        # is a far smaller defect than a mismatched one. Updating BOTH from the
        # newest member would also be coherent, but it rewrites the headline a
        # reader may have arrived on, which is a bigger product change than this.
        event.summary = summaries[0] if summaries else event.summary
        event.projection = {
            "event_type": max(set(event_types), key=event_types.count) if event_types else None,
            "source_count": len(rows),
            # The newest member's publication time. events.last_updated_at is
            # set to now() on every projection rebuild, so it records when the
            # INGEST ran, not when the news happened — the feed printed one
            # identical batch timestamp against every story, and 79% of events
            # (13,657 of 17,385) were more than six hours out, one by 7.7.
            # DESIGN.md reserves the mono provenance line for exactly this
            # claim, so it has to be the news's own clock.
            "latest_published_at": (
                latest_published.isoformat() if latest_published else None
            ),
            "source_slugs": sorted(set(source_slugs)),
            "role_interests": sorted(role_interests),
            # Languages this event is covered in + the per-language display headline
            # (drop the internal sort key). Feed filters/ranks + localises on these.
            "languages": sorted(languages),
            "headlines": [
                {k: v for k, v in h.items() if k != "_pub"}
                for h in sorted(best_headline.values(), key=lambda x: x["lang"])
            ],
            # Origin-country distribution of the coverage — the axis Prism
            # measures balance on (vs. Ground News' US left/right axis).
            "coverage": {
                "origins": origins,
                "unknown": unknown_origins,
                # ONE MASTHEAD, not one country. This was len(origins) == 1,
                # and origins are source COUNTRIES — so on an India-first feed
                # it fired on 97% of multi-article events (1,039 of 1,070) and
                # told a reader nothing. Counting publishers it fires on 57%,
                # which is the thing worth warning about: a story only one
                # newsroom is carrying, with no second account of it.
                "single_origin": len(publishers) == 1 and len(rows) >= 2,
            },
            "cyber": cyber or None,
            "finance": finance or None,
        }
        event.last_updated_at = func.now()


# Re-run the (LLM) analysis only when the membership crosses a tier — a
# burst of near-simultaneous members otherwise re-buys the same analysis
# once per article. Fibonacci-ish: early members change the story most.
REGEN_TIERS = {2, 3, 5, 8, 13, 21, 34}
# Single-source news has no competing perspective and its brief generates on
# demand — so it never triggers the LLM analysis here (the throughput win).
MIN_SOURCES_FOR_ANALYSIS = 2


async def _analyze_event(event_id: uuid.UUID) -> tuple[bool, bool]:
    """One pass per tier: perspectives + impacts + pipeline briefs.

    Returns (has_news, ran_llm/deterministic-analysis).
    """
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
        event_sector = event.sector if event else None
        event_regions = list(event.regions or []) if event else []
        event_projection = dict(event.projection or {}) if event else {}
        has_perspectives = (
            await session.execute(
                text("SELECT 1 FROM perspectives WHERE event_id = :eid LIMIT 1"),
                {"eid": str(event_id)},
            )
        ).first() is not None
    if not members:
        return False, False

    settings = get_settings()
    has_news = any(m["source_slug"] not in ("nvd", "cisa_kev") for m in members)

    # Single-source news: no competing perspectives; brief is generated on demand
    # on first view. Skip the LLM entirely — this is where most events land.
    if has_news and len(members) < MIN_SOURCES_FOR_ANALYSIS:
        return has_news, False

    if len(members) not in REGEN_TIERS and has_perspectives:
        return has_news, False  # between tiers: keep the existing analysis

    briefs: dict = {}
    if has_news:
        article_lines = []
        for m in members:
            stance = ((m["shared_fields"] or {}).get("stance") or {})
            article_lines.append(
                f"- id={m['article_id']} source={m['source_name']} country={m['source_country'] or '?'} "
                f"stance={stance.get('label') or 'unknown'} summary={m['summary'] or '(none)'}"
            )
        lenses = ["reader"]
        primary = primary_lens_for(event_sector)
        if primary != "reader":
            lenses.append(primary)
        lens_fields = {k: v for k, v in event_projection.items() if k in ("cyber", "finance") and v}
        prompt = fetch_prompt("event-analysis")
        messages = prompt.compile(
            event_summary=event_summary or "(no summary)",
            sector=event_sector or "unspecified",
            regions=", ".join(event_regions) or "unspecified",
            lenses=", ".join(lenses),
            articles="\n".join(article_lines),
            lens_fields=json.dumps(lens_fields, default=str)[:2500] or "(none)",
        )
        analysis = await structured_chat(
            model=settings.prism_model_correlate,
            messages=messages,
            output_model=EventAnalysis,
            trace_name="event-analysis",
            metadata={"stage": "correlation", "event_id": str(event_id)},
            langfuse_prompt=prompt if prompt.version else None,
        )
        result = analysis
        briefs = {
            slug: read
            for slug, read in analysis.briefs.model_dump().items()
            if slug in lenses and read and read.get("text")
        }
    else:
        result = _deterministic_correlation(members)
        briefs = template_briefs(event_projection, event_summary)

    valid_article_ids = {str(m["article_id"]) for m in members}
    async with session_scope() as session:
        # Idempotent rebuild: perspectives/impacts are derived data.
        await session.execute(delete(Perspective).where(Perspective.event_id == event_id))
        await session.execute(delete(Impact).where(Impact.event_id == event_id))

        for group in result.perspectives[:4]:  # cap for readability (prompt also asks for <=4)
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

    try:
        await persist_briefs(event_id, briefs)
    except Exception:
        # Briefs are additive; never fail the correlation stage over them.
        logger.exception("pipeline_briefs_failed", event_id=str(event_id))
    return has_news, True


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
    slug = entity_slug(name)
    result = await session.execute(select(Entity.id).where(Entity.slug == slug))
    return result.scalar_one_or_none()
