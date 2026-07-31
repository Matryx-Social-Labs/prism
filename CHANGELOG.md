# Changelog

All notable changes to Prism are documented here.
Format: [MAJOR.MINOR.PATCH.MICRO] — dated YYYY-MM-DD.

## [0.0.81.9] - 2026-07-31

### Added
- `tools/scratch --score` replays the labelled articles through the real
  `find_event` and scores the result, instead of printing cluster sizes for a
  human to read.

### Discovered
- **The over-merge in production is historical damage, not a live defect.** Same
  171 articles, same labels: production as stored scores B-cubed precision 0.2908,
  purity 0.4842, 6 clusters. Replayed through today's matcher it scores **0.8017 /
  0.9223 / 71 clusters**, with 110 of 171 articles rejoining a story that already
  exists. The 0.29 was written by code predating the 0.0.79-81 fixes.
- **Today's matcher errs toward fragmentation** (71 clusters against 56 real
  events), which is the opposite failure. The `ent_cos` rule measured in 0.0.81.7
  raises precision and tightens the window, so it would push the live failure
  further in the direction it is already wrong. Not shipped.
- Docstrings in `tools/gold_labels.py` and `tools/score_clustering.py` now state
  which of the two numbers each measures, because reading 0.29 as "the algorithm is
  broken" is what nearly caused the wrong fix to ship.

## [0.0.81.8] - 2026-07-31

### Fixed
- **The entity matcher stopped scanning the whole corpus per article.** Its
  corroboration subquery had no parameterised path in, so Postgres materialised
  (event, entity) over every membership on each ingest — measured on production at
  51,840 rows sorted with a 2,952 kB external merge to disk. It is joined on
  `ee.entity_id = d.id`, so only this article's actors can ever survive; pushing
  that filter inside is exactly equivalent because the aggregate is already grouped
  by entity_id. **273.7ms -> 5.9ms, output verified identical (193 rows = 193).**
- Added the missing `event_memberships(article_id)` index. The table carries
  UNIQUE(event_id, article_id), so nothing led with article_id and every "which
  event holds this article?" lookup was a sequential scan — on the per-article path
  in both `_match_by_url` and `_match_by_entities`.

## [0.0.81.7] - 2026-07-30

### Added
- `tools/tune_entity_rule.py` — scores candidate entity-match rules over all 14,535
  pairs of the labelled articles in seconds, with no database writes and no
  re-clustering. The fast loop for changing the matcher.

### Measured
- **A rule that strictly dominates the one in production.** `ent_cos >= 0.45,
  n_shared >= 2, within 48h` versus production's
  `sum(1/df) >= 0.15 AND (max(1/df) >= 0.1 OR n_shared >= 4)`, like for like:
  precision 0.678 -> 0.867 (+28%), recall 0.133 -> 0.243 (+83%), wrong merges
  39 -> 23 (-41%), Cdet 0.0475 -> 0.0385 (-19%). Better on every axis, not a trade.
- The load-bearing change is replacing `max(1/df)` with a cosine over the full
  log-IDF entity vector. A max rule merges on the single rarest shared actor, so
  one coincidence carries the whole decision.
- Contradicting the literature on this corpus: removing the `BROAD_SHARED = 4`
  branch added in 0.0.80.5 makes things WORSE (Cdet 0.0481 vs 0.0475). It stays.

## [0.0.81.6] - 2026-07-30

### Added
- A hand-labelled gold clustering (`tools/gold_labels.py`) for the six largest
  production events, 171 articles read in publication order and assigned to the
  56 real-world events they actually belong to, plus `tools/score_clustering.py`
  to score production against it.
- **Baseline, measured: B-cubed precision 0.29, macro purity 0.48, 6 predicted
  clusters against 56 real events.** The worst cluster holds 22 distinct stories in
  49 articles. The scorer ranks the six exactly as reading them did — Assam floods
  cleanest at 0.86 purity, the CJP protest cluster worst at 0.20 — which is the
  metric agreeing with a judgement made before it existed.
- Deliberately a regression suite, not a corpus sample: these six were chosen
  because fusion is worst there, so B-cubed recall starts near 1.0 by construction
  and is not meaningful. Precision, purity and the cluster count are.

## [0.0.81.5] - 2026-07-30

### Added
- `correlation/cluster_metrics.py` — B-cubed, macro cluster purity, cluster counts
  and a TDT-style detection cost, so the next change to the matcher can be argued
  against a number instead of against a reading of a few clusters. Every threshold
  in `clustering.py` was picked by judgement; that caught the catastrophic failures
  and missed the subtle ones, and cost one revert (`MIN_TOP_IDF` shipped in
  0.0.80.0, walked back in 0.0.80.5).
- B-cubed **precision** is reported separately because it is the over-merge signal,
  and MUC is deliberately absent because it over-rewards merging — on the standard
  benchmark two systems 7.4 CEAF-e points apart both score above 98.8 on MUC.
- `detection_cost` defaults `c_fa` to 4x `c_miss`: an event that absorbs an
  unrelated story is a visible defect, two events that should have been one is a
  mild annoyance. F1 assumes those cost the same; they do not.

## [0.0.81.4] - 2026-07-30

### Fixed
- **A party is one entity, not two.** Outlets mix "BJP" with "Bharatiya Janata
  Party" freely, often inside a single article, and the two were separate rows:
  measured on production, bjp 176 articles vs bharatiya-janata-party 234, cjp 54 vs
  cockroach-janata-party 430, plus dmk/nda/tvk and three singular-plural org pairs.
  Each half carried half the document frequency, so the matcher's 1/df weighting
  scored a national fixture as twice as distinctive as it is — the opposite of what
  the IDF weighting exists to do. Folded by hand in `common/entity_aliases.py`.
- Folded by hand and NOT by an initialism rule, deliberately: in this corpus "BRS"
  initialises both Bharat Rashtra Samithi and the Boston Red Sox, and "CJP" also
  initialises four other organisations. A regression test asserts brs stays unfolded.

## [0.0.81.3] - 2026-07-30

### Added
- `PRISM_VETO_ENABLED` master switch for the grounded storyline veto, mirroring
  `PRISM_INGESTION_ENABLED`. **Set to false in production.**

### Fixed
- The hourly veto pass was paying for LLM work that almost never reached a reader.
  It loses twice: `persist_veto_overlay` publishes only if its base run is still
  current, and with a 15-minute base cadence against a ~13-minute veto it loses
  that race roughly half the time; and when it does win, `persist_base_run`
  unconditionally republishes with `veto_state='pending'` on the next tick, so the
  refinement is discarded within 15 minutes. Measured on production: of 10 retained
  partition runs exactly one carried an applied veto, and it survived 4m33s. The
  switch stops the spend; the structural fix (carry a previous run's veto decisions
  forward through the base pass) is deliberately not attempted here, because the
  veto's output has been observed exactly once and has not been judged worth keeping.

