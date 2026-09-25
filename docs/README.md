# Prism documentation

Every document here says what it covers and whether it describes the system as it
runs today (**current**) or a design that has since changed (**historical** — kept
because the reasoning still matters). When a document and the code disagree, the
code is right and the document is a bug: fix it in the same change.

## Start here

| If you want to… | Read |
|---|---|
| run Prism on your machine | [TUTORIAL](./TUTORIAL.md) |
| understand the whole system on one page | [ARCHITECTURE](./ARCHITECTURE.md) |
| follow one article from feed to screen | [PIPELINE](./PIPELINE.md) |
| call or change the API | [API](./API.md) |
| work on the web app | [FRONTEND](./FRONTEND.md) and [`../DESIGN.md`](../DESIGN.md) |
| know what every table holds | [DB-SCHEMA](./DB-SCHEMA.md) |
| know which models run, how good they are, how that was measured | [ML-EVALUATION](./ML-EVALUATION.md) |
| understand how duplicate reports become one event | [CANONICALIZATION](./CANONICALIZATION.md) |
| deploy, or find out why production is unhappy | [DEPLOYMENT](./DEPLOYMENT.md), [HOWTO](./HOWTO.md) |

## Reference — current, code-accurate (2026-09-25)

| Document | Covers |
|---|---|
| [ARCHITECTURE](./ARCHITECTURE.md) | containers and deployment topology, module map, auth and security model, configuration and feature flags, delivery (branches, CI, promote), observability |
| [PIPELINE](./PIPELINE.md) | worker loops and Redis Streams; ingestion, classification (LLM or Jev), enrichment (full text, extraction, verbatim quotes, embeddings, gist), the event match cascade, analysis, the story layer, podcasts, X posts, Ask; production configuration |
| [API](./API.md) | every route: method, params, auth tier, response, caching; error conventions; how to add a route |
| [FRONTEND](./FRONTEND.md) | every route in `web/`, the API client, state and cookies, key components, tests and the jsdom traps, the design system for developers |
| [DB-SCHEMA](./DB-SCHEMA.md) | every table (models and migration-only), keys, indexes, who reads and writes it; ER diagrams |
| [ML-EVALUATION](./ML-EVALUATION.md) | model inventory, embeddings and distance scales, every measured AUC / precision / recall with its date and dataset, gold and silver sets, methodology rules, how to run each measurement |
| [CANONICALIZATION](./CANONICALIZATION.md) | the event match cascade, the 2026-09-25 duplication audit, every per-article signal scored, the verified tier (gist + Jev), cost, rollout |
| [ENRICHMENT-SCHEMA](./ENRICHMENT-SCHEMA.md) | the extraction schema's intent — for the live field list read `enrichment/schemas.py` and [PIPELINE §5](./PIPELINE.md#5-enrichment) |

## How-to — task-oriented

| Document | Covers |
|---|---|
| [TUTORIAL](./TUTORIAL.md) | zero to a running pipeline and a lens flip |
| [HOWTO](./HOWTO.md) | add a source, lens or language; trigger ingestion; inspect production; run the tests |
| [DEPLOYMENT](./DEPLOYMENT.md) | Railway (API, worker, Postgres, Redis, Langfuse) and Vercel; environment variables; troubleshooting |
| [LOCAL_DEV](./LOCAL_DEV.md) | local infrastructure and Langfuse |
| [SEO](./SEO.md) | sitemaps, structured data, IndexNow, owner-side search-console steps |

## Explanation — why it is built this way

| Document | Status |
|---|---|
| [CANONICALIZATION](./CANONICALIZATION.md) | current |
| [STORY-GRAPH](./STORY-GRAPH.md) | **historical** (2026-07-30): the on-read story graph. The story layer now runs Leiden over a mutual-kNN graph (`correlation/partition.py`) and reconciles stories in `correlation/trending.py` — see [PIPELINE §7](./PIPELINE.md#7-story-layer) |
| [STORYLINE-DESIGN](./STORYLINE-DESIGN.md) | **historical** proposal (2026-07-24) that became the story layer; its code sample (`RBConfigurationVertexPartition`) is not what shipped (`CPMVertexPartition`) |
| [INGESTION-CLASSIFICATION](./INGESTION-CLASSIFICATION.md) | **historical** (2026-07-14): the ported design. Current behaviour, including the Jev decisions path: [PIPELINE §3–4](./PIPELINE.md#3-ingestion) |
| [DATA-SOURCES](./DATA-SOURCES.md) | sourcing strategy; the live outlet list is `GET /api/v1/sources` and `/sources` |
| [AGENT](./AGENT.md) | the per-story grounded Ask agent (design); current wiring in [PIPELINE §8](./PIPELINE.md#8-side-channels) |
| [OPTIMIZATION-LEDGER](./OPTIMIZATION-LEDGER.md) | model-call optimisations and what each saved |
| [AUDIT-2026-09](./AUDIT-2026-09.md) | the September hardening audit and what shipped |

## Product, business and compliance

[`../PRODUCT.md`](../PRODUCT.md) (product truth and founder decisions) ·
[PRODUCT-BRIEF](./PRODUCT-BRIEF.md) · [PRODUCT](./PRODUCT.md) · [PERSONAS](./PERSONAS.md) ·
[FEATURES](./FEATURES.md) · [ROADMAP](./ROADMAP.md) (historical phasing) ·
[BUSINESS-MODEL](./BUSINESS-MODEL.md) · [MARKET-RESEARCH](./MARKET-RESEARCH.md) ·
[PLAN-LAUNCH](./PLAN-LAUNCH.md) · [COMPLIANCE-INDIA](./COMPLIANCE-INDIA.md) ·
[`../DESIGN.md`](../DESIGN.md) (design system v2) · [`../BLUEPRINT.md`](../BLUEPRINT.md)

## Keeping these true

- A change that moves behaviour updates the document that describes it, in the same PR.
- Numbers carry their source and date (`file:line`, the tool that produced them); a
  number with neither is not a measurement.
- Diagrams are Mermaid, rendered by GitHub; check they parse
  (`npx -p @mermaid-js/mermaid-cli mmdc -i diagram.mmd -o /tmp/out.svg`).
