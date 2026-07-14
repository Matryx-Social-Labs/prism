# Prism

**Prism** is a role-aware, personalized global news intelligence platform. It takes worldwide
news across every sector and, for each story, delivers three things: **Both Sides** (the full
spectrum of perspectives, including sources from the countries or parties involved), **So What**
(an end-to-end impact analysis of the affected organizations, companies, and people, plus the
likely second-order outcomes), and **Ask** (a grounded AI agent that answers a reader's
follow-up questions from that story's own sources).

Each user tells Prism their job role and interests at onboarding, and that profile drives a feed
tailored to them, where every story still receives the full depth treatment.

> "Prism" is a working codename (one event, split into its full spectrum of perspectives and
> consequences). The final product name is still to be decided.

## Status
Blueprint stage. This directory holds the product and technical documentation and the code
skeleton. No services are running yet. The research report and strategic rationale that led here
live in [`BLUEPRINT.md`](./BLUEPRINT.md) and [`docs/MARKET-RESEARCH.md`](./docs/MARKET-RESEARCH.md).

## Lineage
Prism generalizes the pipeline from the author's EduThreat-CTI research (ingest, classify,
enrich, cluster and canonicalize, correlate into an impact graph, then serve) from the narrow
domain of education-sector cyber incidents to worldwide news. The proven enrichment and
correlation logic is ported here rather than the codebase being forked.

## Beachhead
The first version ships for one role where the team holds an unfair advantage:
**cybersecurity and GRC professionals** who want fast CVE and security news with a clear read on
what it means for their controls. Later roles (finance and trading first) are added as lenses on
the same backbone rather than as new pipelines.

## Documentation map
| Doc | What it covers |
| --- | --- |
| [BLUEPRINT.md](./BLUEPRINT.md) | One-page strategy: concept, differentiation, decisions, phasing |
| [docs/PRODUCT-BRIEF.md](./docs/PRODUCT-BRIEF.md) | Problem, promise, positioning, success metrics |
| [docs/MARKET-RESEARCH.md](./docs/MARKET-RESEARCH.md) | Market size, competitor landscape, demand signals, the gap |
| [docs/PERSONAS.md](./docs/PERSONAS.md) | Role-driven personas and the personalization model |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Streaming-first architecture, pipeline phases, tech stack |
| [docs/DATA-SOURCES.md](./docs/DATA-SOURCES.md) | Hybrid ingestion strategy and source catalog |
| [docs/INGESTION-CLASSIFICATION.md](./docs/INGESTION-CLASSIFICATION.md) | Collection, relevance gate, and routing detail |
| [docs/ENRICHMENT-SCHEMA.md](./docs/ENRICHMENT-SCHEMA.md) | Shared extraction schema plus role lenses (with the cyber lens) |
| [docs/DB-SCHEMA.md](./docs/DB-SCHEMA.md) | Database tables, keys, relationships, and stream topics |
| [docs/AGENT.md](./docs/AGENT.md) | The per-story grounded question-answering agent |
| [docs/ROADMAP.md](./docs/ROADMAP.md) | Phasing, milestones, and the first end-to-end slice |

## Code skeleton
```
prism/
  ingestion/        collectors + API adapters + domain feeds (publish to the stream)
  classification/   relevance gate + sector/region/role routing
  enrichment/       schema-constrained extraction + grounded NER + role lenses
  correlation/      event clustering + perspective grouping + impact propagation
  personalization/  per-user relevance and ranking, feed assembly, alerts
  api/              REST + streaming (FastAPI, websockets/SSE)
  agent/            per-story retrieval-augmented Q&A
  web/              Next.js app (feed, story view, ask)
  db/               schema + migrations
```
