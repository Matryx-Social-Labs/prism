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
- Two signature motions: the **lens flip** (scan line + re-ink behind it, 500–1100ms at a constant 0.9px/ms) and the **coverage bar drawing in** (segments grow left→right, 240ms, staggered 30ms). Reduced motion collapses both.

## The mark

A 24×24 box: an equilateral prism, fill only (no stroke — a stroke put every edge on a fraction and clipped the base), base 20 wide at y 19.5, apex at 2.18; the spectrum a band ATTACHED to the base — its top edge is the base line, no gap (a gap read as a split icon) — exactly the base's width, 2.75 tall, as one continuous spectrum with stops at the coverage bar's four hues (red → amber → cyan → violet). Geometry lives once in `web/src/lib/mark.ts`; the favicon, the share card and the PNG exports (`design/logo/build.py` → `design/logo/exports/`, shareable set at `/brand/*.png`) draw the same numbers. The triangle takes `currentColor`; the band is the only spectrum in the system. Fixed 2026-09-20 after the founder zoomed in on the old base.

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

**Display: Newsreader** (variable, optical sizes 6–72, weights 400–600, italics). Falls through per script to Tiro Devanagari Hindi, Noto Serif Kannada / Tamil / Telugu (loaded through next/font, unicode-ranged, not preloaded: fetched only when a glyph needs them), then Georgia. Bengali and Gujarati are not loaded yet — add their Noto Serif when a source in those scripts is added.
**Sans: Hind** with Hind Siliguri (Bengali), Vadodara (Gujarati), Mysuru (Kannada), Madurai (Tamil), Guntur (Telugu), then `system-ui`.
**Mono: JetBrains Mono** 400/500, `font-variant-numeric: tabular-nums` everywhere.

**Character:** a paper of record set on an instrument. Newsreader was drawn for on-screen news reading and has real optical sizes, so a 60px promise and a 19px row headline come from one voice. Hind keeps five Indian scripts on one baseline so a Kannada row and an English row read as one page. JetBrains Mono is narrow enough for a time and a count to sit in a 26px monogram row without wrapping.

### Scale (mobile → desktop)
| Token | Voice | Size | Line | Weight | Where |
|---|---|---|---|---|---|
| display-xl | Newsreader | 40 → 60 | 1.05 | 500, −0.02em | landing promise |
| display-l | Newsreader | 30 → 38 | 1.12 | 500, −0.015em | story title, measure 28ch so a 60–70 character headline sets in two lines of the 640 column |
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

**Rails scroll with the page**: a right rail that fits the viewport holds at the top; one taller than it (thirty reports) scrolls with the page until its own end is in view and holds there (`Rail`), so nothing in it waits for the column to run out. **Desktop:** top bar 60px (mark + wordmark, Today · Stories · Pulse · Watchlist, a visible 260px search field with `/`, theme, Sign in or the avatar; the primary pill appears only on the landing) · a three-column grid: left rail 220px (subjects on Today/Stories/Search; "On this story" on a record) · main column · right rail 300px (Developing over days on Today; Reports + Named entities on a record). Rails are sticky under the top bar. **The right rail waits for 1280px** (`xl`); from 1024 the grid is two columns, the record keeps its 640 measure and the rail's content sits inline as on the phone. At 1024 with three columns the reading column was 360px: a five-line headline and an 80px photo tile.

**A wide desk (≥1536px)** grows the shell to 1600 (1760 at ≥1920) and the rails with it — left 240, evidence 360 (400) — and the chart runs in **two columns** with the lead across both; the reading measure stays 640. Width buys simultaneity, never longer lines (founder, 2026-09-20: the desktop was not using the screen).

**Vertical rhythm** is the 4px scale: rows are 12px apart; cards pad 14–20px; sections on a record are 22px blocks separated by a `line`.

## Components

