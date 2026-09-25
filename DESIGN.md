---
name: Prism
description: "Follow the story, not the headlines."
world: "Design System v2 (2026-09-24, tokens 5.0.0; replaces Spectrum v4). Source: Claude Design project 'Prism Design System' (95aedb30-fd57-40e7-9d01-029b95a54b61)"
tokens: design/tokens.json
generated: web/src/app/globals.css (uv run python design/gen_css.py; --check in CI)
colors:
  # Light (default). Dark values, data palettes and roles live in design/tokens.json.
  paper: "#F7F6F2"
  surface: "#FFFFFF"
  sunken: "#EEECE6"
  elevated: "#FFFFFF"
  ink: "#111317"
  ink-2: "#3F434A"
  ink-3: "#5B6069"
  line: "#DFDDD6"
  line-strong: "#8E8B82"
  accent: "#0B57D0"
  accent-strong: "#0842A0"
  accent-soft: "#E3ECFB"
  coverage-national: "#1E3A6E"
  coverage-intl: "#1583A8"
  coverage-regional: "#C4470F"
  coverage-wire: "#767872"
  lens-markets: "#117A48"
  lens-cyber: "#7A3FC4"
  lens-health: "#B8246B"
  lens-policy: "#8A6100"
  danger: "#B42318"
  paper-dark: "#0F1114"
  surface-dark: "#171A1F"
  ink-dark: "#F2F1ED"
  accent-dark: "#8AB4F8"
typography:
  record: { fontFamily: "Newsreader, Noto Serif Devanagari/Kannada/Tamil/Telugu/Bengali/Gujarati, Noto Nastaliq Urdu, Georgia, serif", fontWeight: 600, quote: "italic 400" }
  read: { fontFamily: "Anek Latin, Anek Devanagari/Kannada/Tamil/Telugu/Bangla/Gujarati, Noto Naskh Arabic, system-ui, sans-serif", fontWeight: 400 }
  mono: { fontFamily: "Geist Mono, ui-monospace, Menlo, monospace", fontWeight: 400 }
rounded: { record: "2px", control: "8px", sheet: "16px", pill: "9999px" }
spacing: { 1: "4px", 2: "8px", 3: "12px", 4: "16px", 5: "20px", 6: "24px", 7: "32px", 8: "40px", 9: "48px", 10: "64px" }
---

# Design System: Prism — v2

> **2026-09-24 — Design System v2 (tokens 5.0.0).** Designed in Claude Design (project "Prism Design
> System"). `design/tokens.json` and the generated block of `web/src/app/globals.css` are the truth for
> values. The system's own component classes live verbatim in `globals.css` (`.p-*` from its
> `components/prism.css`, `.sc-*` from its `screens/screens.css`); the older shared classes (`.btn`,
> `.chip`, `.card`, `.row-card`, `.covbar`, `.status-*` …) are restyled onto the same shapes, so a
> component not yet rebuilt still paints in v2. Pages designed in v2: Landing, Today, Story (Pages v3),
> the phone tabs (Stories, Search, Watchlist, You), Plus / Welcome / Account, the labeller workspace and
> its story-boundary task, and the admin Overview and Controls. Everything else inherits the tokens and
> classes and is on the missing list sent back to Claude Design.

## Overview

Prism reads Indian news from many outlets in many languages and keeps **one record per event**: every
outlet that reported it, in every language, with **who said what, word for word**, each quote checked
against its article. A reader can re-read any story through a **lens**. Prism shows the record, not a
verdict. The product speaks to the reader as *you*; on record surfaces Prism refers to itself as
*Prism*, never *we* ("we" is allowed in account, legal and email copy).

## Content rules (binding)

- **Counts are counts:** "9 outlets · 2 languages", "4 developments". Below 30 a share is "3 of 4", never
  "75%"; a change off a small base is "+3 from 4". A figure not yet counted is "—" with "Not counted yet",
  never 0 and never "no change".
- **Provisional says so:** "Provisional grouping", "Grouping under review", "One source so far".
- **Verbatim or nothing:** a quote in its exact words with speaker, outlet, time and "Open at the quote ↗";
  a translation says "translation"; no paraphrased quotes.
- **Never list lens names** in generic copy; pickers render the lens API.
- **No placeholders in the product:** everything on screen is live data or real product copy. The design
  mocks' ILLUSTRATION banners and sample data never ship; a section with no live data is left out.
- **Errors in words** ("Today's record could not load") with one way on; empty states worded per filter
  ("No Politics records today"); busy states replace the words ("Sending…"); no spinners on the record.
