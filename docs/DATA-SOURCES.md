# Data Sources and Ingestion Strategy

Ingestion is hybrid: buy breadth from news-event APIs, add domain feeds for the beachhead, and
build a small number of own collectors where control matters. This avoids the multi-year cost of
rebuilding global collection from scratch, while keeping a path to proprietary sources. Every
collector publishes to the `raw.items` stream rather than writing straight to the database.

## Source tiers

### Tier 1 — News-event APIs (breadth)
Used for worldwide, multi-language coverage and first-pass clustering and entities.
- **GDELT** (and GDELT Cloud): global event and article stream with entities, tone, and clustered
  stories; petabyte-scale, strong for geopolitics and cross-country coverage.
- **NewsCatcher** or **Event Registry** (choose one to license first): NLP-enriched articles with
  topic classification, entity extraction, sentiment, and article clustering across many sources.
These give immediate global reach and reduce how much clustering Prism must do from zero.

### Tier 2 — Domain feeds (cyber beachhead depth)
Used for authoritative, structured cybersecurity signal.
- **NVD / CVE**: canonical vulnerability records with CVSS, affected product configurations (CPE),
  and references.
- **CISA KEV**: the Known Exploited Vulnerabilities catalog, for exploitation status.
- **Vendor advisories**: security advisories from major vendors for affected products and fixes.
- Optional later: exploit and PoC trackers, and ransomware or leak-site trackers ported from
  EduThreat for incident coverage.

### Tier 3 — Own collectors (control and differentiation)
A small set of collectors whose logic is ported from the EduThreat scrapers into fresh
streaming-first collectors. Used for key or under-covered national outlets, and for the
cross-national both-sides feature where domestic-language sources from the parties involved are not
well indexed by the Tier 1 APIs. These are added deliberately, not as a global scraping estate.

### Tier 4 — Finance feeds (Phase 2, the trader lens)
- **Marketaux** (entity-first news across many markets and languages) and, if the fast-lane needs
  lower latency, a real-time catalyst feed such as Benzinga. Added when the finance lens ships.

## Watermarks and cost
Each collector keeps a per-source watermark so scheduled runs fetch only new items, keeping
continuous operation affordable, the same pattern used in EduThreat. API cost is controlled by
pulling incrementally and by pushing expensive LLM enrichment only past the relevance gate.

## Cross-national framing note
The both-sides promise depends on having sources from more than one side of a contested story.
Tier 1 APIs provide language and country coverage, and Tier 3 collectors fill gaps for specific
country pairs that matter first. The initial region and language priority is an open decision to
set at build time, guided by the beachhead audience (English-first for cyber, with a short list of
priority languages to follow).

## What to license first (recommendation)
Start with GDELT (free tier and Cloud) plus one paid enrichment API, and the NVD/CVE and CISA KEV
feeds, which are free and authoritative for the beachhead. Add own collectors only where the APIs
leave a real gap. Defer finance feeds to Phase 2.

## Expansion 2026-09-24 (founder D-e: Indian news breadth, most-read languages first)

Bengali, Gujarati and Punjabi candidates failed with 403/Cloudflare from a datacenter IP; retry them from Railway's egress before calling them dead.

### How a source reaches production

- `ingestion/runner.py::run_all()` calls `await seed_sources()` as the FIRST step of
  every ingestion cycle — the worker's scheduled tick, an admin-triggered run, and
  the worker's own startup (`worker/__main__.py::_initial_ingest` /
  `_handle_admin_trigger`, both go through `run_all()`).
- `seed_sources()` (`ingestion/seed.py`) does `INSERT ... ON CONFLICT (slug) DO
  NOTHING` for every row in `SOURCES`. It is fully idempotent and requires no
  migration or manual seed command — a new row is picked up on the very next
  ingestion cycle after a normal deploy.
- **`seed.py` alone is not enough.** `SOURCES` in `seed.py` only carries outlet
  *metadata* (name, country, language, publisher, reliability) — no feed URL. The
  actual crawl target lives in `ingestion/rss.py`'s `FEEDS: list[FeedSpec]`
  (url, sector/subsector/state, enabled). A slug seeded without a matching
  `FeedSpec` is inert — it appears in `sources` but nothing ever fetches it, and a
  slug in `FEEDS` without a seed row raises at fetch time
  (`ingestion/base.py::get_source`: `"source '{slug}' not seeded"`). I verified
  programmatically that every new slug added here has an entry in **both** files
  (`uv run python3` importing `ingestion.rss.FEEDS`/`ingestion.seed.SOURCES` and
  diffing the slug sets — zero mismatches, zero duplicate slugs).
- `make seed` in the Makefile is unrelated — it loads a dev fixture corpus, not
  this `SOURCES` list.
