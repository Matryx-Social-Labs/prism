# Plan: stories you can follow, breaking you can trust, roundups that cite

**Asked (2026-10-01):** audit where the product goes wrong end to end and redesign it where the design is
wrong. Scope: the best canonicalization at each stage; stories that read as a timeline; facets of a developing
story; pinned stories (US–Iran war, Russia–Ukraine, the flydubai flight) and breaking news; articles that report
several happenings (Asian Games roundups) cited per passage. Also evaluate `data-accuracy-and-sources.plan.md`.
**Complexity:** Large. Six phases (A–F), about 3 weeks. Phase A is small and can ship first.
**State measured:** prod DB, read-only, 2026-10-01 15:30–18:30 UTC (main 2ad5bd7 + #261, `PRISM_EVENT_VERIFY=confirm`
since 09:25 UTC). Facts checked online. One offline prototype replayed 12,941 real records ($0.36).
Scripts are in `quito/.context/audit2/` and become `tools/` in Phase B.

---

## 0. In one paragraph

The record layer is nearly right, but it splits one happening across several records about 14% of the time. The
story layer is wrong by design. It re-partitions every record from scratch every 15 minutes with Leiden, which
(a) cannot grow a story past ~25 records, (b) compares records by the weak raw-text embedding, (c) has no identity
of its own, and (d) only materialises a story while it trends. So the Iran war (360 records in three weeks) never
existed as a story for more than a day, and flydubai is 35 fragments. **Replace it with persistent stories that
records join at birth.** The same propose → judge pattern that fixed records does this: the stories of a record's
gist neighbours are proposed, the judge confirms "part of this story?", and the record attaches to one story (star
to the story, never chained). The prototype put 92% of flydubai into one story (from 13%) at ~0.94 attach
precision, for ~$0.05/day. Facets come from the same judge call as a fixed development kind (event,
investigation, response, people, reactions, politics, impact…), counted. Breaking and pinned "developing" stories
are computed from counted outlet arrivals by first-publish time, with hysteresis and a founder override. Roundups
stop becoming junk records: they are split into cited passages that attach to the records they report.

---

## 1. What the product is for (the bar every change is measured against)

From `PRODUCT.md` and the founder decisions: Prism is **India's verifiable news record**. The reader jobs:

1. **What happened?** One record per happening, with every outlet and language that reported it, counted. The
   record is the evidence unit, and duplicates break its counts ("one source" on a happening six outlets reported).
2. **Follow the story, not the headlines.** A developing story as a dated timeline, with its facets, and what is new
   since the last read.
3. **What matters right now?** What is breaking, and which long-running stories readers come back for.
4. **Can I check it?** Counts, verbatim quotes, named outlets, the passage that says it. Nothing invented, and
   provisional things say so.

Lenses read verified records. They come after 1–4 are right.

---

## 2. What was measured (2026-10-01)

### 2.1 Records (one happening)
| Finding | Number | How |
|---|---|---|
| Articles founding a new record since the confirm flip (09:30–15:30 UTC) | 1,196 of 1,641 (73%) | `event_memberships.match_type` |
| New records whose best refused candidate scored 0.65–0.85 | 218 (143 at 0.75–0.85, 75 at 0.65–0.75) | `event_match_verdicts` mode `confirm` |
| My blind read of 40 of those pairs (model labeller) | **31 same happening**, 4 follow-ups, 2–3 different, 1 roundup | `.context/audit2` |
| ⇒ duplicate records being created now | **≈14% of new records** (~170 in 6 h) | — |
| Why | gist-only candidates need 0.85 (`clustering.py:797-803`); the judge scores paraphrased reports 0.68–0.83 | e.g. "Rubio ordered Iranian delegation to leave" 0.83 / 0.81 against two records of the same happening |
| Examples that survive merges | IRGC drone seizure of 27 Sep = 4 records (online: one IRGC claim, Remus 600); flydubai airlift ×5, UAE probe ×5, Gujarat award ×6, Modi praise ×6 | titles + verdicts |
| Data hygiene | records dated in the future (`first_published_at` 11-04, 12-04); 95 merged stories still `status='active'` | `events`, `stories` |

