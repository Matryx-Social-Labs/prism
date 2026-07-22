# Changelog

All notable changes to Prism are documented here.
Format: [MAJOR.MINOR.PATCH.MICRO] — dated YYYY-MM-DD.

## [0.0.44.0] - 2026-07-22

### Changed
- Extraction moved to a ~4.7× cheaper model. Extraction is ~66% of LLM spend
  (Langfuse: $4.87 of $6.50 in a day) — all on `qwen/qwen3.7-plus` ($0.32/$1.28 per
  M). Benchmarked cheaper models on 25 real India articles for entity reliability
  (entities drive clustering): gemini-3.1-flash-lite left **40% of articles with no
  entities** (recall 0.39), gemini-3.5-flash 96% empty, deepseek-v4-flash 25% empty +
  truncation — all unusable. **`qwen/qwen3.5-flash-02-23`** ($0.07/$0.26 per M) was
  the cheapest that stayed reliable: **0 empty, ~0.77 recall** vs qwen3.7-plus.
  Switched `prism_model_extract` and `prism_model_extract_light` to it (soft-news was
  on gemini-flash-lite, silently emitting no entities → those sectors couldn't cluster
  by entity). Projected: extraction ~$4.87/day → ~$1.0/day; total ~$6.5 → ~$2.6/day.
  Trade-off: ~23% fewer *peripheral* entities than qwen-plus; principal actors (the
  clustering signal) are retained. Analysis/brief/agent stay on qwen3.7-plus (quality,
  low volume). No code path change — config only.

## [0.0.43.0] - 2026-07-21

### Fixed
- OpenRouter `402 Insufficient credits` now pauses LLM calls instead of storming.
  `_QUOTA_STATUS` only covered 401/403/429, so a spent OpenRouter balance raised a
  full traceback on *every* queued item (gate/classify/enrich) — hundreds per
  minute — with no cooldown. Added **402** to the quota set: it now trips the
  global cooldown and raises `LlmQuotaError` (a `ConnectionError`), so the stream
  leaves the item pending and the pipeline **self-heals on top-up** (no redeploy,
  no data loss). Test: `tests/test_llm_quota.py`. Operational note: watch the
  OpenRouter credit balance — a 402 silently stalls the whole pipeline.

## [0.0.42.0] - 2026-07-21

