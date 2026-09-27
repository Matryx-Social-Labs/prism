"""Cyber facts are stored only on an article classified cyber.

The extractor fills its cyber lens on any article, and the enrichment stored it
unconditionally: a child's burn death carried CWE-284 and a pooja NIST AC-6 —
260 events in 7 days (audit, 2026-09-27). The classification already says
whether the article is about computer security; the store asks it.
"""

import json
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import enrichment.consumer as ec
from common.db import session_scope

EXTRACTION = {
    "shared": {"event_type": "other", "headline_summary": "A child died of burns at home."},
    "cyber": {"weakness": ["CWE-284"], "control_mapping": [{"framework": "NIST_800-53", "control": "AC-6"}]},
}


@pytest.mark.parametrize(("classification", "cyber"), [
    ({"sector": "cybersecurity", "subject_path": "tech.security.breaches"}, True),
    ({"sector": "technology", "subject_path": "tech.ai"}, True),
    ({"sector": "politics", "role_interests": ["cyber"]}, True),
    ({"sector": "other", "subject_path": "civic.accidents"}, False),
    ({"sector": "business", "role_interests": ["markets"]}, False),
    ({}, False),
])
def test_what_counts_as_classified_cyber(classification, cyber):
    assert ec.cyber_classified(classification) is cyber


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _stored_lens_fields(monkeypatch, classification: dict) -> dict | None:
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
                 "RETURNING id"), {"s": f"cy-{uuid.uuid4().hex[:8]}"})).scalar_one()
        for raw in (first_raw, second_raw):
            await s.execute(
                text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, relevance, classification) "
                     "VALUES (:i, :s, :x, :u, 't', '{}'::jsonb, 'relevant', CAST(:c AS jsonb))"),
                {"i": str(raw), "s": str(source), "x": raw.hex, "u": url, "c": json.dumps(classification)},
            )
        await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                             "VALUES (:i, :r, 'the body', 'body', 2)"), {"i": str(article), "r": str(first_raw)})
        await s.execute(text("INSERT INTO enrichments (id, article_id, model, raw_model_output) "
                             "VALUES (gen_random_uuid(), :a, 'openrouter:test', CAST(:p AS jsonb))"),
                        {"a": str(article), "p": json.dumps(EXTRACTION)})

    await ec.handle_classified_item({"raw_item_id": str(second_raw)})

    async with session_scope() as s:
        return (await s.execute(
            text("SELECT e.lens_fields FROM enrichments e JOIN articles a ON a.id = e.article_id "
                 "WHERE a.raw_item_id = :r"), {"r": str(second_raw)})).scalar_one()


async def test_a_non_cyber_article_stores_no_cyber_facts(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    lens = await _stored_lens_fields(monkeypatch, {"sector": "other", "subject_path": "civic.accidents"})
    assert "cyber" not in (lens or {})


async def test_a_cyber_article_keeps_them(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    lens = await _stored_lens_fields(monkeypatch, {"sector": "cybersecurity", "subject_path": "tech.security"})
    assert lens["cyber"]["weakness"] == ["CWE-284"]