### 2.2 Stories (the developing story)
| Finding | Number |
|---|---|
| Iran-war records (3 weeks, title match) in the current Leiden run | 360 records in **198** groups; never a story for more than ~1 day (`stories`: 5–11 members, all dormant) |
| Asian Games / flydubai / Russia–Ukraine | 387 → 152 groups · 58 → 26 · 179 → 94 |
| `stories` table | 68 active, mean 6.4 records, max 20; the Iran war is not in the top 40 trending |
| Live flydubai story page | 18 of ~115 records, "Provisional grouping · No chronology implied"; the incident itself (22 articles) sits in another story |
| Identity | slugs no longer match content: `netanyahu-calls-accusations-of-genocide-in-gaza-…` holds flydubai; `guntur-district-police-vakul-jindal-…` holds a CBFC row |
| Representation | partition, trending and threads use `events.embedding`, the founder's raw first 1,200 chars (AUC 0.46 on hard pairs). The gist (0.91–0.99) is used only by the record verifier |
| Retrieval is NOT the limit for big stories | a sibling is in a record's 4 nearest neighbours 97–100% of the time (raw and gist). Gist neighbourhoods are cleaner: Iran precision@25 0.57 → 0.76 |
| Why Leiden fragments | CPM keeps a group only at internal density ≥ γ. With mutual-kNN k=4, a story is capped near n ≈ 1 + degree/γ ≈ 25 (story-layer research note, leidenalg docs). No k or γ yields a 100-record story without topic merges |

### 2.3 Prototype: persistent stories, judge-confirmed (offline, 24 Sep–1 Oct, 12,941 records, 8,235 calls, $0.36)
Each record in first-report order: the stories of its ≤12 nearest earlier records by gist (distance ≤ 0.11) are
proposed (≤3). One Jev call asks per story "part of the same specific developing story?" against the story's
founding report, its latest report and its two members nearest the record. Attach at ≥ 0.70, else found a story.

| Known story | Leiden today: groups / share in largest | Prototype |
|---|---|---|
| flydubai FZ1073 (102 by title) | 35 / 13% | **8 / 92%** (one story of 103; its "foreign" members are flydubai records my regex missed) |
| Iran war (129) | 72 / 7% | 48 / 44% |
| Russia–Ukraine (25) | 15 / 12% | 11 / 36% |
| Asian Games (214) | 97 / 8% | 109 / 7%. Medal by medal, no record is a "development" of another; per-sport stories form (kabaddi 22, squash 18). **Needs an umbrella anchor** (§4.3) |

- **Attach precision**, blind read of 60 random attaches: 55 right, 2 wrong (a Bay of Bengal depression joined to
  northern Kerala rain; two unrelated Cabinet decisions from the same day), 3 borderline ⇒ **0.92–0.97**.
  Several attaches were same-happening duplicates (Bezos Earth Fund, Indirapuram fire, the red-sanders arrest), so
  the story layer also exposes the record gap in §2.1.
- **Largest stories:** the CEC / SIR row (131, correct as a running dispute, but the row is still spread over ~8
  stories), flydubai 103, the Odisha/AP deep depression 88, Iran ceasefire and Hormuz 61.
- **Facets:** clustering inside a story gives same-happening groups of 3–5 records, not facets. That makes it a
  merge-candidate source, not a facet source. **A fixed development kind**, one Choice question per record, gives
  readable facets: flydubai event 13 · investigation 12 · response 9 · people 19 · reactions 42 · politics 7.
  Iran: diplomacy 31 · impact 16 · response 9 · reactions 4. $0.003 per 100 records.

### 2.4 Front page, trending, breaking
- The feed unit is the record. The visible order is `source_count` desc (`web/src/lib/chart.ts:12-18`): the lead is
  whichever record has the most outlets, however old. No breaking, pinned or developing concept exists. The
  classifier's `fast_lane` answer is computed and ignored (`classification/decide.py:149-151`).
- Trending velocity counts outlets by **membership creation time**, not publish time (`correlation/trending.py:201,234`),
  so a backlog looks like a surge. Candidates decay by `exp(-0.03·days)` (half-life ~23 days, `trending.py:216`).
- Calibration on our own arrivals (first article per outlet per record, by publish time, 16 days):

  | Bar | Records/day (full ingest days) |
  |---|---|
  | ≥ 5 outlets within 2 h of first report | 1–14 |
  | ≥ 5 within 3 h and ≥ 2 languages | 2–16 |
  | **≥ 8 within 2 h** | **0–3** (hockey semi 14, Kohli 15,000 runs 14, kabaddi gold 10, Pune drowning 9) |

  flydubai broke on 30 Sep while ingestion was paused, so it cannot measure latency.
- Online: Wikipedia's Current events portal lists **Ongoing: Iran war · Russo-Ukrainian war** and filed
  "Flydubai Flight 1073 hijacking attempt" under 30 Sep. That is a free, human-curated list of running stories
  with QIDs, usable as an anchor source (CC BY-SA).

