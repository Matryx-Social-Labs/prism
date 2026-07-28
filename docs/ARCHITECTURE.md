# Architecture

Prism is built fresh and streaming-first. It is not a fork of EduThreat, but it ports EduThreat's
proven enrichment and correlation logic. The design goal is that a new item flows from collection
to a user's feed continuously, and that the trader fast-lane in Phase 2 can be added without
re-architecting.

## Design principles
- **Stream, not batch.** Every stage is a consumer of an event stream and a producer to the next
  topic, rather than a job in a batch queue. This gives low end-to-end latency and natural
  backpressure and replay.
- **Shared backbone, role lenses.** One pipeline produces shared fields for every story; each role
  lens adds its own fields and framing declaratively. See [PERSONAS.md](./PERSONAS.md).
- **Provenance first.** Every extracted value keeps a link to the source that evidenced it, ported
  from EduThreat's field-level provenance. This is what makes the agent trustworthy and the
  perspective grouping auditable.
- **Never merge identity, never inflate impact.** Clustering and impact propagation preserve
  distinct entities and do not double-count, the direct analog of EduThreat's canonicalization and
  supply-chain rules.

## Pipeline phases
```
              ┌─────────────┐   raw.items   ┌──────────────┐  classified.items
 sources ───▶ │ 1 Ingestion │ ────────────▶ │ 2 Classify   │ ─────────────────┐
 (APIs,       └─────────────┘   (stream)     │   + route    │                  │
  CVE feeds,                                 └──────────────┘                  ▼
  scrapers)                                                            ┌────────────────┐
                                                                       │ 3 Enrichment   │
                                                                       │  + role lenses │
                                                                       └────────────────┘
                                                                                │ enriched.items
                                                                                ▼
   ┌──────────────┐   events    ┌───────────────────────────┐  correlated  ┌───────────────┐
   │ 6 Personalize│ ◀────────── │ 5 Perspective + Impact     │ ◀─────────── │ 4 Clustering  │
   │  + rank      │             │   correlation (graph)      │              │  canonicalize │
   └──────────────┘             └───────────────────────────┘              └───────────────┘
          │ feed.updates
          ▼
   ┌──────────────┐
   │ 7 Serving    │  REST + streaming (websockets/SSE) + per-story agent
   └──────────────┘
```

1. **Ingestion (hybrid).** Collectors and API adapters pull worldwide, multi-language sources and
   publish each observation to `raw.items`. Sources: news-event APIs for breadth (GDELT and one of
   NewsCatcher or Event Registry), domain feeds for the cyber beachhead (NVD/CVE, CISA KEV, vendor
   advisories), and a small set of own collectors whose logic is ported from EduThreat. Detail in
   [DATA-SOURCES.md](./DATA-SOURCES.md) and [INGESTION-CLASSIFICATION.md](./INGESTION-CLASSIFICATION.md).
2. **Relevance and classification.** An LLM relevance gate drops non-stories, then a classifier
   tags sector, region and countries involved, language, and the active role interests, and sets a
   routing decision (fast-lane vs standard). Emits to `classified.items`.
3. **Enrichment with role lenses.** Schema-constrained LLM extraction produces the shared typed
   fields (entities, event type, stance, claimed facts, impact assertions, with provenance),
   reusing grounded NER and retrieval augmentation. Active lenses add their fields (the cyber lens
   adds CVE, CVSS, affected products, exploitation status, control mapping). Emits `enriched.items`.
   Full schema in [ENRICHMENT-SCHEMA.md](./ENRICHMENT-SCHEMA.md).
4. **Event clustering and canonicalization.** The many reports of one real event are merged into a
   canonical event with a persisted match trail. Candidate retrieval uses the search store; the
   merge rules are ported from EduThreat canonicalization. Emits `events`.
5. **Perspective and impact correlation.** Two layers over the canonical event: perspective
   grouping (cluster the event's sources by stance and by country or party of origin, to render
   both sides) and impact propagation (link the event to affected entities and second-order
   consequences without merging identity or inflating impact). Writes the event graph.
6. **Personalization and ranking.** For each user, the profile selects the lens and a relevance and
   ranking model scores new events, producing a feed specific to that user. Alerts and the
   real-time fast-lane are the push side of the same layer. See [DB-SCHEMA.md](./DB-SCHEMA.md) for
   `user_event_scores` and `feed_items`.
7. **Serving.** A REST API, the personalized feed, the fast-lane with push over websockets or SSE,
   and the per-story agent. See [AGENT.md](./AGENT.md).

## Tech stack (recommended, to confirm at build time)
| Layer | Choice | Why |
| --- | --- | --- |
| Streaming spine | Kafka or Redpanda (or NATS for a lighter start) | Low-latency topics between stages, replay, backpressure |
| Pipeline services | Python (FastAPI for the API, stream consumers for stages) | Keeps the LLM and ML work in the ecosystem EduThreat already uses |
| Canonical + served store | PostgreSQL with pgvector | Relational core plus vector retrieval for the agent in one store |
| Search / candidate retrieval | OpenSearch or Elasticsearch | Fast candidate lookup for clustering and full-text search |
| Hot feed + alerts | Redis | Per-user feed cache and rate-limited alert fan-out |
| Real-time transport | Websockets or SSE | Push for the feed and the Phase 2 trader fast-lane |
| LLM layer | Model-agnostic interface | Swap hosted and local models; grounded NER and retrieval ported from EduThreat |
| Frontend | Next.js | Feed, story view, and the ask experience |

Python is kept for the ML and LLM work; the streaming spine is the genuinely new part relative to
EduThreat. The exact broker and search store are the main choices to lock at build time.

## Data flow summary
Raw observations are never edited in place; they are preserved and forwarded, so the pipeline is
auditable and replayable. Enrichment adds structure with provenance. Clustering groups reports
into events. Correlation adds the perspective and impact graph. Personalization turns the shared
graph into per-user feeds. Serving exposes feeds, stories, and the agent. Every reported value can
be traced back to the source that evidenced it.
