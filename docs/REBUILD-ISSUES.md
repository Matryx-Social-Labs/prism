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
| A17 | **Wikidata alias sets are not identity-preserving — exact match alone folds distinct entities.** | Q234277 is the **CPI(Marxist)** and carries plain `Communist Party of India` as an alias — a different party that still exists and that our corpus names separately. Breaking the tie on prominence (52 sitelinks vs 46) merged them. The corpus also offers `BJP` → **British Journal of Pharmacology** and `CPI` → **isolated cleft palate** as rival candidates. | **FIXED** — three rules: candidates filtered to people/orgs via P31/P279*; strongest surface-form tier competes (label > wiki title > alias/derived); still tied ⇒ **refuse**, never tie-break |
| A18 | **58 entities refused as genuinely ambiguous — a measured backlog, not a defect.** | `Indian National Congress` → Q10225 (current) and Q3523002 (*active 1969–77*), both labelled identically. `Aam Aadmi Party` → Indian Q129844 and **Pakistani** Q17003198. `Amit Shah` → three different people. Name alone cannot separate these; refusing leaves them on their slug, i.e. exactly today's behaviour, so there is no regression. | **PARTLY FIXED** — `narrow()` applies liveness (P576/P570) then, only if that fails, country (P17), as pre-filters before `resolve`. Genuine person-name collisions (three Amit Shahs) stay refused, correctly |
| A19 | **Wikidata single-token aliases merged unrelated people.** | Q114270322 is a Kashmiri poet, Hemangi Sharma, whose item lists BOTH `Rahul` and `Kiran` as aliases — so two unrelated corpus entities folded into a poet neither of them is. Rejecting short aliases wholesale would also lose `bjp`, `cbi`, `rss`, `nta`, the most valuable folds. | **FIXED** — `is_identifying()`: a single-token alias is accepted only if it is an initialism of the item's own label (joiners skipped: Press Trust of India → PTI) or a word of it (C. Joseph Vijay → vijay). Dropped 985 weak aliases in production |
| A20 | **PRODUCTION MEASURED, read-only: 85 splits fold, worst IDF distortion 1.72×.** | 19,356 events / 2,794 person-org entities with df ≥ 2. 1,301 linked (47%), 265 refused. Biggest: `bharatiya-janata-party(256)+bjp(134)` 1.39×, `cockroach-janta-party(128)+cjp(52)`, `c-joseph-vijay(53)+vijay(31)` 1.55×, `jp-nadda+j-p-nadda+jagat-prakash-nadda` 1.48×, `rss+rashtriya-swayamsevak-sangh` 1.72×. The plan estimated 39 splits; the real number is **85**. | **MEASURED — gate met (< 2×).** Applying it needs the migration in prod, i.e. a Railway deploy approval |
| A21 | **APPLIED TO PRODUCTION.** | Fold ran in two passes: **85 QID groups / 1,668 mentions**, then **18 slug-variant groups / 168 mentions**. 1,301 entities carry a qid; 107 redirects set. `bharatiya-janata-party` df 256→356, `rss` 25→43, `priyanka-gandhi` 38→63. Re-run is idempotent (0 groups). Both journals kept outside the repo; `--unfold --write` reverses either. | **DONE** |
| A22 | **Spaced and dotted initials were different entities.** | Removing dots turns `V.D. Satheesan` into `VD Satheesan`, but `V D Satheesan` keeps its spaces — so `vd-satheesan(23)` and `v-d-satheesan(16)` were separate rows for the Kerala LoP, plus `kc-venugopal`, `ps-narasimha`, `kt-rama-rao` and 14 more. Indian coverage writes initials both ways constantly. | **FIXED** — `canonical_entity_name` joins runs of single-letter initials; existing rows folded |
| A23 | **The fold report undercounted itself.** | `report()` keyed groups in a dict by qid, so every group folded on slug alone shared the placeholder key and overwrote the rest — 18 groups displayed as 3. The report is what the fold decision is read from. | **FIXED** — a list, not a dict |
| A24 | **Two stories anchored on one event served as two cards.** | Live: two active stories both on hero `91456068` ("Karnataka cabinet expansion"), sharing 7 members. Every threshold missed it — member overlap 7/21=0.33 vs 0.60, cast Jaccard 0.20 vs 0.50, IDF cast overlap 0.003 vs 0.12 (their one shared actor, Dharmendra Pradhan, has df 339). | **FIXED + verified live** — `_same_story` treats a shared hero as identity, before any threshold. Duplicate headlines on the feed: 0 |
| A25 | **The curated alias list was never consulted by the fold.** | `cockroach-janata-party(212)` had no QID while `cockroach-janta-party(172)` had Q139857349, so they never grouped — and the live feed showed BOTH spellings in one cast, the defect that started this work. Not separator-identical either ("janata" vs "janta"), and Wikidata records only one form. | **FIXED** — `resolve_alias` is a third grouping key. 3 groups / 234 mentions folded; `cockroach-janata-party` df 212→**361** |
| A14 | **Entity slugs DELETED every non-Latin script, folding unrelated names into one row.** | `slugify` was `[^a-z0-9]+`, which does not transliterate — it strips. `entity_slug("भारतीय जनता पार्टी")`, `("ನರೇಂದ್ರ ಮೋದಿ")` and `("نریندر مودی")` all returned **`"unknown"`**, i.e. one entity. The slug IS the identity, so eight languages' actors would merge into a single row with an enormous df — and every clustering site weights by 1/df, making the corpus's largest entity its least informative. Latin diacritics were dropped too: `Ávila` → `vila`, a *wrong* slug rather than a broken one. Latent (extraction still emits English), armed by the eight Indic feeds. | **FIXED** — Unicode-aware, Latin accents folded, Indic matras preserved (they are letters, not accents). 4 tests, mutation-verified |
| A15 | **Wikidata items can lack an English label while clearly having English coverage.** | Q1058 — Narendra Modi — carries **137 labels and no `en`**, description "Prime Minister of India since 2014", enwiki title "Narendra Modi". A labels+aliases index therefore does not contain the string "Narendra Modi" for Modi: the most prominent entity in the corpus falls to `local:` and keeps splitting. | **FIXED** — the alias index also ingests **sitelink titles**, which are curated and exist per language |
| A16 | **Search-only linking inherits the exact defect it is meant to fix.** | `wbsearchentities("Pakistan Muslim League-Nawaz")` → no hit; `("Pakistan Muslim League (N)")` → Q799577. The item's *alias list* does not carry the missing form either — an earlier draft assumed it would, and the module self-check caught that. Its **enwiki title** "Pakistan Muslim League – Nawaz" does; hyphen-vs-en-dash vanishes under normalisation. | **FIXED** — search proposes candidates, the local index decides, match is exact-only |
| A13 | **Wikidata coverage MEASURED — the QID plan is viable.** | n=100 per sample: **97%** of top-df entities found, **72%** among df ≥ 2 (the ones that can actually form an edge), 34% across the whole vocabulary. Every uniform-sample miss was df 1 — clustering-inert local figures. And 72% is a **lower bound**: the probe's exact-string search misses `Pakistan Muslim League-Nawaz` while `Pakistan Muslim League (N)` resolves to Q799577. | **MEASURED — proceed.** Confirms candidate generation must use a local ALIAS index, not live exact search |
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

