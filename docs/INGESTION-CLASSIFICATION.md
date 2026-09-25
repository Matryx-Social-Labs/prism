# Ingestion and Classification

> **Historical (2026-07-14).** The design as first ported. Since then: GDELT was removed, classification can run as one typed Jev decision (`PRISM_DECISIONS_MODE`, live in production), and several fields below were never built. Current behaviour: [PIPELINE §3–4](./PIPELINE.md#3-ingestion).

This covers phases 1 and 2 of the pipeline: getting observations in, and deciding what they are and
where they go. Phase 3 onward is in [ENRICHMENT-SCHEMA.md](./ENRICHMENT-SCHEMA.md) and
[ARCHITECTURE.md](./ARCHITECTURE.md).

## Phase 1 — Ingestion

### Collectors
Each source has a collector (an API adapter for Tier 1 and 2, or an own scraper for Tier 3). A
collector runs on a schedule or a subscription, keeps a per-source watermark, and normalizes each
item into a `raw_item` shape before publishing to the `raw.items` stream. Collectors do no cleaning
or deduplication; they preserve the observation exactly as received so the record stays auditable
and replayable.

### The raw item (normalized envelope)
A collector maps whatever the source returns into this common envelope:
```jsonc
{
  "source_id": "gdelt",              // which collector produced this
  "source_type": "news_api",         // news_api | cve_feed | advisory | rss | scraper
  "external_id": "abc123",           // id in the source, for dedup within a source
  "url": "https://...",              // primary URL, if any
  "title": "…",
  "body": "…",                       // full text if the source provides it, else null
  "language": "en",                  // as reported by the source, may be corrected later
  "published_at": "2026-07-14T09:00:00Z",
  "observed_at": "2026-07-14T09:03:11Z",
  "raw": { /* the untouched source payload */ }
}
```
Full-text retrieval for sources that give only a title or snippet uses a fallback chain (direct
fetch, then a paid proxy, then a web archive), the same tiered approach as EduThreat. Retrieval
tier is recorded so coverage can be measured.

### Idempotency
Items are deduplicated within a source by `(source_id, external_id)` before publishing, so a
re-poll does not double-emit. Cross-source deduplication is not done here; that is clustering's job
in phase 4.

## Phase 2 — Relevance and classification

### Step 2a: relevance gate
A binary LLM gate answers a single question per item: does this report a real, specific event
(for the beachhead, a real security incident or vulnerability disclosure) rather than opinion, a
product promo, or a passing mention. Only affirmative items proceed. Separating this cheap binary
call from expensive extraction keeps cost down and lets the gate be tuned independently, exactly as
in EduThreat.

### Step 2b: classification and routing
Affirmative items are tagged and routed. The classifier assigns:
```jsonc
{
  "sector": "cybersecurity",         // sports | finance | politics | business | …
  "regions": ["US", "DE"],           // countries involved (not just the outlet's country)
  "language": "en",                  // corrected if the source was wrong
  "role_interests": ["cyber_grc"],   // which role lenses this item is relevant to
  "route": "standard",               // standard | fast_lane
  "confidence": 0.86
}
```
- **Sector and regions** drive the feed and the both-sides framing (regions are the countries
  involved in the event, which is what enables cross-national perspective grouping later).
- **Role interests** decide which lenses run in enrichment, so the cyber lens only runs on items
  relevant to the cyber role.
- **Route** sends time-sensitive items (Phase 2 finance, or actively exploited CVEs) down a
  low-latency path, and everything else down the standard path.

### Outputs
The relevance decision and the classification are persisted with the item and emitted to
`classified.items`. Rejected items are kept (not deleted) with their rejection reason, so the gate
can be audited and improved, again as in EduThreat.

## Quality and evaluation
A small labeled gold set per stage (relevance correct or not, sector and region correct or not)
lets both stages be measured with simple accuracy and, where useful, confidence intervals. This is
carried over from the EduThreat evaluation harness and should exist before scaling collection.
