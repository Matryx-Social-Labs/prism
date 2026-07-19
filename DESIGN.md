# Design System — Prism

Created by `/design-consultation` (2026-07-19): live competitive research (Ground News,
Semafor, Particle, Inshorts captured in-browser), an independent contrarian design voice,
and a rendered preview approved via the interactive flip demo.

## Product Context
- **What this is:** Role-aware AI news intelligence — worldwide coverage clustered into
  canonical stories, each re-readable through professional lenses. "One story. Every perspective."
- **Who it's for:** Everyone who reads news (India-first), with professional depth for
  cyber/GRC and markets readers; more lenses added continuously.
- **Space/industry:** Perspective/news-intelligence apps (Ground News, Particle, Semafor,
  Inshorts adjacency).
- **Project type:** Consumer web app + marketing landing (Next.js); mobile later.

## The Memorable Thing
**"The same story changed meaning when I flipped the lens."**
Every design decision serves the flip. Design that tries to be memorable at everything is
memorable at nothing.

## Aesthetic Direction
- **Direction:** Editorial/Refracted — a calm ivory newspaper that re-typesets itself when
  the reader flips a lens.
- **Decoration level:** Intentional — hairline rules, spectrum as 2–3px bars only, no
  gradients-as-decoration, no blobs, nothing centered by default.
- **Mood:** Semafor-grade editorial calm at rest; spectral energy exactly at the flip.
- **Reference evidence:** ground.news (density reads as homework — avoid), semafor.com
  (warm ivory + serif + one accent — the calm to match), particle.news (AI-gradient gloss —
  avoid), inshorts.com (zero-brand utility — avoid).

## The Color Rule (the brand)
**Chrome is monochrome. Color only ever means a lens is speaking.**
Anything colored that is not lens-semantic gets re-inked to the neutral scale. The lens
flip is the only colorful event on the page — that is what makes it the memorable thing.

## Typography — three voices, three jobs
- **Display/Hero:** Fraunces (400–700, opsz axis) — editorial gravitas; the storytelling voice. KEPT.
- **UI/Body:** General Sans (400/500/600, Fontshare) — replaces Space Grotesk (the
  "safe alternative to Inter" convergence trap; both design voices independently picked
  General Sans). Slightly squared counters keep 12–13px metadata legible.
- **Provenance/Data:** IBM Plex Mono (400/500) — NEW third voice. Used ONLY for evidence:
  timestamps, source codes, citation numbers `[3]`, funding labels (STATE-AFFILIATED /
  PUBLIC), chain dates, CVE ids, tickers. Teletype heritage: provenance should look like
  evidence. Discipline: never for prose, never for headings.
- **Loading:** next/font (Google: Fraunces, IBM Plex Mono; Fontshare CDN or self-host:
  General Sans). CSS vars: `--font-display`, `--font-ui`, `--font-mono`.
- **Scale:** display 76/64/42px (landing hero xl/sm/base), 34px story H1, 30px page H1,
  23px section H2, 15.5px card title, 14.5px body, 13.5px secondary, 12.5px captions,
  11px chips, 10.5px mono-micro.

## Color
- **Approach:** Restrained, rule-driven (see The Color Rule).
- **Grounds (adaptive):** light `#FAF8F5` ivory / dark `#0F0E0C` warm charcoal;
  surfaces `#FFFFFF` / `#171512`; sunken `#F1EDE7` / `#211E1A`.
- **Ink scale:** `#1C1917` ink, `#78716C` muted, `#A8A29E` faint (dark: `#ECE9E2` /
  `#A8A29E` / `#78716C`); lines `#E7E2DA` / `#2B2723`.
- **Lens hues (semantic, discrete — never gradients):** General reader amber `#F59E0B`,
  Cyber cyan `#06B6D4`, Markets violet `#8B5CF6`; future lenses draw from a reserved
  palette (sky `#0EA5E9`, rose `#F43F5E`, lime `#84CC16`, fuchsia `#D946EF`).
- **Spectrum gradient:** brand accent, hairline bars (2–3px) and gradient text only.
- **Semantic:** up/success `#047857` (dark `#34D399`), danger `#B91C1C` (dark `#F87171`);
  warning uses amber only when not lens-ambiguous in context.
- **Dark mode:** same hue relationships, warmed surfaces, saturation held (lens hues are
  identical across themes — they are semantic identifiers, not decoration).

## Spacing
- **Base unit:** 4px; **Density:** comfortable.
- **Scale:** 2xs(2) xs(4) sm(8) md(16) lg(24) xl(32) 2xl(48) 3xl(64).

## Layout
- **Approach:** Hybrid — grid-disciplined app, poster-style landing.
- **Max content width:** shell/landing 1320px, feed/sector 1200px, story 880px,
  about 760px, onboarding/interests 720px; padding `px-5 sm:px-8 xl:px-10`.
- **Border radius:** chips/pills 9999px, cards 18px, panels 22px, thumbnails 12px.
- **Alignment:** hard left edges for content; centered only for marketing section heads.

## Motion
- **Approach:** Intentional, with ONE signature: **the re-typeset flip.**
  - Never a crossfade. A 2px lens-colored scan line sweeps the lens block (~500ms
    ease-out); the brief re-inks behind it (opacity .25→1); underlines, hairlines, and
    markers adopt the lens hue; annotations stagger in at 60ms.
  - Body text and layout never move — the reader must feel it is the same story, re-read.
- **Everything else stays subtle:** reveal-on-scroll, stagger lists, fade-swap; existing
  beam/prism hero animations unchanged.
- **Easing:** enter ease-out, exit ease-in, move ease-in-out.
- **Duration:** micro 50–100ms, short 150–250ms, medium 250–400ms, flip 500ms.
- **Reduced motion:** every animation (including the flip) collapses to an instant swap.

## Named Risks (deliberate departures)
1. **Color-is-a-lens discipline** — quieter feed at rest; the flip becomes the only
   colorful event. Non-lens colored chips get re-inked.
2. **The re-typeset flip** — signature choreography scoped to the lens block.
3. **Provenance mono** — third font family; strict usage discipline.
4. **General Sans UI swap** — escapes the Space Grotesk AI-tool convergence.

## Decisions Log
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-19 | Initial DESIGN.md via /design-consultation | Live research + outside voice + approved interactive preview |
| 2026-07-19 | Memorable thing = the lens flip | Founder choice (D2) |
| 2026-07-19 | Keep light+dark, keep lens hues, keep WebGL prism hero | Founder's prior explicit calls; contrarian "Night Desk" dark-only direction declined |
| 2026-07-19 | Space Grotesk → General Sans; add IBM Plex Mono provenance layer | Anti-convergence + both design voices agreed |

## Preview artifact
`~/.gstack/projects/Matryx-Social-Labs-prism/designs/design-system-20260719/prism-design-preview.html`
(interactive flip demo; open in any browser)
