# HTTP API Reference

Prism's serving layer is a FastAPI app under `api/` mounted at `/api/v1`. Every
endpoint is read-only except auth, watchlist, and the admin pipeline trigger.
Responses are JSON unless noted (the Ask endpoint streams Server-Sent Events).

- **Base URL (prod):** `https://prism-production-6747.up.railway.app`
- **Base URL (local):** `http://localhost:8000`
- **Auth:** most endpoints are public. Watchlist and `/auth/me` require a
  `Authorization: Bearer <session-token>` header (from `/auth/verify`). The admin
  trigger requires `X-Admin-Token`.
- **Content type:** `application/json`. The frontend caches most GETs with Next's
  `revalidate` (feed 60s, trending 120s, taxonomy/regions/lenses 3600s).

The route surface is locked by `tests/test_api_routes.py` — if you add or move a
route, update that test.

---

## Conventions

- **Lens** — `reader` (default), `cyber`, `markets`. The full list comes from
  `GET /api/v1/lenses`; an unknown or missing lens falls back to `reader`
  (all sectors). See [STORY-GRAPH.md](./STORY-GRAPH.md) and `common/lenses.py`.
- **Region / state** — ISO 3166-2 codes. `region` is the country (`IN`), `state`
  is the sub-national code (`IN-KA` = Karnataka).
- **Languages** — ISO 639-1 (`en`, `hi`, `kn`, `ta`). A comma-separated
  preference list ranks (never filters) the feed and picks the served headline.

---

## Discovery

### `GET /healthz`
Liveness probe. Returns `200 ok`. Used by Railway healthchecks.

### `GET /api/v1/lenses` → `LensesResponse`
Shipped lenses only (upcoming/drafted lenses are excluded).
```json
{ "lenses": [ { "slug": "cyber", "name": "Cybersecurity / GRC", "tagline": "…" } ],
  "default": "reader" }
```

### `GET /api/v1/languages`
Offered launch languages, native labels included.
```json
{ "languages": [ { "code": "en", "name": "English", "native": "English" },
                 { "code": "hi", "name": "Hindi", "native": "हिन्दी" } ],
  "default": ["en"] }
```

### `GET /api/v1/taxonomy` → `TaxonomyResponse`
Sector/subsector tree used by the feed's section rail.
```json
{ "sectors": [ { "slug": "politics", "name": "Politics",
                 "subsectors": [ { "slug": "governance_policy", "name": "Governance & policy" } ] } ] }
```

### `GET /api/v1/regions`
India states (ISO 3166-2) for the onboarding/scope selector: `{ "states": [ { "code": "IN-KA", "name": "Karnataka" } ] }`.

### `GET /api/v1/professions`
Grouped profession registry (onboarding "What do you do?"), each mapping to a lens.

---

## Feed & search

### `GET /api/v1/feed` → `FeedResponse`
The personalized, lens-shaped feed of canonical events.

| Param | Type | Default | Effect |
|---|---|---|---|
| `lens` | string | `reader` | Lens whose RANKING shapes the feed — it no longer filters by sector, so `?lens=cyber` returns every sector, not cybersecurity only. Unknown → `reader`. |
| `sector` | string | — | Restrict to one sector slug. |
| `interests` | csv | — | Interest slugs (the web app sends these for the reader lens only). These *do* narrow the feed: `sector` keeps the whole sector, `sector:subsector` keeps only that subsector. |
| `region` | string | — | Country code; marks matching events `is_regional`. |
| `state` | string | — | Sub-national code; local news ranks up. |
| `languages` | csv | `en` | Preference order; ranks coverage + picks the served headline. |
| `sort` | `latest`\|`top` | `latest` | `latest` = recency, then raw records (NVD/KEV) woven in two-stories-to-one so a record-including lens doesn't return a changelog. `top` = personalization score, never interleaved. |
| `limit` | int | 30 | Maximum page size, clamped to 100. Best-effort: a thin corpus returns fewer. |

`FeedResponse` = `{ "items": [FeedItem], "lens": "reader" }`. **FeedItem:**
```
id, title, headline_lang, available_languages[], summary, sector, subsector,
regions[], image_url, is_regional, coverage{origins,unknown,single_origin},
event_type, source_count, cvss_score, cvss_severity, kev_listed, cve_ids[],
tickers[], catalyst, price_impact_direction, last_updated_at, score
```
The cyber fields (`cvss_*`, `kev_listed`, `cve_ids`) populate only for the cyber
lens; the markets fields (`tickers`, `catalyst`, `price_impact_direction`) only
when the markets lens is speaking. `headline_lang` is the language of the served
`title`; the UI tags it when it isn't the reader's primary language.

### `GET /api/v1/search?q=<query>` → `FeedResponse`
Full-text + semantic search over events. Same `FeedItem` shape as the feed.

---

## Trending

### `GET /api/v1/trending`
Velocity-ranked, persistent trending **stories** (durable, shareable, slugged).

| Param | Type | Effect |
|---|---|---|
| `state` | string | Geo scope — defaults trending to the reader's state when set. |
| `sector` | string | Restrict to one sector. |
| `limit` | int | Page size. |