## [0.0.81.2] - 2026-07-30

### Fixed
- **Every development in a storyline is reachable again.** `BranchTree` listed a
  story's members as plain `<div>`s — titles that look tappable and aren't — so
  `/trending/{slug}` was a dead end. That was survivable while the event page
  carried its own timeline linking to siblings; 0.0.81.1 removed it, which left
  collapsed branch developments with no inbound link anywhere in the app. Spine,
  branch and satellite rows now link to `/story/{id}`; the development you are
  already on stays inert, and the branch toggle stays a button.

## [0.0.81.1] - 2026-07-30

### Fixed
- **One story, one timeline.** The event page and the story page each rendered
  "the story so far", but computed it from different member sets: the event route
  called `story_timeline(event_id)` against the LIVE partition, while
  `/trending/{slug}` builds the same arc from the story's FROZEN
  `member_event_ids`. The two could legitimately disagree about which
  developments exist. The arc belongs to the story, so the story page owns it and
  `GET /api/v1/events/{id}` no longer returns `story` at all — which also takes a
  Redis lookup and a partition/BFS assembly off the most-viewed route.

### Removed
- `EventDetail.thread` and `EventDetail.related`. The timeline superseded both in
  0.0.65 and no component ever read them. `fetch_thread` / `related_developments`
  stay in `correlation/threads.py` — still tested, still useful to the graph work.

## [0.0.81.0] - 2026-07-29

### Fixed
- **The entity feedback loop is closed.** `event_entities` is cumulative, so an
  actor arrived when an article was absorbed and stayed forever — every bad merge
  permanently widened what the event could match, and one event reached 978
  actors. New `article_entities` table lets the matcher ask how many of an event's
  OWN articles name an actor, so one inherited from a single mistaken member
  carries no weight. Backfilled from existing extractions; no LLM cost.

## [0.0.80.5] - 2026-07-29

### Fixed
- **A regression from 0.0.79.1.** Requiring one individually-specific shared actor
  rejected real stories: an article sharing eight actors with its event was
  refused because its rarest shared actor sat at df 12, just past the df<=10 the
  threshold implies. A broad cast overlap now satisfies the guard on its own.

## [0.0.80.4] - 2026-07-29

### Fixed
- A shared storyline link now lands on the live story however many merges deep.
  The route followed exactly one hop on the assumption that merges always point
  at a canonical story; production has a two-hop chain, so that link resolved to
  a story that was itself merged — dormant, and not what the reader should see.

## [0.0.80.3] - 2026-07-29

### Fixed
- **The commonest structured-output failure is now named, not guessed at.** In 50
  of 129 production failures the model returned the JSON Schema instead of an
  instance; the retry reported the symptom ("shared: Field required") and quoted
  the schema back, which encouraged it to echo again. 21 messages were dropped
  outright after retries ran out.

## [0.0.80.2] - 2026-07-29

### Fixed
- **The same article arriving via two feeds is now extracted once.** Dedupe keys
  on `(source_id, external_id)`, so a URL reaching us through a national feed and
  a regional one was fetched twice and sent to the model twice — 534 duplicate-URL
  groups, 355 wasted enrichments. The second copy reuses the first extraction and
  keeps its own article, so corroboration and the match trail are unaffected.

## [0.0.80.1] - 2026-07-29

### Fixed
- CVE summaries no longer ship HTML entities. The CVE lens builds its summary
  from raw NVD JSON and never passed through the `clean_text` choke point, so
  9 summaries created *after* that fix still carried `&amp;` and `&nbsp;`.
- BleepingComputer is disabled: it 403s on every 30-minute cycle. The block is on
  the egress IP, not our User-Agent — the feed returns 200 to the same UA from a
  residential address.
- The crawler now identifies itself as `Prism/1.0 (+https://www.readprism.news)`
  instead of `prism-prototype/0.1`, which named no product and gave no contact.

## [0.0.80.0] - 2026-07-29

### Fixed
- **Corroboration counts mastheads, not feeds.** The Hindu ships six regional RSS
  feeds and republishes the same article across them — 666 articles in that family
  share a byte-identical body — so one newsroom filing one story could report up
  to six independent sources. New `sources.publisher` column; unrelated sources
  default to their own slug and are unaffected.

## [0.0.79.3] - 2026-07-29

### Fixed
- **Romanisation variants of one party no longer split its cast.** जनता reaches
  us as both "Janta" and "Janata" and भारतीय as "Bharatiya" and "Bhartiya" — both
  correct, both in real mastheads — so live trending stories carried near-duplicate
  actors. Folded via a curated alias table, never by a transliteration rule.

## [0.0.79.2] - 2026-07-29

### Fixed
- **The partition retention pass had been failing every 15 minutes for days.**
  `partition_runs` references itself, and that self-FK is NO ACTION where the
  other two are CASCADE and SET NULL — so pruning an old base run that a retained
  overlay still pointed at raised a ForeignKeyViolation, deterministically, on the
  same row. It took the whole partition pass down with it and left the grounded
  veto stuck at `pending`, which is why an over-merged 107-member story stayed at
  the top of Trending.

## [0.0.79.1] - 2026-07-28

### Fixed
- **Outlets are no longer extracted as actors.** `prajavani` was the most-shared
  "entity" across a 139-article over-merge — the outlet doing the merging — and
  `tv9kannada` was the first cast name on a live trending story. Filtered at both
  the clustering gate and the entity graph, so the two cannot disagree.
- A match now needs at least one shared actor that is specific on its own, not
  merely specific in aggregate: three actors at df 15 summed past the IDF floor
  while none of them was actually particular.

## [0.0.79.0] - 2026-07-28

### Fixed
- **Kannada and Tamil articles no longer cluster on embedding distance alone.**
  The embedding model's subspace for those scripts is collapsed — unrelated
  articles sit as close as genuine duplicates — so one production event absorbed
  139 unrelated Kannada stories. Those scripts now match on shared actors only.
  Latin and Devanagari, both measured separable, are unchanged.

## [0.0.78.2] - 2026-07-28

### Fixed
- **Desktop story pages were missing their entire evidence layer.** Perspectives,
  the timeline, What to expect and every source lived inside the mobile-only
  tree, so desktop showed a headline, a brief and a lens board and then stopped —
  a story with 35 sources displayed none of them. Ask was unreachable on desktop
  for the same reason. Page height on a real story went 961px to 2023px.
- The sector page scrolled sideways at 390px: a grid item's default
  `min-width:auto` let the sort-chip rail widen the column instead of scrolling
  inside it.

## [0.0.78.1] - 2026-07-28

### Fixed
- Canonical, `og:url` and the sitemap pointed at the old Vercel deployment URL
  after the domain move, telling Google the throwaway host was the real site.
  The value is pinned in CI, so changing it in the Vercel dashboard had no
  effect — it was overwritten on every build.

