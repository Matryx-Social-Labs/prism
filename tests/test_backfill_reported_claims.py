"""The reported claims the direct-only gate dropped come back — and nothing else moves.

Between #226 (27 Sep, 19:26 UTC) and #241 the write-time gate stored only
quotes, so Indian-language articles lost the words their articles report
("…ಎಂದು ಜಿಲ್ಲಾಧಿಕಾರಿ ಸಂಗಪ್ಪ ಹೇಳಿದರು"). The extractor's own output is still on
each row, so the backfill re-runs today's gate on it and replaces the claims —
the one field it may touch.
"""

import json
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from enrichment.claims import verify_claims
from enrichment.schemas import ArticleExtraction
from tools.backfill_reported_claims import run

REPORTED = "ನಗರವನ್ನು ಸ್ವಚ್ಛ ಹಾಗೂ ವಾಸಯೋಗ್ಯವಾಗಿಡುವಲ್ಲಿ ಪೌರಕಾರ್ಮಿಕ ಪಾತ್ರ ಅತ್ಯಂತ ಮಹತ್ವದ್ದಾಗಿದೆ"
QUOTED = "ಪೌರಕಾರ್ಮಿಕರ ಆರೋಗ್ಯ ತಪಾಸಣೆಗೆ ಶಿಬಿರ ಆಯೋಜಿಸಲಾಗುವುದು"
BODY = f"ಬಾಗಲಕೋಟೆ: {REPORTED} ಎಂದು ಜಿಲ್ಲಾಧಿಕಾರಿ ಸಂಗಪ್ಪ ಹೇಳಿದರು. ‘{QUOTED}’ ಎಂದು ಅವರು ತಿಳಿಸಿದರು."
RAW = {
    "shared": {
        "event_type": "other", "headline": "Civic workers honoured", "headline_summary": "Civic workers honoured in Bagalkot.",
        "reader_brief": "The district honoured its civic workers.", "regions": ["IN", "IN-KA"],
        "entities": [{"name": "Sangappa", "type": "person", "role": "actor"}],
        "claims": [{"speaker": "Sangappa", "quote_text": REPORTED}, {"speaker": "Sangappa", "quote_text": QUOTED}],
    },
    "finance": {"tickers": ["SBIN"], "catalyst": "other"},
}
LENS = {"finance": {"tickers": ["SBIN"], "catalyst": "other"}, "cyber": {"weakness": ["CWE-79"]}}
# Every column but the claims, as Postgres prints them: the backfill must not change a byte of any.
UNTOUCHED = text(
    "SELECT (shared_fields - 'claims')::text AS shared_rest, summary, event_type, occurred_at, sentiment, model, "
    "lens_fields::text AS lens, raw_model_output::text AS raw FROM enrichments WHERE id = :i"
)


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _article(language: str) -> uuid.UUID:
    """An article stored by the direct-only gate: its quote kept, its report dropped."""
    shared = ArticleExtraction.model_validate(RAW).shared
    stored, _ = verify_claims(shared.claims, BODY)  # the gate as it was: no language, quotes only
    shared_fields = shared.model_copy(update={"claims": stored}).model_dump()
    raw_item, article, enrichment = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with session_scope() as s:
        source = (await s.execute(
            text("INSERT INTO sources (id, slug, name, source_type) VALUES (gen_random_uuid(), :s, :s, 'rss') RETURNING id"),
            {"s": f"br-{uuid.uuid4().hex[:8]}"})).scalar_one()
        await s.execute(
            text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, relevance, language) "
                 "VALUES (:i, :s, :x, :u, 't', '{}'::jsonb, 'relevant', :l)"),
            {"i": str(raw_item), "s": str(source), "x": raw_item.hex, "u": f"https://example.test/{raw_item.hex}", "l": language})
        await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                             "VALUES (:i, :r, :t, 'direct', 20)"), {"i": str(article), "r": str(raw_item), "t": BODY})
        await s.execute(
            text("INSERT INTO enrichments (id, article_id, event_type, summary, sentiment, shared_fields, lens_fields, "
                 "raw_model_output, model) VALUES (:i, :a, 'other', 'Civic workers honoured in Bagalkot.', 0.2, "
                 "CAST(:sf AS jsonb), CAST(:lf AS jsonb), CAST(:raw AS jsonb), 'openrouter:test')"),
            {"i": str(enrichment), "a": str(article), "sf": json.dumps(shared_fields, ensure_ascii=False),
             "lf": json.dumps(LENS), "raw": json.dumps(RAW, ensure_ascii=False)})
    return enrichment


async def _row(enrichment: uuid.UUID) -> tuple[dict, list]:
    async with session_scope() as s:
        rest = dict((await s.execute(UNTOUCHED, {"i": str(enrichment)})).mappings().one())
        claims = (await s.execute(text("SELECT shared_fields -> 'claims' FROM enrichments WHERE id = :i"),
                                  {"i": str(enrichment)})).scalar_one()
    return rest, [c["quote_text"] for c in claims]


async def _now():
    async with session_scope() as s:
        return (await s.execute(text("SELECT now()"))).scalar_one()


async def test_apply_restores_the_dropped_report_and_touches_nothing_else():
    if not await _db_reachable():
        pytest.skip("no database")
    since = await _now()
    kn, en = await _article("kn"), await _article("en")
    before_kn, claims_kn = await _row(kn)
    before_en, claims_en = await _row(en)
    assert claims_kn == [QUOTED] and claims_en == [QUOTED]  # the report was dropped at write time

    dry = await run(since, apply=False)
    assert (dry["articles"], dry["claims"]) == (1, 1)  # the Kannada article; English stays quotes only
    assert await _row(kn) == (before_kn, [QUOTED])  # a dry run writes nothing

    done = await run(since, apply=True)
    assert (done["articles"], done["claims"], done["cost"]) == (1, 1, 0.0)
    after_kn, claims_kn = await _row(kn)
    assert claims_kn == [REPORTED, QUOTED]
    assert after_kn == before_kn  # summary, entities, lens fields, tickers, cyber facts, raw output: byte-identical
    assert await _row(en) == (before_en, [QUOTED])

    again = await run(since, apply=True)
    assert again["articles"] == 0  # idempotent: the row now matches today's gate
