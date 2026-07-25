# Prism — Desktop UI design brief (for Claude Design)

Generated 2026-07-25 by `/design-consultation`. Inputs: live competitive capture
(Semafor, Ground News; FT blocked by Cloudflare), two independent design voices
(Codex + a Claude design voice that read the implementation), and DESIGN.md
(authoritative — extended, not replaced).

**Direction name: "The Stone."** Mobile is a printed copy in your hand. Desktop is
the composing stone — the flat table where a page is imposed before it prints. That
metaphor earns everything below: hard left edges, visible rules, real columns, and a
press bar that sweeps the forme when the type is re-set.

**How to use:** paste **BLOCK 0** first, then one screen block per artifact.

---

## BLOCK 0 — System contract (paste first, every time)

You are designing the **desktop** UI for Prism, an India-first role-aware AI news
intelligence product. Worldwide coverage is clustered into canonical stories; each
story can be re-read through a professional lens (General reader / Cybersecurity+GRC
/ Markets). Tagline: "One story. Every perspective."

**The memorable thing — everything serves this:** *the same story changed meaning
when I flipped the lens.*

Mobile already shipped and is good. You are NOT redesigning the design system. You
are designing how it uses a wide screen.

### Non-negotiable rules

1. **Chrome is monochrome. Color ONLY ever means a lens is speaking.** General amber
   `#F59E0B`, Cyber cyan `#06B6D4`, Markets violet `#8B5CF6`. Discrete — never
   gradients. Anything colored that is not lens-semantic gets re-inked to neutral.
   The spectrum gradient appears ONLY as a 2–3px hairline bar or gradient text.
   **Target: exactly one hue on screen at a time.**
2. **Three type voices.** **Fraunces** (display) — headlines, section heads.
   **General Sans** (UI) — body, labels, controls. **IBM Plex Mono** — provenance
   ONLY: timestamps, source codes, citations `[3]`, funding labels, CVE ids,
   tickers, counts. Never prose, never headings.
3. **Signature motion — the re-typeset flip.** Never a crossfade. A 2px lens-hued
   scan line sweeps (~500ms ease-out); text re-inks behind it (.25→1); markers adopt
   the hue; annotations stagger at 60ms. **Body text and layout NEVER move.**
   Reduced motion collapses to an instant swap.
4. **Grounds:** ivory `#FAF8F5` / surfaces `#FFFFFF` / sunken `#F1EDE7`;
   dark `#0F0E0C` / `#171512` / `#211E1A`. **Ink:** `#1C1917` / `#78716C` /
   `#A8A29E`. **Lines:** `#E7E2DA` (dark `#2B2723`).
5. **Type scale:** 42px desktop hero, 34px story H1, 30px page H1, 23px section H2,
   20px lens brief (see Story), 15.5px card title, 14.5px body, 13.5px secondary,
   12.5px caption, 11px chip, 10.5px mono-micro. **Spacing:** 4px base.

### The grid — one number set, everything derives from it

**12 columns × 74px, 32px gutters = 1240px** (preserves the existing 1240 content
shell, so left edges still align with landing/story/sector).
Spans: 3=254 · 4=338 · 5=498 · 6=604 · 7=710 · 8=816 · 9=922.

Outside the field, in the left margin: **the ledger rail, 104px**, IBM Plex Mono.

```
104 rail | 32 gutter | 1240 field  = 1376  + 32 page padding ×2 = 1440
```

1440 (the MacBook viewport) is the **native size** of this design, not something to
be responsive around.

- **≥1440** — rail + field.
- **1280–1439** — field 1240 (+20 padding ×2 = 1280 exactly), no rail; provenance
  right-aligns inside each row.
- **1024–1279** — field = `100vw − 80`; 6/6 splits shift to 7/5; prose holds ~604.
- **<1024** — the shipped mobile design, untouched. Zero regression surface.

### Hard anti-patterns (reject on sight)

- **No cards on desktop app surfaces.** No borders, no card shadows, no 18px radii
  around content. **Rules and type only.** Cards solve a *mobile* problem: on a
  phone a card is a tap target that survives a stream. At 1440px a card is a box
  drawn around content that whitespace had already separated — redundant ink,
  repeated forty times. Every competitor is a card grid; that is the opportunity.
