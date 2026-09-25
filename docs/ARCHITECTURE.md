# Prism — System Architecture

Drafted 2026-09-25 against branch `feat/verified-event-match` (VERSION `0.0.97.0`). Source of
truth is the code; `docs/ARCHITECTURE.md` and `docs/DB-SCHEMA.md` (July 2026) describe an earlier,
Kafka/OpenSearch-flavored design that was never built that way and are used here only for
background contrast, not as fact. All claims below are cited `path:line` against files read
directly for this doc. See `.context/docs-drafts/DB-SCHEMA.md` for the database schema in detail,
and `docs/API.md` for the full endpoint reference (this doc only summarizes the surface).

## 1. System context and containers

Prism is an Indian multilingual news-intelligence product. One Postgres database and one Redis
instance are the only state; every other box below is a stateless compute or a third-party API.

| Container | What it is | Where it runs | Key entry point |
|---|---|---|---|
| **web** | Next.js 15 app (reader UI, `/admin`, `/label`) | Vercel, root directory `web/` (`vercel.json:3-5`) | `web/src/app/**` |
| **api** | FastAPI REST + SSE serving layer | Railway, default role of the shared Docker image (`Dockerfile:46`) | `api/main.py` |
| **worker** | Pipeline stage consumers + scheduled jobs | Railway, `PRISM_SERVICE_ROLE=worker` on the same image (`Dockerfile:46`) | `worker/__main__.py` |
| **Postgres** | Canonical store | Railway pgvector template in prod; `pgvector/pgvector:pg16` locally and in CI (`docker-compose.yml:6`, `.github/workflows/ci.yml:29`) | extensions `vector`, `pg_trgm` created by migrations |
| **Redis** | Stream spine (Streams, not pub/sub) + locks + rate-limit counters + caches | Railway Redis; `redis:7-alpine` locally (`docker-compose.yml:24`) | `common/stream.py` |
| **Langfuse** | Tracing, managed prompts, offline evals | Self-hosted, **separate** Railway project (own Postgres/ClickHouse/Redis/MinIO) | `common/observability.py` |
| **OpenRouter** | Primary LLM provider: chat models for every pipeline stage, plus the alpha **Decisions API ("Jev")** | External | `common/llm.py`, `common/decisions.py` |
| **fastembed** | In-process multilingual embeddings (`intfloat/multilingual-e5-base`, 768-dim), no network call | Baked into the Docker image at build time (`Dockerfile` — `RUN python -c "from common.embeddings import _get_model; _get_model()"`) | `common/embeddings.py` |
| **Razorpay** | Billing (checkout, subscriptions, refunds) | External | `common/razorpay.py`, `common/billing.py`, `api/routes/billing.py` |
| **Email** | Magic-link delivery, pluggable | Console sender (dev) or Resend (prod), via `prism_email_provider` | `common/email.py` |
| **Google Identity Services** | Sign-in (ID-token or access-token flow) | External, verified against Google's `tokeninfo` endpoint | `common/auth.py` |
| **IndexNow** | SEO push-indexing | External, called from a scheduled worker job | `common/indexnow.py` |
| **Ollama Cloud** | Fallback LLM provider (`llm_provider=ollama`) | External | `common/config.py:23-24` |

### 1.1 System context diagram

```mermaid
flowchart LR
    Reader["Reader (browser)"] -->|HTTPS| Web["web — Next.js on Vercel"]
    Web -->|"REST + SSE\nNEXT_PUBLIC_API_URL"| API["api — FastAPI on Railway"]
    API --> DB[("Postgres 16\npgvector + pg_trgm")]
    API --> Redis[("Redis — Streams")]
    Worker["worker — pipeline consumers\n+ scheduled jobs"] --> DB
    Worker --> Redis
    API -.->|admin trigger| Redis
    Worker -->|chat + Jev Decisions| OpenRouter["OpenRouter"]
    Worker -->|fallback| Ollama["Ollama Cloud"]
    Worker -->|in-process| FastEmbed["fastembed\nmultilingual-e5-base"]
    API -->|traces| Langfuse["Langfuse\n(self-hosted, separate Railway project)"]
    Worker -->|traces| Langfuse
    API -->|checkout, webhook| Razorpay["Razorpay"]
    API -->|magic link| Email["Email (console/Resend)"]
    API -->|sign-in| Google["Google Identity Services"]
    Worker -->|push-index| IndexNow["IndexNow"]
    Worker -->|cyber feeds| CVE["NVD / CISA KEV"]
    Worker -->|news| RSS["RSS sources"]
    Worker -->|allowlisted accounts| X["X / Twitter API"]
    Worker -->|show feeds| Podcasts["Podcast RSS + audio"]
```