### Story row (`.row`)
The unit of the product, identical on Today, Stories, Search, Watchlist and the landing's live proof. A `surface` card, `line` border, 10px radius, 14/16px padding; the lead row pads 20/18px and sets its title at 26–30px. Inside, top to bottom:
1. **Meta** (mono-s caps): subject or region · time since last report · languages when more than one.
2. **Title** (title voice).
3. **What changed** (body-s, ink-2, two lines max).
4. **Foot**: outlet monograms (max 3 + "+N") · **coverage bar** with its text ("9 outlets · 2 languages") · spacer · lens dot ("Markets read") when the story earns one.
A single-source row has a dashed border. A row carries the report's photograph as a credited thumbnail when one exists (§ Images; Decisions, 2026-09-20).

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
Status pill · updated time · subject, then the title (display-l), the summary (17px ink-2, 62ch), the monogram stack + large coverage bar + text ("5 outlets · 15 reports · English"), then the action row. Follow is the primary; Share is secondary; Ask has no button in the header — the bar rides the foot of the viewport on a desk and sits in the thumb zone on the phone.

### Record sections (in this order, always)
**The record** (the Reader brief, 16.5px, with "What to watch" bullets) → **What changed** (timeline: accent "now" dot, then ink dots on a `line-strong` spine; mono time · outlet, serif headline) → **Who said what** (quote cards) → **Heard on** (podcast clips, when any) → **Coverage** (large bar, legend with counts, entities, the report list on the phone) → **Why it matters** (impacts) → **Ask** (input pill + suggested questions). The desktop left rail lists the same six with counts; the right rail holds Reports and Named in the reports.

### Entity marks (`.ent`)
The story's named entities, marked in the record's prose — the summary, the brief, the watch points. A mark is ink text with a 1.5px underline in the accent at 55%, lifting to `accent-soft` on hover and focus; never blue text, never bold. One mark per entity per passage (its first mention), longest name first, whole words, case-sensitive for names under four letters ("US" never marks "us"); the text is never altered. Hover or focus (desktop) and tap (touch) open a 260px card anchored under the mark: the name · its kind (Person, Government, Company…), "Quoted N times on this story ↓" when the entity spoke, and one action, "All stories about X →". A second tap follows the action; Escape and an outside tap close it. Quotes are never marked — verbatim text stays visually verbatim.

### Report card (`.row-card`, compact)
One report as the reader sees it: the outlet's icon (its own favicon, 20–28px in the monogram disc, the monogram as fallback) and name, when it published (relative time, mono), the headline the outlet wrote (Hind 500, three lines), and a foot of `[n]` · origin (English national, Indian-language, International) · funding label when known. The whole card opens the article. Cards stack in the desktop evidence rail (compact) and under Coverage on the phone (eight, then "All N reports"). The same reports appear in "What changed" as a timeline — the sequence view — with the outlet icon and time on each row.

### Images (`ReportImages`, card thumbnails)
Prism has no photographs of its own. An outlet's photograph appears only **credited** — the outlet's icon on the image, the alt text naming whose it is — and only as the report's own picture: (1) **on a story row** (founder, 2026-09-20: a picture is what makes a reader tap one story rather than read every line) as a thumbnail on the right of the row, across the top of the lead on the phone and beside it on a desk; (2) **on the record** as the **photo deck** under the header: one stage (16:10 on the phone, 2:1 on a desk, the reading measure wide) showing one outlet's picture with its credit bar and "Open report ↗", the others fanned behind it as a stack, a filmstrip of all of them on a desk, native swipe on the phone; prev/next arrows and the keyboard step it, a mono "2 / 5" counts it, and it never advances on its own; (3) **on a Stories row** as a **photo pile**: up to three of the story's developments' photographs, newest in front and credited; the pile *settles* into its fan as the row comes into view (480ms on a spring, staggered, once), a hover on a desk spreads it further, each photograph fades in as it loads, "+N" counts the rest; (3b) **on a story page** the same photo deck as the record, and a **Who reported it** rail of outlets with their report counts; (4) a 64px thumbnail on a report card. **Placeholders are not photographs**: an outlet's logo or a stock district shot (The Hindu's og-image on 363 reports in a fortnight, TOI's generic msid on 87) is recognised by repetition — the same hash on four or more reports in 14 days — and never shown as a story's picture (`common/images.placeholder_hashes`); a row with no real picture keeps its shape. Every tile opens the report it came from; the outlet's icon and "Photo: <outlet>" sit on the image itself (no badge: the tile is the link), and the alt text says whose photo it is. Images are hotlinked with `referrerpolicy=no-referrer`, never proxied or resized by us, never the share card, never the JSON-LD image, never a row's hero. `NEXT_PUBLIC_REPORT_IMAGES=0` removes every one of them: the right to even this much is not settled in India (legal note, 2026-09-18), and the design must survive without them.

