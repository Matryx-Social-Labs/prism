---
name: Prism
description: "Follow the story, not the headlines."
colors:
  # Light ground (default; `data-theme="light"` or no preference)
  bg: "#f2f4ee"
  bg-elevated: "#fafbf8"
  bg-sunken: "#e8ece2"
  ink: "#141414"
  ink-muted: "#5c5f58"
  ink-faint: "#6d7068"
  line: "#d6dbcf"
  line-strong: "#b9c0b1"
  lens-general: "#b45309"
  lens-cyber: "#0e7490"
  lens-finance: "#6d28d9"
  lens-general-bg: "#fef3e2"
  lens-cyber-bg: "#e0f4f8"
  lens-finance-bg: "#ede9fe"
  danger: "#b91c1c"
  up: "#047857"
  # Dark ground (`data-theme="dark"` or system preference)
  bg-dark: "#141613"
  bg-elevated-dark: "#1b1e19"
  bg-sunken-dark: "#0f110e"
  ink-dark: "#ebeee6"
  ink-muted-dark: "#a3a79d"
  ink-faint-dark: "#82867f"
  line-dark: "#2a2e27"
  line-strong-dark: "#3d423a"
  lens-general-dark: "#fbbf24"
  lens-cyber-dark: "#22d3ee"
  lens-finance-dark: "#a78bfa"
  lens-general-bg-dark: "rgba(251, 191, 36, 0.12)"
  lens-cyber-bg-dark: "rgba(34, 211, 238, 0.12)"
  lens-finance-bg-dark: "rgba(167, 139, 250, 0.14)"
  danger-dark: "#f87171"
  up-dark: "#34d399"
typography:
  display:
    fontFamily: "Teko, sans-serif"
    fontSize: "26px"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "0.03em"
  display-count:
    fontFamily: "Teko, sans-serif"
    fontSize: "44px"
    fontWeight: 400
    lineHeight: 0.9
    letterSpacing: "-0.01em"
  display-nav:
    fontFamily: "Teko, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.04em"
  headline:
    fontFamily: "Hind, Hind Mysuru, Hind Madurai, Hind Guntur, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 500
    lineHeight: 1.25
  headline-row:
    fontFamily: "Hind, Hind Mysuru, Hind Madurai, Hind Guntur, system-ui, sans-serif"
    fontSize: "15.5px"
    fontWeight: 500
    lineHeight: 1.4
  title:
    fontFamily: "Hind, Hind Mysuru, Hind Madurai, Hind Guntur, system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 500
    lineHeight: 1.15
  body:
    fontFamily: "Hind, Hind Mysuru, Hind Madurai, Hind Guntur, system-ui, sans-serif"
    fontSize: "14.5px"
    fontWeight: 400
    lineHeight: 1.6
  ui-label:
    fontFamily: "Hind, Hind Mysuru, Hind Madurai, Hind Guntur, system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 500
    lineHeight: 1.55
  hint:
    fontFamily: "Hind, Hind Mysuru, Hind Madurai, Hind Guntur, system-ui, sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "Martian Mono, ui-monospace, Menlo, monospace"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.7
    letterSpacing: "0.06em"
  mono-dateline:
    fontFamily: "Martian Mono, ui-monospace, Menlo, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0.04em"
rounded:
  none: "0px"
  focus: "2px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  row: "14px"
  row-lead: "20px"
  header: "56px"
  strip: "44px"
  control: "48px"