### 1.2 Container / deployment topology

```mermaid
flowchart TB
    subgraph Vercel
        WebSvc["web service\nroot = web/\nvercel.json:3-5"]
    end
    subgraph RailwayPrism["Railway project: prism"]
        APIsvc["api service\nDockerfile default role:\nalembic upgrade head && uvicorn\nDockerfile:46"]
        WorkerSvc["worker service\nPRISM_SERVICE_ROLE=worker\npython -m worker"]
        PG[("Postgres 16 + pgvector\nRailway template")]
        RedisSvc[("Redis")]
    end
    subgraph RailwayLangfuse["Railway project: langfuse (separate)"]
        LF["Langfuse web + worker"]
        LFPG[("Langfuse Postgres")]
        CH[("ClickHouse")]
        MinIO[("MinIO")]
    end
    WebSvc -->|"NEXT_PUBLIC_API_URL=https://api.readprism.news"| APIsvc
    APIsvc --> PG
    APIsvc --> RedisSvc
    WorkerSvc --> PG
    WorkerSvc --> RedisSvc
    APIsvc -.->|LANGFUSE_PUBLIC_KEY/SECRET_KEY/BASE_URL| LF
    WorkerSvc -.-> LF
    LF --> LFPG
    LF --> CH
    LF --> MinIO
```

Both Railway services are built from the **same Docker image** (`railway.json:2-5`, `builder:
DOCKERFILE`) and differentiated purely by `PRISM_SERVICE_ROLE` (`Dockerfile:46`): the default role
runs `alembic upgrade head && exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}`; the
`worker` role runs `exec python -m worker`. **Migrations therefore run on every `api` boot**, before
the process starts serving — a slow migration delays `/healthz` going green (`railway.json:19`:
`healthcheckPath: /healthz`, `restartPolicyType: ON_FAILURE`, `restartPolicyMaxRetries: 5`).
`railway.json:6-17`'s `watchPatterns` scope rebuilds to backend directories only, so a `web/`-only
push does not trigger a Railway rebuild.

The worker can also be split into per-stage Railway services with no code change — it takes a
`--stages`/`PRISM_STAGES` argument (`worker/__main__.py:40-57`) — but the current deployment runs
one `worker` process covering all stages (`docs/DEPLOYMENT.md`, background only, unverified against
a live Railway dashboard from this repo).

`vercel.json:1-16` (repo root) defines exactly one Vercel service, `web`, rooted at `web/`, with a
catch-all rewrite to that service — it is a router into the Next.js app, not an API proxy; the web
app calls the API directly, cross-origin, via `NEXT_PUBLIC_API_URL`.

Local dev mirrors this with `docker-compose.yml`: `postgres` (`pgvector/pgvector:pg16`, creates a
`prism_test` database on first boot via `docker/initdb`, consumed by the test-DB safety guard — see
§5), `redis` (`redis:7-alpine`), and an optional `ollama` service gated behind `--profile
local-llm` so `docker compose up -d` stays fast for anyone pointed at OpenRouter
(`docker-compose.yml:32-49`).

### 1.3 Request path — reader opens `/story/<id>`

```mermaid
sequenceDiagram
    participant Browser
    participant Web as "web/src/app/story/[id]/page.tsx\n(Server Component)"
    participant API as "GET /api/v1/events/{event_id}\napi/routes/events.py:312"
    participant DB as Postgres

    Browser->>Web: GET /story/<id>
    Web->>Web: load(id) -> fetchEvent(id)\n(page.tsx:17-23, api.ts:689)
    alt anonymous reader
        Web->>API: fetch, next:{revalidate:60}\n(api.ts:697, page.tsx:13)
    else signed-in reader (token present)
        Web->>API: fetch, cache:"no-store"\n(api.ts:691-696 — paid-lens leak guard)
    end
    API->>DB: SELECT ... FROM events WHERE id=:id (events.py:318-329)
    API->>DB: JOIN event_memberships/articles/raw_items/sources\nLEFT JOIN enrichments (events.py:333-357)
    API->>DB: SELECT ... FROM perspectives WHERE event_id=:id (events.py:359-369)
    API->>DB: SELECT ... FROM impacts LEFT JOIN entities (events.py:371-386)
    API->>DB: SELECT ... FROM event_entities JOIN entities LIMIT 12 (events.py:388-402)
    DB-->>API: rows
    API->>API: strip PAID_LENS_FIELDS not in unlocked_lenses\n("the paywall's real boundary", events.py:431-462)
    API-->>Web: EventDetail JSON
    Web-->>Browser: rendered story page
```

