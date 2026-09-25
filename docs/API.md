# Prism HTTP API

Audience: anyone calling or changing the API. Read from `api/main.py`,
`api/deps.py`, `api/schemas.py` and every file in `api/routes/` as of
2026-09-25. The route surface is locked by `tests/test_api_routes.py` — adding,
moving or removing a route means updating its `EXPECTED` set in the same change.

- **Base URL (prod):** `https://api.readprism.news`.
- **Base URL (local):** `http://localhost:8000`.
- **Content type:** `application/json` unless noted (the Ask endpoint streams `text/event-stream`; one admin metrics route streams `text/csv`).
- **OpenAPI:** the app is `FastAPI(title="Prism API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")`.
- **CORS:** `allow_origins = settings.cors_origin_list`, plus an `allow_origin_regex` matching `https://prism-[a-z0-9-]+-matrixsociallabs-projects\.vercel\.app` (deliberately narrower than a wildcard `*.vercel.app`, which is a shared, publicly-registrable suffix). `allow_credentials=True`.
- **Rate limiting:** there is no framework-level limiter (no slowapi/starlette-limiter). Every limit in the app is hand-rolled per route — Redis counters, a Postgres advisory lock, or an in-process window — noted per route below.

## Auth model — three distinct tiers

There are three independent auth mechanisms, all defined in `api/deps.py`:

1. **Account session** — `get_current_user` (required) / `get_current_user_optional` (anonymous allowed, never rejects a bad token). Resolution order: an `Authorization: Bearer <token>` header wins if present; otherwise the `prism_session` HttpOnly cookie is used, **but only if the request's `Origin` header is in `cors_origin_list` or matches the preview regex** (`_origin_ok`) — a cookie presented with a missing/bad Origin on an unsafe method is ignored. This is CSRF defense-in-depth for cookie-authenticated writes. Cookie params: `httponly=True`, `samesite="lax"`, `secure` per `settings.prism_cookie_secure` (default `True`), `max_age = prism_session_ttl_days * 86400` (default 30 days).
2. **Static admin token** — `require_admin`: compares an `X-Admin-Token` header against `settings.prism_admin_token` with `hmac.compare_digest` (constant-time). Used only for operational triggers (`/admin/status`, `/admin/pipeline/run`, `/label/{key}/export`). The app refuses to start (`assert_admin_token_configured`, run at import time in `main.py`) if this token is still the placeholder `"change-me"` and the app isn't pointed at localhost.
3. **Admin-by-account** — `require_admin_user`: requires an account session (tier 1) whose email is in the `PRISM_ADMIN_EMAILS` allowlist (`admin_emails()`). Gates the whole `/admin` dashboard's data routes (not the two static-token triggers above). Chosen deliberately over a shared token so every admin action is attributable to a person (`common/admin_audit`) and offboarding is "edit one variable," not "rotate a secret everyone holds."

A fourth, separate scheme exists just for the labelling task protocol (`api/routes/label.py`): a **per-batch invite token**, carried as an `X-Label-Token` header or a JSON body field — never a cookie, never the account session, so an anonymous or invited labeller can work without an account. `api/routes/labeller.py` (the signed-in workspace in front of it) uses the ordinary account session (tier 1).

There is no shared pagination dependency — each route declares its own `limit`/`offset` `Query(...)` params inline.

## Error conventions