components:
  chart-row:
    typography: "{typography.headline-row}"
    textColor: "{colors.ink}"
    padding: "14px 0"
    rounded: "{rounded.none}"
  chart-row-lead:
    typography: "{typography.headline}"
    textColor: "{colors.ink}"
    padding: "20px 0"
    rounded: "{rounded.none}"
  chart-row-count:
    typography: "{typography.display-count}"
    textColor: "{colors.ink}"
    width: "56px"
  chart-row-label:
    typography: "{typography.label}"
    textColor: "{colors.ink-faint}"
  section-head:
    typography: "{typography.display}"
    textColor: "{colors.ink}"
    padding: "16px 0 0"
  masthead-wordmark:
    typography: "{typography.display}"
    textColor: "{colors.ink}"
  masthead-dateline:
    typography: "{typography.mono-dateline}"
    textColor: "{colors.ink-muted}"
  nav-header-link:
    typography: "{typography.display-nav}"
    textColor: "{colors.ink-muted}"
    padding: "4px 4px 2px"
  nav-header-link-active:
    typography: "{typography.display-nav}"
    textColor: "{colors.ink}"
    padding: "4px 4px 2px"
  sector-code:
    typography: "{typography.mono-dateline}"
    textColor: "{colors.ink-muted}"
    height: "{spacing.strip}"
    padding: "12px 8px 8px"
  sector-code-active:
    typography: "{typography.mono-dateline}"
    textColor: "{colors.ink}"
    height: "{spacing.strip}"
    padding: "12px 8px 8px"
  tab-underline:
    typography: "{typography.label}"
    textColor: "{colors.ink-muted}"
    height: "{spacing.strip}"
  tab-underline-active:
    typography: "{typography.label}"
    textColor: "{colors.ink}"
    height: "{spacing.strip}"
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.bg}"
    rounded: "{rounded.pill}"
    padding: "8px 16px"
    typography: "{typography.ui-label}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "6px 12px"
    typography: "{typography.ui-label}"
  lens-tab:
    backgroundColor: "transparent"
    textColor: "{colors.ink-muted}"
    rounded: "{rounded.pill}"
    padding: "6px 14px"
  lens-tab-selected:
    backgroundColor: "{colors.lens-general-bg}"
    textColor: "{colors.lens-general}"
    rounded: "{rounded.pill}"
    padding: "6px 14px"
  input:
    backgroundColor: "{colors.bg-elevated}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: "{spacing.control}"
    padding: "0 16px"
  field-label:
    typography: "{typography.ui-label}"
    textColor: "{colors.ink}"
  bottom-tab:
    typography: "{typography.label}"
    textColor: "{colors.ink-muted}"
    height: "44px"
  bottom-tab-active:
    typography: "{typography.label}"
    textColor: "{colors.ink}"
    height: "44px"
---

# Design System: Prism

> The world changed on 2026-09-15. The old system (Fraunces / General Sans / IBM
> Plex Mono on ivory, 18px cards, "Perspectives") is retired; this file records
> the reservation chart as it shipped, derived from `web/src/app/globals.css`,
> `web/src/app/layout.tsx` and the components. What survived the change is the
> brand, not the costume: the colour rule, the three-voice commitment, the lens
> flip, the tagline, and the refusal to enumerate lens names in prose. The
> Decisions Log at the end carries the old history forward.

## Overview

**Creative North Star: "The Reservation Chart"**

The day's news is the reservation chart pinned at the platform: one public list,
every name on it, read the same way by everyone, re-sorted rather than rewritten
when the reader changes how they read. The ground is pale continuous stationery,
the ink is one black, and the structure is a strict table of hairlines, codes and
counts. Nothing is decorated; the evidence is the design. The number at the left
of a row is how many outlets reported it, the code is the subject, and the label
grid beneath is the same three facts in the same order on every row.

The system is dense but never crowded: rows are 14px apart on 1px rules, the lead
row is set large, and the page is one column at every width. Colour is absent
from chrome so that when it appears it means exactly one thing: a professional
lens is speaking. State is carried by line form (solid, dashed, half-weight),
never hue. Confirmed rejections: the category default of a cream broadsheet with
a serif lead and cards beneath; perforations, dot-matrix faces and distressing;
a marketing hero on the chart.

**Key Characteristics:**
- One ink, three greys, one rule colour; the three lens hues are the only colour.
- Three voices: Teko for structure, Hind (six scripts) for reading, Martian Mono for provenance.
- Hairlines for structure, no cards, no shadows, no gradients in chrome.
- Counts are printed as counts; quotes are verbatim; single-source rows sit on a dashed rule.
- One signature motion (the lens flip) plus one authored entrance (the chart printing).

## Colors

A monochrome stationery ground with one ink; the three lens hues are semantic identifiers, present only where a lens speaks.

### Primary
- **Ink** (`{colors.ink}` / dark `{colors.ink-dark}`): every heading, headline, count, active tab underline, primary pill fill, focus ring, and text selection. There is no other primary.

### Secondary
- **General amber** (`{colors.lens-general}` / dark `{colors.lens-general-dark}`), **Cyber cyan** (`{colors.lens-cyber}` / `{colors.lens-cyber-dark}`), **Markets violet** (`{colors.lens-finance}` / `{colors.lens-finance-dark}`): the 7px lens dot after a headline, the selected lens tab's text and 1.5px inset ring, the flip's scan line, and the "Reads as" dot on the form. The `-bg` tints are the selected lens tab's fill and nothing else. Discrete, never a gradient. Dark mode brightens the hue two steps; it never desaturates.

