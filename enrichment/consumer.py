"""Phase 3 — enrichment: full text, schema-constrained extraction, embeddings.

Consumes classified.items. CVE-feed records are enriched deterministically
from their structured payload; news articles go through the LLM extractor
(shared schema + cyber lens in one call). Every value keeps field-level
provenance; the raw model output and model id are stored for
reproducibility. Article text is chunked + embedded for the agent.
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy import text as sa_text

from common import stream
from common.config import get_settings
from common.db import session_scope
from common.embeddings import embed_texts
from common.llm import REASONING_OFF, structured_chat
from common.logging import get_logger
from common.models import Article, ArticleChunk, Enrichment, FieldProvenance, RawItem, Source
from common.observability import fetch_prompt, observe
from common.schemas import EnrichedItemMessage
from common.securities import validated
from common.text import chunk_text
from enrichment.claims import verify_claims
from enrichment.cve_lens import extract_from_kev, extract_from_nvd
from enrichment.fulltext import retrieve_fulltext
from enrichment.schemas import ArticleExtraction

logger = get_logger(__name__)

MAX_EXTRACT_CHARS = 12000


@observe(name="enrichment-stage")
async def handle_classified_item(payload: dict) -> None:
    raw_item_id = uuid.UUID(payload["raw_item_id"])

    async with session_scope() as session:
        item = await session.get(RawItem, raw_item_id)
        if item is None or item.relevance != "relevant":
            return
        existing = await session.execute(
            select(Article.id).where(Article.raw_item_id == raw_item_id).limit(1)
        )
        if existing.first() is not None:
            return  # already enriched (stream replay, or a reclaimed twin that finished first)
        source = await session.get(Source, item.source_id)
        source_slug = source.slug if source else "unknown"
        source_id = item.source_id
        title = item.title
        body = item.body
        url = item.url
        raw = dict(item.raw)
        published_at = item.published_at
        sector = (item.classification or {}).get("sector")
        has_image = item.image_url is not None

    meta = {"stage": "enrichment", "source_slug": source_slug, "raw_item_id": str(raw_item_id)}
    settings = get_settings()

    # Pay for one extraction per URL, not one per feed that carried it.
    reused = await _extraction_for_same_url(url)

    # 1. Full text
    og_image: str | None = None
    if reused:
        clean_text, raw_model_output, model_used = reused[0], reused[1], reused[2]
        extraction = ArticleExtraction.model_validate(raw_model_output)
        tier = "duplicate_url"
        logger.info("enrichment_reused_for_duplicate_url", raw_item_id=str(raw_item_id), url=url)
    elif source_slug in ("nvd", "cisa_kev"):
        clean_text, tier = (body or title), "body"
    else:
        clean_text, tier, og_image = await retrieve_fulltext(url, body)
        if not clean_text:
            clean_text, tier = title, "title"

    # 2. Extraction — deterministic for CVE records, LLM for articles
    model_used: str
    if not reused:
        raw_model_output = None
    if reused:
        # extraction / model_used / raw_model_output were all set above. Falling
        # through here would reset raw_model_output to None and re-run the model,
        # which is the exact spend this branch exists to avoid.
        pass
    elif source_slug == "nvd":
        extraction = extract_from_nvd(raw)
        model_used = "deterministic:nvd"
    elif source_slug == "cisa_kev":
        extraction = extract_from_kev(raw)
        model_used = "deterministic:cisa_kev"
    else:
        extract_model = (
            settings.prism_model_extract_light
            if sector in ("sports", "entertainment", "health", "science")
            else settings.prism_model_extract
        )
        prompt = fetch_prompt("extract-shared")
        messages = prompt.compile(
            title=title,
            source=source_slug,
            published_at=str(published_at or "unknown"),
            text=clean_text[:MAX_EXTRACT_CHARS],
        )
        extraction = await structured_chat(
            model=extract_model,
            messages=messages,
            output_model=ArticleExtraction,
            trace_name="extract-shared",
            max_tokens=6000,
            reasoning=REASONING_OFF,
            metadata=meta,
            langfuse_prompt=prompt if prompt.version else None,
            # `impacts` stays pruned: correlation re-derives them in
            # event-analysis and nothing reads the extracted ones, so asking for
            # them costs output tokens on the highest-volume stage for nothing.
            # CVE impacts come from the deterministic cve_lens path regardless.
            #
            # `claims` is BACK. It was pruned on the same "nothing reads it"
            # reasoning, which was true and is the reason the perspectives layer
            # does not exist — the tagline promises every perspective and the
            # pipeline was told not to collect any.
            prune_fields={"impacts"},
        )
        # The ACTUAL provider, not a hardcoded one. This read "ollama:" while
        # llm_provider defaulted to openrouter and the OpenRouter key was set, so
        # every row claimed a provider that had not been called. The prefix is
        # load-bearing — correlation/consumer.py and tools/scratch.py both test
        # `startswith("deterministic:")` to spot CVE records — and it is the first
        # thing anyone reads when attributing spend, which is exactly how it
        # misled a spend investigation on 2026-08-03.
        model_used = f"{settings.llm_provider}:{extract_model}"
        raw_model_output = extraction.model_dump()

    # 3. Chunk + embed
    chunks = chunk_text(clean_text)
    embeddings = await embed_texts(chunks)

    # 4. Persist article, chunks, enrichment, provenance
    article_id = uuid.uuid4()
    enrichment_id = uuid.uuid4()
    shared = extraction.shared
    async with session_scope() as session:
        if og_image and not has_image:
            item = await session.get(RawItem, raw_item_id)
            if item is not None:
                item.image_url = og_image
        session.add(
            Article(
                id=article_id,
                raw_item_id=raw_item_id,
                clean_text=clean_text,
                retrieval_tier=tier,
                word_count=len(clean_text.split()),
            )
        )
        for idx, (text, vector) in enumerate(zip(chunks, embeddings, strict=True)):
            session.add(
                ArticleChunk(article_id=article_id, chunk_index=idx, text=text, embedding=vector)
            )
        # VERBATIM OR NOT STORED. The model is asked for a quote; whether it
        # actually copied one is checked here against the article, because a
        # fabricated quote renders exactly like a real one and no reader can tell.
        verified, claim_rejects = verify_claims(shared.claims, clean_text)
        shared = shared.model_copy(update={"claims": verified})
        if any(claim_rejects.values()):
            logger.info("claims_rejected", raw_item_id=str(raw_item_id), **claim_rejects)

        lens_fields = {}
        if extraction.cyber:
            lens_fields["cyber"] = extraction.cyber.model_dump()
        if extraction.finance:
            fin = extraction.finance.model_dump()
            # The one place a ticker enters the database. Everything downstream —
            # the event projection, the watchlist join, the digest's movers —
            # reads what is written here, so a symbol that cannot be traced to a
            # listed security is refused at this line rather than filtered at
            # each of the places it would later be shown. `raw_model_output`
            # above keeps the extractor's original list, so nothing is lost.
            fin["tickers"] = await validated(session, fin.get("tickers") or [])
            lens_fields["finance"] = fin
        session.add(
            Enrichment(
                id=enrichment_id,
                article_id=article_id,
                event_type=shared.event_type,
                summary=shared.headline_summary,
                occurred_at=_parse_date(shared.occurred_at),
                sentiment=shared.sentiment,
                shared_fields=shared.model_dump(),
                lens_fields=lens_fields or None,
                raw_model_output=raw_model_output,
                model=model_used,
            )
        )
        # Field-level provenance: single-source extraction in the prototype,
        # so every populated top-level field points at this item's source.
        populated = [
            f"shared.{name}"
            for name, value in shared.model_dump().items()
            if value not in (None, [], {})
        ]
        for lens_slug, lens_dump in lens_fields.items():
            populated += [
                f"{lens_slug}.{name}"
                for name, value in lens_dump.items()
                if value not in (None, [], {})
            ]
        for field_path in populated:
            session.add(
                FieldProvenance(
                    enrichment_id=enrichment_id,
                    field_path=field_path,
                    source_id=source_id,
                    confidence=None,
                )
            )

    await stream.publish(
        stream.ENRICHED_ITEMS,
        EnrichedItemMessage(
            raw_item_id=str(raw_item_id),
            article_id=str(article_id),
            enrichment_id=str(enrichment_id),
        ).model_dump(),
    )


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


async def _extraction_for_same_url(url: str | None) -> tuple[str, dict, str] | None:
    """An enrichment already produced for this exact URL, if there is one.

    534 URL groups in production arrive more than once — 533 of them CROSS-source,
    the same article reaching us through a national feed and a regional one under
    different external_ids. Dedupe keys on (source_id, external_id), so URL is
    never compared and both copies are fetched and sent to the model: 355 excess
    enrichments, entirely wasted spend.

    Reused rather than skipped. Skipping the second article would drop the record
    that a second feed carried it, and event membership is what corroboration and
    the match trail are built from. This keeps both articles and pays for one
    extraction — the embedding pass still runs locally, which is cheap.
    """
    if not url:
        return None
    async with session_scope() as session:
        row = (
            await session.execute(
                sa_text(
                    """
                    SELECT a.clean_text, e.raw_model_output, e.model
                    FROM enrichments e
                    JOIN articles a ON a.id = e.article_id
                    JOIN raw_items ri ON ri.id = a.raw_item_id
                    WHERE ri.url = :url AND e.raw_model_output IS NOT NULL
                    ORDER BY e.created_at ASC
                    LIMIT 1
                    """
                ),
                {"url": url},
            )
        ).first()
    if row and row.raw_model_output:
        return row.clean_text, row.raw_model_output, row.model
    return None