### Quote card (`.quote`)
`surface`, 14px radius: speaker avatar (accent-soft, initials) + name + their role on a line under the name ("Vice President of the United States") + "quoted in N outlets"; the quote in Newsreader italic 17.5px; outlet pill · time · "Open at the quote ↗" (text fragment link); an "In the article" disclosure that prints the surrounding sentence with the quote in `accent-soft` `<mark>`.

The role is printed only when the article's own words support it (`enrichment/claims.faithful_role`: every content word present, no brackets or clauses, title-length; an English role on a Hindi article is unverifiable). No role is better than a plausible one — same rule as the quotes: verbatim or absent.

### Podcast clip (`.clip`)
"Heard on", between *Who said what* and the route, only when a clip exists (the section never advertises absence). A `card` with one control — a 44px ink play disc — beside the show's art (24px, monogram-disc fallback with a headphones glyph), the show's name (Hind 600), its publisher, the episode's age (mono) and `TRANSCRIPT 2:00–3:00` (mono caps). The body is the transcript of that stretch alone in the reading voice at 16px: no written title, the first sentence is the headline, no cleanup beyond punctuation. Words sit in `ink-3` and ink to `ink` as they are spoken; a 2px ink progress rule runs under the text (clips are evidence, never a lens hue). The foot names the episode, links *Full episode ↗* to the publisher's page, and offers *Keep listening*, which lets the episode run on past the clip.

One `<audio>` per section, playing the publisher's own file (`preload=none`, never proxied, never ours). Play seeks to the clip; at its end the queue advances to the next card after 400ms, across episodes, then stops. ← → move between clips. While something plays, a `glass` bar rides above the thumb zone on the phone (bottom of the reading column on desktop) with the art, the show and publisher, the clock, pause and next; the Media Session names the show and publisher on the lock screen. Hosts stitch ads in per request, so the player compares the loaded file's duration with the one we transcribed and shifts the seek and the read-along by the difference (`clipShift`). `NEXT_PUBLIC_PODCAST_CLIPS=0` removes the section and the row line.