## [0.0.78.0] - 2026-07-28

### Changed
- **The product is called Prism again**, and the mark is the prism again — a solid
  ink triangle standing on a spectrum bar, ported from `Prism Landing Desktop.dc.html`.
  `readprism.news` is secured. The design system never changed through either
  rename; only the name and the mark did, which is the tell that the spectrum
  hairline and the discrete lens hues were always the prism's argument.
- The sign-in email, API title, OG/JSON-LD metadata, share cards and every screen
  carry the name again. `PRISM_*` env vars and `prism.*` storage keys were never
  renamed and still aren't.

## [0.0.77.1] - 2026-07-27

### Fixed
- A sector with one story no longer gets a full-width row of its own on the
  desktop feed — one photo beside three empty columns read as a failed load.
  Thin sectors collapse into a single "Also filed" band, so every sector still
  appears in a quarter of the space.
- Dropped the red SINGLE-ORIGIN flag from sector rails. It fired on five bands
  out of six.

## [0.0.77.0] - 2026-07-27

### Changed
- **Every screen now has a desktop layout**, not the phone column stretched wide.
  Story shows all three lens readings side by side and re-inks the margin — the
  evidence changes with the lens, so cyber shows the CVE and markets the tickers.
  Trending is a ruled ledger of ranked storylines with the headline each is
  currently running under. Your Prism reads as a colophon. Search gains a margin
  ledger counting what matched and where it was filed.

## [0.0.76.2] - 2026-07-27

### Fixed
- **The desktop Feed was hiding most of the news.** It showed four sectors and
  dropped any sector with fewer than four stories — so on a normal feed five of
  nine never appeared at all, cybersecurity among them. Every sector now gets a
  band, however few stories it has, and a band with more to show links through to
  the full sector page.

## [0.0.76.1] - 2026-07-27

### Changed
- **The desktop Feed is a desktop layout now**, not the phone column stretched
  wide. A lead story with its own frame, the four next-biggest stories beside it,
  then each sector in its own band — with every source count, timestamp and origin
  moved out to a margin rail so the headlines read uninterrupted. (This shipped in
  0.0.76.0; that entry described only the trending fix it rode along with.)

## [0.0.76.0] - 2026-07-27

### Fixed
- **Trending showed the same story several times over.** One protest had taken 7
  of 17 slots, under near-identical titles. Each pass merged the duplicates and
  then immediately recreated them, so the count only ever grew. Slices of one
  story now fold into it instead of becoming new entries.

## [0.0.75.1] - 2026-07-27

### Fixed
- **Apostrophes in headlines showed up as `&#039;`.** Feeds hand us HTML-escaped
  text and nothing decoded it, so punctuation arrived as raw codes mid-sentence.
  Every affected headline was Hindi. New stories read correctly from now on;
  already-stored ones need a one-off pass.

## [0.0.75.0] - 2026-07-27

### Fixed
- **Storylines are trees again, not one flat pile.** The branch tree was
  attaching almost every development straight to the lead story, so a 29-part
  storyline opened as a single "21 developments" row with no structure to read.
  Developments now attach to what they actually follow from: the same storyline
  shows a six-part spine with branches of nine, two and one hanging off the
  developments that caused them, five levels deep.

## [0.0.74.3] - 2026-07-27

### Fixed
- **Clearing the search box left you stuck on "Searching…".** If you emptied the
  field while a search was still running, the page never came back — the spinner
  stayed and the trending entities and suggestions never returned. Clearing now
  always takes you back to the start screen.

## [0.0.74.2] - 2026-07-27

### Fixed
- **Search went blank when it failed.** If the request didn't come back, the
  results area showed nothing at all — no error, no explanation, and no hint the
  search had even run. It now says so, and it no longer tells you there were no
  matches when the truth is that it never got to look.
- The state dropdown in Your Prism survives the regions service being down, and
  now announces itself to screen readers.

## [0.0.74.1] - 2026-07-26

### Fixed
- **The sign-in email said Prism.** Subject, wordmark, button and sign-off — the
  first thing a new reader sees with our name on it, months after the rename.
  Its palette had also drifted cool against every other surface.

## [0.0.74.0] - 2026-07-26

### Added
- **The storyline branch tree.** A trending story is not a list — it forks, and
  some developments only loosely attach. Prism has been recording that shape on
  every partition run and never showing it. The storyline page now opens on
  TRUNK, which reads exactly like the timeline it replaces plus one counted line
  of structure; branches sit collapsed at the point they fork from, as a single
  tappable row; and ALL adds the loosely-attached developments, marked, so you
  are told which ones they are rather than having them quietly mixed in.

### Fixed
- **Trending names the story, not one outlet's headline.** Rows led with a single
  member's headline while the page they opened was titled with the story's own
  cast, so the two disagreed about what you had just tapped.

## [0.0.73.0] - 2026-07-26

### Fixed
- **Feed images no longer download at full article resolution.** A 64px thumbnail
  was pulling a 170KB publisher photo — up to 455KB for some — on every visible
  row. Prism now asks each publisher's CDN for a thumbnail-sized version where it
  supports one. Measured across a feed screen: 1,544KB → 314KB, an 80% saving.
  Hindustan Times and LiveMint serve only one fixed size, so those are unchanged.
- **Landing sections were invisible without JavaScript.** Six content sections
  were hidden by a reveal animation that only JavaScript could undo, so crawlers,
  link-preview bots and anyone whose script failed saw blank space. Matters for
  the public story pages coming next.
- **Share cards still said PRISM**, in Georgia on cool grey. They now carry the
  Prism name and the real typefaces on the warm ground.
- Trending shows the actual name of every Indian state. It knew seven and printed
  the raw code — "IN-BR" instead of "Bihar" — for everywhere else.

### Changed
- The scrolling feed composites one translucent blur instead of three, which is a
  common source of scroll stutter on mid-range Android.
- Feed and Trending no longer fire a throwaway un-personalised request on every
  mount before the profile loads: 6 requests down to 3, and 2 down to 1.
- The scope sheet is one component instead of two copies that had drifted apart.



### Fixed
- **The lens flip works again.** Tapping Cyber or Markets on a story did nothing
  at all if you weren't signed in — no re-typeset, no prompt, nothing — and the
  same was true of the pinned rail on a phone and the 1/2/3 keys on a desktop.
  The product's signature interaction was a dead button for every signed-out
  reader. It now flips, shows the story re-typeset through that lens, and offers
  to unlock it (still free, still just an account).
- **The feed reads as news again for cyber readers.** Choosing the Cyber lens
  turned the whole feed into a vulnerability changelog: no elections, no markets,
  no world news, and — stranger still — no cybersecurity *journalism* either,
  because raw CVE records are re-stamped every few minutes and buried the real
  reporting under them. Records now sit alongside stories roughly two-to-one for
  as long as there are stories to pace them. Readers on every other lens had been
  seeing no cybersecurity coverage at all for the same reason; they do now.