| A9 | ~~mE5-base regresses monolingual L1~~ **RESOLVED by cascade replay — it does not.** | The isolated embedding-tier test said regression (Cdet 0.4957 vs 0.4613). Replaying the **full cascade** through the real `find_event` says otherwise: mpnet P 0.9032 / R 0.4590 / F1 0.6087 / **Cdet 0.5766**; mE5 with its own thresholds P 0.7949 / R 0.5082 / F1 **0.6200** / Cdet 0.5868. Equivalent — F1 +1.9%, Cdet +1.8%, both inside noise on 61 positives. The title and entity tiers recover what the embedding tier misses, exactly as `gold_pairs`' docstring warns about pairwise scoring. | **RESOLVED — swap is ~neutral monolingually, large gain cross-lingually** |
| A11 | **Thresholds had to be keyed to the model, and the failure is silent both ways.** | mE5 run with mpnet's thresholds: **76 false merges vs 3** — a 25x increase, because E5's same-event median is 0.063 and different-event 0.145, so 0.12 sits between them. Nothing raises; the feed just fuses unrelated stories. My earlier one-example guess predicted the *opposite* direction (too tight). | **FIXED** — `_SCALE` keyed by model, uncalibrated models warn |
| A10 | **`EMBEDDING_DISTANCE_THRESHOLD` is badly tuned for the model we already run.** | Optimal against `gold_pairs` is **0.305**; production uses **0.12**. Recall is being left on the table today, with no model change involved. Caveat: the embedding tier is one rung of a cascade, not a standalone classifier, so the isolated optimum is not automatically the right ship value — it needs `scratch.py --score` through the real matcher. | **OPEN — measure via cascade replay** |

| A12 | **Step 4's title-cosine gate: MEASURED AND REJECTED.** | Pairwise at 0.45 looked excellent (P 0.9706, fp 1). Cascade replay: baseline tp 28 / fp 3 / Cdet 0.5766 vs gated tp 24 / fp 0 / Cdet 0.6066. Kept in-tree as `TITLE_COSINE_GATE`, defaulted off, numbers in the comment so nobody re-derives it. | **WONTFIX — measured** |

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
| H11 | **A gate with PERFECT precision can still lose.** The entity-path title-cosine gate removed every false merge (P 1.0000) and lost anyway — 4 true merges sacrificed for 3 false ones, Cdet 0.5766 → 0.6066. Third time this shape has been tried here; third time the cascade contradicted the pairwise number. | Compounding: a rejected merge doesn't just not-merge, it CREATES an event that becomes a smaller, wronger candidate for the next article. |
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
