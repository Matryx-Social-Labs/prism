# Database Schema

The canonical and served store is PostgreSQL (with pgvector for the agent's retrieval). The design
mirrors the pipeline: raw observations, then articles, then canonical events, then the perspective
and impact graph, then the personalization and product tables. Search and candidate retrieval for
clustering use a separate search store (OpenSearch); the hot feed and alert fan-out use Redis.
These are caches and indexes over the tables below, not the source of truth.

Conventions: every table has a UUID primary key `id` and `created_at` / `updated_at` timestamps
(omitted below for brevity). JSONB is used where the shape is flexible or lens-specific.

## Ingestion layer

### `sources`
| Column | Type | Notes |
| --- | --- | --- |
| slug | text unique | e.g. `gdelt`, `nvd`, `cisa_kev` |
| name | text | display name |
| source_type | text | news_api, cve_feed, advisory, rss, scraper |
| country | text | outlet country, nullable |
| language | text | default language, nullable |
| reliability | jsonb | bias and reliability metadata, nullable |
| watermark | jsonb | per-source incremental cursor |

### `raw_items`
The as-received observation, never edited in place.
| Column | Type | Notes |
| --- | --- | --- |
| source_id | fk sources | |
| external_id | text | id within the source |
| url | text | nullable |
| title | text | |
| body | text | nullable if only a snippet was provided |
| language | text | as reported |
| published_at | timestamptz | nullable |
| observed_at | timestamptz | when collected |
| raw | jsonb | untouched source payload |
| relevance | text | pending, relevant, rejected |
| rejection_reason | text | nullable, kept for audit |
| classification | jsonb | sector, regions, role_interests, route, confidence |
Unique on `(source_id, external_id)` for idempotency.

### `articles`
Retrieved and cleaned full text for a raw item (one-to-one or one-to-many if re-fetched).
| Column | Type | Notes |
| --- | --- | --- |
| raw_item_id | fk raw_items | |
| clean_text | text | |
| retrieval_tier | text | direct, proxy, archive |
| word_count | int | |
| fetched_at | timestamptz | |

## Enrichment layer

### `enrichments`
The structured extraction for one article, shared fields plus lens fields.
| Column | Type | Notes |
| --- | --- | --- |
| article_id | fk articles | |
| event_type | text | controlled vocabulary |
| summary | text | neutral one-liner |
| occurred_at | date | nullable |
| sentiment | numeric | nullable |
| shared_fields | jsonb | claims, stance, regions, etc. |
| lens_fields | jsonb | keyed by lens, e.g. `{ "cyber": { … } }` |
| raw_model_output | jsonb | stored for reproducibility |
| model | text | provider and model id, for auditability |

### `field_provenance`
Which source contributed each field value.
| Column | Type | Notes |
| --- | --- | --- |
| enrichment_id | fk enrichments | |
| field_path | text | e.g. `impacts[0].effect` |
| source_id | fk sources | |
| confidence | numeric | nullable |

## Canonical event layer

### `events`
The deduplicated real-world event, the unit of analysis and the unit shown in the feed.
| Column | Type | Notes |
| --- | --- | --- |
| title | text | promoted, human-readable |
| summary | text | |
| sector | text | |
| regions | text[] | countries involved |
| occurred_at | date | nullable |
| first_seen_at | timestamptz | |
| last_updated_at | timestamptz | |
| projection | jsonb | promoted shared + lens fields for serving |
| embedding | vector | pgvector, for the agent and similar-event lookup |

### `event_memberships`
Links an enriched article to its canonical event, with the match trail (ported from EduThreat).
| Column | Type | Notes |
| --- | --- | --- |
| event_id | fk events | |
| article_id | fk articles | |
| match_type | text | url_exact, resolved_url, title_time, entity_time, feed |
| match_score | numeric | composite score |
| is_survivor | bool | which article's value was promoted |

## Perspective and impact graph

### `entities`
Canonical people, companies, organizations, places, products, tickers.
| Column | Type | Notes |
| --- | --- | --- |
| slug | text unique | normalized key |
| name | text | display |
| entity_type | text | person, company, organization, government, place, product, ticker |
| aliases | text[] | |
| metadata | jsonb | e.g. ticker symbol, vendor of a product |

### `event_entities`
Role of an entity in an event.
| Column | Type | Notes |
| --- | --- | --- |
| event_id | fk events | |
| entity_id | fk entities | |
| role | text | subject, affected, actor, source_cited |
| provenance | jsonb | contributing source ids |

### `perspectives`
Per-event framing groups, for the both-sides view.
| Column | Type | Notes |
| --- | --- | --- |
| event_id | fk events | |
| label | text | e.g. "US framing", "Iraqi framing", "critical", "supportive" |
| origin_country | text | nullable, for cross-national grouping |
| stance | text | |
| member_articles | uuid[] | articles in this framing group |
| summary | text | how this side frames the event |

### `impacts`
The consequence graph: affected entity, effect, and second-order links.
| Column | Type | Notes |
| --- | --- | --- |
| event_id | fk events | |
| entity_id | fk entities | affected entity |
| effect | text | e.g. stock_drop, service_outage, resignation |
| direction | text | positive, negative, mixed |
| horizon | text | immediate, days, weeks, longer |
| confidence | numeric | |
| parent_impact_id | fk impacts | nullable, for second-order chains |
| provenance | jsonb | |
Impact rule (ported from EduThreat): identity is never merged and impact is never double-counted;
a disclosed magnitude is attributed once, and downstream affected entities are linked without
inheriting the same figure.

### Dimensions
`sectors`, `regions`, and `tickers` are small dimension tables for filtering the feed and, later,
the finance fast-lane.

## Personalization and product layer

### `users`, `user_profiles`, `user_interests`
| Table | Key columns |
| --- | --- |
| users | auth identity, email, plan |
| user_profiles | user_id, job_role, seniority, org_type |
| user_interests | user_id, sectors[], regions[], followed_entity_ids[] |

### `role_lenses`
Declarative definition of a lens: which extra fields, framing, and ranking weights apply.
| Column | Type | Notes |
| --- | --- | --- |
| slug | text unique | e.g. `cyber_grc`, `finance_trader` |
| extra_fields | jsonb | lens schema fragment |
| ranking_weights | jsonb | how this role weights recency, severity, follow-matches |
| framing | jsonb | display defaults |

### `user_event_scores` and `feed_items`
| Table | Key columns |
| --- | --- |
| user_event_scores | user_id, event_id, score, reasons jsonb, scored_at |
| feed_items | user_id, event_id, rank, state (unseen, seen, saved), served_at |

### `alerts` and `subscriptions`
| Table | Key columns |
| --- | --- |
| alerts | user_id, rule jsonb, channel, last_fired_at |
| subscriptions | user_id, plan, status, period, provider_ref |

## Agent layer

### `agent_sessions`, `agent_messages`
| Table | Key columns |
| --- | --- |
| agent_sessions | user_id, event_id, started_at |
| agent_messages | session_id, role (user/assistant), content, cited_source_ids uuid[], created_at |
The agent answers only from the cited event's sources; `cited_source_ids` records the exact
articles used, so every answer is auditable. See [AGENT.md](./AGENT.md).

## Stream topics (the spine)
The tables above are written by consumers of these topics; the topics are the transport, the tables
are the record.
| Topic | Produced by | Consumed by |
| --- | --- | --- |
| `raw.items` | collectors | classification |
| `classified.items` | classification | enrichment |
| `enriched.items` | enrichment | clustering |
| `events` | clustering | correlation |
| `event_links` | cross-event threads (leads_to/related/none; 'none' = negative cache) | correlation |
| `event.updates` | correlation | personalization |
| `feed.updates` | personalization | serving and alerts |

## Migrations
Migrations live in `db/` (Alembic or an equivalent). The schema is additive: new lenses add columns
or JSONB keys and new dimension rows, not destructive rewrites, so existing data and served
projections stay valid as roles are added.

### `event_links` (added July 2026)

| column | type | notes |
|---|---|---|
| id | uuid pk | |
| from_event_id | fk events | cause side for `leads_to` |
| to_event_id | fk events | effect side for `leads_to` |
| relation | text | `leads_to` \| `related` \| `none` (rejection, never re-asked) |
| confidence | float | from the thread-link judge |
| rationale | text | one-sentence grounded connection |

Also added July 2026: `events.subsector` (taxonomy sub-domain), `events.image_url`,
`raw_items.image_url` (thumbnails), `projection.coverage` (origin distribution + single_origin),
`projection.role_interests` (union of member classifications, drives conditional lenses).