- **Your scope choice survives a refresh.** Picking a wider view and reloading
  snapped straight back to your state, and the sheet's "Applies everywhere"
  promise wasn't true between Feed and Trending. It is now.
- **The scope chip no longer names a filter it isn't applying.** With no state
  set it still read "Your state" or "National" over completely unfiltered
  stories, with the option greyed out so you couldn't correct it.
- Trending no longer quietly narrows a scope set on the Feed, which had been
  hiding your own state's news without being asked.
- The feed fills the page it is asked for whenever the corpus can supply it. A
  vulnerability-heavy sector used to hand back a third of one, and there is no
  way to ask for the rest.
- Sorting by top is score-ordered again, so the lead story is the top-ranked one.

### Changed
- Scope tiers read **All / \<state\> / National** everywhere, matching the design
  system. The Feed called the widest tier "World" while Trending called the same
  thing "National" one tap away. Your saved scope resets once.
- Scope chips are a full-size tap target on phones.
- Greyed-out scope options and locked lenses now say why they are unavailable
  instead of reading as broken controls — including to screen readers.
- The feed's candidate query keeps its index scan: an earlier cut of the
  cybersecurity fix made every request sort ~10MB to temp files.

## [0.0.71.0] - 2026-07-25

### Changed
- **The product is now called Prism.** "Prism" collided with the NSA's PRISM
  surveillance programme — an unwinnable association for a product whose whole
  pitch is transparency — and was squatted across every TLD. The new mark is a
  citation bracket holding three rules: one record, read three ways, the last
  line shorter because the story is still open. It replaces the prism triangle,
  which was the one place a gradient was allowed to sit permanently; the 3px
  spectrum bar is now the only coloured brand object.

### Fixed
- **Desktop was serving the phone layout.** Feed and Trending pinned a 620px
  column with no breakpoint, so on a 1440px screen readers got a narrow strip
  with 410px of dead space on each side, under two stacked brand headers. Both
  now use the full width, with provenance moved into a mono ledger rail in the
  left margin so the prose runs clean.
- **Search opened as a blank screen.** It now starts with trending entities
  pulled from live coverage, example queries, and the query itself set in the
  display face.

### Added
- **Flip lenses from the keyboard on desktop.** Press 1, 2 or 3. The phone has a
  thumb rail for this; a desktop reader had nothing, and the flip is the thing
  worth showing someone.
- **The landing page states the record up front** — a dateline carrying real
  source, story and origin counts, the way a newspaper masthead does.
- On phones the landing now shows the lens demo *before* asking you to sign up.
- **The story-branch structure is now served by the API.** Storylines have been
  splitting into branches and satellites since the partitioner shipped, and the
  shape was computed every run but never read by anything. `/trending/{slug}`
  now returns it, counted rather than summarised: developments, forks,
  satellites, depth. One real storyline reports 29 developments across 20 forks
  with 3 loosely-attached satellites — structure a flat list cannot show. The UI
  for it lands next.

## [0.0.70.0] - 2026-07-25

### Added
- **Prism on a phone is now a real app, not a shrunk desktop site.** Feed, Story,
  Trending and a new You hub were rebuilt mobile-first, with a bottom tab bar
  (Feed · Trending · Pulse · Search · You) as the navigation spine and a unified
  scope chip that opens a bottom sheet. Reading a story now puts the lens rail
  and Share/Ask in the thumb zone where you can reach them one-handed, and the
  coverage bar — how many outlets, how many origins, whether it's single-origin —
  is promoted onto the phone instead of hiding in a desktop sidebar.
- **You keep your place.** Returning from a story lands you exactly where you
  were on Feed, Trending, Search and Sector, with the list still populated
  instead of reloading from the top.
- **Every shared story now previews with an image.** Stories without a publisher
  photo — well over half of them — used to land in WhatsApp as a bare text link;
  they now get a generated card carrying the headline, sector and source count.

### Changed
- **Lens copy reads in plain language.** The sign-in prompt said "The
  Cybersecurity / GRC read of this story", which means nothing to anyone outside
  that profession. Lenses now describe what they tell you — "who's exposed by
  this, and what to fix first" — while pickers keep the role names.
- Sharing sends the headline rather than a naked link, and dismissing the share
  sheet no longer copies the link behind your back.

### Fixed
- **Tap targets, contrast and iOS zoom on the phone.** Lens pills were under the
  44px minimum, bottom-tab labels failed WCAG AA contrast, and both text inputs
  were small enough that iOS zoomed the page on focus and left it zoomed. The Ask
  chat also sat behind the pinned rail on notched iPhones.
- Tapping a lens scrolls the brief into view, so the re-typeset flip happens
  where you can see it instead of reading as a dead button.
- Two Trending filters could never return a story: Markets queried a subsector
  the API doesn't filter on, and Cyber is excluded from trending entirely.
- The phone no longer shows two stacked headers, a footer buried behind the tab
  bar, or a story timestamp that flickered on load.
- Hardened story pages: a headline containing markup can no longer break out of
  the structured-data block, and event ids are escaped in API paths.
- `/you` is excluded from search-engine indexing, alongside the account pages it
  replaces.

### Infrastructure
- **The web app has tests for the first time** — vitest, jsdom and Testing
  Library, wired into CI so every PR runs them. 39 tests cover the scroll
  restoration, sharing, navigation and header logic; each regression test is
  mutation-verified, meaning it was confirmed to fail when the bug it guards is
  put back.

## [0.0.69.0] - 2026-07-25

### Changed
- **Entity extraction now names people by personal name only.** The `extract-shared`
  prompt normalized script/language but not titles, so the LLM emitted
  `Union Education Minister Dharmendra Pradhan` alongside `Dharmendra Pradhan` — two
  entity rows for one person, which fragmented clustering, story-linking, and the
  trending merge. Added a rule to strip titles/offices/ranks/honorifics from PEOPLE
  (organizations kept whole). Verified empirically on real articles: titles stripped,
  entity recall preserved or improved. Published as Langfuse `extract-shared` v14
  (fallback in `common/prompts/fallbacks/` kept in sync). Only affects new extractions.

## [0.0.68.0] - 2026-07-25

### Changed
- **Trending detection now reads the global partition instead of per-seed BFS.**
  `detect_trending_communities` sources story membership from `_partitioned_members`
  (BFS only as a fallback for events not yet in a run), so trending communities match the
  boundaries `/events` serves — removing the last per-seed BFS caller.