### 2.5 Articles reporting several happenings
- An article belongs to exactly one record (`uq_event_memberships_article`, `common/models.py:203-209`); extraction
  returns one headline, summary and date. Roundups become their own junk records ("India achieves further success
  at the Asian Games", "India win sailing, wrestling silver; cricket and hockey teams advance"), or the classifier
  drops them as `not_news` (live blogs, digests), losing the coverage.
- Size: ~1.1% of records are roundup-shaped by title (124 of 11,019 in 7 days). Small, but they carry most of the
  minor results (medals, district news), and they decide whether an umbrella story is complete.

### 2.6 Facts checked online
| Ours | Public reporting | Verdict |
|---|---|---|
| flydubai: "saves 180 passengers" (6 outlets) beside "174 lives" | 174 aboard, Tabuk landing, surgery, airlift ([Outlook](https://www.outlookindia.com/international/flydubai-hijack-smit-machchhar-cockpit-incident-explained), [i24](https://www.i24news.tv/en/news/israel/artc-flydubai-pilot-smit-machchhar-undergoes-surgery-after-cockpit-stabbing)) | figures disagree. Show both with who said which; never pick one |
| 4 records "Iran claims capture/seizure of US underwater drone" (27 Sep) | one IRGC claim, Remus 600, 27 Sep; a different seizure on 8–9 Sep ([Malay Mail](https://www.malaymail.com/news/sports/2026/09/27/iran-guards-claim-capture-of-us-underwater-drone-in-strait-of-hormuz/236784), [Defense News](https://www.defensenews.com/news/your-military/2026/09/09/iran-says-it-captured-us-submarine-drone-in-strait-of-hormuz/)) | 4 → 1 record; the 8 Sep seizure must stay separate (a good judge test) |
| "India enter hockey final after beating Pakistan 4-3" — one record, 16 articles | 1 Oct semi, 4-3, last-minute goal ([Hockey India](https://www.hockeyindia.org/news/indias-last-minute-goal-takes-them-to-asian-games-2026-final-with-a-thrilling-4-3-win-over-pakistan)) | right |

---

## 3. Where we go wrong (root causes, ranked by harm to the reader)

1. **Stories are recomputed, not kept.** A global partition every 15 minutes, reconciled to `stories` by overlap
   heuristics (member overlap, cast Jaccard, IDF cast, hero anchor), only while a story trends, dormant after 24 h.
   Identity, labels and slugs drift, and mega-stories cannot exist.
2. **The story boundary is a density cut on a similarity graph.** Story-level questions ("is this the same
   developing story?") are answered by a topic-level instrument with a size cap. The judge that answers the real
   question exists and is cheap, but it isn't used for stories.
3. **Duplicate records (~14% of new records).** One fixed floor (0.85) for gist-only candidates, where the judge's
   scores for paraphrases sit at 0.68–0.85. The cost lands on counts: "single source" shown on happenings that six
   outlets reported, and breaking/heat signals split across copies.
4. **No notion of "now".** The front page ranks by total outlets, trending by ingest-time velocity. Breaking,
   developing and pinned don't exist. `fast_lane` is ignored.
5. **One article = one happening.** Roundups and live blogs either pollute or vanish, and there is no passage-level
   citation.
6. **The weak representation is still in the story layer.** The raw-chunk embedding, though the gist is in hand.
7. **Hygiene:** future-dated records, merged stories left active, story labels taken from a hero that no longer
   leads.

---

## 4. Target architecture

```
RSS / X / podcasts
   │
Article ──extract──▶ form: single | roundup | live_blog | opinion | explainer      (Phase E)
   │ single                                   │ roundup / live_blog
   ▼                                          ▼
   one happening                           segments: verbatim sentences per happening
   │                                          │
   ▼   propose (url, cve, title, entities, gist kNN)  →  judge same_happening   (live)
RECORD  ◀────────────────────────────────── segment mentions (cited; shown, not counted as outlets)
   │   0.65–0.85 band → escalation judge (Phase A); merge pass over in-story clusters
   ▼   propose (stories of gist neighbours, verified follow-ups, running-story scope)
STORY   ← judge part_of_story + facet kind (same call), star-attach      (Phase B)
   │   persistent from birth; one story per record; hidden until ≥2 records & ≥2 outlets
   │   kind = story | running (scope line, optional QID, window, facet list)
   ▼
SURFACES  Breaking (record heat) · Developing (story heat, pinned) · Feed (records; a pinned story = one card)
          Story page (timeline by day, facets, latest, new since last read) · Record page (part of story · facet)
```

Rules carried over: cheap signals propose, the judge decides. Floors come from labels, never 0.5. Star-attach,
never chain. Every repair is dry-run → canary → journalled. Counts by first-publish time, never ingest time.

### 4.1 Layer contracts
| Layer | Unit | Identity | Decided by | Measured by |
|---|---|---|---|---|
| Record | one happening | `events.id`, founder fixed | judge same_happening (+ escalation in the band) | residual duplicate rate on new records (sampled, labelled) ≤ 3%; wrong attach ≤ 2.5% |
| Story | a developing story or running situation | `stories.id` + frozen slug at birth; merges 301 | judge part_of_story vs anchor/scope + latest + 2 nearest | attach precision ≥ 0.9; fragmentation of watched stories; B³ on a story-centric sample |
| Facet | a development kind inside a story | fixed vocabulary, or the running story's facet list | Choice in the same judge call | facet accuracy ≥ 0.85 on 100 labels |
| Breaking | a record's arrival burst | record id | counted rule (§D) | precision on must-hit / must-not lists, firings per day, minutes to fire |
| Developing | a story's sustained heat | story id | counted EWMA + hysteresis + founder override | pinned days per story, flapping count |

### 4.2 Story granularity (the definition the judge is given)
A story is **one specific developing situation**: an incident and everything that follows from it (flydubai:
attack → landing → probe → honours), or one ongoing conflict, dispute, case, campaign, tournament or disaster (the
Iran war, the CEC/SIR row, the 2026 Asian Games). It is never just a shared country, party, person, sector or topic.
Different crimes, cases, bills, companies' results or days' weather are different stories. This is the question the
prototype measured, and the founder ratifies it (decision 1).

### 4.3 Running stories (umbrellas: wars, tournaments, elections, long disputes)
A `kind='running'` story has a founder-written **scope line**, e.g. "The 2026 Iran war: military, diplomatic and
economic developments" or "The 2026 Asian Games, Aichi-Nagoya, 19 Sep–4 Oct". It also has an optional `anchor_qid`
(Iran war, Q27016751 for the Games), an optional window, and an optional facet list (Asian Games: the sports). The
judge reads the scope instead of a founding report. That is what makes a medal in squash part of the Games story,
which the prototype could not do without it. Created by the founder (`tools/story_anchor.py`). Prism suggests
candidates from sustained heat and from Wikipedia's "Ongoing" list; it never creates one on its own.

---

## 5. Phases

### Phase A — one happening, one record (2–3 days)
| # | Change | Where | Check |
|---|---|---|---|
| A1 | **Escalation in the 0.65–0.85 band** for gist-only candidates: a second judgement with more context (both ledes, ~600 chars each, plus headlines and times). Bake-off on 150 labelled band pairs (model labeller, blind): (i) Jev with ledes, (ii) Jev order-swapped and averaged, (iii) gemini-3.1-flash-lite with minimal reasoning, (iv) one mid-tier chat model. Ship the cheapest at P ≥ 0.95, R ≥ 0.8. Flag `PRISM_EVENT_ESCALATE=off\|shadow\|live` | `correlation/verify.py` (`escalate()`), `correlation/clustering.py:790-803`, `common/config.py` | `tests/test_verified_tier.py` cases from the labelled band; shadow 24 h, then the dup sample |
| A2 | **Merge the backlog** of the band: `tools/merge_duplicates.py --band 0.65-0.85 --escalate` over 14 days, dry-run CSV → canary 50 → rest | `tools/merge_duplicates.py`, `correlation/merge.py` | journal; my read of 40 merges |
| A3 | **Future-date guard**: an article `published_at` > observed + 1 h falls back to `observed_at` (old plan 2.4) | `ingestion/base.py` | unit test; prod count of future records → 0 |
| A4 | **Stories hygiene**: merged ⇒ dormant, in the reconcile and once in SQL | `correlation/trending.py`, one migration | 95 → 0 |

**Exit:** new-record duplicate rate ≤ 3% on a daily sample of 50 (from ~14%), wrong-attach ≤ 2.5%. Cost
≤ $0.5/day (≈ 250–400 band cases/day).

**Phase A status (2026-10-01, 0.0.124.0).** Founder: "yes" to the plan (recommended answers taken on §10).
- Labels: 160 refused candidates since the confirm flip, blind (model labeller): 0.75–0.85 → 51/60 same,
  0.65–0.75 → 33/60, 0.55–0.65 → 21/40. `.context/audit2/band_labelled.json`.
- Bake-off (same 147 decided pairs): flash-lite P 0.79, glm-5.3-flash 0.88, haiku-4.5 0.76, gemini-3.5-flash
  (medium reasoning, $0.004/call) 0.85. **Jev on the opening texts, first reading ≥ 0.65, second ≥ 0.80, not a
  later development: P 0.981, 52 taken, recall 0.49 of the band's duplicates, $0.00005/call** → shipped as
  `PRISM_EVENT_ESCALATE` (A1). The other half of the band's duplicates no cheap judge separates from
  follow-ups at P ≥ 0.95. They are left to the story layer (B), which groups same-happening records as one
  timeline entry. **Exit revised: duplicate rate ≈ 14% → ~8% from A; ≤ 3% is not reachable with today's judges.**
- A3 dropped: `correlation/chronology.FIRST_PUBLISHED` already windows publish dates (prod has 0 future-dated
  records). The odd dates were raw article timestamps, so Phase D must count with the same window.
- A4 fixed: `_update_story` reactivated stories merged earlier in the same pass.

### Phase B — stories that persist (week 1–2), the core redesign
| # | Change | Where |
|---|---|---|
| B1 | Schema: `stories` += `anchor_event_id`, `kind` (`story`\|`running`), `scope`, `anchor_qid`, `window_start/end`, `facets jsonb`, `first_published_at`, `last_development_at`, `visible` (≥2 records and ≥2 outlets). New `story_events(story_id, event_id UNIQUE, method found\|judge\|merge\|founder, noul, facet, facet_conf, created_at)`. `member_event_ids` is derived for one release, then dropped | `db/versions/*`, `common/models.py:305-330` |
| B2 | **Assign at record birth**, in the analysis sweeper (outside the match lock, like `link_event_threads`, `consumer.py:330-366`). Candidates: the story of the verified follow-up target (`_link_follow_up`, `consumer.py:277-312`); the stories of ≤12 gist neighbours within 14 days at distance ≤ 0.11; running stories whose QID or anchor entity the record names. One Jev call: `part_of_story` (Noul) per candidate (≤3) + `facet` (Choice). ≥ τ (0.70 to start, set from labels) → attach; else found a story. An article attached to an existing record inherits the record's story: no call | new `correlation/stories.py`; question text beside `SAME_STORY` in `correlation/verify.py` |
| B3 | **Story merge pass** (hourly): story pairs with ≥2 cross-proposals at q ≥ 0.5, or a verified follow-up link crossing them → judge anchor+latest vs anchor+latest → merge, oldest survives, slug 301, journalled. Creating a running story absorbs in-scope stories the same way | `correlation/stories.py`, `tools/story_anchor.py` |
| B4 | **Backfill 30 days** in first-report order (the prototype, made a tool): `tools/assign_stories.py --days 30 --dry-run` → report → `--apply`. ≈ 25k records ≈ $0.8 | `tools/assign_stories.py` |
| B5 | **Delete what this replaces:** the global Leiden story boundary, `reconcile_stories`' overlap/cast/hero heuristics, `_converge_existing`, the BFS fallback, the veto overlay (off since 07-30). Keep `partition.py`'s CPM only if Phase C uses it for merge candidates; otherwise delete | `correlation/partition.py`, `correlation/trending.py`, `correlation/threads.py`, `worker/__main__.py:92-121` |
| B6 | Labels and slugs: the slug comes from the anchor's English headline at birth, frozen. The label is the anchor headline, or the founder's title for running stories. Never an outlet name | `correlation/stories.py` |
| B7 | Gate tool `tools/audit_stories.py`: story-centric sample (200 records; the model labeller rebuilds each one's true story), B³ P/R, fragmentation of watched stories, 60-attach precision. Weekly on `/admin` | `tools/`, `api/routes/admin_metrics.py` |

**Exit (gate to show stories as verified):** attach precision ≥ 0.9; B³ precision ≥ 0.85 at recall ≥ 0.7; flydubai = 1
story, Iran war ≤ 2 once its running story exists; human audit of 10% of the model labels agrees ≥ 90%. Then
`STORY_BOUNDARY_STATUS = "verified"` (`common/stories.py:11`). Cost ≈ 1,500 calls/day ≈ **$0.05/day**.

### Phase C — the story page readers follow (week 2)
Phone first, following DESIGN.md (counts in mono, line states, 640 column, no invented text):

```
DEVELOPING · DAY 2                                   UPDATED 12M AGO
Flydubai FZ1073: co-pilot attack, emergency landing in Saudi Arabia
103 records · 64 outlets · 9 languages · first reported 30 Sep, 13:03 IST
[coverage bar]
Latest ───────────────────────────────────────────────
 21:00  India to review aviation safety protocols …        Response · 3 outlets
 19:19  Co-pilot underwent radical indoctrination: Netanyahu  Investigation · 6 outlets
New since you last read: 7
[All 103] [The event 13] [Investigation 12] [Response 9] [People 19] [Reactions 42] [Politics 7]
WED 1 OCT ────────────────────────────────────────────
 …each entry: time · record headline · facet · "n outlets · k languages"; single-outlet entries
   behind "+18 more on this day"
TUE 30 SEP ───────────────────────────────────────────
 13:03  Commercial flight from Dubai to Israel diverted to Saudi Arabia   The event · 15 outlets
Where reports differ: "174 aboard" (k outlets) · "180 passengers" (m outlets)      [later, needs figures]
Rail (desk): outlets per day · languages · who is in it · related stories
```

| # | Change | Where |
|---|---|---|
| C1 | API `GET /api/v1/stories/{slug}`, with `/trending/{slug}` kept as an alias: timeline by IST day (from `story_events` + records), facets with counts, latest 3 (≥2 outlets preferred), counts, `boundary_status` | `api/routes/trending.py:316-425` → `api/routes/stories.py`; `api/schemas.py:701-722`; contract test `tests/test_trending_contract.py` |
| C2 | Story page: facet chips filter the timeline; "new since you last read" from a localStorage last-visit time (no account); dashed "Provisional" until the gate | `web/src/app/trending/[slug]/`, `StoryTimeline.tsx` (already groups by IST day) |
| C3 | Record page: "Part of: <story> · <facet>" and "Earlier / later in this story" (its timeline neighbours), replacing the provisional related list | `StoryView.tsx:644-656`, `api/routes/events.py:571-584` |
| C4 | Running-story page = the same page; facets are the scope's facet list (sports for the Games); "Day N" from the window start | same |
| C5 | Search: story first (grouping shipped in 0.0.122.0) | `api/routes/search.py` |

### Phase D — breaking and developing (week 2)
**Counting.** Each outlet counts once per record, at its first article's publish time; ownership groups later
(with wire detection, old plan 2.3). X posts never count.

**Breaking** (record): fires when, within 3 h of first report, ≥ **8** outlets (start; tune to 1–3/day by replay)
and ≥ 2 languages have reported it, **and** it was not anticipated (its story had < 3 outlets in the previous
24–72 h). A record of a pinned story never takes the banner; it becomes that story's latest development. Exit: 6 h
max, or < 2 new outlets in 60 min for 3 ticks after the first hour. Slots: 1 (2 only for a second, different
story). Copy is counts only: "14 outlets · 8 languages in 2 h".

**Developing / pinned** (story): heat H = EWMA (half-life 36 h) of distinct outlets per IST day. Pin when H ≥ 10,
≥ 3 outlets on 3 of the last 4 days and ≥ 2 languages. Unpin when H < 5 or there is no ≥ 3-outlet record for 48 h.
Minimum 24 h pinned and 24 h before re-pinning. ≤ 3 slots. Founder override `story_pins(story_id, mode
pin|never, until, by)`.

| # | Change | Where |
|---|---|---|
| D1 | `correlation/heat.py`: record arrivals and story heat every 10 min; state on `events.breaking_until` and `stories.heat`, `pinned_until` | worker schedule `worker/__main__.py` |
| D2 | Replay calibration `tools/replay_heat.py --days 16`: firings/day, minutes to fire, must-hit / must-not lists (30 each, model-labelled: hockey semi, Kohli, Pune drowning; match previews, earnings, scheduled verdicts) | `tools/` |
| D3 | Front page: Breaking strip (≤1–2) + Developing cards (≤3: label · Day N · latest 2 developments with counts · "+n today"). Records of a pinned story collapse into its card (no double listing). The chart below stays `source_count`-ordered but within the last 24 h | `FrontPage.tsx`, `Chart.tsx`, `lib/chart.ts`, `api/routes/feed.py` |
| D4 | Fix trending velocity to publish time; drop the 23-day decay; `/trending` lists stories by heat | `correlation/trending.py:190-235` (or its replacement) |
| D5 | Founder controls on `/admin`: pin / never / unpin, with an audit row | `api/routes/admin_controls.py` |

### Phase E — articles that report several happenings, cited (week 3)
| # | Change | Where |
|---|---|---|
| E1 | Extraction adds one field, `form` (single · roundup · live_blog · opinion · explainer · reaction). Only for roundup/live_blog, a **second** cheap call over numbered sentences returns `happenings[]` (headline_en, summary_en, sentence_ids, role report\|mention). The main prompt and its cache prefix change once | `enrichment/schemas.py:109-135`, `enrichment/` prompt |
| E2 | `article_segments(id, article_id, seq, headline_en, summary_en, sentence_ids int[], quote text, gist_embedding, role)` + `event_mentions(segment_id UNIQUE, event_id, noul)`. The quote is verified verbatim in the article (reuse `enrichment/claims.py`). Offsets come from our splitter, never the model | migration, `common/models.py` |
| E3 | Matching: each `report` segment goes through the same propose → judge against existing records (`verify.judge` with a segment block). v1 never founds a record from a segment; it retries once at +6 h. A roundup gets **no** membership, so no junk record. Live blogs: `LiveBlogPosting.liveBlogUpdate` items are segments (TOI and IE carry it), so the gate stops rejecting them | `correlation/consumer.py`, `classification/decide.py:108-115` |
| E4 | Counting and display: the coverage bar counts memberships only. The record shows "6 outlets · also in 3 roundups"; the record page lists "Also reported in roundups": outlet · the verbatim sentences · "Open at the passage ↗" | `api/routes/events.py`, `StoryView.tsx` |
| E5 | Repair: dissolve existing roundup records (dry run; their articles become segments) | `tools/repair_roundups.py` |
| E6 | The Asian Games example: the running story (scope + window + sports facet list) gathers the hockey record, the swimming record and every roundup passage that reports them, each cited to its sentences. "Asian hockey" articles that only name-check the Games are `mention` segments: shown on the record, not attached as reports | — |

**Gate:** shadow on 100 labelled roundups/live blogs per language family; segment-attach precision ≥ 0.9.

### Phase F — the quality loop (alongside, on `/admin`)
Daily, each figure sourced and counted:
- duplicate-record rate (50 new records/day, model-labelled)
- wrong-attach rate
- story attach precision (50/day)
- fragmentation of watched stories (founder list)
- breaking firings and precision; pinned days and flaps
- time skew (first_seen − first_published)

The model labeller labels; a 10% human audit checks it. A release that moves any figure the wrong way is held.
Existing infra: `api/routes/admin_metrics.py`, `/label` kinds (add `story_attach`, `band_pair`, `segment`).

---

## 6. The existing plan (`data-accuracy-and-sources.plan.md`) — evaluated

| Phase | Status | Verdict |
|---|---|---|
| 0 restart fixes | shipped 0.0.117.0 | done |
| 1 every attach verified | live 0.0.118–0.0.123 | right. Its residual is the gist-only band → **Phase A here** (replaces "label more before lowering the floor") |
| 2.1 keep fetched signals (canonical, dates, author, outbound links) | open | **keep, raise.** Feeds D (honest counts) and E (live-blog structure) |
| 2.2 primary-document key | open | keep: an exact record key, and the X URL tier |
| 2.3 wire detection | open | **keep, raise:** breaking must not fire on one PTI copy run by 8 outlets |
| 2.4 future-date guard | open | **now** (A3) |
| 2.5 per-source telemetry | open | keep; gate for Phase 3 waves |
| 2.6–2.10 Wikidata / context entity linking | open | keep, after B. Only `anchor_qid` for running stories is needed earlier (manual) |
| 3 source waves | gated | keep gated. More sources mean more duplicates, so after A |
| 4 verified stories / threads | partly prototyped | **replaced by B–C.** Kept: star-attach, never transitive, outlets never cast, founder story definition (4.4 → decision 1). Changed: threads ≠ Leiden communities. Facets are development kinds; in-story clusters feed merges. 4.7 (slug identity) and 4.8 (partition sleep) disappear with the global partition |
| 5 lenses | open | keep, after B/C: lenses read verified records |
| §11 vision | — | this plan is its structured version; the layer list there gains Segment and loses Thread-as-Leiden |

---

## 7. Patterns to mirror
| Category | Source | Pattern |
|---|---|---|
| Judge questions | `correlation/verify.py:53-74` | literal question constants that name the traps; Noul per candidate; one call per item |
| Fail-safe | `verify.py:47-50` | judge timeout or error = no match, the item founds its own record/story; never blocks ingest |
| Repairs | `tools/repair_attaches.py`, `tools/merge_duplicates.py` | `--dry-run` CSV → founder read → `--apply --limit` canary → rest, journalled |
| Logging | structlog `logger.info("decision", …)` | never pass `event=` as a kwarg (structlog trap) |
| Data access | `sqlalchemy.text()` in `correlation/`, Alembic in `db/versions/` | raw SQL with explicit casts for pgvector |
| Tests | `tests/test_verified_tier.py`, `tests/test_trending_contract.py`, `web/src/**/*.test.tsx` | regression tests mutation-verified; contract test keeps Python ↔ TS fields equal |

## 8. Cost
| Item | Per day |
|---|---|
| A1 escalation (≈250–400 band cases) | ≤ $0.5 (bake-off decides; Jev variants ≈ $0.02) |
| B2 story judge + facet (≈1,500 records) | ≈ $0.05 |
| B3 merge pass | < $0.01 |
| E segments (≈ 2% of articles × ~5 happenings) | ≈ $0.05 |
| One-off: A2 merges + B4 backfill + E5 repair | ≈ $2 total |

About +$0.6/day on today's ≈ $4–8/day. The experiments for this plan cost $0.37; balance $37.57 before them.

## 9. Risks
| Risk | Mitigation |
|---|---|
| Mega-stories absorb neighbours (the CEC row took a Kerala student clash) | judge reads anchor/scope + latest + 2 nearest; precision sampled daily; founder can split or move a record (`tools/story_anchor.py --move`) |
| Topic drift through "latest report" in the story block | measured at 0.92–0.97 with it. If drift shows, judge against anchor + facet-nearest only |
| Running stories become catch-alls | founder-only creation; scope line names the situation; window bounds dates |
| Escalation lowers precision | P ≥ 0.95 gate on labelled band pairs; shadow first |
| Breaking false alarms (wire copies, scheduled events) | conservative K, anticipation rule, wire detection (2.3), founder "never" pin, replay calibration |
| Backfill moves URLs | slugs frozen; merges 301; dry-run report first |
| Judge outage | record founds its own story; merge pass and backfill tool re-home later |
| Model labels share the judge's blind spots | 10% human audit per set; disagreements adjudicated by a founder |

## 10. Founder decisions needed
1. **Story definition** (§4.2): one specific developing situation, incident chains and running conflicts or
   tournaments included. Recommend yes.
2. **Facets as development kinds** from a fixed list (event · investigation · response · diplomacy · people ·
   reactions · politics · impact · explainer); running stories may define their own (sports). Recommend yes, over
   generated names.
3. **Anticipated events never get the breaking banner** (match results, earnings, scheduled verdicts); they show as
   their story's latest development. Recommend yes.
4. **Pinned slots:** up to 3 automatic + founder pin / never / unpin.
5. **Roundups:** shown and cited, counted separately ("6 outlets · also in 3 roundups"), not as outlets. Recommend yes.
6. **Escalation budget** ≤ $0.5/day for the 0.65–0.85 band.
7. **Running stories are founder-created** (one-line scope); Prism suggests from heat and Wikipedia's Ongoing list.
   First set: Iran war, Russia–Ukraine war, 2026 Asian Games, CEC/SIR row.
8. **Where a reader lands:** feed rows stay records with a "Part of <story> · Day N" chip; Developing cards and
   search go to the story.

## 11. Order
| Week | Ship |
|---|---|
| 1 | A1–A4 (A1 in shadow day 1, live after the bake-off); B1–B2 in shadow; B4 dry run |
| 2 | B3–B7, gate → verified; D1–D5; C1–C3 |
| 3 | C4–C5; E1–E6 (shadow → gate); F panel |
| then | old plan 2.1–2.5, 3 (waves), 2.6–2.10, 5 (lenses) |

## 12. Validation
```bash
uv run pytest -q                                  # backend (local DB only; conftest guard)
cd web && npm test                                # web
uv run python -m tools.audit_event_dups --survivors --days 1         # A exit: dup rate on new records
uv run python -m tools.assign_stories --days 30 --dry-run            # B4 report
uv run python -m tools.audit_stories --sample 200                    # B gate: B3, attach precision, fragmentation
uv run python -m tools.replay_heat --days 16                         # D calibration
```

## 13. Acceptance
- [ ] New-record duplicate rate ≤ 3%; wrong-attach ≤ 2.5% (daily sample)
- [ ] Story attach precision ≥ 0.9; B³ P ≥ 0.85 at R ≥ 0.7; flydubai one story; Iran war ≤ 2
- [ ] Story page shows the dated timeline with facets and "new since you last read"; boundary verified
- [ ] Breaking fires 1–3/day with must-hit recall ≥ 0.8 and must-not false alarms ≤ 1/week; Developing holds ≤ 3 stories without flapping
- [ ] Roundup passages attach at ≥ 0.9 precision, cited verbatim; no roundup founds a record
- [ ] Every regression test mutation-verified; `/admin` quality panel live
