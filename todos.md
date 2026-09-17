# TODOS

## Redesign — the Reservation Chart (status, one line per surface)

Brief: `~/.gstack/projects/Matryx-Social-Labs-prism/designs/redesign-20260915/01-shape-brief.md`
(surfaces 1–11, states, anti-goals). Contract: `.impeccable/surfaces/web-src-app-page-tsx.md`.
Truth: `PRODUCT.md`. Everything lands on `dev`; nothing promotes until the founder has seen
the preview. **Until every row below is DONE, untouched surfaces render the OLD layout in the
NEW type and palette** — the foundation swapped the global fonts and grounds for every page
at once (c244aa6), which is why a half-built dev looks worse than either end state.

| # | Surface | Status | Notes |
|---|---|---|---|
| 0 | Foundation — palette, three voices, six sectors, `?sector=` list, SectorStrip, Masthead | DONE c244aa6 | |
| 1 | Front page `/feed` — the chart (Today · For you, scope, sector re-sort) | DONE c61dcc8 | not yet: `/feed/yesterday` (API has no day window), in-place FLIP re-sort, sub-sector chips, desktop rail, "Moving now" |
| 2 | Sector `/sector/<slug>` | DONE c61dcc8 | |
| 11 | Landing `/` (first visit) + `/about`; returning readers → `/feed` | REBUILT 4218595 | founder rejected the first version; rebuilt under design-taste-frontend: general news only (cyber filtered), Delhi diesel-ban flip demo, real rows with the lead's photo, one feature grid with the product doing each thing, next/tiers/close. Fresh finish review: fix → fix → **ship** (this surface). Found on the way: Hind was never loading anywhere (--font-ui on :root), fixed product-wide |
| 3 | Story `/story/<id>` — the ticket (strip · route · passenger list · coaches; lens flip kept, Perspectives cards retired per D4) | DONE 9d8b026 | not yet: tapping a station re-typesets in place (stations still navigate) |
| — | Chrome: SiteHeader, footer | DONE 41da9ab | Teko wordmark and nav, no spectrum bar, monochrome toggle |
| 4 | Trending `/trending` — the chart of arcs | DONE 19500ee | API: comma-list ?sector=, hero_event_id / first_seen_at / last_updated_at (needs promote before the preview shows them) |
| 6 | Search `/search` | DONE dc44247 | query on the masthead's second line, ChartRows, strip filters in place |
| 8 | You `/you` — the reservation form | DONE (this commit) | ReservationForm: state · languages · profession → lens · six subjects with beats; /interests redirects here; YouDesktop retired |
| 9 | Onboarding `/onboarding` | DONE (this commit) | the same fields in three steps |
| 5 | Pulse `/pulse` | DONE (this commit) | dated supplement, markets hue marks the read, tickers → watchlist rows (signed in) or search |
| 7 | Watchlist `/watchlist` | DONE (this commit) | a chart of the reader's signals, ticker in the count column, ?ticker= narrows; StoryCard retired |
| 10 | Sign-in / unlock — the paywall moment | DONE (this commit) | the unlock sheet was already re-set with the ticket (9d8b026); sign-in, account and the arc page's headings follow. Left for the finish review: AskPanel's chrome (mechanics untouched per the brief), /label (internal tool) |
| F | Finish — detector, finish review, documenter → new DESIGN.md | DONE (this commit) | detector clean at 390/1440 on every surface; finish review: fix → fix → **ship** (scoped to the fix list); DESIGN.md + `.impeccable/design.json` rewritten from the shipped build; CLAUDE.md core rules synced. Left for a later pass: /label (internal tool), the orphaned 3D hero files, unused CSS leftovers (`--shadow-*`, `.spectrum-*`, `.beam-*`, `.stagger`) |

All rows done on `dev`; nothing promoted. Next: founder review on the preview, then `make promote`.

**The page designs, implemented (2026-09-17, founder decisions 1b · 2 · 3 · 4 · 5, direction A):**

