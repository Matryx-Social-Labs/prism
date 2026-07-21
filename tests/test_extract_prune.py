"""Extraction schema pruning — the news LLM extract drops claims/impacts.

Those fields have no news-side reader (correlation re-derives impacts in
event-analysis; nothing reads claims), so structured_chat prunes them from the
schema shown to the model. cve_lens still populates them deterministically for
CVE records, so the pydantic model keeps the fields — validation fills the
defaults when the model omits them.
"""

from common.llm import _prune_schema_props
from enrichment.schemas import ArticleExtraction, SharedExtraction


def test_prune_removes_nested_props():
    schema = ArticleExtraction.model_json_schema()
    shared = schema["$defs"]["SharedExtraction"]["properties"]
    assert "claims" in shared and "impacts" in shared  # present before

    _prune_schema_props(schema, {"claims", "impacts"})

    shared = schema["$defs"]["SharedExtraction"]["properties"]
    assert "claims" not in shared and "impacts" not in shared
    # Fields we keep survive.
    assert {"entities", "regions", "stance", "headline_summary"} <= set(shared)


def test_prune_keeps_required_intact():
    schema = ArticleExtraction.model_json_schema()
    _prune_schema_props(schema, {"claims", "impacts"})
    req = schema["$defs"]["SharedExtraction"].get("required", [])
    assert "claims" not in req and "impacts" not in req
    assert "headline_summary" in req  # untouched required field stays


def test_model_validates_without_pruned_fields():
    # What the model returns once the schema no longer lists claims/impacts.
    extraction = ArticleExtraction.model_validate(
        {
            "shared": {
                "event_type": "other",
                "headline_summary": "A test event happened.",
                "entities": [{"name": "Acme", "type": "company", "role": "subject"}],
                "regions": ["IN"],
            }
        }
    )
    assert extraction.shared.claims == []
    assert extraction.shared.impacts == []
    assert extraction.shared.entities[0].name == "Acme"


def test_cve_lens_path_still_populates_impacts():
    # cve_lens builds SharedExtraction with impacts directly — must still work.
    shared = SharedExtraction(
        headline_summary="CVE-2024-0001 in Acme Widget is exploited.",
        impacts=[{"entity": "Acme Widget", "effect": "patch_required"}],
    )
    assert shared.impacts[0].entity == "Acme Widget"
