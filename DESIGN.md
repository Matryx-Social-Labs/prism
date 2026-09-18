---
name: Prism
description: "Follow the story, not the headlines."
world: "Spectrum (v3, 2026-09-18) — replaces The Reservation Chart"
tokens: design/tokens.json
board: design/board (uv run python design/board/build.py)
colors:
  # Light (default). Full scale, dark values and roles live in design/tokens.json.
  bg: "#FAFAF7"
  surface: "#FFFFFF"
  sunken: "#F1F1EC"
  ink: "#15151A"
  ink-2: "#4B4D57"
  ink-3: "#6C6F7A"
  line: "#E6E6E1"
  line-strong: "#CFCFC8"
  accent: "#5B3FE6"
  accent-fill: "#6B4EF6"
  accent-soft: "#EEEAFE"
  coverage-national: "#DC9412"
  coverage-regional: "#E4573D"
  coverage-intl: "#0E9FB8"
  coverage-wire: "#8A6CF2"
  lens-markets: "#0F9D6A"
  lens-cyber: "#2563EB"
  lens-health: "#DB2777"
  lens-policy: "#B7770D"
  danger: "#D93A2B"
  up: "#0F9D6A"
  down: "#D93A2B"
  bg-dark: "#0F0F12"
  surface-dark: "#16161B"
  ink-dark: "#F1F1EE"
  accent-dark: "#A08BF6"
typography:
  display: { fontFamily: "Newsreader, Tiro Devanagari Hindi, Noto Serif Kannada, Noto Serif Tamil, Noto Serif Telugu, serif", fontWeight: 500 }
  sans: { fontFamily: "Hind, Hind Siliguri, Hind Vadodara, Hind Mysuru, Hind Madurai, Hind Guntur, system-ui, sans-serif", fontWeight: 400 }
  mono: { fontFamily: "JetBrains Mono, ui-monospace, Menlo, monospace", fontWeight: 400 }
rounded: { xs: "4px", sm: "6px", md: "10px", lg: "14px", xl: "20px", pill: "9999px" }
spacing: { 1: "4px", 2: "8px", 3: "12px", 4: "16px", 5: "20px", 6: "24px", 7: "32px", 8: "40px", 9: "48px", 10: "64px" }
---

# Design System: Prism — Spectrum

> The world changed on 2026-09-18. "The Reservation Chart" (Teko / Hind / Martian
> Mono, monochrome stationery, hairlines-not-cards, 0-radius) is retired. The
> founder's brief: the product read as dull, readers could not tell what Prism is
> for, and the mobile web has to become a React Native app without a second design.
> What survives is the brand, not the costume: the mark, the record-not-verdict
> principle, verbatim-or-nothing, counted structure, the lens flip, the refusal to
> enumerate lens names in prose, and the accessibility floors. The Decisions Log at
> the end carries the whole history forward.

## Overview

**Creative North Star: "White light in, spectrum out."**

The mark is a prism: many reports enter as white light and leave as a spectrum.
That is now the visual grammar of the whole product. The page ground is white
light — near-white, calm, uncoloured. The **record** (the story) is written in a
serif on that ground, the way a paper of record would print it. Colour appears
exactly where the prism does its work: when the coverage of a story is split into
its parts (the **coverage bar**), when the same facts are re-read through a
professional **lens**, and on the single brand accent that says "this is
interactive". Nothing else is coloured. The result should feel like a serious
newspaper that has been rebuilt as an instrument: quiet ground, confident type,
and a small set of coloured glyphs that mean something every time they appear.

Three things a first-time reader must understand within one screen, without
reading a manual:

1. **This is one story from many reports** — the coverage bar and the outlet
   monograms say so on every row.
2. **Nothing here is invented** — quotes carry the speaker, the outlet, the time and
   a link to the line; counts are printed as counts; provisional groupings say so.
3. **I can read it for my work** — the lens control sits on the record, and a
   locked lens still shows what it would add.

