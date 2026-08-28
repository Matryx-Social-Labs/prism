# Rebuild issues log

Running list of defects found during the v2 rebuild. Every entry is **measured**,
not suspected. Status: `OPEN` · `FIXED` · `DEFERRED` · `WONTFIX`.

Ordered by severity within each group. Update as things land.

---

## A. Correctness — reader-visible

| # | Issue | Evidence | Status |
|---|---|---|---|
| A1 | **Story layer is wrong about half the time.** | P 0.4344 / R 0.5146 / F1 0.4711 vs 45-story gold set. ~200 configs swept; plateau. | OPEN — step 6 |
| A8 | **`detect_script` had no Arabic range, so Urdu returned `"latin"` — and it FAILS OPEN.** | Not harmless: it put Urdu inside `EMBEDDING_TRUSTED_SCRIPTS` with nothing validating the embedding there, AND made the partition's cross-script guard read an Urdu/English pair as the *same* script — so `content_similarity` compared them, found zero shared words (different alphabets share none) and **cut the edge**. The absence-of-evidence guard defeated by the detector rather than by its own logic. Found by adding Urdu. | **FIXED** — Arabic ranges added, plus a test tying the detector to every language the feeds ingest |
| A2 | **Language is a lie at the source.** `ingestion/rss.py:115` hardcoded `language="en"` on every envelope. | All **1,385** non-Latin production articles labelled English while `sources.language` held the truth. | **FIXED** — source is now the authority at the persist choke point; migration backfills |
| A3 | **Indic embedding quality — resolved by bake-off across 5 models × 12 languages, on three axes.** | **Cross-lingual, FLORES prose (P@1)**: mpnet kn 0.875 / as 0.715 → mE5-base **1.000 / 0.985**. **Cross-lingual, REAL NEWS (P@1)**: mpnet deva 0.483 / kn 0.444 → mE5-base **0.531 / 0.778**; LaBSE 0.497 / 0.722 despite perfect FLORES — its bitext specialism does not transfer. **Monolingual news AUC**: kn 0.7006 → 0.7475; deva 0.8518 → 0.8311. Vyakyarth (Indic-specific) loses on every axis. | **DECIDED — `intfloat/multilingual-e5-base`.** 768-dim, official ONNX, fastembed-servable with no torch in the container. See **B0** before implementing. |
| A4 | **Tickers are hallucinations.** `FinanceLens.tickers` are LLM-guessed strings validated against nothing, joined into `watchlist`. | No market data exists at all. A hallucinated symbol becomes a followable entity. | OPEN — step 9 |
| A5 | **Perspectives cannot do what the tagline promises.** Per-event not per-story; speaker is free text not an entity; no quotes; no time; forces one article into exactly one narrative. | `event-analysis` prompt, Task 1. An article quoting two actors is filed under one. | OPEN — steps 5b–5d |
| A6 | **Offices resolve to the wrong person over time.** "The Education Minister" is Pradhan before his resignation and someone else after — mid-arc in the CJP story. | Would silently attribute one person's statements to another. | OPEN — step 5b |
| A7 | **Entity canonicalization is a hand-maintained list.** 21 pairs, English-romanisation-specific. | 39 slugs hold multiple entity rows; IDF distorted up to **372×**. Both `Cockroach Janata Party` and `Cockroach Janta Party` sit in one story's cast. | OPEN — step 5 |

## A-bis. Product concepts to build (founder direction)

