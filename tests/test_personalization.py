"""Milestone A checks: taxonomy validation, lens applicability, interests parsing."""

from common.taxonomy import TAXONOMY, valid_subsector
from correlation.briefs import available_lenses


def test_valid_subsector():
    assert valid_subsector("sports", "cricket") == "cricket"
    assert valid_subsector("sports", "chess") is None
    assert valid_subsector("nonsense", "cricket") is None
    assert valid_subsector("other", None) is None


def test_available_lenses_cricket_story_offers_general_only():
    projection = {"source_slugs": ["espncricinfo"], "role_interests": []}
    assert available_lenses(projection, "sports") == ["general"]


def test_available_lenses_cyber_fields():
    projection = {"cyber": {"cve_ids": ["CVE-2026-1"]}}
    assert "cyber_grc" in available_lenses(projection, "politics")


def test_available_lenses_role_interest():
    projection = {"role_interests": ["finance_trader"]}
    lenses = available_lenses(projection, "politics")
    assert "finance_trader" in lenses and "cyber_grc" not in lenses


def test_available_lenses_sector_and_cached_brief():
    assert "cyber_grc" in available_lenses({}, "cybersecurity")
    assert "finance_trader" in available_lenses({}, "business")
    # a cached brief keeps a lens offered even without current evidence
    assert "finance_trader" in available_lenses({"lens_briefs": {"finance_trader": "x"}}, "sports")


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
