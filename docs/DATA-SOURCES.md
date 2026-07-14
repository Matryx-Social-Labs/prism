# Data Sources and Ingestion Strategy

Ingestion is hybrid: buy breadth from news-event APIs, add domain feeds for the beachhead, and
build a small number of own collectors where control matters. This avoids the multi-year cost of
rebuilding global collection from scratch, while keeping a path to proprietary sources. Every
collector publishes to the `raw.items` stream rather than writing straight to the database.

## Source tiers

### Tier 1 — News-event APIs (breadth)
Used for worldwide, multi-language coverage and first-pass clustering and entities.
- **GDELT** (and GDELT Cloud): global event and article stream with entities, tone, and clustered
  stories; petabyte-scale, strong for geopolitics and cross-country coverage.
- **NewsCatcher** or **Event Registry** (choose one to license first): NLP-enriched articles with
  topic classification, entity extraction, sentiment, and article clustering across many sources.
These give immediate global reach and reduce how much clustering Prism must do from zero.

### Tier 2 — Domain feeds (cyber beachhead depth)
Used for authoritative, structured cybersecurity signal.
- **NVD / CVE**: canonical vulnerability records with CVSS, affected product configurations (CPE),
  and references.
- **CISA KEV**: the Known Exploited Vulnerabilities catalog, for exploitation status.
- **Vendor advisories**: security advisories from major vendors for affected products and fixes.
- Optional later: exploit and PoC trackers, and ransomware or leak-site trackers ported from
  EduThreat for incident coverage.

### Tier 3 — Own collectors (control and differentiation)
A small set of collectors whose logic is ported from the EduThreat scrapers into fresh
streaming-first collectors. Used for key or under-covered national outlets, and for the
cross-national both-sides feature where domestic-language sources from the parties involved are not
well indexed by the Tier 1 APIs. These are added deliberately, not as a global scraping estate.

### Tier 4 — Finance feeds (Phase 2, the trader lens)
- **Marketaux** (entity-first news across many markets and languages) and, if the fast-lane needs
  lower latency, a real-time catalyst feed such as Benzinga. Added when the finance lens ships.

## Watermarks and cost
Each collector keeps a per-source watermark so scheduled runs fetch only new items, keeping
continuous operation affordable, the same pattern used in EduThreat. API cost is controlled by
pulling incrementally and by pushing expensive LLM enrichment only past the relevance gate.

## Cross-national framing note
The both-sides promise depends on having sources from more than one side of a contested story.
Tier 1 APIs provide language and country coverage, and Tier 3 collectors fill gaps for specific
country pairs that matter first. The initial region and language priority is an open decision to
set at build time, guided by the beachhead audience (English-first for cyber, with a short list of
priority languages to follow).

## What to license first (recommendation)
Start with GDELT (free tier and Cloud) plus one paid enrichment API, and the NVD/CVE and CISA KEV
feeds, which are free and authoritative for the beachhead. Add own collectors only where the APIs
leave a real gap. Defer finance feeds to Phase 2.