- No generic 3-column SaaS dashboard. No card grid as first impression.
- No centered-everything. Hard left edges.
- No purple gradients, no blobs, no glassmorphism.
- **No tooltips anywhere.** Detail on hover is written into the ledger rail instead.
- No global lens switcher in the header — the lens is a per-story re-reading event,
  not a feed filter. Settled founder decision.
- Do not widen the prose measure. Extra width buys **marginalia and simultaneity**,
  never longer lines.

### The width rule (the core idea)

**The 620px column was never the bug. The 410px of dead ivory was.**

Prose measure stays. Width buys three things, none of them a sidebar:

**A. The margin.** Every timestamp, source code, citation, CVE id, ticker, funding
label, coverage origin and satellite tag is **evicted from the content** into the
104px mono rail, baseline-aligned to the line it annotates. On mobile these are
inline chips interrupting an AI-written sentence. On desktop the prose runs clean
and the evidence sits beside it. Zero new data; it finally gives the third typeface
a job worthy of being a third typeface.

**B. The other reading, held.** On mobile the flip is sequential — you see lens A,
then lens B, and you *remember* the difference. On desktop the outgoing lens does
not vanish: it settles into the right half as a **ghost** at 13.5px ink-muted with
its hue on a 2px left rule. "One story. Every perspective." stops being a claim and
becomes a fact visible on screen.

**C. The shape of a story.** A phone reader scrolls a flat list and can never
perceive that a story *branched*. Desktop shows the arborescence in one glance.

### The shell

One 56px header at 1240: prism mark + wordmark (Fraunces 20px) left; nav as plain
13.5px General Sans text; scope + language chips right. The 3px spectrum bar pins to
the viewport top — the one sanctioned brand-color object. **Exactly one brand bar on
screen, ever** (the current build stacks two — that dies here).

---

## BLOCK 1 — Feed (the front page)

Design desktop **Feed** at 1440×1024 (also 1280 and 1680).

1. **Dateline**, directly under the header rule, mono, hard left:
   `FRI 25 JUL 2026 · 14:22 IST · 1,284 SOURCES · 37 STORIES`.
   Every newspaper has one; no news app does. All computable from existing data.
2. **Lead — asymmetric 7/5.** Cols 1–7 (710px): 16:9 image, Fraunces 42px headline,
   14.5px dek. Cols 9–12 (338px): *"Also reading this"* — four headline-only
   stories, hairline-separated, source counts in the rail.
3. **Sector bands.** Full-width horizontal strata, each with a 12px uppercase
   General Sans label at the left edge, stories laid **four-up at 3 cols (254px)**,
   headline-only at 15.5px, **one image per band**. The reader gets Politics, then
   Markets, then Cyber — reading *down a page*.
4. **Ledger rail** carries, per row, baseline-aligned: source count, time, and origin
   codes (`IN ×4 · US ×1`). A single-origin story is tagged `SINGLE-ORIGIN` in
   neutral ink — it is a fact, not an error, so never red.

Density triples; visual noise halves. Ground News reads as homework because
everything is a boxed module — removing the boxes is the entire fix.

**The feed is 100% monochrome.** No lens chrome here. That silence is deliberate: it
is the setup for the flip.

---

## BLOCK 2 — Story (the forme)

Desktop **Story** at 1440×1024. **A clean 6/6 split: 604 | 32 | 604.** The page
divides in half, which *is* the product thesis.

Head zone spans the full 1240: kicker chips, then **H1 Fraunces 42px across cols
1–9** (a headline should not run full width), then a hairline. Dateline in the rail.

**Critical fix:** the current desktop build lets a giant hero own the fold and pushes
the lens control below it — the memorable moment is off-screen on arrival. Cap the
hero (~320px) or crop it beside the standfirst. Above the fold, in order:
title → standfirst → **the lens brief with its lens board**.

**Left 604 — the reading.** The lens brief set in **Fraunces 20px** — the only prose
in the product set in display type, which makes the brief feel like *the article* and
everything below it feel like apparatus. Then lens points (markers in lens hue),
Perspectives, The story so far, What to expect, Sources — all at 604px, all
scrolling.

**Right 604 — the field**, sticky, three strata separated by hairlines:

1. **The lens board.** All available lenses as horizontal **plates**: name at
   13.5px, a 2px rule, and **the first line of that lens's brief** at 12.5px
   ink-faint — the reader sees what the other readings say *before* flipping.
   Locked pro lenses keep the padlock and blur the preview. **At rest every
   unselected rule is an ink-faint hairline; hue appears only on the selected plate
   and on hover.** Exactly one hue on screen. After a flip, the outgoing plate
   expands into **the ghost** (13.5px ink-muted, its hue on a 2px left rule).
2. **The branch tree** — BLOCK 3.
3. **Ask, docked** to the viewport bottom — permanently open, never a floating
   bubble. Shows the suggested questions. Streamed citations render as mono `[3]`,
   and **hovering one lights the matching row in the left column's Sources
   section** — cross-column, monochrome, impossible on a phone.

### The flip on desktop — bigger, not closer

Mobile pinned the flip to the thumb. Desktop has a keyboard.

**Keys `1` `2` `3` flip lenses from anywhere on a story, no modifier.** That is the
desktop thumb rail: zero-travel, muscle memory, and crucially *repeatable* — a
reader will hit `1-2-3-2-1` in two seconds, and repeatability is what turns a trick
into the thing you show a colleague. Clicking a plate does the same. Hover pre-inks
a plate's rule; it never previews the flip.

Still 500ms, still 2px, still zero layout movement — but **the bar spans the full
1240px field, not just the 604px brief.** One press bar sweeps the whole page:

- `t=0` — lens-hued 2px line appears at the top of the field, sweeps down, ease-out.
- `t=0–500` — the brief re-inks .25 → 1 behind it.
- `t=60` — **the ledger rail re-inks too.** Cyber shows CVE ids and CVSS; Markets
  shows tickers and catalyst; Reader shows source counts and origins. The flip does
  not just change the prose — **it changes what counts as evidence.**
- `t=500` — the ghost is already there when the line clears: pre-rendered at
  opacity 0, revealed by the bar's passage. No crossfade, no fade-in, no movement.

Three regions re-inking under one bar beats one paragraph under a short one.
The flip also writes `?lens=cyber` to the URL — desktop readers share links, and a
shared flipped story is how the flip propagates.

**Deliver a 3-frame sequence** of this.

---

## BLOCK 3 — The Column of the Story (branch tree — the new surface)

A canonical story splits into branches. The data is persisted
(`event_story(run_id, event_id, story_label, branch_parent_id, off_spine)`, written
every 900s) and **never read**. Root is `branch_parent_id IS NULL`. There are no
branch titles and no branch summaries, and **this design deliberately requires
none.**

Not a mindmap. Not a horizontal org chart (the enterprise default). Not a force
graph (the indie cliché). A **vertical arborescence read like a river seen from
above**, in the middle stratum of the right column at 604px.

- **Time runs down, mapped ordinally, not linearly** — a linear axis makes a story
  with a three-week gap unreadable. ~44px per event. The rail prints the date in
  mono at each new day.
- **The spine is a 2px ink rule at x=16**, root at its top.
- **A branch is a 1px hairline leaving the spine at its parent's row**, dropping to a
  secondary rule indented +28px. Depth 2 = +56. Cap the visual at depth 3 with a
  mono `+2` marker — real trees here are shallow.
- **Each node is one line of General Sans 13.5px**, truncated, with `source_count`
  in mono at the right. No cards, no images, no boxes.
- **`off_spine = true` renders a dashed connector and ink-faint title**, tagged
  `SATELLITE` in the rail. The reader instantly sees "this one is loosely attached."
- **The current event is a filled 6px square in the lens hue** — the only color in
  the tree, meaning "you are here, reading this lens." So the tree re-inks on flip.

**Three interactions:**

1. **Hover → the margin writes.** Full title, date, sources, regions appear in the
   ledger rail. No tooltips — detail always appears in the one column where detail
   lives.
2. **Click → the reading column swaps to that event's brief, in the current lens,
   using the same 500ms scan line.** The tree does not re-render or re-center; only
   the "you are here" square moves. **The tree IS the navigation, and traversing the
   story reuses the flip choreography.** One motion primitive, two meanings: flip a
   lens, or flip a moment.
3. **`TRUNK` / `ALL`** — one mono toggle, bound to `T`. `TRUNK` (default) hides
   satellites and collapses to root → longest on-spine chain, which is exactly
   today's flat "story so far," so nothing regresses. `ALL` reveals the real shape.

**The shape readout — instead of a generated summary.** One mono line above the tree:

