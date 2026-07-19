# Changelog

All notable changes to Prism are documented here.
Format: [MAJOR.MINOR.PATCH.MICRO] — dated YYYY-MM-DD.

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