| # | Concept | Where it lands | Status |
|---|---|---|---|
| P1 | **Maximise Indian-language coverage.** | **8 BBC Indian-language feeds added** (hi, ta, te, mr, gu, pa, bn, ur) + existing kn. Verified end-to-end locally: 1,226 articles, every language correctly stamped from the source, every script detected. Still missing: Malayalam, Odia, Assamese — no working RSS found yet (candidates 404 or serve English). | **DONE for 9 languages** |
| P2 | **Coverage contribution — "100% by contributor".** Per canonical event, the share of unique claims each source FIRST reported. Republishers score ~0; whoever broke it scores high. | Falls out of the claims layer (5b/5c): every claim carries a source, clusters dedupe across outlets. | PLANNED — after 5c |
| P3 | **Missing coverage.** The complement of P2: a claim held by 6 of 7 sources and absent from the 7th is a gap in that outlet's reporting. | Same data. Computed, not asserted. | PLANNED — after 5c |
| P4 | **English-first source ordering** on a multilingual canonical event, other languages below. | UI decision per `DESIGN.md`; data carries `(claim, source, language, first_reported_at)`. | NOTED |

> **P2/P3 precondition:** both are only honest once claim recall is measured.
> "This source contributed nothing" and "this source omitted X" are
> indistinguishable from "our extractor read it badly" — the same
> absence-of-evidence trap as silence-as-signal, which has caught this repo four
> times.

## B. Silent failure — things that look fine and are not