### Tertiary
- **Danger** (`{colors.danger}` / `{colors.danger-dark}`): fetch failures and destructive confirms only. **Up** (`{colors.up}` / `{colors.up-dark}`): a price move on a markets read. Neither appears in chrome.

### Neutral
- **Stationery** (`{colors.bg}` / dark `{colors.bg-dark}`): the page, the sector strip, the bottom tab bar.
- **Elevated** (`{colors.bg-elevated}` / `{colors.bg-elevated-dark}`): inputs, selects, the Ask sheet, the unselected lens pill on the phone rail, the landing's demo frame.
- **Sunken** (`{colors.bg-sunken}` / `{colors.bg-sunken-dark}`): a selected square chip's fill and loading skeleton bars.
- **Print grey** (`{colors.ink-muted}` / `{colors.ink-muted-dark}`): summaries, hints, inactive nav, the dateline, the bottom tab's inactive label (5.28:1 on light).
- **Faded** (`{colors.ink-faint}` / `{colors.ink-faint-dark}`): the label grid, `[n]` citations, section counts, the single-source count. Set at 4.5:1 on both grounds specifically so 11px mono still reads.
- **Rule** (`{colors.line}` / `{colors.line-dark}`): every hairline, the header and strip borders, the live row rule.
- **Rule strong** (`{colors.line-strong}` / `{colors.line-strong-dark}`): the dashed single-source rule, square button and input borders, the scrollbar thumb.

### Named Rules
**The Lens Speaks Rule.** Chrome is monochrome. Colour only ever means a lens is speaking; anything coloured that is not lens-semantic is re-inked to the neutral scale.

**The Line Form Rule.** State is line form, never hue: solid 1px rule = live, multi-source; dashed 1px `line-strong` = single-source; solid at 60% opacity = stale. No badge, no colour, no icon says these things.

**The One Gradient Rule.** The mark's own spectrum base (a 3-unit bar under the triangle) is the only gradient on any surface. No spectrum hairline above the header, no gradient text.

## Typography

**Display Font:** Teko (with sans-serif)
**Body Font:** Hind, falling through per glyph to Hind Mysuru (Kannada), Hind Madurai (Tamil), Hind Guntur (Telugu), then system-ui
**Label/Mono Font:** Martian Mono (with ui-monospace, Menlo)

**Character:** Station signage over a reading face over a teletype. Teko is the condensed board lettering of the chart itself; Hind is one family across Latin, Devanagari, Kannada, Tamil and Telugu so a Kannada headline and an English one sit on the same page without a fallback seam; Martian Mono is tabular by definition (`font-variant-numeric: tabular-nums` on every `.font-mono`) because a column of counts and times must align.

### Hierarchy
- **Display** (Teko 500, 26px, line-height 1, +0.03em, uppercase): section heads (TODAY, FOR YOU, WHAT WAS SAID) and the PRISM wordmark (400, +0.01em). Lens brief heads and landing terms drop to 22px; the Ask sheet title to 20px.
- **Display count** (Teko 400, 44px, line-height 0.9, -0.01em): the lead row's source count only. Never running text.
- **Display nav** (Teko 400, 18px, uppercase, +0.04em): the desktop header links.
- **Title** (Hind 500, 30px → 34px at sm, line-height 1.15; 40px on the desktop ticket): the story headline on the ticket.
- **Headline** (Hind 500, 22px → 26px at sm, line-height 1.25): the lead row. Landing hero runs 38/48/56px at the same weight.
- **Headline row** (Hind 500, 15.5px, line-height 1.4): every other chart row, the sources' outlet names, section labels on the form.
- **Body** (Hind 400, 14.5px, line-height 1.6): summaries, quotes, briefs, prose. Runs 14.5–16px; inputs are 16px so iOS never zooms. Measures cap at ~36em (hints, definitions) to 44ch (landing prose) and 52ch (field hints).
- **UI label** (Hind 500, 13.5px): field labels above controls, sector names in the strip, pill button text (13–14.5px semibold).
- **Hint** (Hind 400, 12.5px): the line under a section head, the ticket's sub-line, the lens board's descriptions.
- **Label** (Martian Mono 400, 11px, +0.04–0.06em, uppercase): the row's label grid (origin · time · code), the ticket strip, `[n]` citations, section counts, "Yesterday's chart →", Q/A markers. This is the floor.
- **Mono dateline** (Martian Mono 400, 12px, +0.04–0.06em): the masthead's second line, sector codes in the strip and on the form, the branch tree's shape readout.

