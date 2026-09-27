"""The write-time gate knows the article's language.

Reported speech ("…ಎಂದು ಜಿಲ್ಲಾಧಿಕಾರಿ ಸಂಗಪ್ಪ ಹೇಳಿದರು") is kept only for an
Indian-language article (founder decision, 28 Sep). The enrichment consumer is
where claims are stored, so it must hand verify_claims the raw item's language:
without it every Kannada report would still be dropped as "not quoted".
"""

import json
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import enrichment.consumer as ec
from common.db import session_scope

QUOTE = "ನಗರವನ್ನು ಸ್ವಚ್ಛ ಹಾಗೂ ವಾಸಯೋಗ್ಯವಾಗಿಡುವಲ್ಲಿ ಪೌರಕಾರ್ಮಿಕ ಪಾತ್ರ ಅತ್ಯಂತ ಮಹತ್ವದ್ದಾಗಿದೆ"
BODY = f"ಬಾಗಲಕೋಟೆ: {QUOTE} ಎಂದು ಜಿಲ್ಲಾಧಿಕಾರಿ ಸಂಗಪ್ಪ ಹೇಳಿದರು. ನಗರಸಭೆ ಸಭಾಭವನದಲ್ಲಿ ಕಾರ್ಯಕ್ರಮ ನಡೆಯಿತು."
EXTRACTION = {"shared": {"event_type": "other", "headline_summary": "Civic workers honoured in Bagalkot.",
                         "claims": [{"speaker": "Sangappa", "quote_text": QUOTE}]}}


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _stored_claims(monkeypatch, language: str) -> list:
    """Through handle_classified_item on the reused-extraction path: a second feed
    carrying a URL already extracted, so no model is called."""

    async def _no_embeddings(chunks):
        return [[0.0] * 768 for _ in chunks]

    async def _no_publish(*_a, **_k):
        return None

    monkeypatch.setattr(ec, "embed_texts", _no_embeddings)
    monkeypatch.setattr(ec.stream, "publish", _no_publish)
    url = f"https://example.test/{uuid.uuid4().hex}"
    first_raw, second_raw, article = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with session_scope() as s:
        source = (await s.execute(
            text("INSERT INTO sources (id, slug, name, source_type) VALUES (gen_random_uuid(), :s, :s, 'rss') "
                 "RETURNING id"), {"s": f"rs-{uuid.uuid4().hex[:8]}"})).scalar_one()
        for raw in (first_raw, second_raw):
            await s.execute(
                text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, relevance, classification, language) "
                     "VALUES (:i, :s, :x, :u, 't', '{}'::jsonb, 'relevant', '{}'::jsonb, :l)"),
                {"i": str(raw), "s": str(source), "x": raw.hex, "u": url, "l": language},
            )
        await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                             "VALUES (:i, :r, :t, 'body', 12)"), {"i": str(article), "r": str(first_raw), "t": BODY})
        await s.execute(text("INSERT INTO enrichments (id, article_id, model, raw_model_output) "
                             "VALUES (gen_random_uuid(), :a, 'openrouter:test', CAST(:p AS jsonb))"),
                        {"a": str(article), "p": json.dumps(EXTRACTION)})

    await ec.handle_classified_item({"raw_item_id": str(second_raw)})

    async with session_scope() as s:
        shared = (await s.execute(
            text("SELECT e.shared_fields FROM enrichments e JOIN articles a ON a.id = e.article_id "
                 "WHERE a.raw_item_id = :r"), {"r": str(second_raw)})).scalar_one()
    return shared.get("claims") or []


async def test_a_kannada_report_is_stored(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    assert [c["quote_text"] for c in await _stored_claims(monkeypatch, "kn")] == [QUOTE]


async def test_without_an_indian_language_it_is_not(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    assert await _stored_claims(monkeypatch, "en") == []
