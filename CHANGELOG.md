# Changelog

All notable changes to Prism are documented here.
Format: [MAJOR.MINOR.PATCH.MICRO] — dated YYYY-MM-DD.

## [0.0.28.0] - 2026-07-20

### Added
- Langfuse tracing environment — `LANGFUSE_TRACING_ENVIRONMENT` (bridged to the
  SDK in `common/config._export_langfuse_env`) tags traces so local/dev runs are
  filterable and never mixed with prod in the shared Langfuse. Local `.env` sets
  `development`; prod stays unset (`default`), so prod config is untouched.

## [0.0.27.0] - 2026-07-20

### Added
- Sign-up profiling — the sign-in form now collects **name + profession**
  (mandatory) so we can curate professional news lists later. Profession is a
  structured, sector-wise vocabulary (`common/professions.py`, 33 roles in 7
  groups, each mapped to a lens + interest sectors), served at
  `GET /api/v1/professions` and rendered as a grouped dropdown. Profile rides on
  the magic-link token and is stamped on the new user (migration `9ddbcc3fd269`
  adds `name`/`profession` to `users` + `auth_tokens`).
- Branded magic-link email (`common/email_templates.py`) — table-layout,
  inline-styled HTML following DESIGN.md (serif display, mono provenance, the
  spectrum bar, ink button), sent as HTML + plaintext via Resend.

### Changed
- Removed the "email delivery isn't wired" dev note from the sign-in page.
- Magic-link URL now honours `PRISM_WEB_URL` (set to the Vercel domain in prod).

## [0.0.26.0] - 2026-07-20

### Added
- OpenRouter as primary LLM provider (`LLM_PROVIDER=openrouter`) — one key, no
  weekly cap, per-token. Client picks base_url/key/headers by provider; Ollama
  stays as fallback. Per-stage model map moved to OpenRouter ids (free for
  high-volume/low-stakes stages, cheap-paid for content), all env-overridable.
- Ask-agent guardrail (`common/moderation.py`) — a cheap moderation pre-check
  rejects explicit/harmful/prompt-injection/spam questions before the RAG agent
  runs (no disallowed content, no paid junk prompts). Fails open with the agent's
  source-grounding as backstop. `PRISM_ASK_GUARD_ENABLED`, `PRISM_MODEL_GUARD`.
- Resend email sender (`PRISM_EMAIL_PROVIDER=resend`, `RESEND_API_KEY`,
  `PRISM_EMAIL_FROM`) — wires magic-link delivery to a real provider.
- Live-ingestion master switch (`PRISM_INGESTION_ENABLED=false`) — stops
  collectors + stalled-item requeue so no new news enters and the LLM pipeline
  idles: the cost brake while the prototype is being finished. On-demand
  briefs/Ask/digest still work.

### Notes
- New env documented in `.env.example`. Requires `OPENROUTER_API_KEY` (and
  `RESEND_API_KEY`) set on Railway before the backend deploys.

## [0.0.25.0] - 2026-07-20

### Changed
- Lens-brief grounding tuned — the brief prompt now explicitly forbids supplying
  names/places/dates/identifiers from the model's own world knowledge (the eval's
  top failure: naming the Genoa bridge or the Mexican state the record omitted),
  and pushes thin/single-source events to the shorter end of the range. Paired
  A/B on prod (same events, old cached vs freshly tuned): mean groundedness
  0.77 → 0.83, fixing the worst thin-record case (0.30 → 1.00). Published to
  Langfuse (lens-brief); `judge-brief-groundedness` + `market-digest` added to
  the sync manifest and published. Applies to newly generated briefs.

## [0.0.24.0] - 2026-07-20

### Added
- Market Pulse (`/pulse`) — an LLM-*synthesized* read across the day's top
  market stories (the value the feed's list can't give): a headline, a 2–3
  paragraph narrative connecting the through-lines, and grounded movers. Backend
  `GET /api/v1/digest/markets` generates from the top 12 finance/business events,
  caches in Redis for 3h with cross-replica single-flight (one LLM call per
  window, no table/migration). Grounding baked into the prompt (never invent
  numbers), and movers are **post-filtered to tickers that actually appear in the
  source events** — the LLM can't surface an inferred ticker. New `market-digest`
  prompt; response schema alias-tolerant. Header **Pulse** link; movers link to
  search. Generation verified against real prod data.

## [0.0.23.0] - 2026-07-20