### Named Rules
**The Three Jobs Rule.** Teko never sets running text; Martian Mono never sets prose or a heading; Hind sets everything a reader reads. A word in the wrong voice is a bug.

**The 11px Floor Rule.** No functional mono label below 11px; no body below 14.5px; 4.5:1 minimum on both grounds. `ink-faint` was moved from #8a8d85 (3.0:1) to #6d7068 for exactly this reason.

## Layout

One column at every phone width, hard left edge, no centring except the landing's final call. Public and app shells now cap at 1400px (`px-5 sm:px-8 xl:px-10`) so the header, landing, chart, trending and search share a left edge. At `lg`, feed, trending and search use the first 188px for the persistent subject rail and keep the story river in the remaining field. Form pages (you, onboarding) remain 720px. The desktop ticket uses the same fluid 1400px field: a 72–104px ledger margin, a reading column capped at 604px, and the remaining width for the sticky lens/evidence board. It never sets a viewport-wider fixed width at the 1024px breakpoint.

Vertical rhythm is the rule: every unit of the page (row, section head, field, source, quote) begins with a 1px hairline and its own top padding. Chart rows are `py-3.5` (14px) on a `40px + 16px gap` count column; the lead row is `py-5` (20px) on a 56px column. Section heads are `pt-4` with `mb-4`. Form fields are `pt-6 pb-6`. The base unit is 4px; the scale actually used is 4 / 8 / 16 / 24 / 32.

Fixed chrome: desktop header 56px (57px with its border); the single sector navigation is a 44px sticky horizontal rail on the phone and reflows into the 188px sticky left subject rail at `lg` without creating a duplicate accessible control; bottom tab bar has five equal columns with 48px targets plus the safe-area inset, hidden at `lg`. The lead row's image sits above the headline on a phone and beside it in a 400px column at `lg`; it is present only when the story has one, never a placeholder.

Breakpoints are Tailwind's defaults: `sm` 640px shows sector names beside codes and header nav text; `lg` 1024px shows the brand header and hides the bottom bar and phone masthead.

## Elevation & Depth

Flat. There are no shadows on any shipped surface: depth is a hairline and, at most, a change of ground (`bg-elevated` for a control or sheet, `bg-sunken` for a selected chip). The two fixed sheets (the header and the ticket's pinned lens rail) use `--glass` (the ground at 82–86% with `backdrop-blur-md`) so content is seen scrolling under them; that translucency is the only depth cue. The selected lens tab draws a 1.5px inset ring in the lens hue, not a shadow.

### Named Rules
**The No Shadow Rule.** A box-shadow on a chrome element is a defect. `--shadow-card` and `--shadow-pop` survive in `globals.css` from the old world and are used by nothing; do not revive them.

## Shapes

Square by default: inputs, selects, secondary buttons, chips, the Ask sheet and the landing's demo frame all have 0 radius and a 1px `line-strong` border. The only round shapes are the pill (`9999px`) and the 7px lens dot. Pills are rationed: lens tabs, and one primary action per page (the header's "Pick your sectors", the landing's call, the ticket's "Ask", "Sign in to unlock"). The theme toggle, the 32px avatar and the header search target are circles because they are icon buttons, not choices. The focus ring is a 2px ink outline at 2px offset with a 2px radius so it does not clip at the corners. Icons are one stroke set: 24-unit viewBox, 2px stroke, round caps and joins, `currentColor`, 12–19px.

## Components

### The Chart Row
The unit of the product; every row the same. A two-column grid: the source count at the left (Teko 44px on the lead, mono 13px `leading-[1.9]` otherwise; `ink-faint` when the count is 1), then the headline in Hind (22/26px lead, 15.5px otherwise, weight 500, `text-balance`), the lens dots (7px, `rounded-full`, one per professional read that exists, `role="img"` with a label), the lead's summary in print grey at 14.5px, and the label grid in mono 11px uppercase faint: origin · time · code, then the headline's language if it differs from the reader's first. A single-source row sits on `.rule-single` (dashed) and prints "1 source" first in the grid; every other row on `.rule-live`. Hover and focus underline the headline (`underline-offset-4`), nothing else moves. The row the reader last opened prints "· read" at the end of the grid. The list prints in with `.chart-print`: opacity 0→1 and a 4px rise, 180ms, exponential ease-out, 40ms stagger, nothing under reduced motion.