- **Magnet-blind cast merge replaced with an IDF-weighted one.** The old "≥3 shared cast
  members → same story" rule (built for the BFS 30-event cap) would re-merge stories the
  veto deliberately SEPARATED when they shared 3 national magnets (Modi/Congress). It's
  replaced with a 1/df-weighted shared-cast overlap (per the IDF principle): distinctive
  protagonists (Cockroach Janta Party, Delhi Police) drive merges, ubiquitous actors don't.
  Genuine Leiden over-splits still re-merge; veto-separated stories stay separate.
  - Known limit: matching is on resolved entity names, so un-folded aliases (`Janta`/`Janata`,
    titled `Union Education Minister Dharmendra Pradhan` vs `Dharmendra Pradhan`) can miss a
    merge (a duplicate card) — never cause a wrong merge. Best fixed at extraction.

## [0.0.67.0] - 2026-07-24

### Added
- **Storyline partitioner wired into serving.** The global Leiden partition + grounded
  veto (staged in v0.0.66.0) now persists to durable, versioned runs and serves the
  canonical story timeline — replacing the entry-dependent per-seed BFS with a boundary
  that is consistent by construction. `story_timeline` reads the partition (BFS only as a
  fallback for events not yet in a run) and caches per `(current run, event)` so a run
  flip invalidates instantly.
  - **Immutable base/overlay runs with atomic cutover.** A cheap frequent Leiden pass
    publishes an immutable *base* run (`partition_runs`, `event_story`); the slow LLM veto
    publishes an *overlay* derived from a base and cuts over only if that base is still
    current (compare-and-swap). A partial-unique index guarantees exactly one live run;
    publishing takes a Postgres advisory lock. Old runs are pruned (keep last N).
  - **Veto verdicts cached and reused** (`story_veto`) keyed on a label-independent,
    versioned story signature, so an unchanged story skips the LLM. The veto prompt is now
    a Langfuse-managed prompt (`story-veto`) with a local fallback, and has a gold eval in
    `evals/run_all.py` (`veto` target) seeded from the validation run.
  - **Shareable trending stories keep their earned identity.** `/api/v1/trending/{slug}`
    now assembles from the story's frozen `member_event_ids` instead of recomputing live,
    so a shared link isn't silently repointed when the global partition shifts.
  - Worker runs a frequent `_partition_reconciler` (base) and a slow `_veto_reconciler`
    (overlay). Adds `event_entities(entity_id)` index for the partition's actor-graph join.

## [0.0.66.0] - 2026-07-24

### Fixed
- **Deferred analysis no longer drops events on failure.** `run_due_analyses` claims an
  event off the dirty set (`zrem`) *before* analyzing, but a failure — LLM timeout or
  **credits exhausted mid-run** — only logged and never re-queued, leaving the event
  permanently un-analyzed (no perspectives, no briefs). Found on live data: 35 multi-source
  events (e.g. an 8-source "WordPress wp2shell" cyber story) had zero perspectives/briefs.
  Failures now re-queue with a backoff so analysis self-heals when the LLM recovers.
- **Entity resolution** now folds trivial punctuation/acronym spelling variants so one
  real-world entity is one row. `D.K. Shivakumar`/`DK Shivakumar`, `J.P. Nadda`/`JP Nadda`
  and `Cockroach Janta Party (CJP)`/`Cockroach Janta Party` were separate entities, which
  quietly fragmented the story cast, the actor graph, and clustering. `entity_slug` (in
  `common/text.py`) canonicalises before slugify — deterministic and conservative, never
  fuzzy (fuzzy once over-merged 1638 CVEs into 7; `CPI(M)`≠`CPI`, `Janta`≠`Janata` stay
  distinct). A one-time backfill (`scripts/backfill_entity_slugs.py`) merged 24 duplicate
  groups on live data, re-pointing `event_entities`/`impacts` and preserving variants as aliases.
- **Relevance gate** scope broadened. The prompt was stale — scoped to "professional roles
  (cybersecurity/GRC and finance/markets)" only — so the gate dropped real general-interest
  Indian news: sampling the rejects surfaced *Assam floods death toll*, *SC orders special
  courts*, ministerial *resignations*, and protest news wrongly rejected. The rewritten
  `relevance-gate` covers politics, courts, protests, disasters, health, science, sports and
  the professional lenses, and clarifies that statements/demands/rulings by newsworthy actors
  **are** events (while still rejecting opinion columns, ads, listicles, gossip). Committed as
  the local fallback and staged in Langfuse (v12, `staging`); production label unchanged pending
  a check on the production model.

### Added
- **Storyline partitioner** (`correlation/partition.py`), staged and validated read-only, not
  yet wired to serving. Three layers per docs/STORYLINE-DESIGN.md: a global **Leiden** story
  boundary (consistency by construction — every development reads the same boundary), a
  spine-anchored branch tree, and a **grounded LLM veto** that separates entangled-politics
  over-merges (validated: cuts NEET/SIR/parliament out of the CJP protest story). Awaits the
  capable veto model before it replaces the on-read story graph.

## [0.0.65.0] - 2026-07-24

### Fixed
- Story graph: a **generic-entity stoplist** stops unrelated disasters/stories from
  linking through shared responders. On live data the Assam flood story pulled in
  the Sikkim tunnel collapse because both name `NDRF` / `Fire and Emergency Services`
  / the `Army` — agencies that respond to everything and are never a story's own
  protagonist. Their `df` is low in a small corpus, so IDF didn't suppress them and
  the embedding gate didn't either (a flood and a tunnel collapse embed close: both
  are "N dead, rescue ongoing, NDRF responds"). These entities are now story-graph
  stopwords — two events sharing only them are not one story. The list is deliberately
  narrow: specific bodies like `Delhi Police` (carries the CJP protest edge) and
  investigative bodies like the ED are kept. Verified on prod: Assam flood → its own
  story (Sikkim gone), CJP → all 12 cross-state developments intact. No LLM cost;
  self-corrects further at corpus scale.

## [0.0.64.0] - 2026-07-24

### Fixed
- Story timeline ("the story so far") no longer explodes across unrelated stories.
  A Cauvery-water story was pulling in 14 unrelated Tamil Nadu items (ammonia leak,
  school fees, cow slaughter, census…). Two causes, two fixes in the story graph
  (`correlation/threads.py`), both validated live:
  - **Roundup/live-blog exclusion.** "Tamil Nadu Today: …" / "… LIVE:" events pack
    many unrelated actors into one body and bridge everything. Excluded from the
    graph by a title marker AND a high entity count (the count keeps single-topic
    "… Q1 Results Today:" items, which have few entities, in the graph — and never
    touches real big stories, which carry no marker).
  - **Seed-relative topical-coherence gate.** A member must be embedding-close to
    the *seed*, not just its BFS neighbour — otherwise a legitimate dual-topic bridge
    ("CM Vijay reviews Mekedatu", water AND politics) leaks a whole cluster in one
    hop. A raised IDF bar can't do this (a mega-story's core actors are high-df
    magnets, so it would also drop cross-state links). Gate at cosine 0.55.
  - Result on prod: the Cauvery story goes 16 → 2 developments (both real water
    events) while the CJP/NEET story keeps its cross-state branches (Delhi / Mumbai /
    Patna), 13 → 12. Read-path change — every existing timeline benefits on deploy,
    no re-processing.

