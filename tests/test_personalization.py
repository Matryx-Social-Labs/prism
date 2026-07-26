"""Milestone A checks: taxonomy validation, lens applicability, interests parsing."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common.db import session_scope
from common.taxonomy import TAXONOMY, valid_subsector
from correlation.briefs import available_lenses

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


def test_valid_subsector():
    assert valid_subsector("sports", "cricket") == "cricket"
    assert valid_subsector("sports", "chess") is None
    assert valid_subsector("nonsense", "cricket") is None
    assert valid_subsector("other", None) is None


def test_available_lenses_cricket_story_offers_reader_only():
    projection = {"source_slugs": ["espncricinfo"], "role_interests": []}
    assert available_lenses(projection, "sports") == ["reader"]


def test_available_lenses_cyber_fields():
    projection = {"cyber": {"cve_ids": ["CVE-2026-1"]}}
    assert "cyber" in available_lenses(projection, "politics")


def test_available_lenses_role_interest():
    projection = {"role_interests": ["markets"]}
    lenses = available_lenses(projection, "politics")
    assert "markets" in lenses and "cyber" not in lenses


def test_available_lenses_sector_and_cached_brief():
    assert "cyber" in available_lenses({}, "cybersecurity")
    assert "markets" in available_lenses({}, "business")
    # a cached brief keeps a lens offered even without current evidence
    assert "markets" in available_lenses({"lens_briefs": {"markets": "x"}}, "sports")


def test_every_lens_slug_known():
    from common.lenses import LENSES
    projection = {"cyber": {"a": 1}, "finance": {"b": 2}, "role_interests": []}
    assert set(available_lenses(projection, "cybersecurity")) <= set(LENSES)


def test_feed_spec_taxonomy_consistency():
    from ingestion.rss import FEEDS
    for spec in FEEDS:
        if spec.sector is not None:
            assert spec.sector in TAXONOMY, spec.slug
        if spec.subsector is not None:
            assert spec.subsector in TAXONOMY[spec.sector], spec.slug


def test_thread_judgement_coercion():
    from correlation.schemas import ThreadLinkResult

    # dict-wrapped judgements + string booleans (observed Ollama drift shapes)
    result = ThreadLinkResult.model_validate(
        {"judgements": {"0": {"index": 0, "related": "yes", "direction": "candidate_causes_event"}}}
    )
    assert result.judgements[0].related is True
    assert ThreadLinkResult.model_validate({"judgements": None}).judgements == []


def test_coverage_single_origin_shape():
    from common.countries import gdelt_country_to_iso

    assert gdelt_country_to_iso("India") == "IN"
    assert gdelt_country_to_iso("united states") == "US"
    assert gdelt_country_to_iso("Atlantis") is None
    assert gdelt_country_to_iso(None) is None


def test_template_briefs_structured():
    from correlation.briefs import template_briefs

    b = template_briefs(
        {
            "cyber": {
                "cve_ids": ["CVE-2026-1"],
                "cvss": {"score": 9.8, "severity": "critical"},
                "exploitation": {"kev_listed": True},
                "remediation": {"action": "Upgrade to 7.2.12"},
                "affected": [{"vendor": "Fortinet", "product": "FortiOS"}],
                "control_mapping": [{"framework": "NIST", "control": "SI-2"}],
            }
        },
        None,
    )
    assert b["reader"]["text"] and b["cyber"]["text"]
    assert "Upgrade to 7.2.12" in b["cyber"]["points"]


async def test_lens_ranks_the_world_it_does_not_filter_it():
    """A lens is a way of RE-READING the world, not a filter that shrinks it.

    REGRESSION: the feed used `sectors = active_lens.sectors` as a hard SQL
    filter when the reader had no explicit interests. The cyber lens declares
    sectors=["cybersecurity"], so every signed-in cyber reader got a
    cybersecurity-only feed — no elections, no markets, no world news. The lens
    must shape the feed through ranking weights instead.

    Same principle already settled for languages: hard-filtering a news feed
    hides major events entirely.
    """
    if not await _db_reachable():
        pytest.skip("no database")

    async with session_scope() as session:
        rows = (
            await session.execute(
                text("SELECT DISTINCT sector FROM events WHERE sector IS NOT NULL LIMIT 3")
            )
        ).scalars().all()
    if len(rows) < 2:
        pytest.skip("needs at least two classified sectors")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/api/v1/feed", params={"lens": "cyber", "limit": 60, "sort": "top"})
        assert r.status_code == 200
        sectors = {i["sector"] for i in r.json()["items"] if i["sector"]}

    # The exact mix depends on the corpus; the invariant is that a pro lens never
    # collapses the feed to its own sector.
    assert sectors - {"cybersecurity"}, (
        f"cyber lens returned only {sectors} — the lens is filtering the feed, not ranking it"
    )