**Key characteristics**
- One ground, one ink, one accent (violet). Four coverage hues and the lens hues are semantic, discrete, never decorative.
- Three voices: **Newsreader** for the record (headlines, titles, quotes), **Hind** for everything read or tapped in every Indian script, **JetBrains Mono** for provenance only.
- Soft geometry: 10–20px radii on cards and sheets, pills for actions and chips, 1px lines for structure. No heavy shadows; one soft shadow for floating sheets.
- Mobile is the product (bottom tabs, thumb-zone actions, 44px targets, safe areas). Desktop is the same components with room for evidence beside the record.
- Two signature motions: the **lens flip** (scan line + re-ink, 500ms) and the **coverage bar drawing in** (segments grow left→right, 240ms, staggered 30ms). Reduced motion collapses both.

## Colour

Roles, not hues, are the API. Every consumer reads a semantic token; the hex lives once in `design/tokens.json`.

### Ground and ink
- **bg** `#FAFAF7` / dark `#0F0F12` — the page. Faintly warm white: "white light".
- **surface** `#FFFFFF` / `#16161B` — cards, rows, inputs, sheets.
- **sunken** `#F1F1EC` / `#0B0B0E` — wells, segmented-control tracks, skeletons, monogram fills.
- **ink** `#15151A` / `#F1F1EE` — headlines, body, primary icons, the Verified pill's fill.
- **ink-2** `#4B4D57` / `#B3B4BC` — summaries, secondary text, inactive nav.
- **ink-3** `#6C6F7A` / `#8E909A` — labels, provenance, tertiary text. 4.9:1 on surface; this is the floor for 11px mono.
- **line** `#E6E6E1` / `#26262E` — card borders, dividers. **line-strong** `#CFCFC8` / `#36363F` — inputs, dashed provisional rules.

### Accent — brand violet
- **accent** `#5B3FE6` / `#A08BF6` — links, active nav and tab, focus ring, selected states, the timeline's "now" dot.
- **accent-fill** `#6B4EF6` / `#7C5CF0` — the primary button (white text, 4.6:1).
- **accent-soft** `#EEEAFE` / `#241E45` — selected chip/nav fill, speaker avatars, the hero wash, the quote highlight (`<mark>`).

Violet is the far end of the mark's own spectrum. It is the *only* colour that means "you can act here", and it never appears in a coverage bar or a lens.

### Coverage — the prism's work
A story's reporting is split by **outlet origin**, in this fixed order so adjacent segments never collide for colour-blind readers (validated with the dataviz palette checker, both modes, all six checks):

| Slot | Meaning | Light | Dark |
|---|---|---|---|
| `coverage-national` | English-language national outlets | `#DC9412` | `#C48314` |
| `coverage-intl` | International outlets | `#0E9FB8` | `#1A9DB6` |
| `coverage-regional` | Indian-language outlets | `#E4573D` | `#E2573E` |
| `coverage-wire` | Wire / agency (reserved — no agency sources yet) | `#8A6CF2` | `#8A6CF2` |

The amber sits below 3:1 against the page on purpose (it is a fill, not text); every bar therefore carries its count in text beside it — the legend is never colour alone.

### Lenses — the same facts, re-read
| Lens | Hue | Soft |
|---|---|---|
| Reader | ink — the record is neutral, it has no colour | — |
| Markets | `#0F9D6A` green / `#2CC08A` | `#E3F6EE` / `#12301F` |
| Cyber | `#2563EB` blue / `#5B8DFF` | `#E6EEFE` / `#15213D` |
| Health *(drafted)* | `#DB2777` rose / `#F472B6` | `#FCE7F1` / `#3B1528` |
| Policy *(drafted)* | `#B7770D` amber / `#E0A030` | `#FBF0DC` / `#332611` |

A lens hue appears only on: the selected lens tab's text, the flip's scan line, the small "Markets read" dot on a row, and the lens brief's heading rule. Never on chrome, never as a wash. New lenses take the next unused stop of the spectrum; the picker renders whatever `/api/v1/lenses` returns.

### Status
- **Verified record** — ink pill with a check. No colour: verification is the default, not an alarm.
- **Provisional grouping** — dashed `line-strong` outline, `ink-3` text.
- **Disputed** `#B7770D`, **Corrected** `#D93A2B` — text and a 12% tint; rare by design.
- **danger / down** `#D93A2B`, **up** `#0F9D6A` — destructive confirms and price moves only.