## [0.0.63.0] - 2026-07-23

### Fixed
- QA (end-to-end) findings — both from LLM endpoints failing during the credit stall:
  - **/pulse no longer hangs on "Composing today's market pulse…".** A cross-origin
    5xx from the digest endpoint is blocked as a CORS error and *rejects* the fetch,
    so `fetchDigest` threw and the page's `setLoading(false)` never ran. `fetchDigest`
    now catches and returns null → /pulse resolves to its "not available right now"
    empty state.
  - **Story lens brief returns an empty brief, not a 500.** `/events/{id}/brief` is an
    on-demand LLM synthesis; with the model quota exhausted it 500'd (the story page
    already degraded to "the <lens> read isn't available yet", but the 500 was noisy).
    It now catches the failure and returns an empty brief — same UI, no 500.

## [0.0.62.0] - 2026-07-23

### Fixed
- Design-review findings on the live feed v3:
  - **Per-card language tags now render.** The API returns `headline_lang: null`
    for every item, so the हिंदी/ಕನ್ನಡ tag never showed. Cards now fall back to
    Unicode-script detection (`detectScript`) from the headline text — a Devanagari
    or Kannada headline is tagged immediately, no backend dependency.
  - **Market Pulse no longer 500s.** `/api/v1/digest/markets` is a pure LLM
    synthesis; with the model quota exhausted it threw an unhandled 500 (which the
    browser reported as a CORS failure). It now degrades: LLM unavailable → the
    digest route 204s and the feed hides the Pulse card. Failures are never cached,
    so it recovers on the next request once the model is back.

## [0.0.61.0] - 2026-07-23

### Changed
- Feed **v3** (design `Prism UI Design.dc.html`, frame 3a): the feed's lens pills are
  gone — lens is a per-story flip, not a feed filter. In their place: a scope selector
  (All / <your state> / National) + a language-preference chip; Trending joins the nav
  (header, left rail, bottom tab bar) and the right rail gains a "Trending now" block.
- Removed the global lens switcher from the header chrome — the lens is set in "Your
  Prism" (/interests) and flipped per-story. Header stays monochrome (a deliberate
  departure from design v3, which kept a header lens chip; see DESIGN.md decisions).
- Cards tag their headline language (हिंदी / ಕನ್ನಡ) when it isn't the reader's primary,
  with a "translation available" hint. Scope tab shows the real state name (Karnataka).
- "Your Prism" (/interests) now manages reading languages; content shells unified to
  1240px (header/footer 1280px). Removed the standalone TrendingBlock component.

## [0.0.60.0] - 2026-07-23

### Fixed
- Feed default lens: **general reader, not cybersecurity**. `DEFAULT_LENS` was `"cyber"`,
  and `get_lens()` falls back to it for a missing OR unknown slug — so a visitor whose
  request carried no lens, or a stale pre-rename lens in localStorage, was served
  `/api/v1/feed` filtered to **cybersecurity-only** (all CVEs, single left-rail section)
  until a lens was re-sent. Confirmed on prod: no-lens feed returned 40/40 cybersecurity
  items; `lens=reader` returned the full sector mix. Default is now `"reader"` (sectors=[]
  → every story). The picker still leads with the professional beachhead (lens order is
  unchanged); only the ambiguous-case fallback moved.

## [0.0.59.0] - 2026-07-23

### Fixed
- Trending stories: **self-healing convergence** + a stronger same-story signal.
  Cast-identity dedup (0.0.58.0) still left the CJP/NEET mega-story as 4 cards: its
  8-member casts diverged per BFS window (Jaccard 0.23–0.45, under the 0.5 bar) and
  even the top-3 protagonists got re-ranked, so no fixed window matched. But the cast
  *intersection* is stable — every fragment shared exactly `{Cockroach Janta Party,
  Dharmendra Pradhan, Delhi Police}`. Two fixes: (1) `_same_story` now also matches when
  casts share ≥ 3 members outright (rank-independent); (2) reconcile runs a union-find
  **cross-story merge pass** so existing active stories that are the same story as *each
  other* collapse into the oldest — previously they could only merge against a freshly
  detected community, so once a cluster stopped trending its duplicates lingered 24h.
  Verified on prod: 6 → 1 CJP card, idempotent across passes.

### Notes
- Root-caused a separate prod symptom (stale/thin feed since ~02:09): **OpenRouter
  credits exhausted** → classification stage 402-ing → ~1189 raw items stuck unclassified
  (no data loss; they retry on cooldown and drain once credits return). Not a code change.

## [0.0.58.0] - 2026-07-23

### Fixed
- Trending stories: dedupe by **cast identity**, not just member-set overlap. On prod
  the CJP cluster (>30 events) exceeded `story_timeline`'s 30-event BFS cap, so each seed
  produced a different 30-member subset; member-overlap fell below 0.6 and one story
  fragmented into **6 near-duplicate trending cards**. Two communities are now the same
  story when member-overlap ≥ 0.6 **OR** cast (protagonist) Jaccard ≥ 0.5 — the
  protagonists are stable even when the capped member window shifts. Verified on prod:
  10 → 4 clean stories (the 6 CJP variants collapse to 1). Applies to both detection
  dedup and the reconciliation match.

## [0.0.57.0] - 2026-07-23

### Added
- **Trending stories** — persistent, shareable communities in the top slot (the thesis:
  "one story, not scattered headlines"). Replaces the old multi-source-event "Top Stories".
  - **Engine** (`correlation/trending.py`, no LLM): rank events by velocity (distinct NEW
    news outlets in 6h, CVE/raw feeds excluded) → group via the existing per-event
    community detection → dedupe by member-set overlap ≥ 0.6. A community earns a durable
    `stories` row only past a min-support gate (≥2 outlets, ≥2 events).
  - **Stable identity** — the reconciliation state machine keeps `/trending/<slug>` from
    silently changing meaning: match ≥0.6 → UPDATE (id + slug persist); no match → CREATE
    (slug frozen at creation from the cast); ≥2 matches → MERGE (oldest wins, the younger
    points `merged_into` and its URL resolves to the canonical); stops trending → `dormant`,
    never deleted (shared links never 404). Runs every 10 min off the ingest path.
  - **API**: `GET /api/v1/trending?state=&sector=` (scoped, ranked) + `GET /api/v1/trending/{slug}`
    (follows merges → `canonical_slug`, returns the live start→now timeline).
  - **Frontend**: feed "Trending now" block with a geo toggle (near-me / India) + auto-scope
    on sector pages; a `/trending` list page; `/trending/[slug]` shareable permalinks.
  - **Shareable** (D2:A): an auto-generated **`next/og`** social card per story (label + cast
    + outlet count + brand spectrum) so a forwarded link renders a premium preview — the
    WhatsApp-first India growth loop. Web Share API + copy-link affordance.

  Deferred: LLM "X vs Y" labels (extractive cast for now); pretty slugs beyond `label-<id6>`;
  per-story share-count analytics; the "what's new since you looked" badge.