> **B0 — CALIBRATED, swap still gated.** Measured against `gold_pairs`: mpnet's
> optimal primary threshold is **0.305**, mE5-base's is **0.080** — a 3.8x scale
> difference, confirming the two are not interchangeable. Percentile mapping for
> the five dependent constants is in `tools/tune_embed_threshold.py`. The
> infrastructure is now in place (`common/embeddings.py` registers mE5 from its
> official ONNX and applies E5's prefixes automatically), so the swap is a config
> change — but see **A9** before making it.
>
> **B0 — original note.** Swapping to mE5 **requires
> retuning every embedding threshold**. E5 compresses the space: measured on real
> text, an EN↔HI *same-story* pair sits at cosine distance **0.1527** while an
> EN↔EN *unrelated* pair sits at **0.1975**. The live `EMBEDDING_DISTANCE_THRESHOLD`
> is **0.12**, which rejects BOTH — so the embedding match tier would silently stop
> firing entirely while every health check stayed green. `STORY_MAX_EMBED_DIST=0.55`
> and `LOOSE_DISTANCE=0.45` need the same treatment. Retune against `gold_pairs`
> before the swap ships, never after.

| # | Issue | Evidence | Status |
|---|---|---|---|
| B1 | **Skip-as-pass.** 20 modules skip DB tests without Postgres; ~88 assertions vanish and the suite reports green. | An event-loop bug once made real failures surface through the same guard as "no database". | **FIXED** — `PRISM_REQUIRE_DB=1`, both directions verified |
| B2 | **Dockerfile baked a model nothing loads.** `bge-small-en-v1.5` (384-dim) vs a 768-dim default. | Cold-start optimization that silently did nothing; prod re-downloaded every boot. A wrong cache is indistinguishable from a cold one, just slower. | **FIXED** — read from config + test |
| B3 | **Fixture corpus would rot silently.** 30-day window means a captured corpus goes partly invisible in weeks. | 32 of 86 gold events had already aged out on first load. Symptom reads as a code regression. | **FIXED** — time-shifted on load + test |
| B4 | **`.env.example` drifted three ways.** 10 of 39 settings missing; all 12 `os.environ`-only vars absent. | Those appear in no class either, so nothing documented them. | **FIXED** — regenerated + coverage test |
| B5 | **CI never typechecked** despite the job being named "test + typecheck + build". | Typing was only whatever `next build` caught. | **FIXED** — `tsc --noEmit` added |
| B6 | **CI didn't run on `dev`.** Triggers were `main` only. | The rebuild branch would have had no gate. | **FIXED** |
| B8 | **`ORDER BY em.created_at` is not a total order — the event SUMMARY depended on a tie.** `created_at` defaults to `now()`, which Postgres evaluates at TRANSACTION start, so members written in one transaction share a timestamp exactly; `event_memberships.id` is a uuid4 and orders nothing. `summaries[0]` becomes the event summary, so an unstable sort silently swaps in a later member's summary — reintroducing the exact headline/summary mismatch #135 fixed. | Pre-existing, verified by running the test on the commit *before* my changes: 5/5 failures there. Same family as the Leiden input-ordering bug. | **FIXED** — `ORDER BY em.created_at, ri.published_at NULLS LAST, a.id` |
| B9 | **The test guarding that summary was itself flaky and effectively vacuous.** It inserted both members with `published_at = now()` inside one transaction, so nothing ordered them and it asserted on a coin flip — 5/5 failures on one run, 5/5 passes on another, no code change between. | And after giving it real timestamps it *still* passes with the fix reverted, because Postgres returns heap order on a small table. The behavioural test cannot detect this bug at all. | **FIXED** — real timestamps + a source-level assertion on the ORDER BY, mutation-verified |
| B7 | **Tests ran destructively against the dev database.** conftest accepts a `_test` DB but nothing created one. | Those tests supersede partition runs, detaching every live storyline. | **FIXED** — `prism_test` created on boot |

## C. Dead weight — costs money or confuses readers

| # | Issue | Evidence | Status |
|---|---|---|---|
| C1 | ~~`event_links` is dead~~ **FALSE — it is reader-visible.** `_assemble_timeline:569` reads it for causal "why" notes; `StoryTimeline.tsx:139` renders `↳ {n.why}`. **563** usable notes in prod. | The "no route reads it" claim came from a grep matching only an import — it is reached indirectly via `story_timeline_from_members`. **Nearly deleted a live feature.** Costs ~9% of LLM spend; keep-or-cut is a founder call. | **CORRECTED** — kept |
| C2 | **`ingestion/gdelt.py` is orphaned and would raise.** Not in `runner.run_all()`, and `gdelt` is absent from `seed.SOURCES`, so `persist_envelopes` hits an FK error. | 128 lines that look live. | **FIXED** — deleted |
| C3 | **`field_provenance` is written and never read.** | Only a test's cleanup touches it. | OPEN — deferred; it is a *provenance* record and the claims layer (step 5b) may want it. Decide there rather than delete now. |
| C8 | **`related_developments` / `fetch_thread` had no production caller.** | Superseded by the timeline; only a test referenced them. | **FIXED** — deleted |
| C4 | **The freemium paywall does not exist.** `common/quota.try_consume_sample` — the atomic decrement — is called from nowhere. Only `grant_samples` runs, at signup. | The lens lock is a signup gate, not a payment gate. | OPEN — step 9 |
| C5 | **Dead stream topics.** `stream.EVENTS` declared, never published. `EVENT_UPDATES` published twice per event, consumed by nobody — **65,736 entries, zero consumer groups**. | | **FIXED** — both removed |
| C6 | **~4 heavy 3D deps serve an orphaned component tree.** `three`, `@react-three/*` used only by unimported components. | `HeroVisual`, `PrismHero`, `LensDemo`, `components/prism3d/*`. | OPEN |
| C7 | **The veto is an hourly LLM bill for a refinement nobody sees.** Config's own docstring: the overlay loses its CAS race about half the time and survives ~4m33s on average. | Uses `prism_model_gate` — the *cheapest* model — for the most semantically demanding judgement in the system. | DEFERRED to step 6 — do not remove a safety net before its replacement is proven |

| A9 | **mE5-base REGRESSES monolingual L1 matching, even as it improves cross-lingual.** | `gold_pairs` (a uniformly random production sample, so ~90% English): mpnet Cdet **0.4613** (P 0.7544 / R 0.7049) vs mE5-base Cdet **0.4957** (P 0.7917 / R 0.6230) — better precision, much worse recall. Step 3's gate is "L1 does not regress", so by that gate mE5 **fails**. Against that: cross-lingual news retrieval kn 0.444 → 0.778. Genuine trade, needs a decision. | **OPEN — founder decision** |
| A10 | **`EMBEDDING_DISTANCE_THRESHOLD` is badly tuned for the model we already run.** | Optimal against `gold_pairs` is **0.305**; production uses **0.12**. Recall is being left on the table today, with no model change involved. Caveat: the embedding tier is one rung of a cascade, not a standalone classifier, so the isolated optimum is not automatically the right ship value — it needs `scratch.py --score` through the real matcher. | **OPEN — measure via cascade replay** |

## D. Performance / scale

| # | Issue | Evidence | Status |
|---|---|---|---|
| D1 | **Search is an unindexed full scan.** `api/routes/search.py:26` — `ILIKE '%q%'`, no trigram or tsvector index. | Flagged in-file with a `ponytail:` comment. | OPEN — step 10 |
| D2 | **`title_time` match tier is a sequential scan.** `pg_trgm similarity()` with no GIN/GiST index on `events.title`. | | OPEN — step 4 |
| D3 | **`_converge_existing` is O(n²)** over the active story set. | Bounded to trending (~tens) today; flagged in-file. | OPEN |

## E. Testing gaps

| # | Issue | Evidence | Status |
|---|---|---|---|
| E1 | **`agent/rag.py` has ZERO tests** — the grounded citations-and-refusal agent, i.e. the product's core trust claim. | No test file imports `agent`. | OPEN — step 10 |
| E2 | **`classification/` has ZERO tests.** Relevance gate + sector routing untested. `shadow_gate` unreferenced in `tests/`. | | OPEN |
| E3 | **Collectors near-zero.** No watermark/idempotency/pagination tests for GDELT/NVD/KEV. | | OPEN |
| E4 | **`worker/__main__.py` has ZERO tests.** Stage selection, scheduler, sweeper, health server. | | OPEN |
| E5 | **API routes mostly untested.** `events`, `feed`, `digest`, `trending`, `meta`, `admin` have no endpoint tests — only a route-surface lock. | | OPEN |

## F. Contract / drift

| # | Issue | Evidence | Status |
|---|---|---|---|
| F1 | **`/api/v1/trending` and `/trending/{slug}` have NO `response_model`.** `TrendingStory`, `BranchNode`, `BranchTreeData` exist only in TypeScript; nothing validates them. | They feed `BranchTree` and `StoryTimeline` — the two most structural screens. | OPEN — step P3-c |
| F2 | **`EventDetail.projection` is `dict` in Python, a narrow struct in TS.** The real projection also carries `headlines`, `languages`, `coverage`, `latest_published_at`. | A lie of omission that two components read through. | OPEN |
| F3 | **`PROFESSION_META` is duplicated** in `web/src/lib/api.ts` because `grouped()` only emits `{slug,label}`. | Verified identical today (33 slugs); a backend edit silently desyncs onboarding. | OPEN |
| F4 | **Three version numbers disagree.** `VERSION`=0.0.81.23, `pyproject`=0.1.0, FastAPI `version=`0.1.0. | | OPEN |
| F5 | **Lens colours differ between DESIGN.md and `globals.css`**, and `StoryDesktop.tsx:33` hardcodes the DESIGN.md hues instead of the CSS vars. | The desktop story rail paints different lens colours than the rest of the app. | OPEN |
| F6 | **`CVE_ONLY_SOURCES` encoded in four places.** `feed.py:22`, `enrichment/consumer.py:72`, `correlation/consumer.py:526`, `tools/scratch.py`. | Plus the load-bearing `deterministic:` model prefix. | OPEN |

## H. Notes to self — how these were nearly missed

| # | Lesson | Where it bit |
|---|---|---|
| H1 | **Grep the call graph, not the filename.** `grep "threads" api/` found only an import; the real use was two hops away through `story_timeline_from_members`. | Nearly deleted `event_links` and 563 live why-notes. |
| H2 | **Check evidence recency, not existence.** "CI works" was based on runs 22 days old. | Told the founder their own account information was wrong. |
| H3 | **A subset cannot measure a corpus-relative statistic.** IDF over 152 events ≠ IDF over 19,337. | Fixture L2 scores P 0.17 vs prod 0.43 — would read as a regression. |
| H4 | **Absence of a signal ≠ a negative signal.** | Guarded in the content gate; the reason silence-as-signal is deferred. |
| H5 | **A source-inspection test will match its own explanatory comment.** Bit twice — the Dockerfile model check and the language check both failed on the comment describing the bug. Strip comments before asserting. | Keeping the history is worth more than a simpler assertion. |
| H9 | **Measure the capability the PRODUCT needs, not the one that is easy to measure.** My first bake-off tested only *monolingual* same-story ("are two Kannada articles about one event close?"), found mE5 flat, and concluded the swap was pointless. The question that actually decides whether non-English ingestion is worth anything is *cross-lingual* ("is a Kannada article close to its English counterpart?") — where mpnet scores 0.875 and mE5 scores 1.000. | Nearly abandoned the single highest-value change in the rebuild. Caught only because the founder pushed to test more languages and Indic-specific models. |
| H10 | **"Domain-specific" is a hypothesis, not a fact.** Vyakyarth is trained specifically on Indian languages and lost to general-purpose mE5 on both cross-lingual and monolingual news. | Test it; do not assume it. |
| H7 | **A metric that needs no labels usually cannot answer the question.** My first bake-off used a label-free "separation ratio" and rated mpnet's Kannada *better* than mE5's — contradicting the known collapse. Without labels you cannot tell "the nearest neighbour is close because it's the same story" from "close because the space collapsed". | Cost one wrong conclusion before I noticed the contradiction. |
| H8 | **Absolute cosine distances are not comparable across models.** E5 packs the space far tighter (Latin 5th-pct 0.19 vs mpnet 0.73), so a fixed 0.12 threshold means different things per model. Compare rank-based measures (AUC), never raw distance. | |
| H6 | **Fixtures and tests must not share a database.** Loading the corpus into `prism_test` silently broke a test that counts rows. | My own error. `make seed` now targets the dev DB and the loader refuses `*_test` outright. |

## G. Operational

| # | Issue | Evidence | Status |
|---|---|---|---|
| G1 | **GitHub Actions unavailable (credits exhausted).** Jobs fail with `steps=0`. Last green run 2026-08-05. | `actions/permissions` still reports `enabled: true` — that endpoint is NOT a usable signal. Check run *recency*. | OPEN — external |
| G2 | **Railway deploys outside CI.** A red CI run does not block a backend rollout; Vercel is gated, Railway is not. | Backend sits at `NEEDS_APPROVAL`, which is the real safety net. Keep it. | ACCEPTED |
| G7 | **Redis streams grew without bound — no `MAXLEN` anywhere.** Redis does **not** drop entries on `XACK`; nothing trimmed. | Production: **306,509 entries** across five topics (`raw.items` 141,185). No symptom whatsoever until Redis hits its memory limit and the entire pipeline stops at once. | **FIXED** — `maxlen=100_000, approximate=True`, tunable via `PRISM_STREAM_MAXLEN` |
| G3 | **NDTV returns 403 on every fulltext fetch**, so those articles fall back to title-only extraction. | Degrades entity quality at the source. UA is `prism-prototype/0.1` — inconsistent with the honest UA RSS uses. | OPEN |
| G4 | **`PRISM_ADMIN_TOKEN` defaults to the literal `"change-me"`.** | Prod is correctly set to a 64-char value — checked. A code-default smell, not a live exposure. | OPEN — low |
| G5 | **Langfuse self-hosting cost $70 in two weeks**, more than the LLM spend it observed. | Now disabled and opt-in. Do not re-enable casually. | **FIXED** |
| G6 | **`entities._cache` is a process-level cache of source names.** A newly seeded source is invisible until restart. | `reset_cache()` exists only for tests. | OPEN — low |