### Named rules
**The Prism Rule.** Colour appears where light is split: the coverage bar, a lens, and the one accent. Anything else coloured is re-inked to the neutral scale.
**The Legend Rule.** No coverage or status is conveyed by colour alone — every bar has its count, every pill has its word, every lens dot has its label.
**The One Gradient Rule.** The mark's spectrum bar and the landing's dispersion figure are the only gradients. No gradient text, no gradient buttons, no tinted photos.

## Typography

**Display: Newsreader** (variable, optical sizes 6–72, weights 400–600, italics). Falls through per script to Tiro Devanagari Hindi, Noto Serif Kannada / Tamil / Telugu / Bengali / Gujarati, then Georgia.
**Sans: Hind** with Hind Siliguri (Bengali), Vadodara (Gujarati), Mysuru (Kannada), Madurai (Tamil), Guntur (Telugu), then `system-ui`.
**Mono: JetBrains Mono** 400/500, `font-variant-numeric: tabular-nums` everywhere.

**Character:** a paper of record set on an instrument. Newsreader was drawn for on-screen news reading and has real optical sizes, so a 60px promise and a 19px row headline come from one voice. Hind keeps five Indian scripts on one baseline so a Kannada row and an English row read as one page. JetBrains Mono is narrow enough for a time and a count to sit in a 26px monogram row without wrapping.

### Scale (mobile → desktop)
| Token | Voice | Size | Line | Weight | Where |
|---|---|---|---|---|---|
| display-xl | Newsreader | 40 → 60 | 1.05 | 500, −0.02em | landing promise |
| display-l | Newsreader | 30 → 38 | 1.12 | 500, −0.015em | story title |
| display-m | Newsreader | 24 → 30 | 1.2 | 500 | lead row, section titles (Today, The record) |
| title | Newsreader | 19 → 20 | 1.3 | 500 | every story row headline |
| quote | Newsreader italic | 17 → 18 | 1.5 | 400 | verbatim quotes only |
| body | Hind | 16 | 1.6 | 400 | record text, summaries on the story |
| body-s | Hind | 14.5 | 1.55 | 400 | row summaries, hints, legends |
| ui | Hind | 14 | 1.4 | 500–600 | buttons, tabs, chips, nav |
| label | Hind | 12.5 | 1.4 | 500–600, +0.06em, caps | card headings, eyebrows |
| mono | JetBrains Mono | 12 | 1.5 | 400, +0.02em | times, "5 outlets · 15 reports" |
| mono-s | JetBrains Mono | 11 | 1.5 | 400, +0.03em, caps | row meta line — the floor |

### Named rules
**The Three Jobs Rule (kept).** Newsreader never sets a button, a label or running UI; JetBrains Mono never sets prose or a heading; Hind sets everything a reader taps or reads at length. A word in the wrong voice is a bug.
**The Floors (kept).** 11px mono, 14.5px body, 16px in inputs (iOS zoom), 4.5:1 on both grounds, 44px targets.
**The Measure Rule.** Reading copy 44–68 characters; the reading column is 640px and never grows with the viewport — width buys evidence beside the record, not longer lines.

## Layout

**Shell** 1360px, gutters 16 / 24 / 32px. **Breakpoints** are Tailwind's: the product switches from phone to desktop at `lg` (1024px); `sm` (640px) only widens type.

**Phone (the future app):** masthead 52px (mark + wordmark, dateline in mono, theme) · subject chips 34px in a horizontal rail · content · bottom tab bar 56px + safe-area inset. The story page swaps the masthead for a back bar and pins Follow · Ask · Share in the thumb zone above the tab bar.

**Desktop:** top bar 60px (mark + wordmark, Today · Stories · Pulse · Watchlist, a visible 260px search field with `/`, theme, Sign in or the avatar; the primary pill appears only on the landing) · a three-column grid: left rail 220px (subjects on Today/Stories/Search; "On this story" on a record) · main column · right rail 300px (Developing over days on Today; Reports + Named entities on a record). Rails are sticky under the top bar.