- **No custom exception handlers** are registered in `api/main.py`. Every error is FastAPI's default: `raise HTTPException(status_code, detail=...)` becomes `{"detail": ...}` at that status.
- **No consistent error envelope.** `detail` is a plain string in most places (`"event not found"`, `"not an admin"`), but several routes hand-build a structured dict when the failure mode is itself meaningful to the client — e.g. the Ask endpoint's `429`: `{"error": "question limit reached", "used", "limit", "signin_helps", "plus_helps"}`; the brief endpoint's `402`: `{"error": "no samples remaining", "remaining", "lens"}`; billing's `409`: `{"error": "already subscribed", "plan"}`. Treat `detail` as either a string or a small dict depending on the route — check the specific route below, not a global assumption.
- **Deliberate non-500 fallbacks** are a recurring, intentional pattern, not an accident: `GET /digest/markets` returns a bare `204` when synthesis is unavailable; `GET /events/{id}/brief` catches any generation failure and returns a normal `BriefResponse` with `brief: null` (refunding the sample it had provisionally consumed); `POST /beacon` always returns `204` regardless of internal outcome (fail-closed, silent, so a broken analytics path never blocks a page). Do not "fix" these into 500s — they are load-bearing product decisions, commented as such in the source.
- **No `ETag` usage anywhere** in the codebase. Only `Cache-Control` is set, and only on the specific routes listed under each area below — most routes set no caching header at all (client-side `revalidate` caching in the Next.js frontend is a separate, cooperative concern, not something the API enforces).
- Two custom exception classes exist and are caught locally, never escaping as raw 500s: `common/auth.py` (`RateLimited`, `GoogleTokenInvalid`), `common/razorpay.py` (`NothingToCancel`, `PauseUnavailable`, and similar billing-state exceptions).

## Conventions

- **Lens** — `reader` (default), `cyber`, `markets` are shipped; `health`/`policy` exist as design tokens but are marked "drafted" as of 2026-09-25 (see `DESIGN.md`). The full shipped list comes from `GET /api/v1/lenses`; an unknown/missing lens falls back to `reader`. Lens **ranks** the feed, it does not filter it (a past bug hid all non-cyber news under the cyber lens — fixed, and now load-bearing).
- **Region/state** — ISO 3166-2 (`region="IN"`, `state="IN-KA"`).
- **Languages** — ISO 639-1 (`en`, `hi`, `kn`, `ta`, ...); a comma-separated preference list ranks (never filters) the feed and picks the served headline language.

---

## Discovery / meta (`api/routes/meta.py`)

| Method & path | Params | Auth | Notes |
|---|---|---|---|
| `GET /healthz` | `freshness_window_hours` (query, clamped `MIN_WINDOW_HOURS..MAX_WINDOW_HOURS`) | public | **No `/api/v1` prefix.** Never fails on pipeline backlog — always `SELECT 1`, then reports Redis stream depth (`streams`) and a 24h window of p50/p95 pipeline-stage latencies (`freshness`). `-1`/`null` means "unavailable," not zero. |
| `GET /api/v1/lenses` → `LensesResponse` | — | public | Shipped lenses only. |
| `GET /api/v1/sources` → `SourcesResponse` | — | public | Public monitored-outlet list; deliberately excludes feed URLs and error text. |
| `GET /api/v1/regions` | — | public | `common.regions.states_payload()`. |
| `GET /api/v1/taxonomy` → `TaxonomyResponse` | — | public | Sector → subsector tree. |
| `GET /api/v1/sitemap/records` | — | public | Full archive, capped at 50,000 (sitemap protocol limit). |
| `POST /api/v1/csp-report` | raw body, ≤8192 bytes | public | `204`. In-process rate limit `CSP_LOGS_PER_MINUTE = 60` via a mutable module-level window (`ponytail`-flagged: fine for one process, would need a shared counter across workers). |

`GET /api/v1/professions` and `GET /api/v1/languages` live in `api/routes/auth.py` — see Auth below.

## Auth (`api/routes/auth.py`)

Passwordless magic link + Google sign-in.