```json
{ "stories": [ { "slug": "dharmendra-pradhan-delhi-police-…-ef0ac0",
                 "label": "Dharmendra Pradhan · Delhi Police · Cockroach Janta Party",
                 "cast": ["Dharmendra Pradhan", "Delhi Police", …],
                 "source_count": 13, "velocity": 0, "developments": 30,
                 "sector": "politics", "hero_title": "…", "hero_image": "…" } ] }
```
Only `active`, non-merged stories are returned. Velocity = distinct new news
outlets in the last 6h. See [STORY-GRAPH.md](./STORY-GRAPH.md#trending).

### `GET /api/v1/trending/{slug}`
One trending story with its developments timeline. **Slugs are frozen** — a merged
story's slug redirects to the canonical one via `canonical_slug`, so a shared link
never breaks. `404` if the slug is unknown.

---

## Story (event) view

### `GET /api/v1/events/{event_id}` → `EventDetail`
The full story: header, coverage, entities, the canonical story timeline, sources,
perspectives (Both Sides), and impacts (So What).
```
id, title, summary, sector, subsector, image_url, regions[], occurred_at,
last_updated_at, projection{}, lens_briefs{lens:text}, lens_points{lens:[…]},
available_lenses[], coverage{}, entities[{name,entity_type,role}],
thread{upstream[],downstream[]}, related[], story{developments[],cast[]},
sources[SourceRef], perspectives[PerspectiveOut], impacts[ImpactOut]
```
`story.developments[]` = the same canonical timeline shown on every development of
the story (see [STORY-GRAPH.md](./STORY-GRAPH.md#the-story-timeline)). `sources[]`
carry `stance` and `funding` (`state`/`public`/null) for outlet-transparency chips.

### `GET /api/v1/events/{event_id}/brief?lens=<lens>` → `BriefResponse`
The on-demand, per-lens re-read of the story. Generated once and cached on the
event projection (single-flight across API replicas), so a burst of viewers costs
one LLM call. `{ "lens": "cyber", "brief": "…", "points": ["…"], "cached": true }`.
When the model is unavailable (quota exhausted), returns `brief: null` (the UI
shows "the <lens> read isn't available yet") — never a 500.

### `GET /api/v1/events/{event_id}/questions?lens=<lens>` → `QuestionsResponse`
Suggested, lens-aware questions for the Ask box. `{ "questions": ["…", "…"] }`.

### `POST /api/v1/events/{event_id}/ask` → **SSE stream**
The grounded per-story agent. Body: `{ "question": "…", "session_id": "…"? }`.
Streams `text/event-stream` tokens as the answer is composed, with inline citations
to that story's own sources; refuses what the sources don't cover. See
[AGENT.md](./AGENT.md).

---

## Market Pulse

### `GET /api/v1/digest/markets` → `DigestResponse`
The synthesized Market Pulse — an editor's read across the day's top market stories,
cached for 3h and single-flighted. `{ headline, narrative, movers[{ticker,note}],
event_ids[], generated_at }`. Returns `204 No Content` when synthesis is
unavailable (the feed hides the Pulse card) — never a 500.

---

## Auth (passwordless magic link)

Email-first. New users sign up by agreeing to terms; returning users just enter
their email. The email is stored for later product/marketing contact.

### `POST /api/v1/auth/request`
Body `{ "email": "you@example.com" }`. Sends a one-time sign-in link (Resend).
Always `200` (no account enumeration).

### `POST /api/v1/auth/verify` → `SessionResponse`
Body `{ "token": "<from-email>" }`. Consumes the token, creates the user if new,
returns `{ "token": "<session>", "needs_profile": true|false }`.

### `POST /api/v1/auth/profile` → `MeResponse`
Bearer-authed. Completes onboarding: `{ state, languages[], lens, interests[] }`.

### `GET /api/v1/auth/me` → `MeResponse`
Bearer-authed. The signed-in user's profile.

---

## Watchlist (Bearer-authed)

- `GET /api/v1/watchlist` → `WatchlistResponse` — followed event ids.
- `POST /api/v1/watchlist` — body `{ "event_id": "…" }`, follow.
- `DELETE /api/v1/watchlist` — body `{ "event_id": "…" }`, unfollow.
- `GET /api/v1/watchlist/events` → `WatchEventsResponse` — followed events, hydrated.

---

## Admin

### `POST /api/v1/admin/pipeline/run`
Header `X-Admin-Token: <PRISM_ADMIN_TOKEN>`. Enqueues an ingestion run over the
Redis stream (the API never ingests in-process; the worker owns collection).
Overlapping triggers coalesce behind one lock.

---

## Related
- [STORY-GRAPH.md](./STORY-GRAPH.md) — how events, story timelines, and trending are formed.
- [DB-SCHEMA.md](./DB-SCHEMA.md) — the tables behind these responses + stream topics.
- [AGENT.md](./AGENT.md) — the grounded Ask agent.
- [ENRICHMENT-SCHEMA.md](./ENRICHMENT-SCHEMA.md) — the extraction schema feeding `projection`.
