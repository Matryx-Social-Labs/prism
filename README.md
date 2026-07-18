# Prism — One story. Every perspective.

**Prism is a role-aware AI news intelligence platform for everyone.** It clusters worldwide
coverage into single canonical events, then reads each one through the user's professional
lens: a war is a humanitarian story for a general reader, a cyber-threat forecast (who's
exposed, what to check) for a security professional, and a market catalyst (sectors, tickers,
likely moves) for a trader — the *same event*, switchable on any story. Per story it delivers:

- **Lens briefs** — written per-lens analysis of what this event means for *you*, switchable
  to any other lens to see how the same news changes meaning
- **Both Sides** — the story's competing narratives grouped by stance, with outlet origin and affiliation labeled
- **So What** — the impact graph: who is affected and the likely second-order outcomes
- **Ask** — a grounded agent answering follow-ups from that story's own sources, with
  citations, refusing what the sources don't cover

The general "keep me informed" reader is a first-class persona, not a fallback: world news
from origin-diverse outlets, clustered, framed, and answerable.

## Status
**Live prototype**: pipeline (ingest → gate → classify → enrich → cluster → correlate →
lens briefs → serve) on Railway, web app on Vercel
([prism-ivory-two.vercel.app](https://prism-ivory-two.vercel.app)), Langfuse observability
self-hosted, CI auto-deploy on push. See the Quickstart below and
[`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md). Strategy in [`BLUEPRINT.md`](./BLUEPRINT.md)
and [`docs/MARKET-RESEARCH.md`](./docs/MARKET-RESEARCH.md).

## Lineage
Prism generalizes the pipeline from the author's EduThreat-CTI research (ingest, classify,
enrich, cluster and canonicalize, correlate into an impact graph, then serve) from the narrow
domain of education-sector cyber incidents to worldwide news. The proven enrichment and
correlation logic is ported here rather than the codebase being forked.

## Lens depth strategy
The **cyber/GRC lens is the deepest** (the team's unfair advantage: CVE/CVSS handling,
exploitation status, control mapping), followed by the finance/trader lens; the general
reader experience spans all sectors. New roles are added as declarative lenses on the same
backbone (`common/lenses.py`) — never as new pipelines.

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

## Code layout
```
prism/
  common/           config, db, Redis-Streams spine, LLM client (Ollama Cloud via
                    langfuse.openai), fastembed embeddings, prompt fetching + fallbacks
  ingestion/        collectors: CISA KEV, NVD 2.0, GDELT DOC, RSS (watermarks, idempotent)
  classification/   relevance gate + sector/region/role routing
  enrichment/       schema-constrained extraction + cyber lens + provenance + chunks/embeddings
  correlation/      event clustering (cve_id/url/title/embedding cascade) + perspectives + impacts
  personalization/  cyber_grc ranking (recency + CVSS + KEV + corroboration)
  api/              FastAPI /api/v1: feed, story view, questions, SSE ask, admin trigger
  agent/            per-story grounded Q&A (event-scoped pgvector RAG, citations, refusal)
  worker/           consumers + scheduled collectors (python -m worker)
  web/              Next.js app (feed, story view: Both Sides / So What / Ask)
  db/               Alembic migrations
  evals/            gold sets + Langfuse dataset experiments + groundedness judge
  docs/             product + technical docs, DEPLOYMENT.md
```

## Quickstart (local)

Prereqs: Docker, Python 3.12+ with [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
cp .env.example .env          # add your OLLAMA_API_KEY (+ LANGFUSE_* when ready)
docker compose up -d          # Postgres (pgvector) + Redis
uv sync                       # Python deps
uv run alembic upgrade head   # schema
uv run python -m worker       # terminal 1: pipeline (ingests on start, then every 30 min)
uv run uvicorn api.main:app --reload   # terminal 2: API on :8000
cd web && npm install && npm run dev   # terminal 3: web on :3000
```

Notes:
- CVE feeds (CISA KEV, NVD) flow end to end **without** an LLM key — deterministic
  enrichment. News items (GDELT, RSS) and the Ask agent need `OLLAMA_API_KEY`
  (Ollama Cloud). Items that stall during an outage are requeued automatically.
- With `LANGFUSE_*` set, every stage and agent turn is traced; publish prompts with
  `uv run python evals/sync_prompts.py` and run evals with `uv run python evals/run_all.py`.
- Production deploy (Railway + Vercel + self-hosted Langfuse): [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md).