| What | Status | Notes |
|---|---|---|
| The route as the rail map (direction A), phone and desk, on the ticket (compact) and the route page (whole), with the attention curve as a toggle | DONE 50cbdab | `lib/route.ts` reads the whole record: through satellites to the nearest on-spine ancestor, a branch carries everything under it, parentless members are branches from the root |
| One floating Ask at every width; the docked panel is gone | DONE 70e41d6 | launcher pill from 1024px; the thumb-zone button opens the same sheet on a phone |
| So what and Coverage back on the ticket | DONE e3ceef7 | Perspectives cards stay retired (D4) |
| The landing's Ask illustration is the ticket's own panel, scripted | DONE 67c5452 | `AskShell` shared by `AskPanel` and `AskDemo` |
| Prism headline, labelled (1b) | DONE 0073321 | `events.headline_by`; extractor returns `headline`; **founder: run `uv run python -m tools.backfill_headlines` on prod (dry run prints the count and token estimate; `--apply` is the spend)** — until then tickets say "Headline as filed by {outlet}" |
| Route glyph on the chart of arcs | DONE db0945e | each trending row carries its route; read with the same `routeShape` |
| Related routes (shared cast · causal links), never drawn on the rail | DONE 8a0d344 | on the ticket's route and the route page; shared cast ≥2 or an event_links note across the boundary |
| Lens facts first, then the brief | DONE b1b4d23 | |
| Share cards in the row grammar | DONE 5f5ad6b | Teko · Hind · Martian Mono, both cases fetched |
| Sign-in with Google | WAITS on OAuth (end of redesign) | the design's "Continue with Google · next" is not shown until it works |
| The design prototype's rail map on a phone | NOT PORTED | `designs/pages-20260917/spine.js` draws the desk form only; the app has the tall form |