- `common/outlets.py`'s `CODES`/`DOMAINS` dicts are optional (both have fallbacks:
  mechanical initials for the monogram, the feed's own host for the favicon) but
  the file curates every existing publisher explicitly, so the same was done here
  for consistency. One entry (`scroll`) needed an explicit `DOMAINS` override
  because its feed is served off `feeds.feedburner.com`, which is not the outlet's
  own domain.
- `common/languages.py`'s `LANGUAGES` dict controls only display (native-script
  name on a quote's language label) and the onboarding language picker's
  candidate pool (`offered()` still filters through `LAUNCH_LANGUAGES`, untouched
  here). It does **not** gate ingestion — `is_valid_language()` is only called
  from `api/routes/auth.py` to filter a reader's *own* language preference. A
  source with an unlisted language code still ingests fine; it would just print
  as a bare uppercase code (e.g. "ML") instead of a name, per the file's own
  docstring. I added `ml`/`or`/`as` anyway since two new outlets there needed it
  for correct display.

### Added (19, all verified live)

Verification method: `curl -sL -A "Mozilla/5.0" --max-time 20 <url>`, parsed two
ways — stdlib `xml.etree.ElementTree` (as instructed) and, as a second check,
`feedparser` (the actual library `ingestion/rss.py` uses — several candidates
that stdlib `ET` rejected on a single unescaped `&` parsed fine under
`feedparser`; ET's stricter reading was still trusted where the two disagreed for
real reasons, e.g. staleness or wrong script). Script check: fraction of letters
in the language's Unicode block across the first ~8 titles. Paywall check:
`trafilatura.extract()` (the same extractor `enrichment/fulltext.py` uses) on one
spot-fetched article per outlet, ≥400 chars = pass (`MIN_USEFUL_CHARS` in
`enrichment/fulltext.py`). All dates below are relative to 2026-09-24.

| Outlet | Slug | Lang | Feed URL | Items/day (est.) | Newest item | Paywall check | Notes |
|---|---|---|---|---|---|---|---|
| The Indian Express | indianexpress | en | indianexpress.com/section/india/feed/ | ~25 | 0.7 h | OK (4232 chars) | broad national+state |
| Scroll.in | scroll | en | feeds.feedburner.com/ScrollinArticles.rss | ~24 | 0.2 h | OK (3453 chars) | domain override needed (feedburner host) |
| Deccan Herald | deccanherald | en | deccanherald.com/feed | ~150* | 0.07 h | OK (11017 chars) | *rate estimate unreliable — see caveat below |
| Deccan Chronicle | deccanchronicle | en | deccanchronicle.com/rss_feed/ | ~297 | 0.03 h | OK (1486 chars on 2nd article) | combined firehose feed; mixes in astrology/sports — first item spot-checked was an astrology blurb (337 chars), 2nd item confirmed fine |
| Telangana Today | telanganatoday | en | telanganatoday.com/feed | ~132 | 0.1 h | OK (2534 chars) | single-state masthead, tagged `state="IN-TG"` |
| Business Standard | businessstandard | en (business) | business-standard.com/rss/latest.rss | ~217 | 0.3 h | OK (3442 chars) | |
| The Economic Times | economictimes | en (business) | economictimes.indiatimes.com/rssfeedstopstories.cms | ~200* | 0.6 h | OK (1917 chars) | *rate estimate unreliable — see caveat |
| Dainik Bhaskar | dainikbhaskar | hi | bhaskar.com/rss-v1--category-1061.xml | ~20 | 1.8 h | OK (9090 chars) | |
| Navbharat Times | navbharattimes | hi | navbharattimes.indiatimes.com/langapi/sitemap/gstandrssfeed.xml | ~121 | 0.4 h | OK (6840 chars) | URL found via the site's own `<link rel=alternate>`, not guessed |
| Maharashtra Times | maharashtratimes | mr | maharashtratimes.com/langapi/sitemap/gstandrssfeed.xml | ~120* | 0.2 h | OK (6702 chars) | *rate estimate unreliable; `state="IN-MH"` |
| Sakshi | sakshi | te | sakshi.com/rss.xml | ~405 | 0.1 h | OK (1463 chars) | n=10 sample, lower confidence on rate |
| Dinamani | dinamani | ta | dinamani.com/stories.rss | ~60* | 0.15 h | OK (1734 chars) | *rate estimate unreliable; URL from `<link rel=alternate>` |
| Mathrubhumi | mathrubhumi | ml | mathrubhumi.com/sitemaps/mathrubhumi/rss | ~306 | 0.3 h | OK (1326 chars on non-video article) | `state="IN-KL"`; URL discovered via homepage link tag |
| Madhyamam | madhyamam | ml | madhyamam.com/feeds.xml | ~267 | 0.03 h | OK (1357 chars on non-video article) | `state="IN-KL"`; URL discovered via homepage link tag |
| Malayala Manorama | manoramaonline | ml | manoramaonline.com/news/latest-news.feeds.rss.xml | ~91 | 0.4 h | OK (2230 chars) | `state="IN-KL"`; n=10 sample |
| Dharitri | dharitri | or | dharitri.com/feed | ~98 | 0.05 h | OK (1376 chars on 2nd article) | `state="IN-OD"`; first item was borderline (380 chars), 2nd confirmed fine |
| Sambad | sambad | or | sambad.in/rss | ~198 | 0.07 h | OK (6160 chars) | `state="IN-OD"`; URL from homepage link tag |
| Asomiya Pratidin | asomiyapratidin | as | asomiyapratidin.in/rss | ~38 | 0.01 h | OK (1961 chars) | `state="IN-AS"`; URL from homepage link tag |
| Qaumi Awaz | qaumiawaz | ur | qaumiawaz.com/feed | ~79 | 1.5 h | OK (1319 chars) | n=11 sample, lower confidence on rate |