### Added
- Brief groundedness eval (`evals/brief_groundedness.py`) — samples real lens
  briefs and LLM-judges each against the SAME structured record it was generated
  from (title, summary, perspectives, impacts, lens fields), flagging invented
  specifics. Guards the brief-depth work (longer briefs = more room to
  hallucinate). New `judge-brief-groundedness` judge prompt; verdict schema is
  alias-tolerant (Ollama doesn't enforce json field names — accepts
  grounded/score/grounded_score/groundedness_score). Baseline on prod (n=8):
  mean 0.66; briefs over-reach on thin/single-source records — a grounding gap
  to tune. Run: `python evals/brief_groundedness.py [N]`.

## [0.0.22.0] - 2026-07-20

### Changed
- Relevance-gate calibration verdict recorded (n=500 balanced DB-labeled
  `raw_items`): the embedding score can't safely replace the LLM gate. Max-cosine
  AUC 0.67; contrastive positive−negative anchors AUC 0.72, but at ≤3% relevant-
  news loss it gates only ~5% of junk, and ~13% junk-gated costs ~5% of real
  coverage — fails the "don't degrade content" bar. `enforce` stays unwired; keep
  the LLM gate. Documented in `common/config.py` + `classification/shadow_gate.py`
  so the roadmap item is closed rather than left as a stale "calibrate then flip".

## [0.0.21.0] - 2026-07-20

### Added
- Search — `GET /api/v1/search?q=` (keyword match across event title + summary,
  recency-ordered, no CVE-only filter since a query is explicit intent) and a
  `/search` page (debounced, URL-synced, StoryRowCard results) with a header
  search icon. No LLM.

### Changed
- Extracted the row→`FeedItem` serialization shared by feed and search into
  `api/routes/serialization.py` (`build_feed_item`); feed keeps its own curation
  filters (CVE-only, subsector). Pure refactor — all 21 backend tests pass.

## [0.0.20.0] - 2026-07-20

### Added
- `sitemap.xml` + `robots.txt` (native Next metadata routes) — the sitemap lists
  public pages and every story URL (from the feed, `lastModified` per event) so
  crawlers can discover the stories the v0.0.19.0 metadata describes; robots
  allows public content and disallows the user-specific pages (account, signin,
  auth, onboarding, interests, watchlist). Sitemap still serves the static pages
  if the API is down. Completes the crawlability half of SEO.

## [0.0.19.0] - 2026-07-20

### Added
- Shareable / SEO story pages — every story now emits per-story `generateMetadata`
  (title, canonical, OpenGraph `article`, Twitter `summary_large_image` with the
  event image, published/modified times, section) plus `NewsArticle` JSON-LD.
  Shares render a real card instead of a blank link; search engines can index
  and rich-result the pages. Site-wide OG/Twitter defaults + `metadataBase` on
  the root layout; `SITE_URL` resolves from `NEXT_PUBLIC_SITE_URL` → `VERCEL_URL`
  → localhost. Distribution win, no LLM.

## [0.0.18.0] - 2026-07-20

### Added
- Follow-from-story — one-tap follow toggles for a story's tickers and sector,
  inside the Markets lens block. Closes the watchlist loop: discover a signal
  while reading, follow it in place (no retyping on /watchlist). Lives in the
  auth-gated pro lens so every viewer can follow; reuses the watchlist API and
  normalizes to its stored form (ticker upper, sector lower) so toggle state
  reconciles with the list. Followed chips carry the finance hue.

## [0.0.17.0] - 2026-07-20

### Added
- Brief player — a "Listen" control on every lens brief that reads it aloud with
  sentence-level read-along highlight (the spoken sentence tints in the lens
  hue). Uses the browser's built-in Web Speech API (`speechSynthesis`) — no
  server TTS, no model call, no new dependency. Briefs are spoken one sentence
  at a time so the highlight tracks and long briefs dodge Chrome's ~15s
  single-utterance cutoff. Pause/resume/stop; hidden where the API is
  unsupported; narration cancels on lens switch and unmount. Reader-facing
  accessibility win that also makes the brief-depth work audible.

## [0.0.16.0] - 2026-07-20

### Added
- Watchlist ("Followed Signals") — read-only follows of tickers and sectors.
  New `watchlist` table (migration `149182e8b853`) + auth-gated routes: list,
  follow (idempotent, normalized — tickers upper, sectors lower), unfollow, and
  a matching-events feed (events whose sector or `finance.tickers` match a
  follow, via `jsonb_exists_any`). New `/watchlist` page (add/remove follows,
  see recent stories on your signals) + a header link when signed in. Push and
  alerts remain Phase 2 (they need delivery infra). Verified end-to-end over
  HTTP (auth + CRUD + matching + 401) in `tests/test_watchlist.py`.

## [0.0.15.0] - 2026-07-20