**Labelling round 3 (2026-09-17)** — two batches on prod, invites minted for Tejas and Vijay
(tokens are in the links sent, never here): `7tfe0eIBu1GH` = "Stories · the live window ·
September 2026" (121 story-boundary tasks, seeds from the last 14 days, `tools/gold_candidates
--since-days 14`); `MGDmtLPZOdjy` = "Same happening, across languages · September 2026" (150
event_identity tasks, `tools/gold_crosslingual`). Watch with `--status --batch KEY`, agreement
with `--agreement`, compile with `gold_candidates --compile-batch` / `gold_crosslingual --compile`.
The cross-language answers become batch 3 of `tools/gold_pairs.GOLD_PAIRS`; the story answers
extend `tools/gold_stories.STORIES` (keep the CJP slice, quote it as such).

**After the redesign (founder, 2026-09-16):**
- **Google / OAuth sign-in replaces the browser-saved profile as the account model** (P1). Today the
  profile is `prism.profile.v1` in localStorage and sign-in is a magic link; the founder wants an
  OAuth login (Google first) so the profile follows the reader. Touches `lib/session.ts`,
  `lib/profile.ts`, the API auth routes, and the onboarding hand-off. Do it as one change at the end
  of the redesign, not piecemeal.
- **English-only for now**: languages are no longer collected in onboarding or on /you (done
  2026-09-16); the profile keeps `languages: ["en"]` so the feed contract is unchanged. Re-add the
  field when non-English display is switched on. Checkpoint (commit + preview) after each row.


Deferred work captured from the CEO plan review (2026-07-19, freemium lens model).
Full context: `~/.gstack/projects/Matryx-Social-Labs-prism/ceo-plans/2026-07-19-freemium-lens-model.md`

## Phase 2 (after the paid markets lens ships and converts)
- **Watchlist push / alerts** (P2). Web + mobile push infra, trigger definition, delivery
  latency. The expensive half of the watchlist; v1 ships read-only follow only. Open question:
  is 30-min ingest cadence fast enough, or does the watchlist need a faster deterministic lane?
- **Premium-TTS provider selection + audio caching** (P2). Only after E6 (voice brief) usage is
  measured. Browser Web Speech is the free-tier default; pick/cache premium TTS once volume is real.
- **Expo React Native app** (P3) reusing the typed `/api/v1` client. App-store distribution.
- **Regional-language + broker-research sources** (P3).
- **Lite ₹99 tier** (P3). Only if ₹399 conversion needs a lower rung.

## Validation-first (strongly recommended to run in parallel with the build)
- **Paid pilot with ~10 traders** (P1). Pre-order / paid trial, not a verbal "would you pay."
  Plus the Langfuse per-stage cost report. Two numbers decide price + first cut.
- **First-user calibration** (P2). Test whether active F&O traders (want speed) or swing/
  long-term retail / finance creators are the right first paid cohort before hardcoding acquisition.

## From the claims-display eng review (2026-09-15)
- **Retire the Perspectives cards once claims are seen beside them** (P2). The rebuild plan
  names verbatim claims as the successor to the ≤4 LLM "competing narratives" (per-event not
  per-story, speaker is a string, no quotes, no time, every article forced into one group).
  The new "What was said" section is rules-and-type; Perspectives is still cards, which
  DESIGN.md forbids on desktop. Keep both until the founder has looked at a real story with
  both present — Perspectives has origin-country grouping that claims does not.
  **Depends on:** the claims section shipping; a look at ~5 live stories.
- **Per-entity story ledger — fold speakers across a story's events via QIDs** (P2). Today
  claims group by speaker STRING per event, so "Pradhan", "Dharmendra Pradhan" and "the
  Education Minister" are three rows across a story. Decision 5 of the rebuild plan wants one
  row per person with their position over time. Needs `entities.qid` populated (22% of df>=2
  entities on 2026-09-14, `entity_alias` empty) and `office_holders` for role→person.
  **Depends on:** plan step 5 (Wikidata linking) reaching useful coverage.
- **Desktop rail leaks paid-lens facts for a LOCKED lens** (was P2). `StoryDesktop.railFacts`
  renders `projection.cyber.exploitation.kev_listed`, CVSS and `finance.tickers` when the
  selected lens is cyber/markets. `get_event` filters `lens_briefs`/`lens_points` out of
  `projection` for locked lenses but NOT the `cyber`/`finance` keys, and a signed-out reader
  can select a locked lens (the flip happens, the brief is gated). So the rail shows "CISA
  KEV LISTED" for a lens the reader has not unlocked — the same class as the `/questions`
  leak closed in 4bde965. Fix is ~3 lines in `get_event` (drop `cyber`/`finance` from
  `safe_projection` unless unlocked) plus one route test; flagged during the claims review
  and kept out of that PR to keep it scoped.
  **Completed:** 2026-09-15 — `PAID_LENS_FIELDS` in common/lenses.py, gated in get_event; the
  route test also covers the f230e0d prose gate, which had none.

## Positioning
- **Distribution plan is hand-wavy** (P2). FinTwit/Telegram/YouTube are crowded + pay-to-play.
  Name concrete channels, a creator list, an offer, and a CAC assumption before spending.
## Broader unit metrics (feed the cost cockpit, E3)
- Track cost per acquired user, per active free user, per trial, per paid subscriber, and
  worst-case Ask abuse — not just cost per served event (P2).

## Mobile web (deferred from /ship 2026-07-25, v0.0.70.0 — review findings not fixed in that branch)
- ~~**Feed thumbnails download full-resolution publisher images**~~ → Completed below. (P1). `next.config.ts` sets
  `images.unoptimized: true` (news CDNs block Vercel's optimizer via hotlink protection), and
  the mobile redesign made `StoryRowCard` thumbs visible below 640px. Measured on the live
  feed: natural width 1200px painted into a 64px box — roughly 350x the pixels needed, per
  visible row, on the India-first mid-range-Android target. `loading="lazy"` bounds it to what
  the reader actually scrolls past, so it is not catastrophic, but it is the largest payload
  regression in the redesign. Fix needs a thumbnail proxy/resizer we control (the CDNs allow
  browser requests but not datacenter ones), or per-CDN URL size params.
  Files: `web/next.config.ts`, `web/src/components/StoryCard.tsx`.
- **Feed and Trending fire throwaway requests on every mount** (P2). `loadProfile()` is a
  synchronous localStorage read but is called inside a mount effect, so the fetch effects run
  once with `profile: null` and again with the profile — ~3 discarded round trips per feed
  mount, and the module cache means Feed re-mounts on every return from a story. The race is
  already handled with a `cancelled` flag; this is the wasted mobile data, not correctness.
  Gate the fetches on a `profileLoaded` flag. Files: `web/src/app/feed/page.tsx`,
  `web/src/app/trending/page.tsx`.
- **OG share cards are off-brand and Latin-only** (P2). Both card routes use cool Tailwind
  greys on pure white with Georgia + generic monospace, not the warm DESIGN.md palette or
  Fraunces/IBM Plex Mono, and pass no `fonts` to `ImageResponse` — so a Hindi/Tamil/Telugu
  headline renders as tofu boxes. This is the most-seen brand surface in the WhatsApp share
  loop. Files: `web/src/app/story/[id]/opengraph-image.tsx`,
  `web/src/app/trending/[slug]/opengraph-image.tsx`.
- **Three stacked `backdrop-blur` layers on the scrolling feed** (P2). Sticky header + sticky
  sector rail + bottom tab bar all composite a translucent blur every frame; stacked
  backdrop-filter is a reliable source of scroll jank on mid-range Android GPUs. Drop the blur
  from the secondary layers and use an opaque background. Verify with a throttled trace.
  Files: `web/src/app/feed/page.tsx`, `web/src/components/BottomTabBar.tsx`.
- **Frontend coverage is ~33%** (P2). vitest now covers the pure-logic surface (scroll
  restore, sharing, tab bar, header). The page components — Feed, Trending, Story, You — are
  untested; they need fetch/session/router mocking or, better, Playwright E2E for the
  return-navigation and share flows. Files: `web/src/app/**`.
- **Duplicated mobile UI logic** (P3). The scope bottom sheet is copy-pasted between Feed and
  Trending and has already drifted; the lens pill is duplicated between the desktop strip and
  the mobile rail (the mobile one dropped `role="tab"`/`aria-selected` and the locked-lens
  tooltip); `SiteHeader.APP_ROUTES` and `BottomTabBar.SHOW_ON` are two route lists with the
  same matcher written three times; `stateLabel` hardcodes seven Indian states while Feed
  resolves names from `fetchRegions()`. Files: `web/src/app/feed/page.tsx`,
  `web/src/app/trending/page.tsx`, `web/src/components/StoryView.tsx`,
  `web/src/components/SiteHeader.tsx`, `web/src/components/BottomTabBar.tsx`.


## Completed
- **Landing page: markets-first coherence** (was P2). Superseded by D1:A (the general reader
  leads) and closed by the 2026-09-16 rebuild: one pitch, no lens names in prose.
- **`.reveal` content is JS-dependent** (was P2). `Reveal.tsx` and `.reveal` were deleted with
  the old landing (c487212); the rebuilt landing has no scroll-reveal — every section is in
  the HTML.
- **Scope chip claims to apply everywhere but doesn't** (was P2). Scope now lives in
  `web/src/lib/scope.ts` (localStorage, `parse.scope.v2`) and is read by both Feed and
  Trending, so the sheet's promise holds. The tiers were also unified to All / <state> /
  National — the Feed had been calling the widest tier "World" while Trending called the same
  thing "National" one tap away.
  **Completed:** v0.0.72.0 (2026-07-26)
- **A failed search rendered a blank screen** (was P2). A rejected `searchEvents` left every
  render branch false — no error, no empty state, nothing. Now a distinct failure message that
  does not falsely claim the query had no matches.
  **Completed:** v0.0.74.2 (2026-07-27)
- **`fetchRegions()` had no `.catch`, and the state select had no accessible name** (was P3).
  **Completed:** v0.0.74.2 (2026-07-27)
