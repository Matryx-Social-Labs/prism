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
from common.llm import structured_chat
from common.logging import get_logger
from common.models import Article, ArticleChunk, Enrichment, FieldProvenance, RawItem, Source
from common.observability import fetch_prompt, observe
from common.schemas import EnrichedItemMessage
from common.text import chunk_text
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
            select(Article.id).where(Article.raw_item_id == raw_item_id)
        )
        if existing.scalar_one_or_none() is not None:
            return  # already enriched (stream replay)
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
            metadata=meta,
            langfuse_prompt=prompt if prompt.version else None,
            # claims/impacts have no news-side reader — correlation re-derives
            # impacts in event-analysis and nothing reads claims. Drop them from
            # the schema so the highest-volume LLM stage emits less (fewer output
            # tokens, less truncation risk on entities). CVE impacts come from the
            # deterministic cve_lens path, which still populates these fields.
            prune_fields={"claims", "impacts"},
        )
        model_used = f"ollama:{extract_model}"
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
        lens_fields = {}
        if extraction.cyber:
            lens_fields["cyber"] = extraction.cyber.model_dump()
        if extraction.finance:
            lens_fields["finance"] = extraction.finance.model_dump()
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