### Added
- Sign-in-gated professional lenses (no paywall — free once signed in): on a
  story, the general reader lens is open to everyone; the Markets and Cyber
  lenses show a lock and, on click, send signed-out readers to sign-in. The lens
  brief panel shows a "sign in to unlock" nudge instead of the pro read, the
  brief isn't fetched/generated for a locked lens, and a signed-out reader is
  never left parked on a locked lens (snaps back to general). Signed-in readers
  switch freely.

## [0.0.14.0] - 2026-07-20

### Changed
- Brief depth: the `lens-brief` and `event-analysis` prompts now produce
  substantive, structured briefs instead of a 3-5 sentence summary — general
  5-7 sentences (what happened → why it matters → what's contested → what to
  watch), professional (cyber/markets) 6-9 sentences with second-order effects,
  because depth is decision-relevant there. Grounding rules explicitly OVERRIDE
  length: if the event data is thin, state what is not yet known rather than
  invent detail to fill the brief (the trust failure mode of AI news). Output
  JSON shape is unchanged (text + points per lens), so no code change; one
  cached call per event, so cost/latency is ~flat. Runtime prompts live in
  Langfuse — `evals/sync_prompts.py` publishes these fallbacks to make it live.

## [0.0.13.0] - 2026-07-19

### Added
- Sign-in UI (magic link): `/signin` requests a one-time link, `/auth/verify`
  exchanges it for a bearer session, `/account` shows the account + sign out, and
  the header shows a sign-in link / account chip. Session is stored client-side
  (`lib/session.ts`); email is server-side + pluggable, so in dev the link prints
  to the API logs and the whole flow works with no provider. New sign-ins get the
  free Markets samples granted automatically.

### Fixed
- **`get_db` never committed**, so every write endpoint (auth — and later the
  paywall gate + watchlist) silently rolled back: the magic-link row was never
  persisted and verify always 401'd, even though the logic-level tests passed
  (they use `session_scope`, which commits). `get_db` now commits on success /
  rolls back on error, with a regression test that drives the dependency directly.

## [0.0.12.0] - 2026-07-19

### Changed
- Catalyst-type badge (design-review E1/D5): the markets catalyst (EARNINGS,
  REGULATORY, RBI, …) now renders as a proper IBM Plex Mono "evidence" chip on
  story cards and in the story view — the SEBI-safe reframe (what kind of event
  is moving this, sourced) rather than a buy/sell direction. Shown on any markets
  story (was hidden unless the finance lens was active), monochrome by default and
  the markets hue only when the finance lens is speaking (color-means-lens).

## [0.0.11.0] - 2026-07-19

### Changed
- CI backend job now runs against real Postgres (pgvector) + Redis services:
  `alembic upgrade head` (plus a down/up round-trip) runs on every PR, and the
  DB-dependent tests (atomic quota concurrency, magic-link auth flow, Redis
  single-flight) actually execute instead of skipping. A migration that fails
  `alembic upgrade head` now fails CI instead of reaching Railway.

## [0.0.10.0] - 2026-07-19

### Fixed
- **Backend deploys were failing their healthcheck** and Railway was silently
  keeping an old (pre-migration) release live. Root cause: the pgvector HNSW
  index build in migration `51de411d824c` used PARALLEL maintenance workers,
  whose dynamic-shared-memory segment overflows the small `/dev/shm` on Railway's
  managed Postgres (`could not resize shared memory segment … No space left on
  device`) — so `alembic upgrade head` in the start command aborted and the API
  never booted. Fix: build all indexes `CONCURRENTLY` (they sit on
  worker-written tables) inside an `autocommit_block`, `IF NOT EXISTS` for
  idempotency, and `SET max_parallel_maintenance_workers = 0` so the HNSW build
  runs single-threaded (~12s for 25k rows, no DSM allocation). The valid HNSW
  index was also built on prod out-of-band so this deploy's migration no-ops it.

## [0.0.9.0] - 2026-07-19

### Changed
- Hero prism, WebGL: the glass now uses proper `MeshTransmissionMaterial` settings
  (samples + resolution for smooth non-grainy refraction, `ior` 1.6, dispersion held
  at an elegant ~0.45 instead of a maxed-out fringe, subtle distortion), antialiasing
  on, retina `dpr`, and a single soft facet line instead of the hard double CAD
  wireframe — a premium glass prism rather than an outlined cone.
- Hero prism, static fallback (no-WebGL / reduced-motion / SSR): the flat hollow
  triangle is now a glassy filled prism with a soft glow and gradient-faded spectrum
  rays, so it reads as intentional even without the 3D scene.
- Renamed "Both Sides" → "Perspectives" across the app (story section title, landing
  copy, taglines, meta) and reframed "a political story has two framings" to "every
  story is told differently depending on who's telling it" — accurate to the N-origin
  reality and consistent with the "One story. Every perspective." tagline.

