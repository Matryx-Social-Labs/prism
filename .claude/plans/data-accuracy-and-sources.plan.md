# Plan: data accuracy first, then scale the sources

**Asked (2026-09-29):** cover the data side completely before credits are added and ingestion resumes —
canonicalization accuracy, whether stories can start, whether X posts and podcast clips are ready and attach
properly, how and when to scale news / podcast / X sources, labelled data needs, cost per day, what we do
wrong, which signals we miss, how Wikidata is used, and how to cover and show the professional lenses.
**Complexity:** Large (6 phases); Phase 0 is small and is the only thing gating the restart.
**State measured:** prod DB + Redis spend ledger + prod flags, 2026-09-29 (ingestion paused since
2026-09-28 02:11 UTC, OpenRouter balance under the $5 floor). Scripts in `/tmp/prismq/` (to be moved into
`tools/` in Phase 1).

---

## 1. What was measured

| Area | Number | How |
|---|---|---|
| Volume | ~5,400 raw items → ~4,100 articles/day after the 09-24 source expansion; 74% pass the gate | `raw_items`, `articles` by day |
| Sources | 59 feeds enabled / 41 publishers / 13 languages; **Prajavani alone = 17%** of raw items; 3 declared feeds off (Business Standard, PIB, SEBI) | per-source counts 09-21..09-28 |
| Fulltext | **16% of articles are enriched from the RSS snippet only** (avg 117 words); NDTV 941/941 at 26 words, TOI, Aaj Tak, ESPNcricinfo mostly snippets | `articles.retrieval_tier` |
| Records | **87.5% of live records have ONE publisher**; 8.2% two; 4.3% three+ | publishers per event, 14 d |
| Tier mix (24 h before the verify flip) | new record 73% · entity_overlap 19% · embedding 6% · title 2% | `event_memberships.match_type` |
| **Tier precision** (Jev, the verified tier's own "same happening" test, 781 attaches) | **verified 100%** (131) · title 92% (150) · embedding 76% (200) · **entity_overlap 44%** (300; 28% clearly different) | `/tmp/prismq/tiers.py`, $0.018 |
| Hand check | verified 40/40 right (most cross-language); entity_overlap ~13/40 wrong + 4 borderline | read by me |
| Corroboration | **1,416 of 2,509 multi-outlet records (56%) are multi-outlet only through entity_overlap/embedding attaches** | 14 d |
| Junk magnet | "Speeding vehicle crushes 3-year-old child in Hyderabad" holds **26 unrelated Aaj Tak articles** via the embedding tier: their "direct" fetch returned a related-headlines list, not the story | members read |
| **Residual duplicates** (surviving records, 5 d, 9,038 records, 11,557 candidate pairs judged, $0.14) | **1.4% are copies at 0.85** (1.0% at 0.87), down from **10.1% on 09-25**; records created after the verify flip 1.2% — the 09-27 merge + live verified tier fixed under-merging; what is left is OVER-merging by the fuzzy tiers | `/tmp/prismq/dups.py` |
| Lenses | Markets brief on 6.9% of records (~100/day), Cyber 1.1% (~16/day), **Health and Policy do not exist** (registry `upcoming=True`, no fields, no prompt, no classifier output) | `projection.lens_briefs` |
| Tickers | ~1 in 4 to 1 in 3 sampled ticker sets name a company the story is not about (CVX on a school water project, BA on an Airbus story, BALRAMCHIN on an NBFC result) | 30 read |
| Cyber facts | CVE ids, CVSS, "KEV listed" are model-read from articles; no validation source since NVD/KEV removal | code + sample |
| Wikidata | **1,301 of 90,674 entities (1.4%) have a QID**; 13% of mentions (14 d); `entity_alias` **empty in prod**; places, companies, government never linked; `qid` read only for `sameAs` | `entities` |
| Stories | 118 active / 2,264 dormant, members avg 24 (max 96); labels like **"Prajavani · Dharmendra Pradhan · BJP"** (an outlet as cast) | `stories` |
| X (shadow on worker since 09-21) | 24 accounts, 1,441 posts (~160/day), 231 attached (16%), **URL tier 0 matches** (posts link PIB/MEA/RBI pages we don't ingest); my read 27/30 right; no gold file | `x_posts`, `event_x_posts` |
| Podcasts (live since 09-20) | 4 shows, 29 episodes transcribed, **25 clips in 9 days (~3/day)**; Moneycontrol newest episode 6 days old | `event_clips` |
| Claims | 53% of records carry ≥1 verified quote (7 d) | `enrichments.shared_fields.claims` |
| Health of the queue | 0 stuck items; dead letters raw 143 / classified 47, no alert | Redis |

## 2. Cost per day (measured, not estimated from docs)

Spend ledger `spend:2026-09-27/28` (Redis), unit costs per relevant article:

| Stage | Model | Unit | Per article |
|---|---|---|---|
| extract-shared | gemini-3.1-flash-lite (AI Studio flex, 41–46% cached) | $0.00087–0.00094/call | $0.00091 |
| event-analysis | glm-5.3-flash, **no reasoning cap, no provider pin** — 2,150 output tokens/call | $0.0013/call × 0.34 | $0.00045 |
| gate-classify | Jev | $0.00021/raw item × 1.3 | $0.00027 |
| lens-brief | glm (sweep) | $0.00024 × 0.46 | $0.00011 |
| thread-link | glm | $0.00025 × 0.28 | $0.00007 |
| event-verify | Jev | $0.000036 | $0.00004 |
| quotes, subject leaf | Jev | — | $0.00003 |
| **Total** | | | **≈ $0.0019 / article ≈ $1.9 per 1,000** |

- **Today: ~4,100 articles/day ≈ $7.8/day ≈ $235/month** (LLM), + X ≈ $0.8/day (separate X bill) +
  transcription ≈ $0.05/day. Embeddings are local (free).
- **After Phase 0 (reasoning off on event-analysis, extraction cache ≥ 80%): ≈ $1.3 per 1,000.**
- **After the Phase 3 source waves (~+1,000–1,500 articles/day): ≈ 5,500/day × $1.3 ≈ $7/day** — about
  today's bill for ~35% more coverage. The Phase 1 verifier adds ~$0.03/day.
- Runway: at ~$7/day, $100 of credit ≈ 2 weeks. The $5 floor is a stop, not a warning — add a warning.

## 3. What we are doing wrong (ranked by harm to the record)

1. **Fuzzy tiers attach without verification.** entity_overlap (19% of attaches, 44% precise) and
   embedding (6%, 76%) put ~1 in 8 articles (~450–500 a day) into a record about a different happening —
   mostly follow-ups (IIT-Bombay: 67 articles over a week in one record), sometimes unrelated
   (Kohli milestone → Greaves century; Sudeep's 30 years → Bigg Boss wildcards). The one tier we
   verified (Jev) is 100% precise and costs $0.00004.
2. **Tiers 5–6, the identical-body guard and the whole story layer compare against the founder's raw
   first 1,200 characters** (`events.embedding`, AUC 0.46 on hard pairs) instead of the English gist
   (AUC 0.91–0.99). That is how a headline list captures 26 Aaj Tak articles.
3. **The extraction prompt asks for "the story's principal actors even for a sub-angle article"** — it
   manufactures the shared actors that pull follow-ups into one record.
4. **16% of articles are read from a snippet**; NDTV is 100% snippet (its pages 403 every UA, and its
   feed carries US NFL stories). Entities, quotes, gist and lens facts on those are thin, and snippets
   embed near each other.
5. **Counting is inflated**: wire copy (PTI/ANI/IANS reprinted by three outlets) counts as three
   publishers; follow-ups attached by entity_overlap count as corroboration. 56% of "same story across
   outlets" records depend on the fuzzy tiers.
6. **Lens "facts" are model inference presented as facts**: tickers ~25–35% off-company, CVE/KEV
   unvalidated, control mappings and the price arrow are model opinion under "Facts first".
7. **Stories are topic blobs**, with outlet names as cast; nothing verifies a story edge.
8. **Wikidata is a one-off** (1.4%); QIDs do nothing in matching, quotes, tickers or places.
9. **Silent failure modes**: no per-source telemetry (reject / snippet / duplicate rates), dead letters
   without an alert, requeue loops with no attempt cap, a budget floor that stops collection but not
   briefs/Ask/Pulse, `/sources` "reachable" wrong after a 304, one-page X reads that drop posts.
10. **Our crawler UA blocks us**: `Prism/1.0 (+https://www.readprism.news)` trips a shared Indian WAF
    rule (URL in UA). With `Prism/1.0 (+readprism.news)` Business Standard, NDTV Profit, PIB and NSE
    answer 200 (laptop test; needs one worker check).
11. Two code bugs found by the audit: the entity tier ignores folded entities (`merged_into`); a
    record-to-record merge can leave the absorbed founder's summary under the survivor's title (up to
    907 merges applied 09-27).

## 4. Signals we are missing (value order)

| Signal | Already in hand? | Buys |
|---|---|---|
| **Primary-document links** in articles (PIB PRID, RBI/SEBI circulars, court orders) | stripped by trafilatura | an EXACT same-happening key (two reports citing PRID 2316569 are one happening), a "primary source" link on the record, and the X URL tier (X posts link exactly those pages) |
| **Wire attribution** (byline/dateline PTI/ANI/IANS/UNI) + text fingerprint | trafilatura `author`, `fingerprint` discarded | honest "k of n outlets"; wire reprints count once |
| `og:url` / `rel=canonical`, `datePublished`/`dateModified` | trafilatura result, discarded | AMP/edition aliasing, future-date guard, "updated" markers, true first-reported time |
| RSS `<category>`, `author`, `content:encoded` | in the parsed entry, kept only as a repr string | classification hints, bio guard, full body without a fetch |
| Embedded tweets | stripped | exact article ↔ X post link |
| Per-item language detection | `detect_script` exists, unused at ingest | wrong-language items, script-trust decisions |
| Dateline city / occurred place | only inside LLM text | state placement, same-happening evidence |
| Wikidata facts (P39 office, P102 party, P946 ISIN, P249/P414 ticker, P2002 X handle, P131 place-in, Indic labels) | not fetched | speaker ↔ entity, ticker cross-check, account ↔ entity, state hierarchy |

## 5. Answers to the questions asked

- **Is canonicalization accurate?** Half of it is fixed: duplicate records fell from 10.1% (09-25) to
  1.4%, and the verified tier is 100% precise. The other half is not: the old fuzzy tiers put the wrong
  articles INTO records (entity_overlap 44%, embedding 76%). Phase 1 puts every fuzzy attach through the
  same verifier and re-judges the backlog.
- **Can stories start?** Not as "developments" yet — today's story rows are topic blobs. They can start
  properly once the Phase 1 verifier also answers "is this a follow-up of that happening?", which turns
  every refused entity-tier match into a verified story edge (Phase 4). Record stays strict (one
  happening); the story links the happenings.
- **Are X posts enough, and do they attach properly?** As confirmations, nearly: ~9/10 right by eye, but
  the gate (≥0.9 on labels) has never been measured, the URL tier can never fire until PIB/RBI/MEA pages
  are ingested, and two bugs lose posts. As coverage, no — X is a signal tier, not a source, by design.
  One post judged to three records also exposes duplicates (Suchika Tariyal ×3) — use it as a dup signal.
- **Can podcast clips be used neatly?** Yes, and they are live, but thin (~3 clips/day, 4 shows,
  English only). Four more daily shows serve identical bytes per request (safe to time-align): Daybreak
  (The Ken), The Daily Brief (Zerodha), Cut the Clutter (ThePrint), All Things Policy. Markets shows feed
  the Markets lens.
- **How/when to scale sources?** In waves, each gated on Phase 1 being live and per-source telemetry
  (Phase 2), measured for 48 h before the next (section 7).
- **Labelled data?** Yes — six small sets, ~1,300 items, mostly pre-labelled by Jev so humans only
  confirm (section 8).
- **Wikidata?** Used for 1.4% of entities and only as `sameAs`. Worth making continuous for identity
  (actor pages, speakers, tickers, places, X accounts), not for event matching (measured zero effect,
  09-09).
- **Professional lens coverage?** Markets ~100 records/day, Cyber ~16, Health/Policy none. Phase 3 adds
  lens desks, Phase 5 builds Health and Policy for real and a lens-desk surface.

---

## 6. Phases

### Phase 0 — before the top-up and restart (≈ 1 day of work)

| # | Change | Where | Check |
|---|---|---|---|
| 0.1 | RSS UA → `Prism/1.0 (+readprism.news)` (the URL in the UA trips the WAF); fulltext UA to the same product name (it still says `prism-prototype/0.1`, which is not what blocks it) | `ingestion/rss.py:177`, `enrichment/fulltext.py:110` | one GET per blocked feed from the worker (`railway ssh`) |
| 0.1b | Snippet-only sources, tested 09-29 from a laptop with 3 UAs: **NDTV and ESPNcricinfo 403 every UA** (bot wall — try their AMP/alternate feeds from the worker; else mark them snippet-only so they never count as depth, and drop NDTV's US-NFL items); **TOI and Aaj Tak return full text from a laptop** (TOI's 70-word prod average points at Railway egress — check from the worker) | `enrichment/fulltext.py`, `ingestion/rss.py` | snippet share per source on the worker, before/after |
| 0.2 | event-analysis: `reasoning` minimal + provider pin like lens-brief | `correlation/consumer.py:758-766` | ledger: output tokens/call 2,150 → <700; bake-off 20 events for quality |
| 0.3 | requeue attempt cap (count in `raw_items.classification` or a small column) + dead-letter count on `/healthz` with a warning threshold | `ingestion/runner.py:55-150`, `common/stream.py` | test: a poison item stops after N tries |
| 0.4 | balance warning at "2 days of spend" (email/admin banner), floor stays $5 | `common/budget.py` | unit test on the threshold |
| 0.5 | Aaj Tak / headline-list guard: refuse a direct fetch whose text is mostly short title-like lines (and fall back to body) | `enrichment/fulltext.py` | fixture from the 26 magnet pages; mutation-verified |

**Restart decision (founder):** (A) top up and restart right after 0.1–0.2 (hours) and let Phase 1's
repair clean what the old tiers mis-attach meanwhile (~450–500 articles/day), or (B) hold until Phase 1.1
lands (+1–2 days). **Recommend A**: the site has shown day-old news since 09-28, and the repair tool is
needed for the backlog anyway.

**Phase 0 status (2026-09-29): built in 0.0.117.0** — 0.1 UA (worker-verified), 0.1b the
400-character bar was the TOI cause (NDTV and ESPNcricinfo 403 every UA from Railway too: left on
summaries), 0.2 event analysis (−68% per call), 0.3 give-up after 3 dead letters, 0.4 founder
emails, 0.5 headline-list guard; plus the prompt-cache fix below.

### Prompt caching audit (asked 2026-09-29)

Per stage, from the ledger (09-27/28) and controlled runs against OpenRouter:

| Stage | Model / endpoint | Cached share before | Finding | Now |
|---|---|---|---|---|
| extract-shared | gemini-3.1-flash-lite, AI Studio flex ($0.125 in / $0.0125 cached / $0.75 out per M) | 42% | Every call hit, but Gemini's IMPLICIT cache only ever served ~2,450 of the 4,380 fixed tokens; a 5.5-min idle gap left 4 of 12 cold. Moving the schema out of the prompt (json_object) cached 0 | explicit mark on one merged system message: 4,380/4,380 cached, $0.00069 → $0.00046 |
| event-analysis | glm-5.3-flash, unpinned | 30% | cost was OUTPUT: 2,220 reasoning-heavy tokens per call | minimal reasoning + Together pin: $0.00166 → $0.00053 |
| lens-brief | glm on Together (pinned) | 66% | implicit prefix caching works when pinned | unchanged |
| thread-link | glm, unpinned | 25% | ~943-token prompts sit under most providers' cache minimum; $0.13/day | leave |
| gate-classify, event-verify, quotes, subject, judges | Jev (Decisions API) | 0% | billed on input only ($0.042/M, output free); nothing to cache | Phase 1: measure a shorter gate input (4,000-char body → 2,000) |

Rules this leaves: pin every high-volume stage to one endpoint (a cache lives per endpoint);
mark the fixed prefix on providers that need a mark (Gemini, Anthropic); keep the variable
content last; for GLM hosts, implicit caching needs only the pin. OpenRouter's sticky routing
only helps unpinned calls and expires after 10 minutes idle.

### Phase 1 — every attach verified (week 1) — the core accuracy fix

1.1 **Propose → verify.** Tiers `title_time`, `embedding`, `entity_overlap` stop attaching; they
    propose their event into the verified tier's candidate set (with the gist candidates). One Jev call
    asks two questions against the founder's text: `same_happening` and `same_story` (a follow-up,
    reaction or later stage). ≥0.85 same_happening → attach. Else ≥τ same_story → **new record + a
    `leads_to` story edge** to the proposed record (keeps "follow the story" without polluting the record).
    Else new record. Timeout → new record (as today). Exact tiers (`url_exact`, `cve_id`) bypass.
    `correlation/clustering.py:210-289`, `correlation/verify.py`. +~1,000 Jev calls/day ≈ $0.03.
1.2 **Gist, not raw chunk**, for candidate generation: event gist = founder's `gist_embedding`
    (backfill column on events), used by tier 5, the identical-body guard, partition kNN and trending.
    Add the missing vector index on gists.
1.3 **Extraction prompt**: drop "principal actors even for a sub-angle article"; tag such actors
    `role=context` and exclude `context` from the entity tier.
1.4 **Repair the backlog** — `tools/repair_attaches.py` (dry-run CSV, then apply): re-judge fuzzy
    memberships of the last 30 days; detach `same_happening < 0.15` and re-home each article through
    `find_event`; follow-ups get the story edge. Recount `source_count`, rebuild projections, 308 for any
    emptied record. Budget ≈ 15,000 pairs ≈ $0.35.
1.5 **Fix the two bugs**: entity tier follows `merged_into`; merge keeps the survivor's own founder
    summary/first_seen (re-run `_rebuild_projection` ordered by founder, not `created_at`) — backfill the
    907 merged survivors.
1.6 **Separate the floors**: `PRISM_EVENT_VERIFY_MIN` (live) vs a merge-tool CLI floor.
1.7 **Measure, as tools**: move `/tmp/prismq/tiers.py` → `tools/audit_tier_precision.py`,
    `/tmp/prismq/dups.py` → `tools/audit_event_dups.py --survivors`; add both to `/admin` weekly.
    Replay gate: `tools/score_cascade` on the 794 labelled pairs must not lose recall vs today at
    P ≥ 0.95.

**Exit:** tier precision ≥ 0.95 on every attaching path; residual copies stay ≤ 2% of new records (1.2%
today — the verifier must not trade precision for new duplicates); multi-outlet records re-counted.

**Phase 1 status (2026-09-29): built in 0.0.118.0**, founder decisions 1A 2A 3A 4A 5A.
- 1.1 `PRISM_EVENT_VERIFY=confirm` (propose → verify, two questions, follow-up links; on
  a Jev failure only a title proposal still attaches). 1.3 dropped: the prompt only asks
  for actors the article names, and under confirm shared actors just propose.
- 1.2 dropped for now: candidates already come from gists in the verifier.
- 1.4 `tools/repair_attaches` (dry run 7 days: 1,891 of 4,217 under 0.5, 452 follow-ups).
- 1.5 both bugs fixed (`--resummarise`: 169 records). 1.6 `merge_duplicates --min`.
- 1.7 labels: `/label` shows records against records only, so `tools/gold_attaches`
  writes two blind sheets (300 article-vs-record pairs, 100 read twice) instead.

**Phase 1 status (2026-10-01): live and applied** (main 2ad5bd7, 0.0.119.1–0.0.123.0).
- Restart after the top-up exposed OpenRouter's opt-in prompt-injection guardrail: a 403 on
  one headline ("How does your system override law?") was read as quota and paused every call
  (0.0.119.1: a refused request is that article's alone; guardrail switched off by the founder).
- `PRISM_EVENT_VERIFY=confirm` since 09:25 UTC. Model labeller (below, §8) labelled the 300
  attach pairs blind → `PRISM_PROPOSAL_VERIFY_MIN=0.65` for records a fuzzy tier proposed
  (P 0.975, R 0.727; 0.85 was P 1.000, R 0.466); gist-only candidates keep 0.85. Old tiers by
  the same labels: title 0.90, embedding 0.79, entity_overlap 0.48.
- Judge against the record **as it stands** (0.0.121.0): founder + 2 confirmed members nearest
  the article's gist; recall 0.727 → 0.770 at the same precision.
- Repair applied for the last 30 days at `--detach-below 0.15` only (~1,580 moved): by the
  labels, 0.15–0.5 is still 20–43% the same happening — re-judge that band after 2.7–2.9.
  URL copies now move together (0.0.121.1: 31 of the first 250 moves were pulled back by a
  second copy of the same article).
- Record merges at 0.85 only (87 in 7 days). The 0.80–0.85 band read ~88% right; its errors
  are reactions folded into the incident ("PM praises pilot" into the attack).
- Records dated by first report, not processing (0.0.122.0): `events.first_published_at`,
  32,615 backfilled, 10,313 had been dated >6h late, 551 links turned; search groups by story.
- One name, one entity (0.0.123.0): spelling variants folded on Jev's word with evidence
  (same record / verified link / one story), journalled and undoable: 1,412 folds, the
  Flydubai pilot 15 entities → 1 (+4 one-off spellings under the floor). Live at ingest
  (`PRISM_ENTITY_VARIANTS=live`).

### Phase 2 — signals and identity (week 2)

2.1 Keep what we already fetch: `og:url`/canonical, `datePublished`/`dateModified`, author,
    categories/tags, fingerprint, outbound links (host + path), embedded tweet ids → new
    `articles.meta` JSONB. RSS `tags`, `author`, `content:encoded` → real JSON in `raw_items.raw`.
2.2 **Primary-document key**: normalise PIB PRID / RBI / SEBI / court-order URLs from outbound links;
    same key → same happening (exact tier), and a "primary source" link on the record. X posts linking
    the same key attach exactly (URL tier finally fires).
2.3 **Wire detection**: byline/dateline/fingerprint → `origin='wire'`; wire reprints count as one outlet
    in `source_count`, `record_indexable` and the coverage bar ("PTI via 3 outlets").
2.4 Future-date guard; per-item language/script check; `rss_last_error` cleared on 304; zero-entry 200
    counts as a failure.
2.5 **Per-source telemetry** on `/admin/sources`: per day raw, gate reject %, snippet %, duplicate %,
    median words, attach rate, fetch errors. This is the scale gate's instrument.
2.6 **Wikidata continuous**: worker job links new person/org/company/government/place entities with
    df ≥ 2 daily (existing `tools/link_entities` logic), fills `entity_alias` with Indic labels, fetches
    P39/P102/P27/P106/P946/P249/P414/P2002/P131. Uses: fold variant actor pages (308), speaker ↔ entity
    for quotes, ticker cross-check (ISIN P946 must match the securities master), X account ↔ entity,
    state placement via P131. Not used for event matching.

**Phase 2 addition (2026-10-01): context-based entity linking.** Spelling folds (0.0.123.0)
only catch one name written several ways. Context also resolves "POTUS", "the 47th President",
"the Chief Minister" and misspellings no rule catches. Research: retrieval and reasoning are
complementary — together +6.9% overall, up to +23.3% on rare entities, benchmark incl. Hindi
and Tamil (Think Before You Link, arXiv 2609.10745); LLMs asked for Wikidata QIDs directly
invent them (<1% precision, arXiv 2505.03473) — so retrieve candidates, let the judge choose.
2.7 **In-article coreference at extraction**: one entity per real person/org per article with
    every surface form the article uses ("Trump", "the President", "POTUS") and the role it
    gives them. Cheap (the extractor already reads the article); fixes in-article spelling.
2.8 **Titles → office holders by date**: role mentions ("PM", "CM of Karnataka", "POTUS",
    "Chief Election Commissioner") resolve to whoever held the office on the article's date —
    Wikidata P39 with P580/P582 qualifiers, cached per office; Indian state offices seeded by
    hand where Wikidata is thin.
2.9 **Retrieval + reasoning linking to Wikidata**: candidates from Wikidata labels/aliases in
    all 12 languages (and our own registry), the judge picks with the article's sentence or
    says none. Today 1.4% of entities carry a QID; flydubai had none.
2.10 **Entity registry**: identity = QID where one exists (else our id), multi-script names,
    roles over time, provenance per link; the slug becomes a display handle, not identity.
    New people (not in Wikidata, like the pilot) keep the skeleton + evidence + verifier fold.
    Gate: 200 `entity_link` labels, P ≥ 0.95 (model labeller + a human audit sample).

### Phase 3 — source waves (weeks 2–3), each after the scale gate (section 7)

| Wave | Feeds (all verified live 09-29 unless marked) | For |
|---|---|---|
| W0 | re-enable **Business Standard** (+markets/economy/companies); **NDTV Profit**; **PIB press releases** (fetch the page for ministry + date); **SEBI press releases** (filter `/press-releases/`) — all need the new UA | Markets, Policy, origin statements free instead of X |
| W1 lens desks | ET Markets, ET BFSI, CNBC-TV18 market/business, Mint markets/companies, BusinessLine markets · ET HealthWorld, ET Pharma, The Hindu Health, Medical Dialogues · LiveLaw, Bar & Bench · ET Telecom, ET Government | Markets ×3, Health 0→4 desks, Legal 0→2, telecom/cyber, policy |
| W2 languages | TV9 Bangla/Gujarati/Marathi/Telugu/Bharatvarsh (one pattern), Kolkata24x7, Live Hindustan, Daily Thanthi, Kannada Prabha, Samakalika Malayalam, New Indian Express | Bengali/Gujarati 1→3, big Hindi/Tamil dailies |
| W3 podcasts | Daybreak (The Ken), The Daily Brief (Zerodha), Cut the Clutter (ThePrint), All Things Policy; check Moneycontrol staleness; retry failed transcriptions | clips on Markets + Policy |
| W4 X | fix: page through timelines until `since_id`; URL tier skips merged records. Add per-lens handles (MeitY, ICMR, CDSCO, FSSAI, NPCI, CBIC, Income Tax, CCI, NITI, TRAI, UIDAI — $0.01 each to resolve). Gate: `tools/gold_xposts` ≥ 0.9 on 100 labels → flip `PRISM_X_ENABLED` on the API | official confirmations on records |

Not added, on purpose: NSE/BSE filings as records (raw rows; NSE terms forbid commercial reuse without
permission) — links/facts only; Moneycontrol, Financial Express, News18 family, Anandabazar (blocked);
Dark Reading (future-dated); anything Spotify-only or with stitched ads (IE 3 Things, BBC Dinbhar until a
two-client offset test passes).

### Phase 4 — stories that are verified (weeks 3–5)

4.1 Story edges come from Phase 1.1 (`same_story` at ingest) + existing `thread-link` `leads_to`/`related`
    edges (4,541) + gist kNN, all confirmed by Jev `same_story`, **star-attached to the story's anchor
    record** (never transitive — the 46-record Trump–Xi chain is why).
4.2 Story cast = QID-linked actors named by ≥2 member records; outlets can never be cast.
4.3 Gate: held-out labelled story pairs, P ≥ 0.9 at R ≥ 0.5, two labellers, κ reported. Then
    `STORY_BOUNDARY_STATUS = "verified"` → developments, timelines, indexing, "Follow the story".
4.4 Founder defines a story on the six contested classes from the 09-14 adjudication (box-office runs,
    same-day weather, a rally remark on an ongoing negotiation, an explainer spawned by an incident,
    daily updates, reactions) — that answer IS the label guide.

**Phase 4 revision (2026-10-01): stories made of threads, no size cap.** After the name fold
the Flydubai story no longer splits by language but by facet: the attack (17 records), the
landing (8), praise (7), the airlift (6), Modi (6), the Gujarat award (6) — because Leiden CPM
caps a community near 25 records (Story Forest's bound) and this story has ~100. Cross-language
gist edges (founder gist, other-language 2-NN, distance ≤ 0.07, headline overlap) were measured
offline on the live window: ~94% right on a read of 33, stories 3,780 → 3,678, max 24, Flydubai
21 → 19 stories — useful, but the cap is the real limit.
4.5 **Story → threads**: a story is the connected set of records joined by verified
    `leads_to` links and confirmed `same_story` edges (star to an anchor, never transitive);
    threads inside it are the current Leiden communities (Attack · Reactions · Investigation ·
    Recovery · Honours · Politics). No size cap on the story; threads stay small.
4.6 **Cross-language story edges** (above) behind replay on labelled story pairs.
4.7 **Story identity**: a story keeps its slug while its anchor record is in it; when none of
    its founding records remain it gets a new slug and the old one redirects
    (`/trending/netanyahu-calls-accusations-of-genocide-in-gaza-…` held the pilot story).
4.8 The partition job sleeps 15 minutes after every worker restart before its first run —
    time it from the last run instead, so deploys do not stall stories.

### Phase 5 — lenses readers can trust, and how they are shown (weeks 3–6)

5.1 **Facts vs reading.** Facts panel shows only validated items: a ticker when the company is named in
    the headline/lede AND (after 2.6) the QID's ISIN matches; a CVE only when validated. Everything the
    model inferred (catalyst, price read, control mapping, "required action") moves under "Prism's
    reading" with `[n]` citations (`lens_cites` exists, in shadow) — never under "Facts".
5.2 **Cyber validation source (founder decision):** NVD CVE API and CISA KEV as *reference lookups*
    (like the securities master) — not as record feeds, which stays banned. Without it, drop the
    "KEV listed" badge.
5.3 **Ticker relevance**: one Jev noul "is this story about <company>?" per candidate ticker (~$0.00002);
    gold = 100 labels on top of `gold_company_links.jsonl`.
5.4 **Health and Policy lenses, built properly**: extraction fields (Health: condition, drug/device,
    regulator — CDSCO/ICMR/FSSAI/WHO — action: approval/recall/advisory/outbreak, place, counts;
    Policy: instrument — bill/act/rule/notification/judgment — issuing body, stage, effective date, who is
    affected, primary document link from 2.2), classifier `role_interests` for both, brief prompts,
    `LensBriefs` slots. **Ship each only when ≥ 30 records/day qualify and lens-fact precision ≥ 0.9.**
5.5 **Show it** (the landing already says "The same facts, read for your work"): a lens desk page per
    lens (today's records the lens has something to say about, ranked by lens signals; Pulse stays the
    Markets board), the lens chip on a feed row only where the lens offers a reading, a per-lens morning
    email for Plus, and the counts on the landing ("n Markets readings today") read from live data, never
    written in copy.

---

## 7. When to add sources — the scale gate

A wave goes in only when all hold, then runs 48 h before the next:
1. Phase 1 live and tier precision ≥ 0.95 (weekly audit).
2. Per-source telemetry live (2.5).
3. The wave's feeds, in the first 48 h: snippet share < 20%, gate reject < 40%, zero future-dated items,
   no feed dominating > 15% of raw items (Prajavani is 17% today — cap its poll or accept it).
4. Balance covers ≥ 14 days at the projected rate.

## 8. Labelled data

| Set | Items | For | How |
|---|---|---|---|
| Compile `MGDmtLPZOdjy` | 300 responses already in (never compiled) | event identity | `tools/gold_crosslingual --compile` — free |
| Event identity, post-fix | 300 pairs, stratified by tier × language | Phase 1 exit | Jev pre-labels; 2 labellers confirm |
| Story pairs | 300 (half from `thread-link leads_to`, to get positives) | Phase 4 gate | after the founder's definition (4.4) |
| X attach | 100 + 50 recall sample | W4 gate | `tools/gold_xposts --sample` |
| Podcast clips | +50 (53 today) | clip gate 0.9 | `tools/gold_clips --sample` |
| Lens facts | 100 ticker relevance + 100 cyber facts + 100 Health/Policy fields each | Phase 5 gates | new `/label` kind `lens_fact` |
| Entity links | 200 QID links | 2.6 precision | new `/label` kind `entity_link` |

**Model labeller (founder instruction 2026-10-01).** Labels are now produced by a model
labeller account — "Claude Opus 5.5 (model labeller)", `claude-opus-5-5@labeller.invalid`,
qualified by grant, its labeller note saying the labels are machine judgements — through the
real `/label` API, blind to the verifier's answers. First set: the 300 attach pairs (S 161,
D 90, F 41, unsure 8). Model labels share blind spots with Jev; a human audit sample per set
stays the check on both. Next sets: 100 gist-only candidates at 0.65–0.85 (a read of 22 says
~91% same at ≥ 0.75), 100 record-merge pairs at 0.75–0.85, 200 entity links (2.10).

≈ 1,300 items. Pairs take ~20–40 s each with the Jev pre-label shown, so ~10–12 labeller-hours per
labeller, two labellers for agreement. The labeller workspace, qualification and hidden checks already
exist; two kinds are new.

## 9. Founder decisions needed

1. Restart now (A) or after Phase 1.1 (B). Recommend A.
2. Record = one happening, follow-ups become story members (recommended; matches the verified tier's
   definition and the label guide).
3. NVD CVE API + CISA KEV as validation lookups (not feeds) — yes/no.
4. Health and Policy: build now (Phase 5.4) or after Markets/Cyber facts are fixed.
5. Monthly LLM budget for the source waves (~$210–250/month projected at 5,500 articles/day).
6. Story definition on the six contested classes (Phase 4.4).
7. X: go live after the 100-label gate; add the per-lens handles.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Verifier makes records stricter → the reader sees more, smaller records until stories are verified | 1.1 writes the story edge at the same time; record page shows "Earlier in this story" from `leads_to` |
| Jev outage → every fuzzy match becomes a new record | same as the verified tier today: timeout = new record; repair tool re-judges later |
| Repair detaches break shared links / SEO | dry-run CSV; 308 for emptied records; sitemap excludes |
| New UA still blocked from Railway egress | per-feed check from the worker before enabling |
| Source waves raise cost | telemetry + gate 4; each wave ~+$0.5–1.5/day at $1.3/1k |
| Labellers disagree (κ 0.3–0.4 before) | founder definitions first, adjudicate disputes, Jev as a third opinion |


## 11. Case study and product vision (2026-10-01) — to be refined into a structured plan

### The Flydubai FZ1073 story, end to end
Ground truth (public reporting): 30 Sep, FZ1073 Dubai → Tel Aviv; the Omani co-pilot stabbed
Captain Smit Machchhar; the jet fell 14,000 ft in under 30 s; the captain opened the cockpit
door, passengers subdued the co-pilot, landing in Tabuk (174 aboard); Saudi arrest. 1 Oct:
surgery, airlift to Abu Dhabi, UAE investigation, flydubai suspends Israel flights; reactions
(Netanyahu, Modi, Trump, Murmu), Gujarat award. ~10–15 happenings.

| Stage | Was (morning) | Now | Left |
|---|---|---|---|
| Entity names | pilot = 15 entities, flydubai 2 | 1 (+4 one-offs), flydubai 1 | context linking (2.7–2.10) |
| Records | 190 articles → 70 records; old rules glued reactions into a 59-article English record; 61% of articles founded records under the 0.85 floor | floor 0.65 for proposals, record-as-it-stands, repair, merges ≥ 0.85 | pre-fix duplicates at 0.70–0.84 (airlift ×5, UAE probe ×6, award ×5, Modi ×7) |
| Time | processing order (all 10-01 08:18–12:14) | first report order (09-30 07:30 →) | — |
| Stories | ~25 stories, split by language | split by facet (17/8/7/6/6/6) | threads (4.5) |
| Search | 20 flat siblings | grouped under the story | story-first results |

### Architecture — the data layers (each with its own judge, measured by labels)
Report → **Mention** (entity + role + QID, 2.7–2.10) → **Record** (one happening, verified, all
languages) → **Thread** (later developments, by first report) → **Story** (the developing story,
made of threads, no size cap). Rules that hold: candidates are proposed by cheap signals and
decided by the judge; floors come from labels, never from 0.5; star-attach, never chain; every
destructive repair is dry-run first, canaried, journalled where possible.

### The product a reader sees
- **Story page**: a timeline by day with times — each entry one happening with "n outlets ·
  k languages"; reactions under what they react to; threads as sections; "new since you last
  read".
- **Record page**: every report of one happening, across languages; where figures disagree
  (174 vs 180 passengers) both are shown with who said which.
- **Entity page**: one person across languages and scripts, roles over time.
- **Search**: stories first, then records (grouping shipped 0.0.122.0).
- Lenses sit on top of verified records only.

### Quality loop
Daily `/admin` panel: residual duplicate rate, wrong-attach rate (sampled and labelled by the
model labeller; human audit sample weekly), name-variant rate, story fragmentation (records per
story, stories per happening cluster), time skew (first_seen − first_published). A release that
moves any of them the wrong way is held.

### Next, ranked
1. Story → threads (4.5) — what readers see; lets the record merge stay strict at 0.85.
2. Context-based entity linking (2.7 → 2.8 → 2.9 → 2.10).
3. Labels: gist-only floor (100), record-merge band (100), entity links (200).
4. Re-judge the 0.15–0.5 repair band and the 0.70–0.84 duplicate records with the
   record-as-it-stands judge and the new labels.
5. Partition timing after restarts (4.8); story slug identity (4.7).

### Open founder decisions
- Thread names: generated per story, or a fixed vocabulary (Incident · Reactions ·
  Investigation · Legal · Honours · Politics)?
- Where a reader lands from search/feed: the story (timeline) or the record?
- Human audit cadence for the model labeller's sets (proposal: 10% of each set, two founders).