## [0.0.56.0] - 2026-07-23

### Added
- **Phase 1: language-aware onboarding + feed** (Bangalore launch, en/hi/kn).
  - **Email-first auth (fixes a live bug).** `/auth/request` is now email-only and
    always returns the same 200 (enumeration-safe); the account is created only on a
    *verified* email; the profile (name, profession, state, languages, consent) is
    collected AFTER verify via `POST /auth/profile`. Verify returns `needs_profile` so
    new readers route to onboarding and returning readers land straight in the app —
    no more re-entering name/profession on every sign-in.
  - **Reader languages** (`users.languages[]`, ordered by preference; `state`,
    `consented_at`). `GET /api/v1/languages` serves the picker (native-script labels).
  - **Language-aware feed (rank, don't filter).** `_rebuild_projection` now stores
    `languages[]` + per-language `headlines[]`; the feed ranks preferred-language
    coverage up and renders each reader the headline in their top language, falling
    back to English (never hides an English-only story). The cluster stays
    cross-language; only display is localised — no re-clustering, no LLM.
  - **Onboarding UI**: email-only signin; two-step post-verify onboarding with a
    monochrome native-script language picker (order = tap sequence, primary first;
    language is not a lens so it carries no colour, per DESIGN.md) + explicit consent.
  - **Kannada sources**: Prajavani + TV9 Kannada RSS (validated Kannada, fresh).

  Deferred (documented): hard language-filter toggle + its GIN index (rank-not-filter
  needs no SQL array-overlap query yet); per-development timeline headline localisation
  (reuses the same `headlines[]` + `_pick_headline`); async batched projection backfill
  (existing events fall back to the event title until re-projected/re-ingested).

## [0.0.55.0] - 2026-07-23

### Changed
- Single-word lens slugs, consistent across API and frontend: `general`→`reader`,
  `cyber_grc`→`cyber`, `finance_trader`→`markets`. One key now refers to a lens on
  both sides (`common/lenses.py` registry, projections, prompts, professions, agent
  question seeding, and the whole frontend). The extraction `lens_fields` keys
  (`cyber`, `finance`) are unchanged. A data migration remaps the lens-keyed fields
  in existing event projections (`lens_briefs`/`lens_points` keys, `role_interests`)
  so the renamed frontend finds briefs without re-ingestion.
- Prompt fallbacks (classifier, lens-brief, event-analysis) emit the new keys. The
  live Langfuse prompts must be republished (`uv run python evals/sync_prompts.py`)
  or the LLM keeps emitting old keys and briefs render empty until it runs.

### Added
- Drafted (not yet shipped) **Health** and **Policy** lenses in the registry with an
  `upcoming` flag — kept for future work, excluded from `/api/v1/lenses` and never
  activating extraction, so the live picker still offers only Reader/Cyber/Markets.

## [0.0.54.0] - 2026-07-23

### Changed
- Mobile-first design refresh (v2). New mobile-only `BottomTabBar` (Feed / Pulse /
  Search / Saved) for app-like navigation on the core browsing routes, hidden on
  desktop (lg+) and on marketing/flow/story routes. Onboarding gains a profession
  picker backed by `fetchProfessions()` (`/api/v1/professions`). Refreshed landing,
  feed, sector, onboarding, StoryView, AskPanel, HeaderNav, PrismMark, LensDemo, and
  BriefPlayer. Frontend-only; deploys to Vercel on merge.

## [0.0.53.0] - 2026-07-23

### Fixed
- Actor graph: deduplicate `event_entities` to one row per `(event_id, entity_id)`.
  The unique key was `(event_id, entity_id, role)`, so the same entity could attach
  to one event multiple times under different roles (subject/mentioned/affected) as
  its member articles merged. The IDF-weighted actor-graph queries (`_match_by_entities`
  clustering + story-timeline edges) `sum(1/df)` over those role-rows **and** multiply
  seed-rows × neighbour-rows, so a duplicated actor inflated an edge weight N-fold —
  over-weighting exactly the bridges community detection then failed to cut, leaking
  unrelated stories into a trending story's timeline. Migration collapses to one row
  per `(event_id, entity_id)` (prefers the `affected` role for cast ordering) and swaps
  the unique constraint; the insert path now conflicts on `(event_id, entity_id)`.
  Validated on a fresh local snapshot: 190 duplicate pairs removed; the CJP story
  tightened from 23 → 20 developments. (Does not fully resolve mega-story over-grouping
  — that is a magnet-actor / small-corpus effect needing a cross-sector-spread signal.)

## [0.0.52.0] - 2026-07-22

### Fixed
- Event clustering (`_match_by_entities`): the **same** df-cutoff bug as the story
  timeline, one level lower. The `entity_overlap` merge tier excluded actors in
  > 2 events (my own KSU over-merge fix), so a trending story's same-development
  cross-language retellings — which share only that story's high-df core — never
  merged into one event either, compounding the fragmentation before the timeline
  even ran. Replaced the `df <= 2` cutoff with the same **IDF weighting** (`1/df`):
  keep every shared actor, require `sum(1/df) ≥ 0.15` plus the ≥2-actor floor. A
  shared national magnet (Google df49 → 0.02, CJP df82 → 0.01) contributes almost
  nothing so unrelated events sharing only magnets still don't merge (KSU
  re-validated: 12 unrelated Android CVEs sharing only "Google" stay separate),
  while a specific actor carries a genuine retelling.
- Event clustering: **near-dup single-actor tier**. In the near-dup embedding band
  (≤ 0.25) one IDF-strong actor is now enough to merge — two Hindi retellings of
  "16 Delhi Metro stations shut" sit at 0.20 distance but share only "Delhi Metro"
  (the ≥2-actor floor was splitting them). Above 0.25 the ≥2-actor floor still
  applies, since a lone shared actor there is more likely coincidental.

## [0.0.51.0] - 2026-07-22