- Sentence case everywhere. CAPS only in mono provenance strips (`UPDATED 12M AGO`) and eyebrow labels.
  No emoji. Unicode arrows (→ ↗ ←) only inside link text; UI icons come from `web/src/components/icons.tsx`.
  A middle dot " · " separates facts.

## The mark

A 24×24 box: an equilateral prism, fill only, base 20 wide at y 19.5, apex at 2.18; the spectrum a band
attached to the base, exactly its width, 2.75 tall, stops #EF4444 · #F59E0B · #06B6D4 · #8B5CF6. Geometry
lives once in `web/src/lib/mark.ts`. The triangle takes `currentColor`; the band is the only gradient in
the product — no background gradients, gradient text or gradient rules anywhere, the header included.

## Colour

Neutral warm paper and carbon ink; colour appears only where the prism "splits light":
- the **coverage bar** — outlet origin in the fixed slot order English national (navy) · international
  (blue-green) · Indian-language (orange) · wire (hatched grey); each ≥ 3:1 on paper, neighbours split by
  hue AND a 2px gap, always with its count beside it;
- a **lens** — one discrete hue AND one shape per lens (Markets green circle, Cyber violet square; Health
  magenta diamond and Policy ochre triangle drafted; further lenses take the next free slot
  `--lens-slot-5…8`); the Reader lens has no hue;
- **one interactive accent**, cobalt `#0B57D0` (dark `#8AB4F8`), for links, the primary action, focus and
  the current nav item.

Admin charts may use `--data-1…6` (Okabe–Ito, darkened) and the one-hue ramp `--seq-1…7`; an uncounted
day or cell is hatched (`--data-uncounted`), never drawn as zero. Colour never carries meaning alone:
every bar has its count, every pill its word, every dot its label. Floors: body text 4.5:1 on both
grounds; tertiary ink `#5B6069` is 5.9:1; white on the accent fill 6.4:1.

## Typography — three voices, three jobs

- **Record** — Newsreader (drawn for news, optical sizes) with a Noto Serif per Indic script and Noto
  Nastaliq for Urdu: headlines, titles, quotes (italic 400) and hero figures, set 600 with −0.02em at
  display sizes. Never a button or a label.
- **Reading/UI** — Anek (Ek Type), one Indic-first design across Latin, Devanagari, Kannada, Tamil, Telugu,
  Bangla, Gujarati, Gurmukhi, Malayalam and Odia, plus Noto Naskh Arabic for Urdu: body, UI, labels, eyebrows (caps, 0.08em). Body
  floor 14.5px; inputs 16px (no iOS zoom).
- **Provenance** — Geist Mono, tabular: only times, counts, [n], outlet codes, tickers and CVE ids. Floor
  11px. Never prose, never a heading.

Scale (phone → desk ≥1024): display-xl 44/72, display-l 30/42, display-m 23/28, title 18/20, title-s 16.5,
quote 18/19, body-l 17/18, body 16, body-s 14.5, ui 15, ui-s 13.5, label 12.5, mono 12, mono-s 11 —
generated as `--t-*` font shorthands. All faces load through `next/font` on `<html>` (self-hosted; the
Indic faces are unicode-ranged and fetched only when a glyph needs them). Every script Prism labels has a
record face and a reading face.

## Layout

4px spacing scale. The reading column is 640px and never grows; width buys evidence beside the record: a
left rail (220 → 240 at ≥1536), an evidence rail (320 → 380), and two story columns on Today's desk. Top
bar 60 (desk), masthead 52 and tab bar 58 (phone), touch targets 44+, gutter 16 / 24 / 32. Fixed chrome:
the top bar or masthead (sticky, paper at 92% with a 12px blur) and the phone tab bar — or, on a story, the
story's own Ask · Share bar so the two never overlap. No page scrolls sideways at any width.

## Shape, rules and state

Records are cut square (2px), controls are pressed (8px), sheets are held (16px). Chips draw at 36px and
ticker chips at 26px, but each carries an invisible 44px tap area (`.p-chip::after`, `.p-hit`). Sections sit under a 3px ink rule, newspaper style; the lead row carries the same rule.
State is line form: solid = verified; dashed = provisional or one source; faded (62%) = stale; dashed +
hatched = not counted. Shadows are almost none: `--shadow-1` marks a selected segment, `--shadow-2` is
for sheets, drawers, popovers and toasts. No card lift on hover.

## Components

