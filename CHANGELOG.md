# Changelog

All notable changes to Prism are documented here.
Format: [MAJOR.MINOR.PATCH.MICRO] — dated YYYY-MM-DD.

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