| Method & path | Body | Response | Auth | Notes |
|---|---|---|---|---|
| `GET /api/v1/professions` | — | — | public | `common.professions.grouped()`. |
| `GET /api/v1/languages` | — | — | public | Offered languages + `DEFAULT_LANGUAGES`. |
| `POST /api/v1/auth/request` | `{email, next?}` | — | public | Always `200 {"ok":true}`, even when internally rate-limited (`RateLimited`) — no account enumeration. `next` is validated by `safe_next()` (must start with `/`, not `//`, ≤500 chars) to block an open redirect. |
| `POST /api/v1/auth/verify` | `{token}` | `SessionResponse` | public | `401` on invalid/expired token. Sets the session cookie. |
| `POST /api/v1/auth/google` | `{credential?, access_token?}` | `SessionResponse` | public | Accepts a Google ID token (button/One Tap) or an OAuth access token — one of the two. `422` if neither given, `401` on `GoogleTokenInvalid`. |
| `POST /api/v1/auth/profile` | `{name, profession, state?, languages[]=[], consent=false}` | `MeResponse` | session (required) | `422` on missing name, invalid profession, no valid language, or `consent=false` (DPDP requirement). |
| `DELETE /api/v1/auth/session` | — | `204` | none required | Revokes whatever token is presented; always `204`. |
| `POST /api/v1/auth/cookie` | — | `204` | Bearer header required | "Adopts" a page's localStorage bearer token into the HttpOnly cookie. `401` if the token is invalid. |
| `GET /api/v1/auth/me` | — | `MeResponse{user_id,email,plan}` | session (required) | `plan` from `common.billing.plan_for`. |

## Feed (`api/routes/feed.py`)

`GET /api/v1/feed` → `FeedResponse`, public.

Params: `lens?`, `sector?` (comma-separated), `interests?` (comma-separated `sector` or `sector:subsector` tokens), `region?`, `state?`, `scope?` (`region`|`national`|`world`|`all`), `languages?` (comma-separated), `sort` (`latest`|`top`, default `latest`), `limit` (clamped 1-100, default 30).