\* **Rate-estimate caveat:** items/day is computed from the spread of `pubDate`s
in one snapshot. Four feeds (Deccan Herald, Economic Times, Maharashtra Times,
Dinamani) had one badly-dated item in the sample that skewed the naive rate to
near zero; I substituted a conservative peer-comparable estimate instead of the
broken raw number and flagged it here rather than either silently using the bad
figure or fabricating false precision.

Malayalam went from **0 → 3 sources** (task's hard requirement of ≥2 met with
margin — three added together on purpose, since Malayalam's own memory notes
mention no prior clustering measurement, so a single source would sit at real
risk of never corroborating). Odia and Assamese are also brand-new (0 → 2 and
0 → 1).

### Rejected (recorded so they are not retried blind)

| Outlet (lang) | What was tried | Reason rejected |
|---|---|---|
| ThePrint (en) | theprint.in/feed/ | Cloudflare JS challenge page ("Just a moment…"), not a feed response |
| News18, all editions incl. bengali/gujarati/punjabi/urdu/tamil/telugu/kannada/malayalam/marathi.news18.com (en + 9 langs) | `/rss/*.xml`, `commonfeeds/v1/eng/rss/india.xml`, `/rss/` | 403 on every subdomain tried — Network18 blocks this egress wholesale |
| The New Indian Express (en) | old `?id=170&getXmlFeed=true` pattern, homepage link-discovery | 404 everywhere; likely migrated CMS with no static feed link (Kannada Prabha, same group, has the same problem) |
| Dainik Jagran (hi) | `/rss/news-national.xml`, `/rss/news.xml` | 404 |
| Live Hindustan (hi) | `/rss/national`, `/rss/` | 503, then 200-but-HTML |
| ABP Live Hindi + Bengali (hi, bn) | `/rss`, `bengali.abplive.com/rss` | 200 but HTML (SPA, no static feed) |
| Anandabazar Patrika (bn) | `/rssfeed/latest`, `/feed` | 403 Cloudflare |
| Ei Samay (bn) | Times-Internet `langapi/...gstandrssfeed.xml` pattern that worked for NBT/Maharashtra Times | "Page not available in your Region" (geo-gated); classic `.cms` path failed to connect at all |
| Sangbad Pratidin (bn) | `/feed/` | 403 Cloudflare |
| Bartaman Patrika, Aajkaal, Ebela (bn) | `/rss`, `/feed`, `/rssfeed/latest` | 404 / empty redirect |
| Zee News bn/gu/pa (bn, gu, pa) | `zeenews.india.com/<lang>/rss` | 403 on all three |
| Divya Bhaskar (gu) | `/rss-v1--category-*.xml` (Bhaskar-group pattern), `/rss` (its own advertised link) | 500 on category guesses; the advertised `/rss` resolves to an HTML landing page, not XML |
| Gujarat Samachar (gu) | `/rss/gujarat`, `/feed` | 404 |
| Sandesh (gu) | `/rss/sandesh-top-news.xml`, `/rss.html`, `/feed` | 200 but tiny/HTML, no usable feed found |
| Jagbani / Punjab Kesari (pa) | `/rss` | 200 but HTML (SPA) |
| Punjabi Tribune (pa) | `/feed/` | 403 Cloudflare |
| Ajit Jalandhar, Rozana Spokesman (pa) | `/rss`, `/feed` | 404 |
| Vijay Karnataka (kn) | multiple guesses incl. Times-Internet pattern | 404 / geo-gated |
| Udayavani (kn) | `/feed` | 200 but HTML |
| Kannada Prabha (kn) | `/rssfeed/?id=...` | 404 (same New Indian Express group problem) |
| Lokmat (mr) | `/rss/` | 403 |
| Loksatta (mr) | `/feed/` | 200 but HTML |
| Eenadu (te) | `/rss.xml`, homepage discovery | 200/301 but HTML, no static feed link found |
| Andhra Jyothy (te) | `/artificial/rssfeed` | 404 |
| Dinamalar, Hindu Tamil Thisai, Dinakaran (ta) | `/rss.xml` and homepage discovery | 404 on all three |
| Inquilab (ur) | `/rss` | 403 |
| Munsif Daily (ur) | `/feed/` | 200, valid feed, **but content is English**, not Urdu script (0% Urdu-block characters) — real content mismatch, not a fetch failure |
| Sahafat (ur) | `/feed/` | 200, genuinely Urdu script, **but newest item ~163 hours × 24 ≈ 163 days old** — stale/abandoned feed, fails the 48h freshness bar |
| Etemaad Daily (ur) | `/feed/` | DNS/connection failure |
| UrduPoint (ur) | `/rss` | 403 |

