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