Next.js's native `fetch` memoizes per-request, so `generateMetadata` and the page body share one
API call (`web/src/app/story/[id]/page.tsx:15-16`). `API_URL` resolves from
`process.env.NEXT_PUBLIC_API_URL`, falling back to `http://localhost:8000`
(`web/src/lib/api.ts:6-10`); production sets it to `https://api.readprism.news` at CI deploy time
(`.github/workflows/ci.yml`, "Inject public build env" step). The handler deliberately does **not**
call the story-timeline assembly used by `/trending/{slug}` on this route, to keep the most-viewed
page cheap (`api/routes/events.py:404-411`).

### 1.4 Ingest path (high level)

Full detail — the match cascade, what gets extracted, cost/latency — belongs in a dedicated
pipeline document. **`docs/PIPELINE.md` is referenced by `docs/CANONICALIZATION.md` but does not
currently exist in the repo** (see Open Questions). The diagram below is scoped to entry points and
stage hand-off only.

```mermaid
flowchart LR
    Sched["APScheduler: ingestion job\nevery PRISM_INGEST_INTERVAL_MINUTES (5)\nworker/__main__.py:196-202"] --> Runner["ingestion/runner.py:run_all"]
    Startup["worker startup\n__main__.py:266,377-382"] --> Runner
    AdminTrig["admin-triggered\nstream.ADMIN_TRIGGERS\n__main__.py:269-276"] --> Runner
    Requeue["APScheduler: requeue_stalled\nevery 10 min\nrunner.py:63"] -.-> RawItems
    Runner --> RSS["ingestion/rss.py"]
    Runner --> NVD["ingestion/nvd.py"]
    Runner --> KEV["ingestion/cisa_kev.py"]
    RSS --> RawItems[("raw_items")]
    NVD --> RawItems
    KEV --> RawItems
    RawItems -->|"stream.RAW_ITEMS\ningestion/base.py:204"| Classify["classification/consumer.py:44\nhandle_raw_item"]
    Classify -->|"stream.CLASSIFIED_ITEMS\nconsumer.py:106-107"| Enrich["enrichment/consumer.py:42\nhandle_classified_item"]
    Enrich -->|"stream.ENRICHED_ITEMS\nconsumer.py:242-243"| Correlate["correlation/consumer.py:91\nhandle_enriched_item -> _attach"]
    Correlate -->|"match cascade\ncorrelation/clustering.py"| Events[("events, event_memberships, ...")]
    Events --> Serving["API serving layer (§1.3)"]
```

Ingestion is never a poll loop of its own — `ingestion/runner.py:run_all()` runs collectors once and
returns; it is triggered by the scheduler, at worker startup, or on an admin trigger. "The API never
ingests in-process" (`worker/__main__.py:269-276`, comment). Each stage is a Redis Streams consumer
group (`common/stream.py`, topics `raw.items` → `classified.items` → `enriched.items`); see
`common/stream.py` in §7 for the transport mechanics. See `docs/CANONICALIZATION.md` for the full
match cascade inside `correlation/clustering.py` (CVE id → URL exact → title/time trigram →
cross-language headline → embedding → entity overlap → the 2026-09-25 **verified tier**, a Jev call
against gist-embedding candidates).

## 2. Backend module map