Recurring pattern: Bengali, Gujarati, and Punjabi came up **completely empty**
for new sources. Most rejections in these three languages are 403s with the
signature of Cloudflare/Akamai bot-management (tiny HTML body, no valid feed
markup) — the same class of block `ingestion/rss.py` already documents for
`bleepingcomputer` ("the block is on the egress IP, not on us... 200 from a
residential address and 403 from Railway"). Since that comment shows the
*production* Railway egress gets a different answer than my sandboxed curl for
at least one known case, it's plausible some of these (especially the ones on
major-outlet domains rather than the New Indian Express/News18 CMS-migration
dead ends) would resolve differently from the real worker IP. Worth a narrow
retry from Railway before concluding these three languages are truly closed
off, rather than retrying the exact URLs here again.

### Data-quality risk

- **Tamil is a documented weak spot.** `prism-clustering-lesson`/embedding memory
  notes say Kannada and Tamil embeddings carry almost no same-story
  cross-lingual signal (AUC≈0.5) — a same-event pair across languages needs
  ≥2 shared actors to merge, or it won't. The new Tamil source (Dinamani) is
  at risk of landing as permanent single-source records rather than
  corroborating with English/Hindi coverage of the same story. This is a
  pre-existing pipeline limitation, not something this change introduces or
  fixes.
- **Malayalam, Odia, Assamese have zero prior measurement.** The mE5-base
  embedding model's documented cross-lingual win (0.444→0.778) was measured
  for Kannada specifically; I found no memory entry measuring embedding or
  clustering quality for these three languages at all. Adding 6 new sources
  across them (3 Malayalam, 2 Odia, 1 Assamese) is therefore going in with an
  **unmeasured** risk in either direction — could be fine, could reproduce the
  Kannada/Tamil same-story-signal gap. Worth a same-story-pair spot check
  (mirroring the existing `tools/score_stories` / gold-pairs approach) once
  these are live, before assuming multilingual clustering "just works" for them.
- **Language registry gap is now closed for this change**: `ml`, `or`, `as` were
  not in `common/languages.py` before this pass (a source in an unlisted
  language still ingests — `is_valid_language()` only gates a reader's
  onboarding preference — but a quote would have printed as a bare "ML"/"OR"/"AS"
  instead of a name). I added all three `Language` entries; `LAUNCH_LANGUAGES`
  and `DEFAULT_LANGUAGES` were left untouched as instructed, so the onboarding
  picker still only offers en/hi/kn.
- **`common/regions.py`'s `COVERED` set is now stale**, and I could not edit it
  (out of the file scope given for this task). `COVERED` currently lists
  `{IN-TN, IN-KL, IN-KA, IN-AP, IN-TG, IN-DL, IN-MH}`. This change adds real
  dedicated-feed coverage for **Odisha (`IN-OD`)** and **Assam (`IN-AS`)** for
  the first time (Dharitri+Sambad, Asomiya Pratidin) — those two codes should be
  added to `COVERED` in a follow-up one-line change so the onboarding state
  picker correctly shows them as covered. (Telangana, Kerala, Maharashtra were
  already covered before this change via existing state editions, so
  Telangana Today/the 3 Malayalam outlets/Maharashtra Times don't change that
  set, just add redundancy within it.)
- **Unrelated observation**: `common/outlets.py` grew a `Feed`/`Monitored`/
  `monitored()` block between my first read of the file and my edit — the Edit
  tool flagged "modified on disk since you last read it" and applied cleanly on
  top. That code is unrelated to this task (looks like an admin
  coverage-monitoring feature); I did not touch it beyond appending to `CODES`/
  `DOMAINS`, and re-read the full file afterward to confirm my entries landed
  correctly and nothing else was disturbed. Worth a `git diff` sanity check on
  this file specifically before merging, since I can't rule out a second process
  writing to this shared worktree.