### Fixed
- Story-timeline: IDF-weighted edges instead of a df cutoff — fixes trending-story
  fragmentation. The df<15 "distinctive actor" cutoff (from the KSU over-merge fix)
  deleted a *huge trending story's own core* (Cockroach Janta Party df82, Dharmendra
  Pradhan 76, Sonam Wangchuk 50 — all far above the cutoff), so its developments
  shared only excluded actors and the story shattered into **~82 orphan events**.
  Root cause: global document-frequency can't tell "central to one big story" (keep)
  from "ubiquitous across unrelated stories" (drop). Fix: stop *excluding* high-df
  actors; keep them all and **weight each shared actor `1/df`** (a magnet contributes
  ~0.01-0.02, a specific actor ~0.17), require an IDF-weighted (× temporal-decay) edge
  ≥ 0.15 plus the ≥2-actor floor, and let community detection separate stories by
  structure. Live: the CJP story regroups into coherent sub-stories (protest / police
  / legal / opposition); the cast strip now shows the story's real protagonists (was
  empty — they'd been excluded). Also applies to `_component_edges` and the cast query.
  **Known limitation:** a *cross-story* magnet that's lower-frequency than a story's
  own core (Trump df41 < CJP df82) can't be dropped by any frequency rule — one
  Trump-adjacent event ("tariffs") still joins a Trump-heavy Iran cluster. The real
  discriminator is cross-sector spread (Trump spans politics+business; CJP stays in
  politics) — a follow-up. Net: fixes the severe, common case (a story with its own
  actors) at the cost of a mild over-merge on dominant-cross-figure US-politics stories.

## [0.0.50.0] - 2026-07-22

### Changed
- Story timeline: temporal edge decay + community-detection split. Two refinements to
  `story_timeline`, both read-path (no LLM cost), prompted by a cross-model design note:
  - **Temporal decay** — each story edge is now weighted `shared_actors × e^(−0.03·days)`,
    a softer version of the hard 30-day window: a distant-but-similar event (a protest
    months ago sharing 2 actors) decays below threshold and can't false-join, while
    a same-day pair sails through. Live: dropped a stale 2025-10 event that the window
    let slip into the current Iran story (10 → 9 developments).
  - **Community detection** — the connected component can span closely-related
    sub-stories (Iran war + Lebanon peace) joined by a few bridge actors. Modularity
    (`networkx` greedy_modularity, pure-Python, tiny local graph) now cuts the weak
    bridges and returns the seed's community, so each development shows its own tight
    arc. Live: the 9-event component splits into a 6-event Iran-war story and a
    3-event Lebanon-peace story; an Iran development now shows the 6.
  Chosen `networkx` greedy-modularity over Leiden/`igraph` (a C-extension) — same
  modularity objective, no build complexity, validated on live data. Cached with the
  timeline (5-min TTL). New dep: `networkx`.

## [0.0.49.0] - 2026-07-22

### Changed
- Unified story timeline UI (PR 2 of 2). Replaced the story page's two per-event
  sections — "The thread" (causal `event_links`, collapsed 6→1 hub-to-leaf) and
  "The story so far" (actor branches, noisy) — with **one** `StoryTimeline` that
  renders the canonical `event.story` component from v0.0.48.0: every development of
  a story now shows the **same** chronological arc, with "you are here" on the
  current one and the causal "why" folded inline as a `↳` note under the development
  it explains. Same DESIGN.md treatment (monochrome, IBM Plex Mono dates, hairline
  rule, reveal-on-scroll). Deleted `ThreadRail.tsx` + `StoryTrail.tsx`.
  Follow-up (PR 3): drop the now-unused `thread`+`related` API fields and their
  `fetch_thread`/`related_developments` computation.

## [0.0.48.0] - 2026-07-22

### Added
- Canonical story timeline API (`story_timeline`, backend of a 2-PR feature). Story
  pages showed a per-event "thread" (causal `event_links`) that collapsed from 6
  nodes on a hub to 1 on a leaf, plus a "story so far" that leaked ubiquitous-actor
  noise ("Trump tariffs" in the Iran-war story via the shared "Donald Trump"). Root
  cause: no canonical story — each event computed its own neighborhood. Fix: the
  story is the connected component over **strong** edges — two events linked iff
  they share ≥2 **distinctive** actors (person/org with document-frequency < 15;
  calibrated on live data where a story's own core sits at df≤10 and cross-story
  magnets are df≥20). Transitive, so a leaf reaches the whole story via its hub;
  magnet-only links (two stories sharing just "Trump") aren't edges, so unrelated
  stories stay out. Every development yields the identical component → one
  consistent timeline. Validated on the live Iran story: a clean 10-development
  Middle-East arc, no tariff noise. On-read + Redis-cached (fail-open, 5-min TTL);
  bounded BFS (size 24, depth 4). Chosen over on-read Louvain after live validation
  showed the strong-edge component is enough — Louvain stays a documented refinement
  if closely-related sub-stories (Iran war vs Lebanon peace) need splitting.
  Added to `EventDetail.story` **alongside** `thread`+`related` so the current UI is
  untouched; PR 2 swaps the frontend to one `StoryTimeline` and drops the old fields.

## [0.0.47.0] - 2026-07-22

### Fixed
- Gate the cyber/finance lens *fields* behind sign-in, not just the lens brief.
  v0.0.46.0 let a signed-out reader flip to a locked lens in place (good) — but the
  lens-fields blocks (`lens === "cyber_grc" && cyber`, `lens === "finance_trader" &&
  finance`) were gated only by lens selection, not `isLocked`. So selecting the locked
  lens rendered the full pro payload (CVSS, affected products, remediation, the whole
  NIST/CIS/ISO control-mapping table; tickers/catalyst/price for markets) below the
  sign-in prompt. Added `!isLocked(lens)` to both blocks so a signed-out reader sees
  only the flip + the "sign in to unlock" prompt. (The brief was already gated.)

## [0.0.46.0] - 2026-07-22

### Changed
- Locked lens tabs now flip in place instead of bouncing to /signin. Clicking a pro
  lens (Cyber/Markets) as a signed-out reader hard-redirected to the sign-in page —
  losing your place on the story, and the signature re-typeset flip never played.
  Now the tab flips to the locked lens (scan line + re-ink in the lens hue) and
  reveals the in-place "sign in to unlock the {lens} lens (free)" prompt that already
  existed in the component but was unreachable. The reader sees "the memorable thing"
  and keeps their place; the freemium gate is unchanged (no brief is fetched or
  generated for a locked lens, so it stays free). `web/src/components/StoryView.tsx`.

## [0.0.45.0] - 2026-07-22

### Fixed
- Feed/story thumbnails all 404'd. Article images come from arbitrary news CDNs
  (tosshub, toiimg, thehindu, livemint, hindustantimes…). Next.js's server-side
  image optimizer (`/_next/image`) fetches them from Vercel's datacenter IPs, which
  those CDNs block (hotlink/bot protection) → every thumbnail returned a 404 (23 per
  feed load), showing gray placeholder boxes + flooding the console. Set
  `images.unoptimized: true` so next/image serves the CDN URL directly to the browser
  (real UA + referer, which the CDNs allow — verified tosshub 200 direct vs 404 via
  optimizer). `onError` still hides the few that fail. Trade-off: no server resize,
  but these are 92–120px JPGs. Also observed: the feed's API-unreachable state renders
  a clean inline notice (graceful degradation working).

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