### Masthead
The mark (a `currentColor` triangle on the spectrum bar, 21px) and PRISM in Teko 26px at +0.01em, then the dateline in mono 12px print grey: date · N sources · N stories. The theme toggle sits right. Phone only; on desktop the brand header carries the same wordmark at the same size.

### Sector Strip / Desktop Subject Rail
One accessible subject nav on every surface. On phones it is a sticky horizontal strip on the page ground with a bottom hairline; at `lg` the same DOM reflows into a persistent left rail with names visible, a left active rule, and a short explanation of the monitored-outlet record. Seven items: ALL then six codes in mono 12px at +0.06em, names in Hind 13.5px 500 from `sm`. Each item is at least 44px tall. On the chart a code re-sorts in place; elsewhere it is a link. Never render separate hidden mobile and desktop copies: CSS-hidden duplicate controls still produce a confusing accessibility tree in non-visual and test environments.

### Section Head
Teko 26px uppercase on a top hairline with `pt-4`; the count follows in mono 11px faint; an optional hint beneath at 12.5px faint, max 36em.

### Navigation
- **Desktop header** (56px, `--glass`, bottom hairline): wordmark left; Today · Trending · Pulse · Watchlist in Teko 18px uppercase with a 2px bottom border (ink when active); a 32px round search target; Sign in; the theme toggle; then either the 28px round avatar (1px `line-strong` border, initial in 12px semibold) or the one primary pill.
- **Bottom tab bar** (phone): five equal columns, 48px targets, 19px stroke icons above 11px labels; active is ink at weight 600, inactive print grey at 500. The glass ground includes the device safe-area inset. Hidden on the ticket, which pins its own rail.

### Buttons
- **Primary** (pill, ink fill, ground-coloured text, 13–14.5px semibold, `px-4 py-2` or `h-12 px-6`): one per page. Hover drops to 85% opacity; the landing's call adds `active:translate-y-px`.
- **Secondary** (square, 1px `line-strong` border, no fill, ink or print-grey text, 12–13px medium, `px-3 py-1.5`): sub-sector chips, "Save", "Back to the reader view" (pill variant exists on the lens gate). Selected chips fill `bg-sunken` and turn the border ink.
- **Underlined tab** (2px bottom border, ink when on): in-place switches: sector codes, TODAY / FOR YOU, language ranks on the form, the branch tree's "all / spine" toggle.

### Lens Tabs
The one place a pill carries colour. Unselected: no fill, print grey (faint when locked, with a 10px stroke padlock). Selected: the lens's `-bg` tint, text in the lens hue, `inset 0 0 0 1.5px` ring in the hue. On the phone rail the unselected pill gains a 1px `line-strong` border on `bg-elevated` and a 44px minimum height. Desktop shows the key hints ("Press 1 · 2") in mono 11px far right.

### Inputs / Fields
- **Field:** label in Hind 13.5px 500 above; hint prose in print grey (max 52ch); the control 12px below; the whole field on a top hairline with 24px padding.
- **Control:** `h-12`, 1px `line-strong` border, `bg-elevated`, 16px text, `px-4`, 0 radius. The Ask composer is the same border on the page ground with a 44px square send button bordered in ink.
- **Focus:** the global 2px ink outline; no glow, no colour.

### The Ticket (StoryView / StoryDesktop)
The story page reads as a reservation ticket. The strip first: a mono 11px uppercase line on the row's own rule (dashed if single-source) with facts separated by a middle dot drawn by CSS (`.ticket-strip`): code · sources · origins · stamp. Then the title (30/34px; 40px on desktop), the summary at 15.5px print grey, the lens tabs on a hairline, and the lens block (`.flip-body`) in 18px-gapped sections. Below, on hairlines with Teko heads: the route (BranchTree: a monochrome tree whose branches are `border-left` line styles, with a mono 12px computed readout `N DEVELOPMENTS · N BRANCHES · N SATELLITES · SPAN`), the passenger list (Said: speaker 14.5px semibold, verbatim quote 14.5px/1.6, provenance `[n] · outlet · date` in mono 11px, the `[n]` a link whose hit area is grown to ~47×44 by a pseudo-element), and the coaches (SourceList: `[n]` in a 28px mono column, outlet 13.5px 500, funding label in mono uppercase, headline truncated in print grey). On the phone a `--glass` sheet pins the lens pills and Share + Ask to the thumb zone.