**Vertical rhythm** is the 4px scale: rows are 12px apart; cards pad 14–20px; sections on a record are 22px blocks separated by a `line`.

## Components

### Story row (`.row`)
The unit of the product, identical on Today, Stories, Search, Watchlist and the landing's live proof. A `surface` card, `line` border, 10px radius, 14/16px padding; the lead row pads 20/18px and sets its title at 26–30px. Inside, top to bottom:
1. **Meta** (mono-s caps): subject or region · time since last report · languages when more than one.
2. **Title** (title voice).
3. **What changed** (body-s, ink-2, two lines max).
4. **Foot**: outlet monograms (max 3 + "+N") · **coverage bar** with its text ("9 outlets · 2 languages") · spacer · lens dot ("Markets read") when the story earns one.
A single-source row has a dashed border. Rows never carry a publisher photo (see Decisions, 2026-09-18).

### Coverage bar (`.covbar`)
Segments in the fixed slot order, 2px gaps, 6px tall on rows and 8px on a record, rounded ends; total width 72px on rows, 120–240px on a record; each segment's width is proportional to its count, minimum 4px. Always followed by mono text with the count. Draws in left→right on first paint.

### Monogram (`.mono-av`)
26px circle, `sunken` fill, 2px `surface` ring and 1px `line` halo, two-letter outlet code in Hind 600 9.5px. Stacks overlap by 7px. Codes come from the source registry, never from initials computed at render (The Hindu = TH, Hindustan Times = HT).

### Status pill (`.status`)
24px pill, 12px Hind 600. Verified: ink fill, check icon. Provisional: dashed outline. Corrected/Disputed: 12% tint of their hue.

### Subject navigation
Phone: pill chips in a scrolling rail, the active chip inverted (ink fill). Desktop: the left rail, 40px items with the mono code in a 28px column, active item `accent-soft` fill with `accent` text. One DOM per breakpoint, never both rendered.

### Buttons
- **Primary** pill, `accent-fill`, white text, 40px (48px `.btn-lg`). One per screen: Follow story on a record, Open today's record on the landing, Save on forms.
- **Secondary** pill, `surface` fill, `line-strong` border. **Ghost** text only. **Icon** 38px round.
- Hover: 5% darker or `sunken`; active: 1px down; all 160ms.

### Lens control (`.seg`)
A segmented control on a `sunken` track, 34px pills; the selected pill is `surface` with shadow-1 and the lens hue for its text; locked lenses show a 13px lock at 55% and still flip. Lives on the record header (desktop, right of the actions) and directly above the record text on the phone. Keyboard 1/2/3 on desktop.

### Record header
Status pill · updated time · subject, then the title (display-l), the summary (17px ink-2, 62ch), the monogram stack + large coverage bar + text ("5 outlets · 15 reports · English"), then the action row. Follow is the primary; Share is secondary; Ask lives at the foot of the record and in the thumb bar.

### Record sections (in this order, always)
**The record** (the Reader brief, 16.5px, with "What to watch" bullets) → **What changed** (timeline: accent "now" dot, then ink dots on a `line-strong` spine; mono time · outlet, serif headline) → **Who said what** (quote cards) → **Coverage** (large bar, legend with counts, entities, the report list on the phone) → **Why it matters** (impacts) → **Ask** (input pill + suggested questions). The desktop left rail lists the same six with counts; the right rail holds Reports and Named in the reports.

### Entity marks (`.ent`)
The story's named entities, marked in the record's prose — the summary, the brief, the watch points. A mark is ink text with a 1.5px underline in the accent at 55%, lifting to `accent-soft` on hover and focus; never blue text, never bold. One mark per entity per passage (its first mention), longest name first, whole words, case-sensitive for names under four letters ("US" never marks "us"); the text is never altered. Hover or focus (desktop) and tap (touch) open a 260px card anchored under the mark: the name · its kind (Person, Government, Company…), "Quoted N times on this story ↓" when the entity spoke, and one action, "All stories about X →". A second tap follows the action; Escape and an outside tap close it. Quotes are never marked — verbatim text stays visually verbatim.

