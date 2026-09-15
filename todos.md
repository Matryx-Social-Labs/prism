# TODOS

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
- **Landing page: markets-first coherence** (P2). Page says "role-aware news for everyone" while
  the sell is "markets intelligence, India." Lead the hero proof with the Markets lens on an
  Indian market-moving event.

## Design resilience (ship WITH E5 — public SEO story pages)
- **`.reveal` content is JS-dependent** (P2, from /design-review 2026-07-19). `globals.css:155`
  sets `.reveal { opacity:0 }` unconditionally; only client JS (`Reveal.tsx` useEffect) or the
  reduced-motion CSS restores it. Default-motion + no-JS (crawlers, social-preview bots, JS
  failure) render 6 content sections invisible. Low impact for real users now; becomes a real
  SEO problem when E5's public story pages ship. Fix (~3 lines): add
  `document.documentElement.classList.add('js')` inline in the layout `<head>`, change
  `.reveal { opacity:0 }` → `.js .reveal { opacity:0 }` so content is visible without JS.
  Files: `web/src/app/globals.css`, `web/src/app/layout.tsx`.

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