The system's components (Claude Design `components/<group>/`) and their app homes: chrome (TopBar =
`SiteHeader` + `HeaderNav`, `Masthead`, `BottomTabBar`, `SectionHead` = `.p-sechead`, SubjectNav,
ScopeChips, StepIndicator, ThemeToggle, SkipLink, the Footer in the root layout); record (`ChartRow` =
StoryRow, `StoryCard`, `Coverage` = CoverageBar / Legend / OutletStack, `StatusPill`, MetaLine `.p-meta`,
QuoteCard, ReportCard, ChangeTimeline, ImpactRow, EntityMark, LangTag, TickerChip, CveChips); lens
(LensSwitch, LensBrief with the flip, BriefPlayer); ask (AskBar, AskAnswer, AskPanel, AskLimitNote,
StoryActionBar, SelectionAskChip); media (PhotoDeck, PodcastClip, XPostCard, `PhotoImg`);
structure (RouteMap, BranchTree, AttentionChart, MarketDigest, RelatedStories, RouteCard); money
(PricingCard, BillingSwitch, CompareTable, FaqItem, TrustLine, PlanCard in 8 states, PaymentRow,
CancelSheet, UpgradeSheet); label (TaskHeader, CandidateRow, AnswerButtons, BatchRow, QualifyRow, Verdict,
GuideInShort, QuoteInContext, ResultScreen); admin (KpiTile, ChartPanel, TrendChart, StackedBars,
RankedBars, DotPlot, Funnel, CohortGrid, NeedsYou, SwitchRow, AuditItem, DataTable, FilterSwitch, KofNBar,
NetworkFrame); ui (Button, Chip, Segmented, TextField, SelectField, Checkbox, ToggleRow, Alert, Toast,
Sheet, Skeleton, EmptyState, OnThisPage, SystemPage for 404 / error / offline).

### The story record (sections in this order)

Header: status pill · updated · subject, the title (display-l), the summary with entity marks, the counted
stats (outlets, languages, reports, quotes, developments — each jumps to its section), the hero coverage
bar, the credited photo deck. Then **Brief** (lens switch "Read it as", the brief, Listen) → **What
changed** → **Who said what** → **Heard on** → **On X** → **How it unfolded** (route map + attention) →
**Why it matters** → **Coverage** → the record's own extras (corrections and versions, "Something
wrong?", related stories) → **Ask**. A section with no data is absent, never empty. Desk: "On this story"
left nav with scroll-spy and counts; evidence rail with Reports and Named in the reports. Phone: back bar,
sticky section tabs, read-progress line, the Ask · Share bar in the thumb zone.

## Motion

Quiet by default: micro 140ms, standard 220ms, ease `cubic-bezier(.2,.7,.2,1)`. Rows print in (200ms,
40ms stagger); blocks reveal once on first view; the hero coverage bar draws in once; sheets arrive from
their edge. **Images:** a publisher photo fades in over its sunken placeholder (320ms) with the credit
already on it; the story's photo deck advances in 480ms `cubic-bezier(.2,.8,.2,1)` — the front photo
leaves sideways with a 5° tilt as the next rises from 94% — and follows a drag at 1° per 40px (past 60px
advances, else springs back). (The photo pile the design still ships is unused: the v3 Stories list draws
no photographs, 2026-09-25.) **The lens flip** is the only signature motion: a 2px scan line in the lens hue sweeps the brief
while a paper veil lifts on the same clock, paced by the block's height (900–1800ms); never a crossfade,
and layout never moves. Reduced motion collapses everything to an instant change.

## Do's and Don'ts

Do: print counts, keep quotes verbatim, mark provisional, use tokens for every colour so both themes hold,
keep 44px targets, keep the reading column at 640. Don't: add a gradient, set prose, headings or labels in
mono, colour-code without a word, invent a number or an example, list lens names in prose, put a card lift
on hover, or ship a mock's placeholder.

## Decisions Log

