# web/

The Next.js application: onboarding (job role and interests), the personalized feed, the story view
with the three-part experience (Both Sides, So What, Ask), trending, market pulse, search, and a
`/you` hub that folds account, interests and watchlist into one screen. In Phase 2 it adds the
trader fast-lane surface.

The app surfaces are mobile-first (bottom tab bar as the nav spine, lens rail in the thumb zone on
Story) and scale up to desktop; the marketing landing stays desktop-led.

```bash
npm install
npm run dev      # :3000, expects the API on :8000
npm test         # vitest + jsdom (CI gate); npm run test:watch to iterate
npm run build    # typecheck + build, same as Vercel (CI gate)
```

See [../docs/PRODUCT-BRIEF.md](../docs/PRODUCT-BRIEF.md), [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md),
and [../DESIGN.md](../DESIGN.md).