### Report card (`.row-card`, compact)
One report as the reader sees it: the outlet's icon (its own favicon, 20–28px in the monogram disc, the monogram as fallback) and name, when it published (relative time, mono), the headline the outlet wrote (Hind 500, three lines), and a foot of `[n]` · origin (English national, Indian-language, International) · funding label when known. The whole card opens the article. Cards stack in the desktop evidence rail (compact) and under Coverage on the phone (eight, then "All N reports"). The same reports appear in "What changed" as a timeline — the sequence view — with the outlet icon and time on each row.

### Quote card (`.quote`)
`surface`, 14px radius: speaker avatar (accent-soft, initials) + name + "quoted in N outlets"; the quote in Newsreader italic 17.5px; outlet pill · time · "Open at the quote ↗" (text fragment link); an "In the article" disclosure that prints the surrounding sentence with the quote in `accent-soft` `<mark>`.

### Ask
Subordinate to the evidence: a card at the foot of the record with a 44px input pill, a round ink send button and three suggested questions as outline chips. Answers cite `[n]` to the report list.

### Cards and rails (`.card`)
`surface`, 14px radius, 16px padding, a 12.5px caps heading in `ink-3`. Used only in the desktop rails and on the landing; the main column is rows and blocks.

### Forms (You, Onboarding, Sign in, Account, Interests)
One shell, 640px: 14px 500 labels above 48px `surface` inputs with `line-strong` borders and 10px radius; hints 13.5px `ink-3`; the primary pill on the right of a sticky footer; errors in `danger` beside the field. Sector and lens pickers are chips; the lens picker is the one place a chip carries a lens hue.

### Landing
A product page built from the product's own components: the promise (display-xl) with the **dispersion figure** (outlet monograms → the mark → four spectrum strands → the real live story row), three proof cards each running a real component on real data (timeline, quote card, coverage bar), the lens flip on a real record, an honest **Available now / In validation / Next** grid, one final call. No device mockups, no stock photography, no numbers that are not counted.

### Empty, loading, error
Skeletons are `sunken` bars in the exact geometry of the row (no spinner on the chart). Empty states say what would be here and offer the one action that fills it. Errors are one sentence in `danger` with a retry.

## Motion

- **micro** 160ms, **standard** 240ms, easing `cubic-bezier(.2,.7,.2,1)`.
- **The lens flip (kept):** a 2px scan line in the lens hue sweeps the reading column top→bottom over 500ms while the text re-inks beneath it; layout never moves. Reduced motion: instant swap.
- **Coverage bar:** segments scale from 0 on first paint, 240ms, 30ms stagger. Once per page load, never on re-sort.
- Rows print in with a 40ms stagger (kept). No parallax, no scroll-jacking, no looping animation anywhere.

## Do's and Don'ts

### Do
- **Do** put the coverage bar and its count on every story row; it is how a reader learns what Prism is without being told.
- **Do** keep the record neutral: Reader is ink; colour arrives with a lens or a coverage split.
- **Do** keep one primary pill per screen and give it the screen's one job (Follow, Open, Save).
- **Do** print counts as counts, quote verbatim or not at all, and mark provisional groupings in words.
- **Do** design every phone screen as an app screen: bottom tabs, thumb-zone actions, 44px targets, `100dvh`, safe-area insets.
- **Do** identify an outlet by its own favicon (nominative — the way a byline names a paper) with the registry monogram as the fallback; never a publisher's photographs.
- **Do** render whatever `/api/v1/lenses` returns and never name lenses in generic copy.

### Don't
- **Don't** hotlink or embed publisher photographs anywhere (rows, records, share cards, JSON-LD). Image rights are unresolved; the design does not depend on them.
- **Don't** colour chrome, tint the ground, or use a lens or coverage hue as decoration.
- **Don't** set body or UI in Newsreader, or a heading in the mono.
- **Don't** infinite-scroll Today; the day is the unit and yesterday is a link.
- **Don't** put a marketing hero on Today; the landing is `/about` and `/` for a first visit only.
- **Don't** use text glyphs as icons; the stroke set in `icons.tsx` (22px, 1.8 stroke) is the only icon set.
- **Don't** invent a fact for a demo. Every number, quote and outlet on the landing is fetched.