**On the record**, the clips are a rail of compact cards (show art 40, show name, publisher · time, the round play button, the episode title in two lines, a progress line with the clip's length in mono) and, under them, ONE **transcript window** for the clip in view — a few lines tall, scrolling on its own to keep the word being spoken in the middle, the whole transcript in ink and the words already said stepped back; a reader who scrolls it takes the wheel for four seconds. Never the whole transcript spilled down the page (founder, 2026-09-21). Feed rows carry `Heard on N shows` (mono, headphones glyph) after the coverage bar when a clip exists. Never the audio on a row, never a clip in the share card or JSON-LD. The **now-playing bar** floats above the thumb zone on the phone; on a desk it docks into the record's foot, above the Ask bar, riding the viewport with it — never over the Ask drawer.

### Ask
One sheet, four ways in. **The bar**: a 44px input pill with a round ink send button, the last block of the record; on a desk it is `sticky` at the viewport's foot so it rides down the whole record and docks under "Ask this story" when the reader arrives — one input, never two, and it leaves while the sheet is open. The three suggested questions show as outline chips only while the bar is focused and empty. **A selection**: select a line of the brief or a quote and an ink "Ask about this" chip appears over it; the line is quoted into the question (`About this line: “…” —`). **A quote card**: "Ask about this quote" prefills the quote and speaker. **An entity card**: "Ask about {name} on this story". **The sheet** (`AskPanel`): on the phone a bottom sheet to 86% over a scrim; on a desk a 420px drawer on the right under the top bar, so the record stays readable beside the answer (220ms from its edge; reduced motion places it). **Every answer has the same anatomy**: the prose (2–5 sentences, each ending in its `[n]` mono chips, which open the cited report) · one table when the question asks for one (timeline · who said what · how outlets differ · numbers; hairline rows, figures and dates in mono, quotes in the record voice) · **Not in the reports**, one mono-labelled line naming what the question asked that the sources do not say · the reports used. Before the first question the sheet also shows **Dig deeper** — Timeline · Every quote · How outlets differ — three chips under a mono label, each answered as a table. Up to three follow-ups the sources can answer take the **suggestion row above the input** once an answer has landed — the row changes, the answer does not grow chips (founder, 2026-09-20). The table, the gap and the follow-ups arrive whole after the prose has streamed (`agent/structure.py`); a reader never watches JSON type. A refusal ("Not in sources") and a limit ("Limit", with the one action that helps: sign in, or wait) are first-class states, never an error colour. Nothing about the question ever reaches analytics.

### Plus (pricing, `/plus`) and the upgrade sheet
The one marketing page besides the landing, so it may use cards. The shape every subscription page a reader already knows, built from the product's own parts: a centred hero (mono meta line "Prism Plus · launch offer …", display-l headline, one-sentence lede), the `.seg` control for Monthly / Yearly with the saving computed from the API's two prices, three `.card`s side by side — Free · **Plus** (ink border, shadow-2, a mono "Recommended" tag; first on the phone, centre on a desk) · Founding member (dashed when the seats are gone) — each with the plan name as a caps label, the price in Newsreader 40px with the period in mono, one mono line of fine print, ONE action, then feature rows on hairlines with `Check` / `Dash` icons. Below: "Side by side" (a two-column table on hairlines), "Before you pay" (six `<details>` on hairlines), one repeat of the primary, and the trust line (Razorpay · GST included · cancel any time · Refund policy). Free is the only card whose action is secondary; Founding's is secondary; Plus carries the page's primary. States: a stranger's buttons read "Sign in to continue"; before the payment keys exist every action is the mono "Opens soon" (never a dead button); on Plus the actions become "Your plan" and the account is linked. Every figure is the API's or a cap the server enforces; the saving and the per-month figure are arithmetic on them.

**The upgrade sheet** (`UpgradeSheet`) is how a limit is met: a bottom sheet on the phone, a 440px centred dialog on a desk (220ms from its edge; reduced motion places it), over a scrim, with Escape/scrim/close all working. Mono meta line with the count ("10 of 10 today"), a counted headline in the record voice ("You've asked today's 10."), three benefit rows with `Check`, the primary with the price of the day ("Get Plus · ₹149 a month" — paid in place for a signed-in reader, "Sign in to get Plus" for a stranger, with the way back), a ghost "All plans →", one line of small print. Entry points: Ask's limit note (free account at its cap; the daily rest), the header's quiet "Plus" ghost link for anyone not on Plus, the account page's plan row, the footer. `?from=` names the door for analytics; nothing about the reader goes with it.

### Legal pages (`/privacy`, `/terms`, `/refunds`)
A policy in the record's own shape, so it reads as part of the product rather than a wall of prose (founder, 2026-09-21). The story page's three columns: **On this page** in the left rail, the section being read marked in accent (the same scroll-spy as "On this story"); the text at the reading measure — mono meta line (`Policy · Last changed <date>`), display-l title, the lede, then each section on a hairline with its heading in the record voice and, under it, **In short**: the section in one plain sentence with a mono label, so a reader who will not read the paragraphs still leaves knowing the rule; the right rail holds the whole document in three or four plain lines ("In short", with `Check` marks), who is behind it with the contact in mono, and the other policies. On the phone the sections become a chip rail under the title and "In short" moves above the text. Lists are dots on hairlines, never cards in the column. Every date is mono; nothing is coloured but the active section and links.

### Account and the subscription's life
`/account`: the email in mono under the title, then **Your plan** first (it is why most people come), then **Payments** (only once there is a charge), then the record (profile, watchlist, theme) and the door out, as hairline-divided rows in one card each. The **plan card** (`PlanCard`) speaks every state in one line and offers one action: *Free* — "Get Plus"; *active* — the plan's name, its price in mono, "Renews <date>", **Cancel** (and **Refund** while the window is open, with a mono line naming the day it closes); *ending* — "Ends <date> · no further charges" (or "· then Plus · yearly from <date>" when one is scheduled), no action; *paused* — "Paused · Plus stays on until <paid date> · resumes <date> on its own" and **Resume now**; *past due* — "The last charge did not go through · Plus stays on until <date> while Razorpay retries", and "Check your email"; *halted* — paused after failed charges, reading stays free; *refunded* — the amount, the day Plus ended, when the money lands; *lapsed* — "Your Plus ended on <date>" and "Get Plus". Under it, in small print, where receipts come from. The same card, compact, sits in the account section of `/you`.

**Cancelling** is never harder than subscribing was (India's CCPA dark-pattern guidelines, 2023, name the "subscription trap"; California's 2025 rule allows one retention offer, shown with the exit). A yearly plan confirms inline — one click, one confirmation naming the date access runs to, "Keep Plus" beside it. A monthly plan opens the **cancel sheet** (`CancelSheet`, the upgrade sheet's frame): the truth first ("Cancelling stops the next charge. You keep Plus until <date> — nothing is taken back"), an *optional* reason as four chips, then ONE offer matched to the reason — **Take a break instead?** (1 · 2 · 3 months on a `.seg`; Razorpay pauses at once, the paid month runs out, the worker resumes it on the day) for "not using it" and by default; **Yearly is ₹N a month** with the saving computed from the two prices, starting the day the month ends so nothing is charged twice, for "too expensive"; a one-line text box and no offer for "missing something" — and **Cancel anyway** on the same row at the same size as the offer's button, always enabled. Never two offers, never a hidden exit, never a discount (Razorpay cannot attach one to a UPI mandate, and the data says a pause keeps more readers anyway). The small print says so: "One click, any time · no calls, no forms".

**The refund** (Refund policy: seven days from any yearly or founding charge) is the same one click: "Refund" on the card, one confirmation naming the amount, the method it returns to and that Plus ends now; Razorpay refunds the latest paid invoice's payment in full at normal speed (5–7 working days), the row records the `rfnd_…`, the subscription is cancelled at once, and the email carries the reference. Outside the window the button is simply absent; the policy page says the same thing in the same words.

**Dates about money are the Indian calendar day.** Razorpay charges, invoices and retries on IST — a cycle ends at 00:00 IST — so "Renews", "Ends", "Paused until", "Refund open until", the payments list and every billing email print the IST date (`lib/dateline.billingDay`, `common/billing_emails._day`), the same words as the receipt in the reader's inbox; a device outside India sees the mono **IST** tag after the date (the founder paid from Berlin at 20:50 on the 20th, was charged on the 21st, and the card said the 20th, 2026-09-21). The product's other clock is the same one: datelines and story times are IST and say so. The Ask allowance is a rolling 24 hours, so it needs no calendar at all.

**Payments** (`Payments`): every charge on hairlines — the date in mono, the plan, the amount in tabular mono, PAID or REFUNDED as a mono word, and "Invoice ↗" to Razorpay's hosted invoice (view, download as PDF). Read live from Razorpay so it never disagrees with the receipt in the reader's inbox; a reader who has never paid sees no section at all.

**The moment of paying** (`/plus/welcome`): a stranger who signs in from `/plus` comes back to `/plus`; the payment happens in Razorpay's sheet over ours, with the account's email prefilled and **locked** (Razorpay builds its customer, and addresses every invoice, from what is typed there — an address changed in the sheet sent the receipts elsewhere, 2026-09-21); a declined card is said beside the plan and the sheet stays open — the flow ends only when the sheet is closed unpaid; the verified callback lands on **You're on Plus.** — the plan and price in the meta line, three lines of what changed, next charge · receipt · how to change your mind as a mono-labelled list, and one primary back to what they were reading. The row is kept true three ways — the verified callback, the webhook, an hourly reconcile against Razorpay — so a missed webhook never leaves a paying reader on Free.

### Email
Every email the product sends — the sign-in link, and the subscription's moments: welcome · a charge failed · cancel scheduled · paused · back on · yearly scheduled · ended / will not renew · refunded (`common/email_templates.shell`, `common/billing_emails`) — is one shape in the record's own voices, inline-styled for mail clients: a 520px card on the paper's ground, **masthead** (the mark as a PNG and "Prism" in Newsreader, the host in mono on the right, a hairline under), a **mono meta line** (plan · price · date, or "Sign in · one-time link · 15 min"), the **title** in Newsreader 500 at 28px, the paragraphs in Hind at 16px in ink-2, a **facts list** on hairlines with mono labels (Next charge · Receipt · Plus ends · Refund · Reaches you), **one** pill button in accent-fill, a hairline, and in mono why the reader got it, then "Prism · Prism Media Intelligence LLP · Follow the story, not the headlines." Web fonts are asked for once (`@import`; Apple Mail sets them, Gmail falls to Georgia / the system sans / the system mono); `color-scheme: light` asks clients not to invent a dark mode. The Prism Rule holds in the inbox: no colour but the one button and the spectrum in the mark — the old three-hue bar across the top was a gradient by another name and is gone. Plain text always travels with the HTML and says the same things in the same order. Razorpay sends the receipt and invoice for every charge; ours say what changed on Prism and what to do next, never a second receipt.

### Share cards (OG images, 1200 × 630)
The record's header at poster scale, in the record's own voices — Newsreader for the headline, Hind for the summary, JetBrains Mono for every label — on the paper's warm white: masthead (the mark and "Prism", the host in mono on the right) · a mono meta line (subject · date · N quotes) · the headline (60px, stepping down to 52/46 for long ones, at most three lines) · the summary (26px, ink-2) · a rule · the **coverage bar in the outlets' slot colours** with its count on the left and the headline's provenance ("Headline by Prism · from N reports") on the right. A story's card is the same shape with the kicker STORY, the developments and days in the meta line and the cast as the summary. **The quote card** (`/story/<id>/quote/<n>`, the Share on every quote) sets one verbatim sentence in Newsreader italic (52/44/38px by length), the speaker in Hind 600 with their role beside it, the record's headline small beneath, and the honesty line in mono at the foot: VERBATIM · outlet · date. The site card carries the promise and the coverage bar's three origins named. Never a photograph, never a colour but the bar and the mark; every glyph the card draws is in the font subset it fetches (`lib/ogFonts`).

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
- **The lens flip (kept):** a 2px scan line in the lens hue sweeps the lens block top→bottom while the text re-inks *behind* it (a veil in the ground colour lifts on the same clock, so line and ink never separate); the clock is the block's height at ~0.9px/ms, clamped 500–1100ms (`lib/motion.flipDuration`), so a five-point brief is swept at the same pace as a three-line locked box. Layout never moves. Reduced motion: instant swap.
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
- **Don't** present a publisher's photograph as Prism's: never on a row, a share card or in JSON-LD, never proxied. Only as a credited link preview of its own report (§ Images), and never as something the design depends on.
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
| 2026-09-21 | Billing dates print the IST calendar day everywhere, tagged IST on a device elsewhere | Razorpay bills on IST; the web used the browser's zone and the emails UTC, so one cycle end read as three different dates and disagreed with the receipt |
| 2026-09-21 | Cancelling a monthly opens one sheet — the truth, an optional reason, ONE offer matched to it (pause 1–3 months, or the yearly saving starting when the month ends), "Cancel anyway" beside it at equal weight; the 7-day refund is one click on the card; Payments lists every Razorpay invoice; the checkout email is locked to the account | Founder asked for retention "instead of letting them cancel directly" and for history, invoices and refunds. India's dark-pattern guidelines forbid a subscription trap and Razorpay cannot discount a UPI mandate, so the pause (the strongest lever in the data) and an honest yearly switch are the offers; a receipt went to a typed-in address, so the address is no longer typed |
| 2026-09-21 | Every email in the record's voices: masthead with the mark, mono meta line, Newsreader title, Hind body, facts on hairlines with mono labels, one accent button, mono footer; the three-hue bar removed | The shell still wore the retired world (Fraunces, Plex, ivory, the lens bar) three days after the change; the One Gradient Rule applies in the inbox too |
| 2026-09-21 | Share cards redrawn in the record's voices (Newsreader · Hind · JetBrains Mono, the coverage bar in slot colours) and a quote card with its own address per quote; the now-playing bar docks into the record's foot above the Ask bar on a desk | Founder: the cards were still the Reservation Chart's; the player lay over the Ask drawer. A sentence someone said is the most shared thing on WhatsApp — it deserves its own card |
| 2026-09-21 | The subscription's whole life on one plan card; `/plus/welcome` as the landing after paying; a declined card no longer ends the purchase; `completed` (paid up) stays active | The first real test purchase: a declined card ended our flow, the UPI success went unheard, no webhook landed, and a one-charge yearly plan read as 'expired'. Truth now arrives three ways and the reader always knows where they stand |
| 2026-09-21 | Stories rows carry a photo pile: up to three of the developments' photographs fanned, the front one credited, "+N" for the rest; legal pages take the record's three-column shape with "In short" per section | Founder: the story of many reports should look like many pictures; a policy should read like the product. Same credit rule, same kill switch |
| 2026-09-20 | Photographs return, credited: a thumbnail on every story row, a photo deck (stage + stack + filmstrip) on the record; placeholders recognised by repetition and never shown; the wide desk gets a two-column chart and wider rails | Founder: images are what make a reader tap a story; the desktop was leaving half the screen empty. The legal posture holds — every picture is the outlet's own, credited, and opens or belongs to its report; the kill switch remains |
| 2026-09-20 | Plus page in the shape every subscription page shares (hero · period control · three cards, recommended marked · side-by-side · FAQ · trust line) and a counted upgrade sheet at the limit | Founder: the first draft read as prose; readers recognise the pricing pattern and it converts (annual default with the saving shown; one primary; FAQ answers the objections). Same ink, same parts, one accent |
| 2026-09-20 | Ask: persistent bar riding the reading column + selection/quote/entity entry points; the sheet is a right drawer on a desk | Founder: a reader had to scroll to the foot to learn Ask existed, and the panel was a plain transcript; Perplexity/Particle put the question within reach of the line that prompted it |
| 2026-09-18 | Publisher photographs retired as Prism's own images; allowed only as credited link previews of the report they came from, behind a kill switch | Indian fair dealing does not cover a whole photograph and the feed T&Cs forbid republication; a credited preview that opens the outlet's page is the search-engine norm and the least exposed use. Founder ask after the Particle comparison; the design still stands without them |
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