### The Lens Flip (signature motion)
Never a crossfade. On a lens change the block re-mounts with `.flip-body` (opacity 0.25 → 0.55 at 60% → 1, 500ms ease-out) while a 2px `.flip-scanline` in the lens hue sweeps top to bottom (500ms ease-out, opacity 1 → 0.85). Body text and layout never move. Desktop binds keys 1/2/3 and does not scroll. Under `prefers-reduced-motion` both animations are `none`: an instant swap.

### Ask Panel
A square `line-strong` sheet on `bg-elevated` (docked on the phone, floating on desktop). Title in Teko 20px uppercase; turns are ruled lines with Q / A in a mono 11px column; the model's citations are `[n]` mono links; suggested questions are square secondary buttons.

### Landing (Persuade surface)
The same world in a 1400px shell. The promise is “Follow the story, not the headlines.” in Hind 42/54/64px 600; prose is 16–17px print grey at 42ch; there is one primary pill. The other half of the first desktop viewport is a real live story record with its latest report time, source support, subject and evidence link. Tablet stays in normal document flow instead of vertically centring two stacked blocks. Lower sections use current product evidence, and every written interaction is marked ILLUSTRATION in the provenance voice. Product status is separated into Available now / In validation / Next, so future work cannot read as shipped.

## Do's and Don'ts

### Do:
- **Do** keep chrome monochrome; colour on a surface means a lens is speaking, and only the 7px dot, the selected lens tab, the scan line and the form's "Reads as" dot may carry it.
- **Do** carry state as line form: solid 1px `line` for live, dashed 1px `line-strong` for single-source, the solid rule at 60% opacity for stale. Never hue.
- **Do** print counted structure as counts (sources, stories, developments, branches, quotes) in the provenance voice; never let an LLM summarise what can be counted.
- **Do** quote verbatim or not at all; every quote carries `[n] · outlet · date` in mono 11px and `[n]` is the same index the sources list uses.
- **Do** mark every written example ILLUSTRATION in mono; no invented numbers on any surface.
- **Do** render whatever `/api/v1/lenses` returns; lens names are data, never enumerated in generic or marketing copy. The public promise is "Follow the story, not the headlines."
- **Do** put every unit on a top hairline with its own padding: rows `py-3.5`, lead `py-5`, section heads `pt-4`, fields `pt-6 pb-6`.
- **Do** hold the floors: 11px for functional mono labels, 14.5px for body, 16px inside inputs, 4.5:1 on both grounds, measures ≤ ~36em for hints and ≤ 44ch for prose.
- **Do** ration the pill to lens tabs and one primary action per page; every other choice is a square 1px `line-strong` button or an underlined tab.
- **Do** collapse every animation to nothing under `prefers-reduced-motion`, including the flip and the chart print.

### Don't:
- **Don't** put an eyebrow, kicker or label above a heading; the heading carries its own weight and the subject lives in the label grid.
- **Don't** draw a card: no bordered-and-shadowed box around content already separated by a rule. No shadows, no gradients in chrome; the mark's base is the only spectrum.
- **Don't** put a thumbnail on every row; the lead's image appears only when the story has one, never a placeholder.
- **Don't** use "Other" as a heading; six subjects, every story in one of them.
- **Don't** add a global lens switcher to the header or the tab bar; the lens is set in the form and flipped on the ticket.
- **Don't** crossfade the lens block, and don't move body text or layout during the flip.
- **Don't** put a marketing hero on the chart; `/feed` is always the list, and `/about` is the landing's permanent address.
- **Don't** infinite-scroll; the day is the unit and yesterday's chart is a link at the foot.
- **Don't** use text glyphs (↗ ▲ ▼ ↳ ▾) as icons; use the stroke set in `icons.tsx`.
- **Don't** set running text in Teko, or prose or a heading in Martian Mono.
- **Don't** use perforations, a dot-matrix face, or distressing; the chart is printed stationery, not a costume of one.

## Decisions Log

Historical entries were written under whichever name was current; the design decision each records is unaffected. Entries before 2026-09-15 describe the retired ivory/Fraunces world and are kept as history; the brand rules they established (colour, three voices, the flip, no cards, counted structure, no global lens switcher) carried into the chart.

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