## Decisions Log

Historical entries were written under whichever name and world was current; the design decision each records is unaffected. Entries before 2026-09-18 describe the retired Reservation Chart and, before 2026-09-15, the ivory broadsheet; they are kept as history.

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-18 | New world "Spectrum": Newsreader / Hind / JetBrains Mono, near-white ground, brand violet accent, soft radii, cards for rows | Founder brief: the chart read as dull and un-navigable; readers could not see what Prism does. The prism's own metaphor — white light in, spectrum out — now sets where colour appears |
| 2026-09-18 | Colour rule widened: coverage hues + lens hues + one accent (was: lenses only) | The coverage bar makes "one story from many reports" visible on every row; the accent makes interaction legible in a mobile app |
| 2026-09-18 | Coverage bar order national · international · regional · wire, palette validated in both modes | Red and amber are indistinguishable for deutan readers when adjacent; the order keeps them apart and the count text is the legend |
| 2026-09-18 | Publisher photographs retired from every surface | Indian fair dealing does not cover a whole photograph; the feed T&Cs (TOI, HT, India TV) forbid commercial republication; agency images are not the publisher's to license. Outlet monograms and the coverage bar carry identity instead |
| 2026-09-18 | Bottom tabs Today · Stories · Search · Watchlist · You; Pulse becomes a module on Today and a route | Five tabs is the ceiling; "Stories" (developing arcs) is a reader's word and "Trending" implies popularity theatre |
| 2026-09-18 | Record sections fixed: The record · What changed · Who said what · Coverage · Why it matters · Ask | Same order on phone, desktop rail and share card; a reader learns it once |
| 2026-09-18 | Tokens live in design/tokens.json; web CSS and the future React Native theme are generated from it | One source of truth for two platforms |
| 2026-09-18 | Entity marks in the record's prose: thin accent underline, first mention only, a hover/tap card with kind · quotes · one action | Founder ask for rich text on the entities; NN/G: links read by contrast, not by painting the paragraph blue |
| 2026-09-18 | Reports as cards with the outlet's favicon, name, time and its own headline; the timeline keeps the sequence view | Founder ask (Particle's articles rail); a reader recognises a masthead by its mark faster than by its initials |
| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-18 | Landing promise narrowed to “Follow the story, not the headlines”; public copy says monitored outlets, not every source | The visible promise now matches what the ingestion and quality system can verify today |
| 2026-09-18 | Desktop feed, trending and search use one responsive subject navigation as a left rail; mobile keeps the same DOM as a horizontal strip | Particle's root news product demonstrated the value of a persistent desktop topic edge, while a single DOM avoids duplicate keyboard and screen-reader controls |
| 2026-09-18 | Public/app shells move to 1400px; story keeps a 604px reading measure inside a fluid three-column field | Wider screens buy simultaneous navigation and evidence, never longer prose; the fluid grid also removes the old 1376px overflow at 1024px |
| 2026-09-18 | Story boundary status is printed in plain language once loaded | A reader must be able to distinguish verified chronological developments from a provisional coverage grouping before interpreting the route |
| 2026-09-17 | Plain words on reader surfaces | The railway metaphor (route, station, main line, branch line, satellite, trunk, ticket, lens board) stays in code and design notes; the page says *How this story unfolded · All developments · Main story / All · Branched off · Also reported · First / Latest / You are here · Read this development · Related stories · Read it as*. A first-time reader should not have to learn a vocabulary to read the news |
| 2026-07-19 | Initial DESIGN.md via /design-consultation | Live research + outside voice + approved interactive preview |
| 2026-07-19 | Memorable thing = the lens flip | Founder choice (D2) |
| 2026-07-19 | Keep light+dark, keep lens hues, keep WebGL prism hero | Founder's prior explicit calls; contrarian "Night Desk" dark-only direction declined |
| 2026-07-19 | Space Grotesk → General Sans; add IBM Plex Mono provenance layer | Anti-convergence + both design voices agreed |
| 2026-07-23 | Feed v3: remove feed lens pills; scope selector + language chip replace them; Trending joins the nav | Lens is a per-story flip, not a feed filter; quieter chrome at rest |
| 2026-07-23 | No global lens switcher in the header chrome | Founder call (B): lens is set in "Your Prism" and flipped per-story |
| 2026-07-23 | Content shells unified to 1240px (header/footer 1280px) | Column left-edges line up across landing/feed/sector/story |
| 2026-07-25 | App surfaces rebuilt mobile-first: bottom tab bar is the nav spine on phones; global brand header hidden on app routes | A phone reader was getting a shrunk desktop site with two stacked headers |
| 2026-07-25 | On Story, the lens rail + Share/Ask pin to the thumb zone | The flip has to be reachable one-handed |
| 2026-07-25 | Desktop width rule: extra width buys simultaneity (ambient evidence), not longer lines | Reading measure is already correct |
| 2026-07-25 | Feed is a ruled editorial river, never a card grid | Prism sells canonical understanding, not abundance |
| 2026-07-25 | Desktop lens control lives on the lens brief's top edge, never in the header or rail | The flip needs proximity, not size |
| 2026-07-25 | Storyline Map (branch tree): monochrome, status by line style not colour, branch re-typesets in place | Branches are partitions of ONE canonical story; colour stays reserved for lenses |
| 2026-07-25 | Desktop direction "The Stone": mono ledger rail outside the field; provenance evicted from prose into the margin | One place on screen means "is this true?" |
| 2026-07-25 | No cards on desktop app surfaces — rules and type only | A card is a mobile tap target; at 1440px it is a box around whitespace |
| 2026-07-25 | Desktop flip: keys 1/2/3, scan line spans the field, ledger rail re-inks; a key press does not scroll | Repeatability, not proximity; "layout never moves" |
| 2026-07-25 | Branch tree ships a computed shape readout, not an LLM branch summary | Countable structure should be counted |
| 2026-07-25 | Renamed to Parse; prism triangle → bracketed record | Name collision and SEO ceiling |
| 2026-07-28 | Renamed back to Prism (v0.0.78.0); the triangle-on-spectrum mark returns | `readprism.news` secured; the mark reverted with the name while everything else stood still |
| 2026-09-15 | New world: "The Reservation Chart" replaces the ivory broadsheet. Grounds #f2f4ee / #141613, one ink, Teko / Hind (six scripts) / Martian Mono replace Fraunces / General Sans / IBM Plex Mono; cards, panel radii and the spectrum hairline above the header retired | The category default (cream, serif lead, cards) was indistinguishable from competitors; the chart is a form the subject already owns. Seed key 31b3f17c, candidate 6 of 7 |
| 2026-09-15 | D1: the general reader leads | The chart is the same list for everyone; professional reads are one tap deep, marked by a dot |
| 2026-09-15 | D2: Today + For you are the only chart tabs | The day is the unit; personalisation re-sorts, never hides |
| 2026-09-15 | D3: six sectors as the subject nav, no "Other" | Every story has a code; a chart has no miscellaneous coach |
| 2026-09-15 | D4: Perspectives cards retired | Replaced by the passenger list (verbatim quotes) and the coaches (sources); an LLM's stance never reaches the payload |
| 2026-09-15 | State is line form: solid live, dashed single-source, half-weight stale | Colour is spent on lenses; the reader sees the thinness of the evidence before the headline |
| 2026-09-15 | `--ink-faint` #8a8d85 → #6d7068 (light) / #82867f (dark) | The label grid prints on every row at 11px; the chart's faded grey sat at 3.0:1 |
| 2026-09-16 | D5 (revised): `/` is the landing for a first visitor and the chart once reached (cookie); `/feed` is always the chart; `/about` is the landing's permanent address | A returning reader must land on the list; a first visitor needs the pitch once |
| 2026-09-16 | D6: bottom bar Today · Trending · Pulse · Search · You; the sector strip is the subject nav on every surface | Navigation by destination in the bar, by subject in the strip; neither carries a lens |
| 2026-09-16 | Finish review returned `ship`; DESIGN.md rewritten from the shipped code | Unreviewed and undocumented is unfinished |