```
14 DEVELOPMENTS · 3 BRANCHES · 2 SATELLITES · SPAN 19d · WIDEST 25 JUL
```

Entirely computable today. Zero LLM, zero cost, zero hallucination. **An AI news
product that refuses to summarize a structure it can simply count** is making a
trust argument competitors can't copy.

Deliver: the **604px in-column tree**, and a **compact 320px variant** for narrow
desktop.

---

## BLOCK 4 — Trending (the ledger)

A typographic ranked table, no borders. 88px rows on hairlines.
Rank in **Fraunces 42px ink-faint** (col 1) · label + hero title (cols 2–7) · cast
(8–9) · velocity as mono `+312%` beside a **monochrome 2px bar** whose length
encodes it · developments + sources (10–12). Hover raises the row to `--bg-elevated`
— no shadow, no movement.

The rail carries **the hour each story last moved**, row-aligned. The page reads as
a day: ranks 1–12 with cast and velocity simultaneously, where a phone shows 2.5
rows.

Scope selector (All / <State> / National) and sector chips sit under the H1. Markets
maps to the `finance` sector; there is deliberately no Cyber chip (cybersecurity is
excluded from trending upstream). `developing` sets in **neutral ink, not green** —
velocity is not a success metric.

---

## BLOCK 5 — Search (the query line)

Search stops being a page. **`/` or `⌘K` from anywhere** opens a full-viewport ivory
scrim at 92% — paper, not glass-blur gloss.

The query sets in **Fraunces 34px** at the field's left edge with a 2px ink caret.
Below a hairline, three strata: **Stories** (6 cols) · **Entities** (3) · **Sources**
(3, with mono slug + funding label). Live as you type, the right 5 cols render **the
top hit's lens board** — so search itself demonstrates that one entity reads three
ways.

Keys: `↑↓` move · `⏎` opens · `⌘⏎` opens in the current lens · `Esc` closes.
Before typing: recent searches, trending entities as chips, and mono examples
(`RELIANCE`, `CVE-2026-62144`, `Kerala`). Never a blank screen.

---

## BLOCK 6 — You (the colophon)

Not a settings dashboard. A colophon states how a book was made; this states **how
your Prism is made.** A two-column definition list: label in 12px caps at 3 cols,
value in **Fraunces 20px** at 6 cols, edit affordance as a text link in the rail.
Lens, state, languages, interests, watchlist. A row that looks clickable must be
clickable.

Identity status ("signed in · synced across devices") sets in **General Sans, not
mono** — it is prose, not provenance.

Plus the one desktop-only pleasure: **your reading record** — 12 weeks × 7 days of
hairline ticks, each day's mark a 2px vertical rule in that day's dominant **lens
hue**. The only place outside a story where color appears, and it is legal: each
tick literally means a lens was speaking that day. The only place you see your own
spectrum.

---

## Deliverables per block

Each screen: **1440×1024** (native), a **1280** state, light + dark.
Story additionally: the **3-frame flip sequence**. Branch tree: **604 in-column**
and **320 compact**.

Use real Indian news content (Kerala power crisis, RBI digital-lending guidelines, a
CVE with CVSS, an NBFC ticker). No lorem ipsum, no US placeholder news.

---

## Build ladder (for implementation, after designs are approved)

1. `screens.rail: 1440px` + lens hues and ink scale into `theme.extend.colors` —
   everything today is inline `style={{}}`, which makes this rebuild miserable.
2. `lg:` grid on Feed / Trending / You / Search — deletes the `max-w-[620px]`
   stranding and ships the visible 80% of the fix.
3. Widen `.flip-scanline` to the field; add rail re-ink; bind `1/2/3`.
4. Ledger rail as one component consuming `{label, value}[]` from whatever is in view.
5. `branches` on `EventDetail.story` (~15 lines in `_partitioned_members` +
   `_assemble_timeline`), then the tree:
   ```jsonc
   "story": { "developments": [...], "cast": [...],
     "branches": { "root_id": str,
                   "nodes": [{"id", "parent_id", "off_spine", "depth"}] } }
   ```

Deferred: branch summaries (the shape readout covers it until Stage 4 lands), the
branch-diff view (⌘-click two branch heads → split reading column headed
`WHY THESE SEPARATED`, using `event_links.rationale`) — ship after the tree proves out.
