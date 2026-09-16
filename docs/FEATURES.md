# Prism — the feature inventory (2026-09-17)

The single list of what Prism does, what it half-does, and what it is going to do,
so the page designs can be decided from it rather than from memory. Status words:

- **LIVE** — built, tested, shown to readers on `dev`.
- **BUILT, NOT SHOWN** — the data or endpoint exists; no surface renders it today.
- **PARTIAL** — built for part of its scope; the gap is named.
- **PLANNED** — in the rebuild plan or a founder decision, not started.
- **DEFERRED** — deliberately after something else; the precondition is named.

Sources: `PRODUCT.md`, the rebuild plan, `todos.md`, `api/routes/*`, `web/src/lib/api.ts`,
`common/lenses.py`, `correlation/partition.py` and `trending.py`.

---

## 1. The record (what the pipeline makes)

| Feature | Status | What it is, precisely |
|---|---|---|
| Multi-outlet ingestion, India-first | LIVE (corpus frozen) | 42 RSS sources across six languages → relevance gate → extraction. `PRISM_INGESTION_ENABLED=false` since 2026-09-05; the corpus is ~19k events / 1,357 stories. Ingestion restarts when the founder decides sources (2 of 42 are business). |
| **Canonical event** ("one story" in the reader's words) | LIVE | One real-world incident, every article that reported it: `events` with `source_count`, `sources[]` (outlet, URL, published time, funding label), `regions`, `sector`/`subsector`, `image_url`, `summary`. Corroboration = the count. |
| Event title | LIVE, convention undecided | Today `event.title` is the hero article's headline (one outlet's words, in that outlet's language). A story's label prefers the hero's English headline, then any Latin-script title, then the cast. **Decision needed: what the canonical title is** (see §7). |
| Story (an arc of events) | LIVE | `stories` = a frozen member set of events with `hero_event_id`, `first_seen_at`, `last_updated_at`, `velocity`, `source_count`. Served by `/trending` and `/trending/{slug}`; the ticket reaches its story through `story_slug`. |
| Spine / branches / satellites | LIVE | `partition.py` roots each story at its most-corroborated event and writes `branch_parent_id` + `off_spine` per member. `BranchTree` prints: the **trunk** (longest on-spine chain from the root), **branches** (on-spine children not on the trunk, collapsed with a date span), **satellites** (off-spine, shown under ALL), and the counted shape `N DEVELOPMENTS · N BRANCHES · N SATELLITES · SPAN`. |
| Causal notes between developments | LIVE | `event_links` "why" rationale (563 in prod) rendered as `↳ why` under a development on `/trending/{slug}` (StoryTimeline). Costs ~9 % of LLM spend; founder decision pending on keeping it. |
| Six subjects | LIVE | Politics · Business & Markets · Sports · Tech & Cyber · Health & Science · Entertainment, grouping the pipeline's ten sectors; "Other" is never a heading (D3). |
| Regional tagging | LIVE | `is_regional`, `regions[]` per event; state-level scope (All / your state / National) on the chart and trending. |
| Multilingual corpus | LIVE, display English-only | Hindi/Kannada/Tamil/Telugu/Marathi articles are ingested and clustered with English (mE5). Display is English-first; **languages are not collected from readers for now** (2026-09-16). |
| Entity spine (Wikidata QIDs) | PLANNED (step 5) | Canonical IDs for people/parties/companies; fixes the 39 split slugs and IDF distortion; unlocks the per-story ledger, office-holder resolution and QID→ISIN tickers. |
| Story-layer quality | KNOWN CEILING | Story boundaries score P 0.02–0.09 as-of; 7 levers rejected; the representation is the ceiling. Gold sets adjudicated (`tools/gold_story_pairs.py`, `tools/gold_claims.py`). |

## 2. Evidence (what a reader can check)

| Feature | Status | What it is |
|---|---|---|
| **Sources list** (the "coaches") | LIVE | Every article on the event: `[n]`, outlet, headline, time, stance label if any, funding label (public broadcaster / state-affiliated) if known. `[n]` is the one index quotes and Ask citations share. |
| **Who said what** (verbatim claims) | LIVE | `claims[]` grouped by speaker: quote text checked verbatim against the article, `[n] · outlet · date`. No stance, no "said at" (model opinions never sit beside a verified quote). 1,285 verified claims, ~45 % of live events. Precision 0.983 on the gold set. |
| Coverage origins | LIVE (data), PARTIAL (display) | `coverage.origins` (IN ×44 · US ×2), `single_origin` flag. The ticket's strip prints origins; the single-origin flag is not called out. |
| Coverage gap for your region | BUILT, NOT SHOWN | StoryView computes "your state has not reported this" (`gapText`) when the reader's region is absent from the origins; it is no longer rendered on the ticket. |
| Per-speaker story ledger | DEFERRED (waits on QIDs) | "What has X said across this story" — speakers fold across events only once speakers are QIDs (step 5c). |
| Position changes (two quotes side by side) | DEFERRED (5d) | Ships only after evaluation on a large labelled sample. |
| Coverage contribution ("who broke what") | PLANNED (after claim recall is measured) | Share of unique claims first reported by each outlet; the inverse of syndication inflation. |
| Both sides (stance-grouped framings) | BUILT, RETIRED FROM DISPLAY (D4) | `perspectives[]` (label, stance, origin, summary) still comes with the event; the cards were retired because the route + verbatim quotes are the perspectives. **Founder wants this shown as "being built next"** — the honest version is stance-grouped *quotes*, which waits on 5c/5d. |
| So what (consequence graph) | BUILT, NOT SHOWN | `impacts[]` per event (entity, effect, direction, horizon, parent) is extracted and served; it was displayed until the ticket rebuild (9d8b026) and is not now. Cheap to restore. |
| Blindspots (one-sided coverage) | PARTIAL | `single_origin` exists per event (origin-country basis). "Every outlet aligned with one party" needs stance at the outlet level — not built. |
| Silence as signal | DEFERRED | Needs claim recall ≥ 0.9 first; otherwise "silent" = "we missed it". |

## 3. Reading (the lens)

| Feature | Status | What it is |
|---|---|---|
| **Lens registry** | LIVE | `/api/v1/lenses`: reader (free), cyber, markets (paid); health, policy are `upcoming=True` (drafted, not served). Never enumerated in copy; UIs render the registry. |
| **The lens flip** (the signature) | LIVE | Per-story tabs; scan line + re-ink, 500 ms; keys 1/2/3 on desktop; instant under reduced motion. Untouched by the redesign. |
| Lens brief + "what to watch" points | LIVE (LLM-written, cached) | `/events/{id}/brief` per lens; reader brief free; paid briefs behind sign-in with 3 free Markets samples (`try_consume_sample`). |
| Lens facts on the record | LIVE, gated | Cyber: CVE ids, CVSS, KEV/exploitation, affected products, remediation, control mapping. Markets: validated tickers (15,701-row securities master, 0 unvalidated), catalyst, price-impact direction. Facts are nulled for a locked lens (paywall gates facts, not only prose). |
| Listen (narration) | LIVE | Browser speech synthesis of the brief and points (BriefPlayer). |
| Lens markers on the chart | LIVE | A 7 px lens-hued dot on a row when a professional read exists for it. |
| Health / Policy lenses | PLANNED | Registry entries exist as `upcoming`; prompts and fields not built. |

## 4. Ask (grounded Q&A)

| Feature | Status | What it is |
|---|---|---|
| **Ask this story** | LIVE | `POST /events/{id}/ask` streams an answer grounded in the event's own chunks; citations `[n]` map to the sources list; refuses with "Not in sources" when the record does not cover the question. Suggested questions come from the lens. Metered: 3 per anonymous session, 30/day signed in. |
| Ask tests | PLANNED (step 10) | `agent/rag.py` has no tests yet; it carries the trust claim. |
| Ask across a story (not one event) | NOT PLANNED YET | Retrieval scope is one event. |

## 5. Navigation and personalisation

| Feature | Status | What it is |
|---|---|---|
| **Today's chart** (`/feed`) | LIVE | One public list, most-corroborated first, same for everyone (D2); a window of 60; dashed rule for single-source rows; rows print in; "For you" tab once interests exist. |
| Sector re-sort in place (`/sector/{slug}`) | LIVE | The strip filters the same day's rows; URL follows. |
| Scope (All / your state / National) | LIVE | Client-side on the chart; National-only on trending. |
| Trending (chart of arcs) | LIVE | Stories by velocity: developments, moved, span; a row opens the ticket with the route in view. |
| Search | LIVE (ILIKE full scan) | Stories, entities, tickers, CVE ids; strip filters results. Index (tsvector) is PLANNED (step 10). |
| The reservation form (`/you`, onboarding) | LIVE | State → profession (sets the lens) → six subjects with beats. Profile in `localStorage` for now. |
| Watchlist | LIVE (signed in) | Follow tickers and sectors; stories that mention them; `?ticker=` from Pulse. |
| Market Pulse (`/pulse`) | LIVE (LLM digest) | Daily markets digest with movers; free. |
| Yesterday's chart | PLANNED | The API has no day window yet. |
| Push / alerts | DEFERRED (phase 2) | After the paid tier converts. |

## 6. Accounts, money, distribution

| Feature | Status | What it is |
|---|---|---|
| Sign-in | LIVE (magic link) | Email → one-time link → bearer session in `localStorage`. |
| **Google / OAuth login** | PLANNED (founder, 2026-09-16) | Replaces the browser-saved profile as the account model; one change at the end of the redesign. |
| Paywall (lens depth) | LIVE (mechanics), no checkout | Locked lens still flips; inline "sign in to unlock"; 3 Markets samples then sign-in. No pricing UI, no payments (UPI Autopay via a PSP is phase 4). |
| Tiers | DECIDED, NOT SOLD | Reader free · Markets ₹299/mo · Cyber ₹299/mo · API/B2B later · ads in reserve. |
| Public story pages, OG cards, sitemap, robots | LIVE | `/story/{id}` and `/trending/{slug}` render server-side with OG images. |
| Landing (`/`, `/about`) | LIVE (rebuilt twice; founder unhappy) | Persuade surface; the subject of the next design round. |
| Internal labelling tool (`/label/{key}`) | LIVE (internal) | Gold-set labelling for Tejas/Vijay; out of the reader's product. |

## 7. Decisions the page designs depend on

1. **The canonical title.** Options: (a) the hero article's headline as now (one outlet's words; often not English); (b) a Prism-written headline from the summary (consistent voice, but LLM-authored and must be labelled as ours); (c) the hero's *English* headline where one exists, else (a) — what stories already do. The same rule must hold on the chart row, the ticket, the route, search, watchlist and share cards.
2. **How the spine is shown on the ticket.** Today: BranchTree (trunk rows, collapsed branches, satellites under ALL) plus the counted shape line. Question for the founder: does the ticket show the *whole* route (the story) or only *this event's place on it* (parent, siblings, children), and what does a branch vs a fan-out look like to a general reader — vocabulary, not just lines.
3. **Which "being built next" features get a slot on the ticket now** (with real data): So what / impacts (BUILT), coverage gap (BUILT), single-origin flag (BUILT); versus which stay as a line on the landing (Both sides, Blindspots by party, ledger, position changes).
4. **Where Ask lives**: a docked panel on the ticket (now), a sheet on the phone (now), and whether the landing shows it as a real interactive demo on a real story (possible: it works on any event) or a written exchange (now).
5. **Titles across surfaces**: chart row = title; trending row = story label; ticket = title + story label? One rule.

