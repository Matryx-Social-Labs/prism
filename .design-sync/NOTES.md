# design-sync notes — prism

- The "design system" is app-embedded (Next.js app in `web/`), no package build: synth-entry
  mode. `cfg.entry` points at a nonexistent `web/dist/index.js` ON PURPOSE — it only anchors the
  package-root walk-up to `web/`; the converter then synthesizes the entry from
  `web/src/components/`.
- **Run `sh .design-sync/build-css.sh` before every converter build** (`cfg.buildCmd`): compiles
  Tailwind v3 (utilities + tokens + Google-fonts import + `--font-*` vars) to `web/.ds-tailwind.css`
  (`cfg.cssEntry`; gitignored). Without it components render with tokens but no layout utilities.
- Next-specific imports are shimmed via `cfg.tsconfig` paths (`.design-sync/tsconfig.sync.json`
  → `.design-sync/shims/next-{image,link}.tsx`). `web/src/lib/api.ts` has a `typeof process`
  guard so the module loads outside Next.
- `.design-sync/overrides/source-kit.mjs` fork: excludes `componentSrcMap: null` files from the
  SYNTH ENTRY too (stock code only removes them from the component list) — without it PrismHero
  pulls three.js and the bundle goes 41 KB → 2.5 MB. Fork needs
  `ln -sfn ../.ds-sync/node_modules .design-sync/node_modules` per clone.
- PrismHero + HeroVisual are excluded by design (WebGL/three.js; headless capture can't verify
  them and designs shouldn't pay 2.5 MB). HeroPoster is the brand figure in the DS.
- Playwright: local chromium cache had builds 1208/1217/1223 → playwright@1.60.0 (pins 1223)
  installed in `.ds-sync/`. The `.d.ts` parse-check prints "typescript not in node_modules"
  (looks in the repo root); prop bodies are hand-written via `cfg.dtsPropsFor` — keep them in
  sync with component props when they change.
- HeroPoster preview pins the settled beam state (`stroke-dashoffset: 0; animation: none`) —
  the draw-in animations outlast the screenshot otherwise.
- StoryView preview drives everything from a static `event` fixture (briefs pre-cached so no
  fetch); LensDemo renders its built-in curated fallback when the API is absent — both are
  deterministic offline.
- Fonts are runtime Google-Fonts `@import` (`[FONT_REMOTE]`, accepted); nothing ships in fonts/.

## Known render warns
- (none — 7/7 clean, no floor cards)

## Re-sync risks
- `dtsPropsFor` bodies are hand-written copies of component props — they rot silently when
  props change; re-check whenever `web/src/components/*.tsx` signatures change.
- The StoryView fixture mirrors the EventDetail API shape (thread/coverage/entities); an API
  shape change breaks the preview composition, not the bundle.
- `build-css.sh` output is gitignored — a re-sync that skips `cfg.buildCmd` ships stale or
  missing CSS ([CSS entry missing] → converter warns "cssEntry … skipped").
- Google Fonts is a network dependency of every render — offline captures fall back fonts.
- 3D hero (`web/src/components/prism3d/`, July 2026): ported from pmndrs/examples
  `demos/nextjs-prism` (MIT) — Reflect/Beam/Rainbow/Flare + prism.glb + lensflare
  textures in `web/public/prism3d/`. The demo's LUT (F-6800-STD.cube, IWLTBAP) is
  proprietary ("cannot be redistributed") — deliberately NOT shipped; the grade is
  approximated with BrightnessContrast+Vignette. All five prism3d components are
  componentSrcMap:null in the DS config (three.js must never enter the DS bundle).