| Package | Purpose | Key files |
|---|---|---|
| **api** | FastAPI serving layer, `/api/v1` REST + SSE | `main.py` (app wiring, CORS, router registration only), `deps.py` (auth dependencies), `schemas.py` (Pydantic response models, ~570 lines), `routes/` (18 modules — see §3) |
| **agent** | Per-story "Ask" grounded Q&A | `rag.py` (pgvector chunk retrieval + structured, cited answer), `questions.py` (static per-lens suggested questions), `structure.py` (parses the model's post-prose JSON tail for timelines/tables) |
| **classification** | Relevance gate + sector classifier (LLM pair, or one typed Jev call) | `consumer.py` (consumes `raw.items`, emits `classified.items`), `decide.py` (Jev typed-Decisions path), `subject.py` (places a story on the subject tree), `schemas.py` |
| **common** | Shared infra — largest package (51 files) | `stream.py`, `observability.py`, `logging.py`, `db.py`, `config.py`, `llm.py`, `models.py` (570 lines, SQLAlchemy ORM — see `DB-SCHEMA.md`), `decisions.py` (Jev client), `pair_judge.py` (generic cached pairwise-judge, reused by podcasts/xposts), `razorpay.py`, `auth.py`, `budget.py`, `embeddings.py`, `imagehash.py` (SSRF-guarded image fetch), `admin_audit.py`, `quota.py`, `usage.py`, `lenses.py` (in-code role-lens registry — stands in for a deferred `role_lenses` table, `common/lenses.py:1-7`) |
| **correlation** | Canonicalize enriched articles into events; storyline/thread/trending layers on top | `consumer.py` (match-or-create, event projection rebuild), `clustering.py` (7-tier match cascade), `verify.py` (the 2026-09-25 verified/Jev tier), `partition.py` (global Leiden storyline partitioner), `threads.py` (cross-event thread links), `trending.py` (community→durable `stories` reconciliation), `briefs.py`, `cites.py`, `digest.py`, `cluster_metrics.py` |
| **db** | Alembic migration environment | `env.py` (`target_metadata = common.models.Base.metadata`), `versions/` (52 files, linear chain, head `e5a9c3b7d2f1`) |
| **enrichment** | Full text, schema-constrained LLM extraction, embeddings, claim verification | `consumer.py` (consumes `classified.items`, emits `enriched.items`; writes `articles.gist_embedding`), `fulltext.py` (trafilatura fetch), `claims.py` (verbatim-quote enforcement), `cve_lens.py` (deterministic, no LLM), `renderings.py` (quote-language verdicts), `schemas.py` |
| **ingestion** | Collectors → `raw.items` | `runner.py` (`run_all()`: budget-floor gate + stall requeue), `base.py` (idempotent persist/watermark), `rss.py`, `nvd.py`, `cisa_kev.py`, `seed.py` (India-first `sources` seed) |
| **personalization** | Per-lens feed ranking | `ranking.py` (`score_event()`: recency decay + lens weights + corroboration) |
| **podcasts** | Poll → transcribe → match transcript windows to events | `runner.py`, `feeds.py`, `transcribe.py` (Groq Whisper via OpenRouter), `match.py`, `judge.py`, `shows.py` |
| **worker** | Single process (or `--stages`-split) running all stage consumers + scheduled jobs | `__main__.py` (387 lines: argparse `--stages`, wires the three stream consumers, a fake `/healthz` HTTP server for Railway, ~9 APScheduler jobs) |
| **xposts** | Poll official X accounts, match posts to events (pay-per-use) | `runner.py`, `client.py`, `poll.py` (`since_id` idempotent), `match.py`, `judge.py`, `compliance.py`, `accounts.py` |
| **evals** | Offline eval harness against Langfuse datasets | `run_all.py`, `sync_prompts.py`, `brief_groundedness.py` |
| **design** | Design-token → CSS generation, checked in CI | `gen_css.py` (`--check` mode used by `make check` and CI) |
| **tools** | 53 offline/ops scripts, grouped by theme | `backfill_*`, `gold_*`/`score_*` (labelled-set builders + matching scorers), `bakeoff_*` (model comparison), `snapshot_l2.py`/`sweep_partition.py` (storyline offline validation), `audit_event_dups.py`/`repair.py`/`redrive_dead.py`/`correct_record.py` (data-quality), `link_entities.py`/`securities.py`/`wikidata_coverage.py`, `export_fixtures.py`/`load_fixtures.py` |

## 3. API surface summary

Full endpoint reference: `docs/API.md`. Grouped by area; auth column names the dependency each
route resolves through (`api/deps.py`).

| Area | Representative routes | Auth |
|---|---|---|
| **Meta** | `GET /healthz`, `/api/v1/lenses`, `/sources`, `/regions`, `/taxonomy`, `/sitemap/records`, `POST /csp-report` | Public |
| **Feed** | `GET /api/v1/feed` | Public |
| **Search** | `GET /api/v1/search` (trigram `ILIKE` over events + entities, `entities.name` via `ix_entities_name_trgm`) | Public |
| **Events / story** | `GET /api/v1/events/{id}`, `/{id}/brief`, `/{id}/questions`, `POST /{id}/ask` (SSE) | Optional auth (`get_current_user_optional`); paid-lens brief/ask requires sign-in + consumes a sample quota (`common/quota.py`); `ask` additionally gated by Redis burst/IP/day-ceiling checks |
| **Corrections** | `GET /api/v1/events/{id}/versions`, `GET /corrections` | Public |
| **Trending / stories** | `GET /api/v1/trending`, `/trending/{slug}` | Public |
| **Entity** | `GET /api/v1/entity/{slug}`, `/sitemap/entities` | Public |
| **Subject** | `GET /api/v1/subjects`, `/subject/{path}` (edge-cached, `s-maxage=900`/`120`) | Public |
| **Digest** | `GET /api/v1/digest/markets` | Public |
| **Watchlist** | `GET/POST/DELETE /api/v1/watchlist`, `GET /watchlist/events` | `get_current_user` (session required) |
| **Auth** | `POST /auth/request` (magic link), `/auth/verify`, `/auth/google`, `/auth/profile`, `DELETE /auth/session`, `POST /auth/cookie`, `GET /auth/me` | Public endpoints for request/verify/google/sign-out/cookie-migrate; `get_current_user` for profile/me |
| **Billing** | `GET /billing/plans` (public); `POST /checkout`, `/verify`, `/cancel`, `/pause`, `/resume`, `/refund`, `GET /me`, `/history` (`get_current_user`); `POST /razorpay/webhook` (HMAC-SHA256 signature, constant-time compare — no user auth) |
| **Labeller** | `/labeller/me`, `/apply`, `/batches`, `/batches/{key}/start`, `/practice/{kind}/start`, `/qualify/{kind}/start`, `/guides/{kind}` | `get_current_user` |
| **Label (task protocol)** | `/label/{key}/join`, `/guide`, `/next`, `/answer` | Per-batch **invite token** (`X-Label-Token` header or body `token`), not a user session |
| **Admin** | `/admin/status`, `/pipeline/run` | Static token (`X-Admin-Token`, `require_admin`) |
| | `/admin/me`, `/admin/audit`, `admin_controls.py` (`/people`, `/flags`, `/pipeline/trigger`), `admin_labellers.py`, `admin_metrics.py` (`/metrics`, `/metrics/weekly.csv`, `/coverage`) | Admin-user session + `PRISM_ADMIN_EMAILS` allowlist (`require_admin_user`) |
| | `/label/{key}/export` | Static token, deliberately separate from the batch invite key |
| **Beacon** | `POST /beacon` | Public; optional user for attribution, fail-closed on Redis errors, bot-UA filtering, per-visitor/IP daily caps |

Rate limiting / quota mechanisms in play: `common/quota.py` (atomic sample debit, per-(event,lens)
unlock tracking, Ask allowance-by-plan, Redis burst/IP/day-ceiling), `common/usage.py` (beacon daily
caps), `common/budget.py` (a global LLM-balance floor gating ingestion, not a per-request limiter),
`common/locks.py.single_flight` (dedupes concurrent brief generation per event+lens, a concurrency
control rather than a rate limit).

## 4. Auth & security model

- **Sessions are dual-transport.** Two credential types: single-use **magic-link tokens**
  (`auth_tokens`, SHA-256 hash only, consumed atomically) and **sessions** (`sessions`, also
  hash-only, TTL `prism_session_ttl_days`, default 30). The client can present either an
  `Authorization: Bearer <token>` header or an **HttpOnly cookie** (`prism_session`, set with
  `samesite="lax"`, `secure=prism_cookie_secure`). Note: `common/models.py`'s `Session` docstring
  still says "Bearer (not cookie) — no CSRF surface," which is stale; `api/deps.py` added cookie
  support later (see Open Questions). Cookie use for unsafe methods additionally requires an
  `Origin`-allowlist check (`_origin_ok`), described in the code as defense-in-depth beyond
  `SameSite=Lax` — there is no separate CSRF token.
- **Google sign-in** verifies either an ID token or an access token against Google's `tokeninfo`
  endpoint, checking audience, issuer, and `email_verified`; the verified email resolves to the
  same account a magic-link signup would create.
- **Admin allowlist**: `PRISM_ADMIN_EMAILS` (comma-separated, empty = nobody) gates
  `require_admin_user` — an account-bound identity rather than a shared static token, so a
  revocation is one env var edit and every admin action is attributable to a person. A **separate**
  static-token tier (`PRISM_ADMIN_TOKEN`, `X-Admin-Token` header, constant-time compare) exists for
  operational/pipeline triggers and refuses to boot outside localhost if left at the `"change-me"`
  placeholder.
- **Admin audit**: every admin-user-gated mutation is recorded via `common/admin_audit.py` in the
  **same transaction** as the change — a change without a matching audit row cannot exist. Read
  back at `GET /admin/audit`.
- **CSP**: configured in `web/next.config.ts`, currently **report-only**
  (`Content-Security-Policy-Report-Only`), not enforced — the comment explicitly frames this as
  pending nonce wiring. Violations post to `POST /api/v1/csp-report`, rate-limited to 60/minute
  **per process** (a known, flagged ceiling — under N replicas the effective limit is `60×N`).
  Enforced alongside it: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, HSTS, and a
  `no-referrer` override on `/label/:path*` to keep labelling batch keys out of `Referer`.
- **CORS**: `api/main.py` configures `CORSMiddleware` with `allow_origins=cors_origin_list`
  (from `CORS_ORIGINS`) plus a project-scoped preview-origin regex
  (`https://prism-[a-z0-9-]+-matrixsociallabs-projects\.vercel\.app`) — deliberately not a bare
  `*.vercel.app` wildcard, which would match any tenant's deployment. `allow_credentials=True`
  because the session cookie is cross-subdomain (`www` calling `api.readprism.news`). The same
  regex gates which origins may write the session cookie, by design, so the two allowlists cannot
  drift apart.
- **Test-suite production guard** (`tests/conftest.py`): a session-scoped autouse fixture refuses to
  run any test against a non-local database — allowed hosts are `localhost`, `127.0.0.1`, `::1`,
  `db`, `postgres`, or any database name ending `_test` — and calls `pytest.exit(..., returncode=2)`
  otherwise (a hard exit, not a skip). A second mechanism turns a "no database" **skip** into a hard
  **failure** when `PRISM_REQUIRE_DB=1` is set, which is exactly what CI sets, so a Postgres service
  that failed to start cannot report green.
- **SSRF guard for image fetches** (`common/imagehash.py`): resolves the hostname and rejects any
  target whose resolved IP is not `is_global` (blocks loopback, RFC1918, link-local/cloud-metadata
  ranges). Follows redirects **by hand** (up to 3 hops), re-checking the guard on every hop so a
  redirect chain cannot smuggle a private target in after the first check passes. Caps body size at
  3 MB while streaming; the fetched image is hashed and discarded, never stored or served.

## 5. Configuration (`common/config.py`)

`Settings(BaseSettings)`, 317 lines, pydantic-settings loading from `.env` (env var name = field
name uppercased). `.env.example` mirrors every default checked. One value is read outside this
class entirely: `PRISM_MODEL_TRANSCRIBE` (podcast transcription model, `.env.example:147`) is
consumed directly by the podcast pipeline, not through `Settings`.

### Models

| Setting | Default | Purpose |
|---|---|---|
| `llm_provider` | `openrouter` | `openrouter` (primary) or `ollama` (fallback) |
| `prism_model_gate` / `prism_model_classify` | `google/gemini-3.1-flash-lite` | Relevance gate / classification — high-volume stages |
| `prism_model_extract` / `prism_model_extract_light` | `google/gemini-3.1-flash-lite` | Nested-JSON extraction (feeds clustering); light variant for soft news |
| `prism_model_correlate` | `z-ai/glm-5.3-flash` | Briefs, thread-links, digest |
| `prism_model_agent` / `prism_model_agent_free` | `qwen/qwen3.7-plus` / `z-ai/glm-5.3-flash` | Ask agent, paid vs. free (~1/6 the cost) |
| `prism_model_judge` | `google/gemini-3.5-flash` | Offline evals |
| `prism_model_fallback` | `z-ai/glm-5.3-flash` | Takes over on content-policy refusal; empty disables fallback |
| `prism_model_guard` | `google/gemini-3.1-flash-lite` | Ask moderation pre-check |
| `prism_embed_model` / `prism_embed_dim` | `intfloat/multilingual-e5-base` / `768` | In-process fastembed model; dimension change requires a `vector(...)` migration |
| `prism_model_decide` | `typesafe/jev-1.13` | Typed-Decisions ("Jev") model via OpenRouter, pinned version |

### Feature flags

Production values are the Railway worker's environment, read 2026-09-25 — the code
default is not always what runs.

| Setting | Default | Production | Pattern | Gates |
|---|---|---|---|---|
| `prism_event_verify` | `off` | `off` (to shadow next) | **off\|shadow\|live** | Verified matching tier (`correlation/verify.py`) |
| `prism_decisions_mode` | `off` | **`live`** | **off\|shadow\|live** | Jev typed decisions replacing gate + classify LLM calls |
| `prism_judge_backend` | `llm` | **`decide`** | **llm\|decide** | Clip, X-post and veto judges |
| `prism_x_enabled` | `False` | `true` | bool; worker/API split acts as shadow | X-posts pipeline |
| `prism_quote_verdicts` | `False` | `true` | bool; worker/API split acts as shadow | Speaker-card quote rendering judge |
| `prism_ask_guard_enabled` | `True` | — | bool | Cheap moderation pre-check before Ask |
| `prism_ingestion_enabled` | `True` | `true` | bool | Master switch for live ingestion |
| `prism_cve_feeds_enabled` | `False` | — | bool | NVD/CISA KEV ingestion |
| `prism_podcasts_enabled` | `False` | `true` | bool | Podcast clip pipeline |
| `prism_veto_enabled` | `True` | **`false`** | bool | Grounded storyline-veto overlay |
| `prism_langfuse_enabled` | `False` | — | bool | Explicit switch required in addition to credentials (self-hosted stack costs money when woken) |
| `prism_email_provider` | `console` | — | **console\|resend** | Email backend |

Derived: `langfuse_enabled` property is true only if the flag AND both Langfuse keys are set.

### Thresholds

| Setting | Default | Purpose |
|---|---|---|
| `prism_event_verify_min` | `0.85` | Jev floor to attach in the verified tier (precision 1.00, 20/20 in a week of production pairs, 2026-09-25) |
| `prism_headline_tier_threshold` | `0.0` (off) | Cross-language headline correlation floor |
| `prism_clip_min_cos` / `prism_x_min_cos` | `0.84` / `0.84` | Candidate-stage cosine floors for podcast clips / X posts |
| `prism_decisions_min_confidence` | `0.0` | Confidence floor below which Jev falls back to the LLM pair |
| `prism_ingest_max_articles` | `0` (no ceiling) | Hard cap on enriched-article corpus size |
| `prism_llm_budget_floor_usd` | `5.0` | Stop collecting when OpenRouter balance falls under this |
| `prism_trusted_proxy_hops` | `1` | Trusted proxy count for `X-Forwarded-For` (Railway = 1) |
| `prism_magic_token_ttl_min` / `prism_session_ttl_days` | `15` / `30` | Magic-link / session lifetimes |
| `prism_magic_request_cooldown_s` | `30` | Per-email magic-link rate limit |
| `prism_free_markets_samples` | `3` | Free Markets-lens samples on signup (founder decision D13) |
| `langfuse_timeout` / `langfuse_flush_at` | `30` / `128` | Self-hosted Langfuse export tuning (SDK defaults too aggressive for a scale-to-zero instance) |

### Infra

| Setting | Default | Purpose |
|---|---|---|
| `database_url` | `postgresql+asyncpg://prism:prism@localhost:5432/prism` | Postgres connection (asyncpg driver) |
| `redis_url` | `redis://localhost:6379/0` | Redis connection |
| `cors_origins` | `http://localhost:3000` | CORS allow-list, comma-separated |
| `prism_admin_token` | `change-me` (must override in prod) | Static admin token |
| `prism_admin_emails` | `""` | Admin-user allowlist |
| `prism_web_url` | `http://localhost:3000` | Magic-link verification target |
| `resend_api_key` / `prism_email_from` | — | Email provider credential / from-address |
| `prism_session_cookie` / `prism_cookie_domain` / `prism_cookie_secure` | `prism_session` / `""` / `True` | Session cookie name/scope/security |
| `google_client_id` | `""` | Google sign-in client id (empty = sign-in off) |
| `razorpay_key_id` / `razorpay_key_secret` / `razorpay_webhook_secret` | `""` | Billing credentials (empty = checkout/webhook 503) |
| `nvd_api_key` | `""` | NVD feed key |
| `x_bearer_token` | `""` | X API bearer token |
| `langfuse_public_key` / `langfuse_secret_key` / `langfuse_base_url` | `""` | Self-hosted Langfuse credentials |
| `prism_paid_launch_date` | `""` | Start of the 90-day paid-offer clock; empty = offer prices shown |

## 6. Delivery

- **Branches**: `dev` is the default branch and the only one anyone commits to; `main` is
  production. `make promote` (`Makefile:63-84`) fast-forwards `dev` into `main`: refuses on
  uncommitted changes, refuses unless `origin/main` is an ancestor of `origin/dev` (no direct
  commits to `main`), refuses unless the latest `dev` CI run is `success` for the exact `origin/dev`
  SHA, then runs `git push origin origin/dev:main` — a pure ref move, never a merge commit. A GitHub
  ruleset on `main` is described as enforcing the same thing server-side (no deletion/force-push,
  linear history, required green checks) — **this is dashboard configuration, not a file in the
  repo, so it was not independently verified for this doc** (see Open Questions).
- **CI** (`.github/workflows/ci.yml`): triggers on push to `main`/`dev` and PRs into `dev` (never
  into `main`). `backend` job (skipped on `main`): real Postgres(pgvector)+Redis services, `ruff
  check`, a design-token drift check, an import-sanity smoke test across every stage module,
  `alembic upgrade head` → `downgrade -1` → `upgrade head` round-trip, then `PRISM_REQUIRE_DB=1
  pytest -q` (so a DB test that cannot reach a DB fails rather than silently skipping). `web` job
  (skipped on `main`): vitest, eslint, `tsc --noEmit`, `next build`, plus two custom checks
  (`check:guides` — labelling guides must not leak into the public bundle; `check:charts` — the
  charts library must load only on `/admin`). `vouched` job (push-to-`main` only): re-reads GitHub's
  check-runs API for the exact `main` SHA to confirm `backend`/`web` were green on `dev` — it does
  **not** re-run tests on `main`. `deploy-web` job (needs `vouched`): re-authors the commit's email
  for Vercel's Hobby-plan owner check, pulls production env, patches in the `NEXT_PUBLIC_*` values
  Vercel would otherwise pull as empty ("Sensitive" vars), builds and deploys via the Vercel CLI.
  `.github/workflows/preview.yml` is manual-only (`workflow_dispatch`), a deliberate cost control
  after a prior five-day Actions-credit exhaustion incident.
- **Migrations on deploy**: baked into the `api` service's boot command
  (`alembic upgrade head && exec uvicorn ...`, `Dockerfile:46`) — there is no separate migration
  step or job; every API boot upgrades the schema first. `railway.json`'s healthcheck is what
  surfaces a stuck migration (the API never comes up, `/healthz` never turns green).

## 7. Observability

- **Langfuse** (`common/observability.py`): `get_langfuse()` returns `None` whenever
  `langfuse_enabled` is false, and `observe()` — the tracing decorator — is a complete no-op wrapper
  in that case, checked **before** the Langfuse SDK is touched at all. This matters because the
  self-hosted instance scales to zero after idle time; touching the SDK would wake (and start
  billing for) the whole stack. `fetch_prompt()` pulls a Langfuse-managed prompt (label
  `production`) with a local-file fallback under `common/prompts/fallbacks/`.
- **structlog** (`common/logging.py`): JSON output in prod, pretty console locally
  (auto-detected via TTY + `RAILWAY_ENVIRONMENT`, overridable with `LOG_FORMAT`).
  **The `event=` kwarg trap**: structlog's `BoundLogger` methods take `event` as their own
  positional argument, so a call like `logger.warning("msg", event=some_id)` collides and raises
  `TypeError` at the log call itself. One **live, unfixed** occurrence: `tools/backfill_subjects.py`
  (a `logger.warning(..., event=r["id"], ...)` call inside an `except` handler — so the failure path
  itself crashes instead of logging). One **already-fixed** occurrence with an explanatory comment
  left in place: `common/pair_judge.py` renamed the kwarg to `event_id=`, with a comment noting the
  original crashed the same handler.
- **Health endpoints**: exactly one, `GET /healthz` (`api/routes/meta.py`). It runs `SELECT 1` for
  liveness, then reports `streams` (per-topic Redis Streams backlog via `common/stream.py`),
  `freshness` (24h p50/p95 pipeline-stage latencies via `common/freshness.py`), and `embeddings`
  (corpus embedding-model consistency check). By design it never fails the check on stream backlog
  or freshness alone — a red health check would pull the API out of Railway's rotation for a
  condition the API itself cannot fix. The worker has no real HTTP surface, so it runs a
  minimal fake-200 health server purely to satisfy Railway's healthcheck.
- **Admin dashboard** (`/admin`, backed by `api/routes/admin.py`, `admin_metrics.py`,
  `admin_controls.py`, `admin_labellers.py`): LLM-balance status, the admin-user audit log, visitor
  and revenue metrics with a CSV export, an outlet co-coverage network view, the labelling ops
  console, and a read-only feature-flag view (deliberately never settable from this route, so no
  secret-shaped value can reach the page).

## Open questions

Confirmed while writing (2026-09-25): the pipeline is **one** Railway worker service
(`PRISM_SERVICE_ROLE=worker`, no `PRISM_STAGES` split), and the GitHub ruleset on `main`
is active ("main is production: fast-forward of a CI-green dev commit only").

- **CSP is report-only everywhere** (`web/next.config.ts`); no enforced
  `Content-Security-Policy` header exists in `api/` or `web/`. Enforcing it waits on nonce
  wiring — a founder decision.
- **`common/models.py`'s `Session` docstring** ("Bearer (not cookie) so there is no CSRF
  surface") is stale: `api/deps.py` also accepts the HttpOnly cookie, with an `Origin`
  allowlist as its CSRF mitigation.