### Fixed
- Entity-overlap over-merge ("KSU railway blockade" event whose brief was about an
  IIT Roorkee advisory). The `entity_overlap` match tier merged ~5 unrelated
  political stories into one blob: it required only "≥2 shared entities + embedding
  ≤0.55", counting *any* entity — so ubiquitous national figures (Rahul Gandhi,
  Congress, Modi), which appear in every day's political story, trivially satisfied
  the threshold, and once an event accumulated them it snowballed the whole topic.
  Fix (`correlation/clustering.py`): the tier now counts only **distinctive**
  actors — `person`/`organization` entities with document-frequency ≤ 2 within the
  match window (so recently-ubiquitous figures and weak types like place/government
  don't count) — and tightens the loose band 0.55 → 0.45. Validated on the live
  over-merge: KSU, the Kerala Congress march, the IIT gag-order, and the Uttarakhand
  HC story each separate into their own event, while the genuine Parliament-dharna
  articles (sharing specific actors) still cluster. Cross-language merging is
  unaffected (a retelling shares ≥2 low-df story actors at ≤0.42).

### Deploy
- Redeploy the **worker** (clustering is code). No env/migration. The fresh data
  already formed with the old tier keeps its over-merges until re-ingested — a
  wipe + re-ingest after deploy gives fully clean clustering.

## [0.0.41.0] - 2026-07-21

### Fixed
- Classifier over-tagging `cybersecurity` — a Bengaluru triple-murder story (the
  accused used an AI chatbot to plan it) was filed under `sector=cybersecurity`,
  which then offered the cyber lens on a crime story. Root cause: the classifier
  is a stochastic LLM (`gemini-3.1-flash-lite`) and the prompt didn't scope what
  `cybersecurity` means, so "AI chatbot + conceal evidence" drifted into it (3/5
  runs on the exact story). The taxonomy has no `crime` bucket, so such stories
  had nowhere honest to land. Tightened the classifier prompt: classify by the
  story's SUBSTANCE not incidental tools, `cybersecurity` is only attacks on/
  defense of systems (breaches, ransomware, CVEs, malware, security policy), and
  a crime that merely used a phone/app/chatbot is a crime (→ `other`). Verified:
  the story now classifies `other` 5/5. Prompt-only (Langfuse-managed) — no code,
  no worker redeploy; republish with `uv run python evals/sync_prompts.py`.
  Existing mislabeled events keep their sector until re-ingested.

## [0.0.40.0] - 2026-07-21

### Changed
- Extract-schema trim — the highest-volume LLM stage (`extract-shared`, one call
  per relevant article) no longer emits `claims` or `impacts`. Neither had a
  news-side reader: nothing reads `claims`, and correlation re-derives impacts in
  `event-analysis` from summaries+stance. `structured_chat` gained a `prune_fields`
  arg that drops those properties from the JSON schema shown to the model (top
  level + `$defs`), so it stops generating the `claims[]` + `impacts[{5 fields}]`
  arrays — fewer output tokens, less mid-JSON truncation (which was the failure
  mode corrupting `entities`, the clustering signal). The pydantic model keeps the
  fields (default `[]`); the deterministic `cve_lens` path still populates impacts
  for CVE records, so the cyber lens is unchanged.

### Deploy
- Redeploy the worker (the schema prune is code). Republish the prompt so prod's
  Langfuse-managed `extract-shared` matches the trimmed prose:
  `uv run python evals/sync_prompts.py`. No env or migration changes.

## [0.0.39.0] - 2026-07-21

### Changed
- Langfuse trace-export resilience — the SDK's 5s OTLP timeout is too short for a
  self-hosted instance; bumped `LANGFUSE_TIMEOUT` to 30s and `LANGFUSE_FLUSH_AT`
  to 128 (smaller batches) via the config bridge, so genuine slow-exports no
  longer drop traces. NOTE: the current "Failed to export span batch" on api +
  worker is actually a **500 Internal Server Error** from the self-hosted Langfuse
  OTLP ingestion endpoint (web health is 200, but the trace-ingestion path errors)
  — a backend issue in the `langfuse` Railway project (likely S3/MinIO blob
  storage or ClickHouse), NOT the SDK. This config helps timeouts but the 500
  needs the langfuse deployment fixed (see the langfuse-web/worker logs).

## [0.0.38.0] - 2026-07-21

### Changed
- Enrichment throughput — the stage's cost is the reliable-but-slow qwen extract
  (~42s, but I/O-bound so it parallelizes: 6 concurrent ≈ 1× latency). Raised the
  enrichment consumer to `concurrency=12` (batch 12) and sized the DB pool for it
  (`pool_size=20, max_overflow=20`). Roughly doubled local throughput (~4 → ~8
  items/min); prod gains more since the Langfuse span export is same-network there
  (locally the export retries were halving throughput).

### Known follow-ups
- Deeper enrichment throughput: embed (mpnet, CPU) contends at high concurrency;
  and `extract-shared` re-derives impacts that correlation also computes — trimming
  the extract schema would cut qwen's output size and latency.

## [0.0.37.0] - 2026-07-21

### Added
- Story trail — a **"The story so far"** timeline on the individual news page: a
  monochrome, chronological rail of the story's developments (branches) with a
  "Following" cast strip of the recurring actors, the current article marked
  in place ("You are here"). DESIGN.md-faithful: hairline rule, IBM Plex Mono
  dates (provenance), General Sans titles/cast, no lens hue (chrome), reveal-on-
  scroll stagger collapsing to instant under reduced-motion. Replaces the plain
  developments list; built from the existing `related` branches + entity cast —
  populates cross-language (an English politics event links to the Hindi CJP
  march via 4 shared actors).

## [0.0.36.0] - 2026-07-21

### Fixed
- Consistent central-actor extraction — `extract-shared` now instructs the model
  to always include the PRINCIPAL actors of a story (its main people, parties,
  organizations) even when an article covers a narrower sub-angle, and runs on
  **qwen** (gemini-3.5-flash reliably returned an EMPTY entities array under
  json_schema on the same text; qwen returned all six). Verified: the CJP march
  (Hindi), hunger strike (Hindi), and AIIMS (English) developments now all extract
  the same three actors — Cockroach Janta Party, Dharmendra Pradhan, Sonam
  Wangchuk — so branches share 3 and group into one story. `related_developments`
  raised to >=2 shared actors now that extraction is consistent.

## [0.0.35.0] - 2026-07-21

### Added
- Story branches — the event view now shows **"This story's developments"**:
  other events sharing a specific actor (person/organization, e.g. Sonam Wangchuk,
  Cockroach Janta Party) within a 30-day window. Entity-based (not LLM), so it
  surfaces the branches of a fast-moving story even when each is single-source and
  never thread-linked — and **cross-language** (the English AIIMS development links
  to the Hindi hunger-strike development via the shared actor). New `related`
  field on the event detail; `correlation.threads.related_developments`.

### Known follow-ups
- Down-weight ubiquitous actors by frequency to cut noise as volume grows.
- Story-level cumulative brief/perspectives across all branches (the events share
  1 actor today because extraction is fragmented — consistent central-actor
  extraction would let branches merge and earn a single story brief).

## [0.0.34.0] - 2026-07-21

### Changed
- Perspectives are now **actor-based, not origin-based** — the analysis groups
  coverage by WHO is framing the event (a party, an official/ministry,
  protesters, "Neutral reporting"), consolidated across all articles and
  languages, capped at 4 for readability. On a synthetic multi-source CJP input it
  produced "Cockroach Janta Party / Protesters", "Education Minister Pradhan /
  Government", and "Neutral reporting" — the competing narratives, not countries.
- The general brief is now **cumulative** for evolving stories — when member
  articles span multiple days/developments it writes the current state of the
  whole arc (began as X → then Y → now Z), so a late arrival gets the full story
  in one read. `event-analysis` prompt published to Langfuse.

## [0.0.33.0] - 2026-07-21

### Fixed
- Extraction reliability — `structured_chat` now sets a generous `max_tokens`
  (8192) so a large nested JSON can't truncate mid-string, and the complex
  `extract-shared` step runs on `google/gemini-3.5-flash` (the cheapest model
  malformed its JSON). Verified: extract now succeeds where flash-lite failed,
  and produces **canonical romanized entities from non-English text** — a Hindi
  article yielded `Abhijeet Dipke`, `Cockroach Janta Party`; another `Sonam
  Wangchuk`, `Kapil Sibal` — which is what lets cross-language coverage match.

## [0.0.32.0] - 2026-07-20

### Added
- Cross-language / same-story clustering — a new `entity_overlap` match tier
  merges coverage the near-duplicate embedding threshold misses: it requires >=2
  shared canonical entities plus a looser embedding band (<=0.55 distance) within
  the time window, so Hindi/Tamil/English retellings of one story become a single
  multi-source event (which then earns the deferred perspective/brief analysis).
  Uses the new events HNSW index.

### Changed
- `extract-shared` now emits all output in **English** and entity names in
  **canonical romanized form** (e.g. "Sonam Wangchuk", not the native script), so
  the same actor matches across languages and the feed reads in one language.
  Published to Langfuse.

### Known follow-ups
- End-to-end cross-language merge depends on enrichment reliably producing those
  canonical entities — the `extract-shared` flash-lite JSON reliability fix is the
  co-requisite before the real HI/EN CJP merge is fully validated on live data.

## [0.0.31.0] - 2026-07-20

### Changed
- Correlation throughput — decoupled the real-time attach from the expensive
  per-story analysis. Ingest now clusters/attaches an article to its event,
  merges the projection, and publishes `event.updates` immediately (no LLM), then
  marks the event dirty; a **debounced sweeper** runs perspectives/impacts/briefs
  + thread-linking once per story, coalescing a burst of coverage into a single
  pass (Redis ZSET, 90s leading debounce). **Single-source news skips the LLM
  entirely** — no competing perspective, and its brief renders on demand on first
  view. Measured locally: ~6× faster event formation (73 events/200s vs ~12/600s),
  and the LLM only runs on multi-source stories. New sweeper task in the worker's
  correlation stage.

### Known follow-ups
- Enrichment's `extract-shared` is now the bottleneck (flash-lite JSON failures) —
  needs a sturdier model/prompt.
- Cross-language / same-story clustering (looser band + entity overlap) so
  Hindi/Tamil/English coverage merges into one multi-source story.

## [0.0.30.0] - 2026-07-20

### Changed
- Multilingual embeddings — swapped `bge-small-en` (384) for
  `paraphrase-multilingual-mpnet-base-v2` (768) so cross-language coverage of the
  same story clusters together. Benchmarked + validated on the live CJP story:
  The Hindu (English) and Aaj Tak (Hindi) coverage of the same Parliament-march
  crackdown score 0.575 vs 0.179 for an unrelated story (bge-small couldn't
  separate Hindi at all: 0.56 vs 0.53). Migration `5493a4141cbb` moves the vector
  columns to 768 and **adds the missing HNSW index on `events.embedding`**
  (clustering + thread retrieval were doing a sequential cosine scan).

### Added
- India-language sources — Aaj Tak, Amar Ujala (Hindi), BBC Tamil (Tamil).
  Ingested + classified correctly (Hindi CJP items → politics).

### Known follow-ups
- Cross-language pairs (~0.57 sim) sit below the near-duplicate clustering
  threshold (0.88) — clustering needs a looser cross-language band + entity
  overlap (Wangchuk/Pradhan/CJP) to merge them, not tight embedding alone.
- `extract-shared` occasionally fails JSON on `gemini-3.1-flash-lite` (retries
  exhausted) — needs a sturdier model/prompt for that step.
- mpnet-base is ~1GB (vs ~130MB) — larger model download + RAM at runtime.

## [0.0.29.0] - 2026-07-20

### Added
- India-first, state-level geography. Onboarding now asks for your **state**
  (`/api/v1/regions`, ISO 3166-2, `covered` flag per state); the feed leads with
  your state, then national (`?state=IN-KA`, stable geo-tier over recency/score).
  State-edition sources (The Hindu state feeds + TOI metros) stamp their ISO
  3166-2 code deterministically through classification → `event.regions`, so the
  reader's local news surfaces first. New `common/regions.py`; `StateSelect`
  onboarding/interests component; profile gains `state`.

### Changed
- **Sources are India-only for now** — dropped international general outlets
  (BBC, Al Jazeera, Guardian, DW, France 24, SCMP, Dawn, TASS, CGTN, Anadolu,
  Press TV) and GDELT (international + rate-limited). Kept India national + state
  + the cybersecurity lens. RSS now runs **before** the CVE feeds so the general
  feed is never starved (CVE feeds stay cyber-lens-only, never in the general
  feed — a dedicated CVE section under cyber is a follow-up).
- Bulk pipeline stages (gate/classify/extract) → `google/gemini-3.1-flash-lite`
  (cheap + reliable structured output; the free `tencent/hy3` returned empty
  content).

### Verified (local, full pipeline on real India ingest)
- 827 India items ingested; state feeds tag `[IN, IN-XX]` through classification;
  correlation merges the state code into `event.regions` (Karnataka article →
  `[IN, IN-KA]`); feed `?state=IN-KA` surfaces the in-state event first. 28
  backend tests pass (+2 geo); frontend builds.

### Known follow-ups
- Correlation throughput is the bottleneck (~40s/event with briefs) — tune before
  scaling volume. City-level granularity + a separate CVE-advisories section under
  the cyber lens are next.

## [0.0.28.1] - 2026-07-20

### Fixed
- `.env.example` no longer ships an active `LANGFUSE_TRACING_ENVIRONMENT=development`
  line — it's commented out so a prod scaffold from the template can't inherit
  "development". Prod was never actually affected (Railway uses service variables,
  not this file; the config default is empty), but the template was misleading.
  Only local gitignored `.env` sets `development`.

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
