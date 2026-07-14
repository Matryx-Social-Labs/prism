# Roadmap

The strategy is a vertical beachhead first, then horizontal expansion by adding role lenses on the
same backbone. This keeps scope tight (the lesson from Artifact's failure) while building toward the
full multi-role vision.

## Phase 0 — Blueprint (done)
Research report, competitive analysis, personas, architecture, schema, and this directory. See the
top-level [BLUEPRINT.md](../BLUEPRINT.md) and [docs/MARKET-RESEARCH.md](./MARKET-RESEARCH.md).

## Phase 1 — Cybersecurity and GRC beachhead
Ship the full experience for one role.

**Milestone 1.1 — Thin vertical slice.** One end-to-end path: ingest NVD/CVE and CISA KEV plus one
news-event API, run the relevance gate, enrich with the shared schema and the cyber lens, cluster
into events, and serve a single event view with sources. Prove the pipeline before widening.

**Milestone 1.2 — The three-part story view.** Add perspective grouping (both sides), the impact
and control-mapping view (so what for your controls), and the per-story agent (ask), for cyber
stories.

**Milestone 1.3 — Personalization.** Onboarding captures role and interests; the cyber lens and a
first ranking model produce a per-user feed. Add follow rules for specific vendors, products, and
CVEs, plus alerts.

**Milestone 1.4 — Prosumer subscription.** Accounts, plans, and billing for individual security and
GRC professionals. Groundedness and extraction evaluation gates in place before opening access.

Exit criteria: a security or GRC user can go from a new CVE to "does this affect me and what do I
do" in under a minute, with sources and a questionable agent, and returns daily.

## Phase 2 — Finance and trader lens
Add the finance lens and the real-time fast-lane on the same backbone: tickers, sector, catalyst,
and price-impact read, delivered with low latency over the streaming transport, plus finance feeds
(Marketaux, and a real-time catalyst feed if needed). This is where willingness to pay is highest,
and it validates the multi-role thesis by adding a role without a rewrite.

## Phase 3 — Horizontal expansion
Open personalization to general roles and sectors, add a prosumer graph and public API, and later
introduce B2B team seats for security, PR, and risk teams. Cross-national both-sides framing widens
from the beachhead's priority languages to broader coverage.

## Cross-cutting, from the start
- **Evaluation harness.** Labeled gold sets for the relevance gate, classification, enrichment, and
  agent groundedness, ported from EduThreat. Do not scale collection before these exist.
- **Provenance and reproducibility.** Field-level provenance on every value, so served numbers and
  agent answers are auditable.
- **Cost discipline.** Incremental collection with watermarks, and expensive LLM work only past the
  relevance gate.

## Open decisions to settle early
- Final product name (working codename "Prism").
- Streaming backbone (Kafka/Redpanda vs NATS) and search store.
- First news-event API to license, and the initial region and language priority.
- Whether Phase 1 also seeds a second research paper, which would raise the measurement rigor baked
  into the pipeline from day one.
