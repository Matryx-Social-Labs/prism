# Enrichment Schema and Role Lenses

> **Intent, not the field list (2026-07-14).** The live extraction schema is `enrichment/schemas.py` (`SharedExtraction`: English headline, one-line summary, reader brief, entities, regions, verbatim-checked claims, lens fields); see [PIPELINE §5](./PIPELINE.md#5-enrichment). The multi-source provenance maps described below were not built as written.

Phase 3 turns a classified item into a structured, measurable record. Extraction is
schema-constrained: the model receives a typed schema and returns valid JSON, with fields the
article does not evidence returned as explicit nulls rather than omitted, so unknown and absent are
never conflated. Every value carries provenance back to the source that evidenced it. This is
ported from the EduThreat enrichment design.

Grounded preprocessing runs first, as in EduThreat: named-entity recognition over the article
grounds people, organizations, places, and (for cyber) products and vendors, and retrieval
augmentation narrows candidate labels before the extraction call.

## Shared schema (every story, every role)
```jsonc
{
  "event_type": "data_breach",        // controlled vocabulary per sector
  "headline_summary": "…",            // one-sentence neutral summary
  "occurred_at": "2026-07-10",        // event date, null if not stated
  "entities": [
    { "name": "Acme Corp", "type": "company", "role": "affected", "provenance": ["src_1"] },
    { "name": "Jane Doe",  "type": "person",  "role": "subject",  "provenance": ["src_2"] }
  ],
  "regions": ["US", "DE"],            // countries involved
  "stance": {                          // per-source stance, feeds perspective grouping
    "src_1": "critical_of_A",
    "src_2": "defends_A"
  },
  "claims": [                          // discrete factual claims, each with its source
    { "text": "…", "provenance": ["src_1"], "contested": true }
  ],
  "impacts": [                         // the "so what": affected entity + effect
    { "entity": "Acme Corp", "effect": "stock_drop", "horizon": "days",
      "direction": "negative", "confidence": 0.6, "provenance": ["src_3"] }
  ],
  "sentiment": -0.4,
  "provenance_note": "field-level source ids recorded for every value"
}
```
Entity types: person, company, organization, government, place, product, ticker, and so on. Entity
roles: subject, affected, actor, source-cited, and similar. The controlled vocabularies for
`event_type` and roles are per sector and are the analog of EduThreat's controlled enumerations.

## Role lenses (declarative add-ons)
A lens adds fields and framing on top of the shared schema. It runs only when classification tagged
the item for that role. Lenses do not branch the pipeline; each active lens contributes its extra
fields to the same record.

### Cyber lens (beachhead)
```jsonc
{
  "cve_ids": ["CVE-2026-12345"],
  "cvss": { "score": 9.8, "vector": "CVSS:3.1/AV:N/AC:L/…", "severity": "critical" },
  "affected": [
    { "vendor": "Acme", "product": "GatewayOS", "versions": "2.1–2.4", "cpe": "cpe:2.3:…" }
  ],
  "exploitation": { "known_exploited": true, "kev_listed": true, "poc_public": true },
  "weakness": ["CWE-89"],
  "remediation": { "fix_available": true, "action": "patch_to_2.5", "workaround": "…" },
  "control_mapping": [                  // the "so what for my controls" read
    { "framework": "NIST_800-53", "control": "SI-2", "relevance": "patch management" },
    { "framework": "CIS", "control": "7.4", "relevance": "continuous vuln remediation" }
  ]
}
```
The cyber lens is where the EduThreat CTI heritage is strongest: CVE and CVSS handling, affected
product and version resolution, exploitation status from CISA KEV, and the mapping to controls and
frameworks that turns a raw advisory into an action for a GRC user.

### Finance lens (Phase 2, sketch)
```jsonc
{
  "tickers": ["NVDA"],
  "sector": "semiconductors",
  "catalyst": "guidance_raise",
  "price_impact": { "direction": "up", "magnitude": "moderate", "confidence": 0.5 }
}
```

### Sports lens (illustrative)
```jsonc
{ "teams": ["…"], "outcome": "…", "standings_effect": "…", "notable_people": ["…"] }
```

## Provenance and reproducibility
Field-level provenance records which source contributed each value, enabling three things carried
over from EduThreat: resolving disagreements between sources by preferring the more reliable source
for that field, selectively re-enriching a single weak field without re-running the whole
extraction, and reproducing any served statistic from the persisted enrichment trail. The raw model
output is stored alongside the structured record so alternative normalization can be applied later
without re-querying the model.

## Quality
Enrichment is evaluated on a labeled sample per role: field-level agreement for categorical fields,
entity and (for cyber) CVE and CVSS accuracy, and numeric error where a value is disclosed. Fields
the model tends to over-assert are flagged and reported rather than trusted blindly, the same
honesty discipline used in the EduThreat validation.