## [0.0.8.0] - 2026-07-19

### Changed
- On-demand lens-brief generation now single-flights across API replicas via a
  Redis lock (`common/locks.py`), replacing the in-process `asyncio.Lock` that
  only held within one process. A burst of viewers of the same (event, lens) now
  costs one LLM call fleet-wide, not one per replica — and, once the paywall
  lands, one sample decrement instead of a double-spend. Falls back to generating
  if the lock holder stalls, so a request never hangs. Exclusivity proven against
  live Redis in `tests/test_locks.py`.

## [0.0.7.0] - 2026-07-19

### Added
- Magic-link authentication (migration `de000473f0e5`): `POST /api/v1/auth/request`
  emails a single-use link, `POST /api/v1/auth/verify` exchanges it for a bearer
  session, `GET /api/v1/auth/me` returns the account. New `users` sign-ins get the
  free Markets samples granted automatically. Security (eng-review N3): tokens
  stored only as SHA-256 hashes, single-use + time-limited magic links, bearer
  sessions (no cookie → no CSRF), per-email rate limiting, and a DPDP consent gate.
- Pluggable email sender (`common/email.py`) — defaults to a console sender so
  auth works end-to-end in dev; swap `prism_email_provider` for a real backend later.
- `api/deps.py::get_current_user` — the bearer dependency the read-time gate,
  watchlist, and personalized brief will hang off.
- Full auth flow + security edges (single-use, expiry, rate-limit, bad token)
  verified against Postgres in `tests/test_auth.py`.

## [0.0.6.0] - 2026-07-19

### Added
- Freemium data model, step one: `users` and `usage_quota` tables (migration
  `02f6edae6a63`) plus `common/quota.py`. The Markets-lens sample cap is one
  counter per account, decremented with a single atomic
  `UPDATE ... WHERE remaining > 0 RETURNING` so concurrent viewers can never
  double-spend the last sample — the cost wall the paywall depends on. Proven by
  `tests/test_quota.py`: 25 concurrent consumers of a 5-sample account consume
  exactly 5 (the test skips cleanly when no database is reachable).

## [0.0.5.0] - 2026-07-19

### Added
- Database indexes on the read hot paths (migration `51de411d824c`): a composite
  `events(sector, last_updated_at DESC)` for the feed window, `event_id` indexes
  on `perspectives` and `impacts` for event-detail joins, and an **HNSW** ANN
  index on `article_chunks.embedding` so agent retrieval stops full-scanning the
  vector column. Applies and reverts cleanly (verified up + down against pg16).
  Prevents latency getting worse once paid "unlimited Ask" ships.

## [0.0.4.0] - 2026-07-19

### Added
- Relevance-gate shadow scorer: an embedding-based relevance score (fastembed,
  in-process, no new dependency) now runs alongside the LLM relevance gate and
  logs a `shadow_gate` line with the score and the LLM's pass/fail for every
  gated news item. Behavior-neutral — it does not filter anything yet. This is
  step one of the LLM cost fix: calibrate the score band from the logs, then set
  `prism_gate_mode=enforce` so only borderline items reach the LLM. Gated by
  `prism_gate_mode` (shadow | enforce | off; default shadow).

## [0.0.3.0] - 2026-07-19

### Changed
- Serving layer refactor: `api/main.py` (573 lines) split into `api/routes/`
  (meta, feed, events, admin) plus `api/schemas.py`. Behavior-identical — the
  served endpoint set is unchanged (locked by `tests/test_api_routes.py`). This
  is the refactor-first step before the freemium build adds auth, billing, and
  watchlist routers, so they land in their own modules instead of one 1000+ line file.

## [0.0.1.0] - 2026-07-19

### Added
- The re-typeset lens flip: switching lenses on a story now sweeps a
  lens-colored scan line across the analysis while it re-inks — the same
  story, visibly re-read. Plays only when you flip (never on page load) and
  collapses to an instant swap under reduced motion.
- A dedicated provenance typeface (IBM Plex Mono) for the evidence layer:
  timestamps, source counts, citation numbers, funding labels, and news-chain
  dates now read as data, distinct from prose.

### Changed
- UI typeface is now General Sans (self-hosted, with a true bold weight),
  replacing Space Grotesk.
- Chrome is monochrome: interface color now only ever signals which lens is
  speaking — region and coverage badges, thread links, label chips, and text
  selection re-inked to the neutral scale. Ticker chips stay in the markets
  hue by design (they are the markets lens speaking).
- Story and feed metadata is easier to read (higher-contrast provenance text).

### Fixed
- Mono-labeled chips no longer render synthesized faux-bold.
