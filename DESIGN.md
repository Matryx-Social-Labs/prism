# Design System — Prism

> Named **Prism** → **Parse** on 2026-07-25 (v0.0.71.0), and back to **Prism** on
> 2026-07-28 (v0.0.78.0) once `readprism.news` was secured. The design system never
> changed through either — only the name and the mark. That is the tell: the
> spectrum hairline and the discrete lens hues were always the prism's argument,
> so the mark reverted with the name while everything else stood still.
>
> Historical entries below were written under whichever name was current at the
> time; the design decision each records is unaffected.

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
- **Project type:** Consumer web app + marketing landing (Next.js). The app surfaces
  (Feed, Story, Trending, You) are mobile-first as of 2026-07-25; the marketing landing
  stays desktop-led.

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
- **Max content width:** header/footer chrome 1280px; content shells
  (landing/feed/sector/story) 1240px so their columns share a left edge; the story
  reading column sits ~880px inside its rail layout; about 760px,
  onboarding/interests 720px; padding `px-5 sm:px-8 xl:px-10`.
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

## Desktop — the width rule (2026-07-25)
**Extra width goes to simultaneity, never to longer lines.** The reading measure is
already right at ~620–680px for 15.5px text; widening it makes the product worse. On
a phone the evidence layer (outlet count, origins, single-origin flag, what else is
moving) is a drill-down behind a tap. On desktop it becomes **ambient** — visible
beside the story without a click. Every desktop app screen is therefore a
proven-measure reading river flanked by context that was previously buried. Rails
carry evidence and orientation, never decoration.

Research behind it: semafor.com (3-zone masthead on full-bleed ivory — the calm to
match), ground.news (evidence inline on every row — take the ambience, reject the
density, which DESIGN.md already calls "homework"); ft.com blocked the capture.

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
| 2026-07-23 | Feed v3: remove feed lens pills; scope selector (All / <state> / National) + language chip replace them; Trending joins the nav | Lens is a per-story flip, not a feed filter; quieter chrome at rest (Prism UI Design.dc.html, frame 3a) |
| 2026-07-23 | No global lens switcher in the header chrome | Founder call (B): lens is set in "Your Prism" and flipped per-story; deliberate departure from design v3, which kept a header lens chip |
| 2026-07-23 | Content shells unified to 1240px (header/footer 1280px) | Column left-edges line up across landing/feed/sector/story |
| 2026-07-25 | App surfaces rebuilt mobile-first: bottom tab bar (Feed · Trending · Pulse · Search · You) is the nav spine on phones; global brand header hidden on app routes; footer hidden behind the tab bar | A phone reader was getting a shrunk desktop site with two stacked headers (Prism Mobile.dc.html) |
| 2026-07-25 | On Story, the lens rail + Share/Ask pin to the thumb zone instead of a desktop sidebar | The flip is the memorable thing — it has to be reachable one-handed, and the flip must scroll the brief into view to stay visible |
| 2026-07-25 | Desktop width rule: extra width buys simultaneity (ambient evidence), not longer lines | Reading measure is already correct; the phone's drill-down evidence layer becomes visible-at-once on desktop (research: Ground News ambience minus its density) |
| 2026-07-25 | Feed is a ruled editorial river, never a card grid | Prism sells canonical understanding, not abundance — a grid optimizes browsing volume, which is the wrong promise (Codex design voice, agreed) |
| 2026-07-25 | Desktop lens control lives on the lens brief's top edge, sticky only while the brief is in view — never in the header or rail | With no thumb zone the flip needs proximity, not size; putting the lens in global chrome turns a comprehension event into settings |
| 2026-07-25 | Storyline Map (branch tree): monochrome, status by line style not color, clicking a branch re-typesets a branch brief in place rather than navigating | Branches are partitions of ONE canonical story — navigating away would break that; color stays reserved for lenses |
| 2026-07-25 | Desktop direction "The Stone": 104px mono ledger rail outside the 1240 field; provenance evicted from prose into the margin, baseline-aligned | Gives IBM Plex Mono a job worthy of a third family, and stops AI-written prose being interrupted by chips. One place on screen means "is this true?" |
| 2026-07-25 | No cards on desktop app surfaces — rules and type only | A card is a mobile tap target; at 1440px it is a box drawn around content whitespace already separated. Every competitor is a card grid |
| 2026-07-25 | Desktop flip: keys 1/2/3, scan line spans the full 1240 field, and the ledger rail re-inks at t=60 | With no thumb the flip needs repeatability, not proximity; re-inking the rail means the flip changes what counts as EVIDENCE, not just prose |
| 2026-07-25 | Branch tree ships with a computed shape readout (`N DEVELOPMENTS · N BRANCHES · N SATELLITES · SPAN`), not an LLM branch summary | Countable structure should be counted — an AI product that refuses to summarize what it can count is a trust argument competitors can't copy |

## Preview artifact
`~/.gstack/projects/Matryx-Social-Labs-prism/designs/design-system-20260719/prism-design-preview.html`
(interactive flip demo; open in any browser)
| 2026-07-25 | Renamed Prism → Prism; prism triangle → the bracketed record | "Prism" collides with the NSA surveillance programme (unwinnable for a transparency product, and an SEO ceiling) and was squatted across every TLD. "Prism" names the method — break the record into structure, issue no verdict. The mark is a citation bracket holding three rules: one record, three readings, the last shorter because the story is open |
| 2026-07-25 | Desktop lens flip binds to keys 1/2/3 | No thumb zone on desktop; the flip needs repeatability, not proximity. A key press does NOT scroll — the brief is already in view and moving the page would contradict "layout never moves" |