Historical entries were written under whichever name and world was current; the design decision each records is unaffected. Entries before 2026-09-18 describe the retired Reservation Chart and, before 2026-09-15, the ivory broadsheet; they are kept as history.

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-25 | Wave 2 from the Claude Design flow boards (Reading, Accounts, Money, Legal, Labeller, Admin, emails, share cards, icons): every remaining route built state by state; lens-mark shapes (circle · square · diamond · triangle) and Today's "Has a professional read" filter ADOPTED (the design adopted both on 25 Sep); Gurmukhi, Malayalam and Odia faces added; chips keep 36px but get a 44px tap area; the record's own 404 and error pages (SystemPage) replace Next's; the favicon is the design's adaptive SVG; Stories rows follow the v3 board — developing-story rows with a one-ink bar and no photo pile (reverses 2026-09-21). Still not built: the onboarding languages step and the offline page (PROPOSED in the design), and anything a board draws that the product has no data for | Founder asked for every unplaced design component used and the whole product designed; the design's own adoption log decided the two PROPOSED items that 2026-09-24 had left out |
| 2026-09-24 | Design System v2 adopted from Claude Design: cobalt accent, Newsreader / Anek / Geist Mono, records 2px · controls 8px · sheets 16px, navy · blue-green · orange · grey coverage, the system's `.p-*` classes verbatim in globals.css; the header spectrum line and the ruled page ground removed; the design's ILLUSTRATION banners and sample data never ship; lens-mark shapes and the "Has a professional read" filter (both PROPOSED in the design) not adopted | Founder asked for the whole product redesigned on the Claude Design system, with anything the system lacks noted rather than invented (the gap list went back to Claude Design) |
| 2026-09-18 | New world "Spectrum": Newsreader / Hind / JetBrains Mono, near-white ground, brand violet accent, soft radii, cards for rows | Founder brief: the chart read as dull and un-navigable; readers could not see what Prism does. The prism's own metaphor — white light in, spectrum out — now sets where colour appears |
| 2026-09-18 | Colour rule widened: coverage hues + lens hues + one accent (was: lenses only) | The coverage bar makes "one story from many reports" visible on every row; the accent makes interaction legible in a mobile app |
| 2026-09-18 | Coverage bar order national · international · regional · wire, palette validated in both modes | Red and amber are indistinguishable for deutan readers when adjacent; the order keeps them apart and the count text is the legend |
| 2026-09-21 | "On X" record section: the official accounts' posts, as written, after Heard on; signal never counted as coverage; X's display rules met inside the monochrome (greyscale avatar, the X mark in the stroke set, View on X); "First on X" as one mono line, strict, never for a link-post | Founder decision to read X as a signal tier, official bodies only, the story never created by a post; a post is the institution speaking in its own name, which the verbatim rule already knows how to print. Speed is not the promise; provenance is |
| 2026-09-21 | Billing dates print the IST calendar day everywhere, tagged IST on a device elsewhere | Razorpay bills on IST; the web used the browser's zone and the emails UTC, so one cycle end read as three different dates and disagreed with the receipt |
| 2026-09-21 | Cancelling a monthly opens one sheet — the truth, an optional reason, ONE offer matched to it (pause 1–3 months, or the yearly saving starting when the month ends), "Cancel anyway" beside it at equal weight; the 7-day refund is one click on the card; Payments lists every Razorpay invoice; the checkout email is locked to the account | Founder asked for retention "instead of letting them cancel directly" and for history, invoices and refunds. India's dark-pattern guidelines forbid a subscription trap and Razorpay cannot discount a UPI mandate, so the pause (the strongest lever in the data) and an honest yearly switch are the offers; a receipt went to a typed-in address, so the address is no longer typed |
| 2026-09-21 | Every email in the record's voices: masthead with the mark, mono meta line, Newsreader title, Hind body, facts on hairlines with mono labels, one accent button, mono footer; the three-hue bar removed | The shell still wore the retired world (Fraunces, Plex, ivory, the lens bar) three days after the change; the One Gradient Rule applies in the inbox too |
| 2026-09-21 | Share cards redrawn in the record's voices (Newsreader · Hind · JetBrains Mono, the coverage bar in slot colours) and a quote card with its own address per quote; the now-playing bar docks into the record's foot above the Ask bar on a desk | Founder: the cards were still the Reservation Chart's; the player lay over the Ask drawer. A sentence someone said is the most shared thing on WhatsApp — it deserves its own card |
| 2026-09-21 | The subscription's whole life on one plan card; `/plus/welcome` as the landing after paying; a declined card no longer ends the purchase; `completed` (paid up) stays active | The first real test purchase: a declined card ended our flow, the UPI success went unheard, no webhook landed, and a one-charge yearly plan read as 'expired'. Truth now arrives three ways and the reader always knows where they stand |
| 2026-09-21 | Stories rows carry a photo pile: up to three of the developments' photographs fanned, the front one credited, "+N" for the rest; legal pages take the record's three-column shape with "In short" per section | Founder: the story of many reports should look like many pictures; a policy should read like the product. Same credit rule, same kill switch |
| 2026-09-23 | A quote prints the language it was PRINTED in whenever its card holds more than one (`ಕನ್ನಡ · Prajavani` in the provenance voice), the card counts languages the way the coverage bar does, no language can be pushed out of the two-quote fold, a signed-in reader's own language leads the rotation with the other rendering beside it, and the share card's honesty line reads VERBATIM IN <LANGUAGE> · outlet · date | Verbatim is checked against the ARTICLE (`enrichment/claims.py`), not against the speaker, so an outlet's own translation passes it — and speaker names are canonicalised to English, which puts the translation on the same card as the original. Measured: 93 speaker cards mix scripts and the fold held whichever outlet published last, with nothing saying a language was missing. Same rule the role already follows one line above: say what the article supports, never more |
| 2026-09-23 | One statement printed in two languages is one quote with the other rendering beside it ("at most one is the words as spoken"); an outlet's translation is labelled `<language> translation` and its share card says TRANSLATED, never VERBATIM | The fold was spending both places on one thing a speaker said, and a lone Kannada rendering of an English sentence printed as the speaker's words. Founder D-quote-2/3/4: the original WITH the translation, renderings printed but labelled, a model may only downgrade |
| 2026-09-23 | The founders' dashboard (`/admin`) is "the ledger": hairline tables, ink only, the accent only on what acts; every figure followed by its source and the day counting began; a day not counted is empty, never zero; below 30 a share prints as a count ("3 of 4"); daily strips are ink (the latest day full ink, the rest `ink-3`) with a day-by-day table beneath; a "Needs you" row first, which says "could not check" rather than "nothing" when it fails | Founders will show these numbers to investors. A figure that cannot say where it came from, or a percentage of four readers, reads as a claim about a market; the record's own rule — counts as counts, nothing invented — applied to Prism itself |
| 2026-09-24 | Every count prints its denominator: "k of N monitored outlets · checked Xm ago" on the record header and the landing, linking **`/sources`** — the monitored set in public, by language (English first, then the most-read Indian languages), each feed with its origin, state desk, single-topic or official note and "Read 3m ago" / "Not reached since 2d ago" in words, a feed silent for an hour on a dashed rule, and "Not read yet" naming the most-read Indian languages with no outlet. Nothing operational (no feed URL, no error text) | Strategy report: "2 outlets" read as everyone who covered it; the record's promise is corroboration, so the denominator and its freshness must be visible. Line form and words, never colour (The Legend Rule) |
| 2026-09-24 | The tone label is gone from report cards and the payload; single-source reads "Single source · not yet corroborated"; the brief's hint and `/about` no longer claim "nothing unsourced" — why-it-matters is labelled Prism's reading; `/about` gains "The words on a record" (a plain glossary) and the structured report links; the landing leads with the evidence and states that the evidence is free | Founder D-a and the strategy report: 76 of 76 live source rows carried an undefined LLM tone word beside a page saying Prism rates no outlet, and "nothing unsourced" sat beside a brief that infers. Claim what the page can show |
| 2026-09-24 | `/admin` becomes charts, an admin-only exception to the reader rules: bordered panels in a grid (V2); one categorical palette `--viz-1..6` plus a one-hue ramp, validated for colour-blind readers on both grounds (`app/admin/admin.css`, V3); Recharts loaded on `/admin` only, checked in CI (`scripts/check-admin-only.mjs`, V1); one 3D view, the coverage network, loaded only when opened with its tables beside it (V4). The ledger's honesty rules stand: source behind an ⓘ on every panel, every chart turns into its table, days not counted shaded and never drawn as zero, "k of n" below 30, change as "+3 from 4" off a small base, state in words and line form (ON solid, OFF dashed) and never red/green | Founder: "everything is in prose". A dashboard is read at a glance and compared over time, which prose and hairline tables do not serve; colour is needed there to tell series apart, so it is confined to `/admin` and checked rather than guessed. 3D earns its place only where the shape is the finding (language islands in who-covers-with-whom); every number stays 2D |
| 2026-09-23 | Labelling guides are served, not shipped: `GuideView` renders what the API sends — the question as title, reading time as a mono line under it (no eyebrow), "In short" first, Do / Do not and examples on hairlines, each verdict a word with a Check or Dash, ILLUSTRATION on an invented example; the red rule on Do not is gone | Founder: do not leak the guides to outsiders — a client component is public JavaScript. `danger` is for destructive actions only; a verdict is a word first (the Legend Rule) |
| 2026-09-23 | The labeller workspace (`/label`, `/label/learn/<kind>`) is set as the task page is — rules and type, no cards, one ink pill for the primary action, mono only for counts; right and wrong in practice are the words "Right." / "Not quite." carried by rule weight, never a colour; the result screen lists the reasons for what was missed | A labelling tool that paints answers green spends the product's one colour rule on a checkbox, and the Legend Rule forbids state by colour alone. Founder decisions 2026-09-23: apply + approval, language gating, a 90% test per kind |
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