## 8. Page map, decided (2026-09-17)

Founder decisions: 1 (b) Prism-written headline, labelled; 2 the ticket shows this event's place
on the route (my proposal, to iterate); 3 So what and coverage back on the ticket; 4 Ask on the
landing as an animated exchange; 5 planned features as "Being built next" sections.
The HTML designs for every page are in
`~/.gstack/projects/Matryx-Social-Labs-prism/designs/pages-20260917/` (open `index.html`); its
`README.md` carries the feature-to-page coverage table and the spine vocabulary (main line,
this development, a branch, a branch line, also reported off the main line, related routes).

| Page | Contains | Reached from / leads to |
|---|---|---|
| `/` landing (signed-out) | Promise · the flip demo · today's chart (4 real rows) · what you get (one cell per LIVE feature, each showing the product) · being built next · tiers · one action | → `/feed`, `/onboarding`, `/signin` |
| `/feed` today's chart | Masthead (date · window · sources) · strip · Today / For you · rows | → `/story/{id}`, `/sector/{slug}` |
| `/story/{id}` the ticket | Strip (code · sources · origins · time) · title · lens tabs + brief + points · **the route** (this event on its story's spine) · who said what · sources · Ask · share/follow | ← chart, trending, search, watchlist, share links → `/trending/{slug}` for the whole arc |
| `/trending` | Chart of arcs (developments · moved · span) | → ticket (route in view) |
| `/trending/{slug}` the arc | Story label · the full route (BranchTree) · timeline with causal notes | ← ticket |
| `/search` | Query · rows · strip filter | → ticket |
| `/you` + `/onboarding` | The reservation form (state · profession · subjects) · following · account | → `/feed` |
| `/pulse` | Markets digest · movers | → watchlist rows / search |
| `/watchlist` | Signals · rows | → ticket |
| `/signin`, `/account` | Magic link now; OAuth later | |