Notable behaviour: CVE-only records (sources `nvd`/`cisa_kev`) are excluded from the main window and woven back in only for lenses whose config sets `include_cve_records`, at a fixed 2-news-to-1-record interleave ratio (not applied under `sort=top`). Per-sector windowing (`ROW_NUMBER() OVER (PARTITION BY sector...) <= 120`) stops one high-churn sector from starving the others. `attach_clip_shows()` runs as a post-hoc extra query to fill `clip_shows`, gated by `prism_podcasts_enabled`. No caching header is set (frontend relies on Next's own `revalidate=60`).

## Search (`api/routes/search.py`)

`GET /api/v1/search` → `FeedResponse` (`items` of `FeedItem`, `lens`), public.

Params: `q` (`Query(..., min_length=2, max_length=100)`), `limit` (clamped 1-50).

**This is substring matching, not full-text or semantic search.** The query:

```sql
WHERE e.title ILIKE :q OR e.summary ILIKE :q
   OR e.id IN (
       SELECT ee.event_id FROM event_entities ee
       JOIN entities ent ON ent.id = ee.entity_id
       WHERE ent.name ILIKE :q
   )
```

with `pattern = f"%{q.strip()}%"`. The route's own comments explain the rejection of `tsvector`: stemming would change what a query *means* (`"modi"` would stop matching `"Modinagar"`), and the corpus spans nine Indian languages with no single stemming config that fits all of them.

**Matches title, summary, AND the names of people/entities in the event's cast** — confirmed by the `event_entities`/`entities` join above. Accelerated by `pg_trgm` GIN trigram indexes, added in two migrations:

- `db/versions/c8a3f5d21b74_search_trgm_index.py` (2026-08-29): `CREATE EXTENSION IF NOT EXISTS pg_trgm`; `ix_events_title_trgm` and `ix_events_summary_trgm` (both `gin (... gin_trgm_ops)`).
- `db/versions/d4b7e2a9c1f3_entities_name_trgm.py` (2026-09-25): `ix_entities_name_trgm` on `entities.name` — added specifically so cast names (e.g. a hospital name) are searchable even when absent from the title/summary; the migration's own docstring notes 4 of 6 sampled name searches returned nothing before this index/query change shipped.

Trigram indexes need **≥3 characters** to actually be used — a 2-character query (the schema's floor) falls back to a full scan; this is documented in the migration as the intended floor, not an oversight. Results are serialized through the neutral `reader` lens (search spans sectors by design; no CVE-only filtering, since an explicit query is read as clear intent).

## Trending / story arcs (`api/routes/trending.py`)

| Method & path | Params | Response | Notes |
|---|---|---|---|
| `GET /api/v1/trending` | `state?`, `sector?` (comma-sep), `limit` (clamped 1-50, default 20) | `TrendingResponse` | Only `status='active' AND merged_into IS NULL`. `route` is only populated when `STORY_BOUNDARY_STATUS == "verified"` — that flag is currently hardcoded to `"provisional"` at module level, so `route` is always `null` in production today. Up to 4 photos/story via `story_photos()` (dedupes by URL and by perceptual hash, `hamming <= 8`, one photo per publisher first). |
| `GET /api/v1/trending/{slug}` | `slug` | `TrendingStoryDetail` | `404` unknown slug. Follows a `merged_into` chain up to `_MAX_MERGE_HOPS=8`; `500 "merge cycle"` if a cycle is detected, `500 "merge chain too deep"` past the hop bound (comment: real 2-hop chains exist in prod, so single-hop-only was a bug). `branches` (the L3 branch tree) is populated under the same currently-always-false `"verified"` flag as `route` above. `_related_stories()` scores IDF-weighted shared-cast relatedness (floor `0.5`) plus causal links from `event_links`, capped at 5. |

## Subject taxonomy (`api/routes/subject.py`)

| Method & path | Params | Response | Cache-Control |
|---|---|---|---|
| `GET /api/v1/subjects` | — | `SubjectTree` | `public, s-maxage=900, stale-while-revalidate=3600` |
| `GET /api/v1/subject/{path:path}` | `path` (dotted, e.g. `world/asia` → `world.asia`), `limit` (clamped 1-60, default 30), `lens?` | `SubjectPage` | `public, s-maxage=120, stale-while-revalidate=600` |

`/subjects`' story counts use a 30-day liveness window; `/subject/{path}`'s `story_count` is the **full archive** — a deliberately different meaning between the two endpoints. `/subject/{path}` matches the node and everything under it (`subject_path LIKE 'path.%'`); `404` if `subjects.is_valid(path)` fails.

## Entities (`api/routes/entity.py`)

| Method & path | Params | Response | Notes |
|---|---|---|---|
| `GET /api/v1/entity/{slug}` | `slug`, `limit` (clamped 1-60, default 30), `lens?` | `EntityPage` | `404` if not found. `indexable` is gated by `INDEXABLE_MIN_RECORDS = 3` for SEO purposes (measured at write time: 55,214 entities total, 5,995 with ≥3 records). Maps the extractor's loose `entity_type` vocabulary to schema.org types (`_SCHEMA_TYPE`). |
| `GET /api/v1/sitemap/entities` | — | — | Entities with ≥`INDEXABLE_MIN_RECORDS` served records, capped at 50,000. |

## Corrections and versions (`api/routes/corrections.py`)

| Method & path | Params | Response | Notes |
|---|---|---|---|
| `GET /api/v1/events/{event_id}/versions` | `event_id` | `VersionsResponse` | Reads `event_revisions` (max 50) + a shared `corrections_for()` helper also used by `events.py`. |
| `GET /api/v1/corrections` | `limit` (clamped 1-500, default 100) | `CorrectionsResponse` | Public editorial corrections log, title-joined against `events`/`event_revisions`. |

## Events — detail, briefs, questions, Ask (`api/routes/events.py`)

The largest route file (727 lines). All routes take `get_current_user_optional`.

| Method & path | Params/Body | Response | Notes |
|---|---|---|---|
| `GET /api/v1/events/{event_id}` | `event_id` | `EventDetail` | `404` if not found. **The real paywall boundary lives here**, not only on `/brief`: `lens_briefs`/`lens_points`/`projection` are filtered down to `{reader} ∪ unlocked_lenses(user)` before serialization — the source comments mark this fix explicitly, after a bypass was found in review. `available_lenses` is still computed from the *unfiltered* projection (which lenses exist is public; what a locked lens says is not). Builds `story_slug` via a JSONB-containment scan over `stories.member_event_ids` (flagged in-code as a spot to add a GIN index if p95 ever shows it). Attaches podcast clips (`prism_podcasts_enabled`) and X posts (`prism_x_enabled`) behind flags, and rendering verdicts behind `prism_quote_verdicts`. |
| `GET /api/v1/events/{event_id}/brief` | `event_id`, `lens` (required query) | `BriefResponse` | `422` unknown lens. A non-reader lens requires sign-in (`401`) and consumes a sample quota on first unlock; `402` with `{"error","remaining","lens"}` if the quota is spent. Uses a **Redis single-flight lock** (`brief:{event_id}:{lens}`) so concurrent viewers of the same lens cost one LLM call, not one each. On generation failure: releases the claimed unlock, refunds the sample, and returns `brief: null` — never a 500. |
| `GET /api/v1/events/{event_id}/questions` | `event_id`, `lens?` | `QuestionsResponse` | `404` if event missing. |
| `POST /api/v1/events/{event_id}/ask` | `event_id`, body `{question (≤2000 chars re-validated in-route, though the schema caps at 500), session_id?}` | **SSE** (`text/event-stream`) | Headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`. Layered limits: plan-based daily allowance (`429` with `used/limit/signin_helps/plus_helps` if exhausted), a Redis burst check keyed on user/session+IP (`429` "too many questions this minute" or "question limit reached" for anonymous IP flooding), and a global daily spend ceiling for non-Plus users (`503` "Ask is resting for today"). `422` if the question is empty or over length. |

## Market Pulse (`api/routes/digest.py`)

`GET /api/v1/digest/markets` → `DigestResponse`. Calls `correlation.digest.get_market_digest()`; returns a bare `204` (no body) when synthesis is unavailable — the frontend hides the Pulse card on `204`, and this path is never a 500. Hydrates up to 24 `event_ids` into `FeedItem` rows via the shared `build_feed_item()` helper under the `markets` lens.

## Watchlist (`api/routes/watchlist.py`)

All four routes require an account session (`get_current_user`). Request/response models are defined locally in this file, not in `api/schemas.py`.

| Method & path | Body/Params | Notes |
|---|---|---|
| `GET /api/v1/watchlist` | — | `WatchlistResponse`. |
| `POST /api/v1/watchlist` | `{kind, value}` | `422` if `kind` isn't `"ticker"`/`"sector"` or `value` is invalid (1-40 chars). `_normalize()` upper-cases tickers, lower-cases sectors. `ON CONFLICT DO NOTHING` upsert (idempotent follow). A watchlist follows a ticker or a sector, not an event. |
| `DELETE /api/v1/watchlist` | query params `kind`, `value` (not a body) | Idempotent unfollow. |
| `GET /api/v1/watchlist/events` | — | `WatchEventsResponse` (max 40). Matches `sector = ANY(:sectors)` or `jsonb_exists_any(projection->'finance'->'tickers', :tickers)`. |

## Billing (`api/routes/billing.py`)

Razorpay Subscriptions (UPI Autopay + cards). All user-scoped routes require an account session; the webhook is separately authenticated.

| Method & path | Body | Notes |
|---|---|---|
| `GET /api/v1/billing/plans` | — | Public `checkout_ready` (is Razorpay configured) + `key_id`. |
| `POST /api/v1/billing/checkout` | `{plan, start_after_current=false}` | `503` if Razorpay unconfigured; `409` if already subscribed unless it's a valid monthly→yearly switch; creates a `subscriptions` row (`status='created'`). |
| `POST /api/v1/billing/verify` | `{razorpay_payment_id, razorpay_subscription_id, razorpay_signature}` | `400` on bad signature. Activates the subscription immediately from the signature; the webhook/reconcile job backfills authoritative state later. |
| `POST /api/v1/billing/cancel` | `{reason?, comment?}` | `404` if no active subscription. Access continues until `current_period_end`. |
| `POST /api/v1/billing/pause` | `{months}` (1, 2, or 3) | `422`/`409` on an invalid state; only a renewing `plus_monthly` plan can pause. |
| `POST /api/v1/billing/resume` | — | `409` if not currently paused. |
| `POST /api/v1/billing/refund` | — | 7-day refund window (`razorpay.refundable_until`); refund-then-cancel ordering is documented in-code. |
| `GET /api/v1/billing/me` | — | Current plan + any scheduled plan change. |
| `GET /api/v1/billing/history` | — | Live read from Razorpay (`list_invoices`) — not cached. |
| `POST /api/v1/billing/razorpay/webhook` | raw JSON | HMAC-SHA256 signature check against `x-razorpay-signature`. `503` if the webhook secret is unconfigured, `401` on a bad signature. |

## Labelling task protocol (`api/routes/label.py`)

Two credential types: a batch `key` (a join capability, safe to put in a URL) vs. a per-person invite `token` (a write credential — header `X-Label-Token` or a JSON body field, **never** in a URL).

| Method & path | Auth | Notes |
|---|---|---|
| `POST /api/v1/label/{key}/join` | none (key-gated) | Body `{name (≤60 chars)}`. `409` if the batch is closed; `403` if the batch is `listed` or not `purpose="work"` (must go through `/labeller` instead) or not `self_join`. |
| `GET /api/v1/label/{key}/guide` | invite token | `403` no token, `404` no guide for that task kind. `Cache-Control: private, no-store`. |
| `GET /api/v1/label/{key}` | invite token optional | Batch header + this invite's progress. |
| `GET /api/v1/label/{key}/next` | invite token | Deterministic lowest-unanswered-position order (not random), so two labellers converge on the same task sequence. |
| `POST /api/v1/label/{key}/answer` | invite token | Body `{task_id, token, selected[]=[], unsure=false, skipped=false, ms_spent?}`. `409` if the batch/round is closed. Work-purpose answers are **final** — no rewrite — to prevent gaming hidden quality checks. Upserts on `(task_id, invite_id)`. |
| `GET /api/v1/label/{key}/export` | **static admin token** (`require_admin`) | Every response, ungrouped, per labeller — explicitly never server-side merged into a verdict. |

## Labeller workspace (`api/routes/labeller.py`)

All routes require an account session (`get_current_user`) — this sits in front of the token-based protocol above.

| Method & path | Notes |
|---|---|
| `GET /api/v1/labeller/guides/{kind}` | `403` unless applied/active/paused. `Cache-Control: private, no-store`. |
| `GET /api/v1/labeller/me` | Status (`none`/`applied`/`active`/`paused`/`removed`), languages read, available language list. |
| `POST /api/v1/labeller/apply` | Body `{languages_read[], note (≤500)}`. `422` if no valid language. Upsert never changes an existing `status`. |
| `GET /api/v1/labeller/batches` | Listed+open+work batches with ≥1 eligible task in the labeller's languages; split into `ready`/`done`, plus per-kind qualification status. |
| `POST /api/v1/labeller/batches/{key}/start` | `403` if not active/not qualified. Mints or returns an existing invite bound to the account. |
| `POST /api/v1/labeller/practice/{kind}/start` | Unlimited attempts; `pg_advisory_xact_lock` prevents a double-start race. |
| `POST /api/v1/labeller/qualify/{kind}/start` | `409` if already passed; `429` if within `RETAKE_AFTER_HOURS` of a failed attempt. Draws `QUESTIONS_PER_TEST` items via `random.SystemRandom().sample`, excluding previously-revealed missed questions (a fix dated 2026-09-23, closing a "see the answer, retake, pass" hole). |

## Cookieless usage beacon (`api/routes/beacon.py`)

`POST /api/v1/beacon` → always `204`. Body `{e: "view"|"arrival"|"share"|"ask"|"lens"|"subscribe"|"signin", d (≤48 chars), ref (≤253), s (≤16)}`. Auth: `get_current_user_optional`. Bespoke Redis rate limiting: per-visitor and per-IP daily caps (`common/usage.py`), plus a new-visitor-per-IP cap and bot-UA filtering (`usage.is_bot`). Fails closed — if Redis is unavailable, the event is silently dropped and the route still returns `204`.

## Admin (`api/routes/admin.py`, `admin_controls.py`, `admin_labellers.py`, `admin_metrics.py`)

`admin.py` (mixed auth — two static-token operational triggers, two account-based dashboard routes):

| Method & path | Auth | Notes |
|---|---|---|
| `GET /api/v1/admin/status` | `require_admin` | LLM budget balance/floor + whether collection is active. |
| `POST /api/v1/admin/pipeline/run` | `require_admin` | Publishes to the `stream.ADMIN_TRIGGERS` Redis stream — the API never ingests in-process; the worker owns collection. |
| `GET /api/v1/admin/me` | `require_admin_user` | `{email}` — whether this account may open `/admin`. |
| `GET /api/v1/admin/audit` | `require_admin_user` | `limit` (clamped 1-500, default 100). |

`admin_controls.py` (all `require_admin_user`, all `Cache-Control: no-store`):

| Method & path | Notes |
|---|---|
| `GET /api/v1/admin/people` | `limit` (1-500, default 200), `offset` (default 0). Every account: plan, 28-day activity window, labeller status. |
| `GET /api/v1/admin/flags` | Read-only view of an 11-key `FLAGS` dict (e.g. `prism_ingestion_enabled`, `prism_veto_enabled`) — deliberately never settable from this endpoint. |
| `POST /api/v1/admin/pipeline/trigger` | The same ingestion signal as the static-token `/admin/pipeline/run`, but audited against the founder's own account before publishing. |

`admin_labellers.py` (all `require_admin_user`, all writes routed through `common.label_ops` and audited):

| Method & path | Body | Notes |
|---|---|---|
| `GET /api/v1/admin/labellers` | — | Labeller list + standing board + known languages. |
| `POST /api/v1/admin/labellers/status` | `{email, status: "active"\|"paused"\|"removed"}` | `404` unknown labeller, `409` on a refused status transition. |
| `POST /api/v1/admin/labellers/add` | `{email, languages_read[]}` | Filters to known languages. |
| `POST /api/v1/admin/labellers/qualify` | `{email, kind, granted}` | — |
| `GET /api/v1/admin/batches` | — | — |
| `POST /api/v1/admin/batches/{key}/listed` | `{on}` | — |
| `POST /api/v1/admin/batches/{key}/open` | `{on}` | — |
| `POST /api/v1/admin/batches/{key}/languages` | — | `label_ops.gate_languages`. |
| `GET /api/v1/admin/batches/{key}/items` | — | `404` unknown batch. |
| `PUT /api/v1/admin/batches/{key}/explanations` | `{edits: [{position (≥0), explanation (≤2000)}]}` | — |

`admin_metrics.py` (all `require_admin_user`, all `Cache-Control: no-store`):

| Method & path | Params | Notes |
|---|---|---|
| `GET /api/v1/admin/metrics` | `days` (1-366, default 28) | `common.metrics.dashboard`. |
| `GET /api/v1/admin/metrics/weekly.csv` | `weeks` (1-104, default 12) | Returns `text/csv` directly (not a JSON model), with `Content-Disposition: attachment; filename="prism-weekly.csv"`. |
| `GET /api/v1/admin/coverage` | `days` (1-366, default 28) | Outlet co-coverage graph (`common.coverage.network`) — feeds `/admin/coverage`'s 3D visualization on the frontend. |

## Photos — no placeholder or fallback images (`common/images.py`)

Confirmed directly in `common/images.py`: there is **no fallback/placeholder URL anywhere** in the module or its callers. The mechanism is exclusion, not substitution — a story with no real photo gets `image_url: null`, never a stand-in image.

- `hi_res(url)` rewrites a few known CDN URL patterns (e.g. BBC's `ichef.bbci.co.uk`) to request a larger rendition of *the same* publisher photo; unrecognized hosts pass through unchanged. It never invents or substitutes a URL.
- **Furniture detection**: a photo (by perceptual hash or URL) seen on ≥4 reports (`PLACEHOLDER_REPEATS`) within a 14-day window (`PLACEHOLDER_WINDOW`) is treated as "furniture" — recurring outlet logos or generic stock photography (the code cites measured examples: one outlet's `og-image.png` on 363 reports, another's generic template image on 87). `placeholders(session)` computes this set with an in-process 5-minute TTL cache (`_PLACEHOLDER_TTL_S = 300.0`, a module-level global — not Redis; fine for one process, would need a shared cache across workers if that becomes a problem).
- `REAL_PHOTO_SQL` is a SQL fragment excluding any row whose `image_phash`/`image_url` is in the placeholder set; `report_photo_join()` (a `LEFT JOIN LATERAL`) uses it to pick one real photo per event across `feed.py`, `search.py`, `digest.py`, `entity.py`, and `subject.py` — preferring the event's own stored image if real, else the earliest other real photo, else SQL `NULL` (which becomes `image_url: null`, never a substitute).
- `is_placeholder(phash, url, keys)` is called directly in `events.py` when building each `SourceRef`: `image_url = None if is_placeholder(...) else hi_res(...)` — a per-source image is explicitly nulled, not shown, if it's furniture.
- `trending.py`'s `story_photos()` adds its own dedup on top (exact URL, then perceptual hash `hamming <= 8`, preferring one photo per publisher) — additive to, not a replacement for, the placeholder exclusion above.

## How to add a route

There is no `CONTRIBUTING.md`-style doc for this; the pattern below is reverse-engineered from every route file and is what to follow:

1. **One router per concern-file** under `api/routes/`. Each module declares its own `router = APIRouter()`. Paths on each `@router.get/post/...` decorator are **fully-qualified** (e.g. `"/api/v1/admin/people"`) — there is no shared prefix applied anywhere, deliberately, per `main.py`'s own comment ("the app's route set is identical to the pre-split single-file version").
2. **Registration is manual**: import the new module by name in `api/main.py`'s `from api.routes import (...)` block, then add `app.include_router(<module>.router)`. `api/routes/__init__.py` is empty — there is no aggregation point.
3. **Response/request models**: put a model in `api/schemas.py` (pure Pydantic, explicitly "no DB or app deps" per its own docstring) only if it's reused across more than one route file (the way `FeedItem` is shared by `feed.py`/`search.py`/`digest.py`/`entity.py`/`subject.py`). If a model is only used by one route file, define it locally at the top of that file — this is the convention in `watchlist.py`, `auth.py`, `billing.py`, `beacon.py`, `admin_labellers.py`, and `label.py`.
4. **Auth**: inject the right tier from `api/deps.py` via `Depends(...)` — `get_current_user` (required session), `get_current_user_optional` (anonymous allowed), `require_admin` (static token), or `require_admin_user` (admin-allowlisted session). If the handler doesn't need the dependency's return value, declare it at the decorator level instead: `@router.get(..., dependencies=[Depends(require_admin)])`.
5. **Data access**: raw SQL via `sqlalchemy.text()` against an `AsyncSession` from `common.db.get_db` — there is no ORM model layer or repository abstraction anywhere in `api/routes/`. Follow the existing SQL style in whichever route file is closest to what you're adding.
6. **Route-surface lock**: `tests/test_api_routes.py` asserts the app exposes exactly its `EXPECTED` set of `(method, path)` pairs. Add the new route there in the same change, or CI fails.

---

## Open questions

- `common/config.py`'s `Settings.cors_origin_list` and the full list of `PRISM_ADMIN_EMAILS`/`PRISM_ADMIN_TOKEN` configuration was confirmed to exist but not read in full — exact production values are intentionally out of scope for a repo doc.
- `STORY_BOUNDARY_STATUS` is hardcoded to `"provisional"` at module level in `trending.py`, which means `route` and `branches` are always null in production today. Whether/when this flips to `"verified"` is a product/data-quality decision, not visible in the route code itself.
- Whether Health/Policy lenses (drafted in `DESIGN.md`) ever reach `GET /api/v1/lenses`'s shipped list is a product decision tracked outside this API surface.
- `common/config.py`'s `prism_trusted_proxy_hops` default (used by `client_ip()` for IP-based rate limiting) was read as `1` but its correctness depends on Railway's actual proxy topology, which this document did not independently verify.
