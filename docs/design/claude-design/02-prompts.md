# Prompts for Claude Design — in order

How to use this:

1. **Start one Claude Design project called "Prism — redesign".** Keep every step
   below in that same project, so the design system from step 1 carries into
   every page.
2. **Give it the context first.** Attach `01-context-pack.md` (this folder) as a
   file, or paste it as your first message if you can't attach files. If Claude
   Design offers to read a codebase or GitHub repo, you can point it at the
   repository's `web/` folder too. Tell it the code shows what exists today, not
   the look to keep.
3. **Attach the brand files:** the logo (`web/public/brand/*.png`, or
   `design/logo/exports/`). If you want it to see what it's replacing, add a few
   current screenshots too.
4. **Paste the prompts below one at a time.** Review each result before the next.
   Step 1 is the most important: don't move on until the design system is right.
   Every later step builds on it.
5. When a step comes back, check it against the "Check before accepting" list
   under that prompt. That list is how you catch anything it missed.

---

## Prompt 1 — the design system (do this first, alone)

```
You have the attached context pack for Prism, an Indian news product. Read all of it before designing anything. Then design a complete new design system for Prism — not a reskin of the current one.

The system must serve three audiences in one visual language:
(a) readers on phones, mostly signed out, in English and Indian languages;
(b) professionals who pay for a "lens" reading of the same stories;
(c) internal users: labellers (people who label news data on their phones) and the founders' admin dashboard (desktop-first, charts).

Deliver, as a design-system page/board:
1. Principles: 4–6 lines that turn the product's rules in the pack into visual rules.
2. Colour: semantic roles (ground, surface, sunken, ink 1–3, lines, the single interactive accent, danger, up/down), each in light AND dark with contrast ratios. Separately: the coverage-bar slot palette (4 outlet origins), the lens hues (the set grows — define how a new lens gets its hue), status colours, and a categorical data-viz palette (6 slots) plus a one-hue sequential ramp for the admin. Every palette must be distinguishable by colour-blind readers, and nothing should rely on colour alone.
3. Type: three voices with three jobs (record/display, reading+UI, provenance mono). Pick the faces and show them setting Latin, Devanagari, Kannada, Tamil, Telugu, Bengali and Gujarati on one baseline. Full scale for phone and desktop, including the floors (11px mono, 14.5px body, 16px inputs).
4. Spacing, grid and breakpoints: phone (the future React Native app), tablet, desktop, wide desktop. Reading measure, rails, the admin grid.
5. Shape, elevation, borders, iconography (one stroke set, no text glyphs used as icons).
6. Motion: the lens flip (a re-typeset with a scan line, never a crossfade, and an instant swap under reduced motion), the coverage bar drawing in, rows printing in, and sheet/drawer transitions.
7. Components, each with every state (default, hover, focus, active, disabled, loading, empty, error) in light and dark: the full component list in section 7 of the pack.

Do NOT design any page yet. Show the system, then list any open questions you have. Throughout this project: never drop a feature, state or rule listed in the pack; if you propose something the product does not have today, label it PROPOSED so I can decide.
```

**Check before accepting:**
- Both themes have every token, and the ratios are shown.
- The Indian scripts actually render in the chosen faces.
- The lens flip is designed as a re-typeset, not a fade.
- Every component in section 7 of the pack is present.
- The logo is used unchanged.

---

## Prompt 2 — the reader's core: Today, a story, and the lens

```
Using the design system we just made, design the reader's two most important surfaces, each on phone (390) and desktop (1440), light and dark:

1. Today (/feed and the subject pages), with every element in section 8.2 of the pack.
2. The story page (/story/[id]), with every section in section 8.3, in the section order given there. Show:
   - the same story through the free reader lens and through a paid lens;
   - a locked lens for a signed-out reader, showing what is missing;
   - the lens flip mid-animation as a storyboard;
   - a single-source story; a provisional grouping; a story with quotes in two languages; a story with podcast clips and posts on X;
   - the Ask drawer open, including its limit states.
Also the quote page (/story/[id]/quote/[n]) and the story loading skeleton.
Follow the honesty rules in section 3 exactly. Use realistic Indian news content, and mark any example you invent with the word ILLUSTRATION.
```

**Check:**
- The coverage bar with its count is on every row.
- Quotes are verbatim with their provenance.
- Nothing shows a number that could be invented.
- The phone story page has Follow, Ask and Share in the thumb zone.
- The desktop shows evidence beside the record, never longer lines.

---

## Prompt 3 — the rest of reading

```
Same system. Design these, phone and desktop, light and dark, with every element and state in section 8 of the pack:
- Trending and a trending group (8.4)
- Pulse (8.5)
- Search, including empty, no-results and failed states (8.6)
- An entity page and a subject page (8.7)
- The landing (/ for a first visitor, and /about) (8.1). The landing counts only real numbers fetched live, and roadmap sections are marked NEXT.
- The global chrome: header, sector navigation, bottom tab bar, theme toggle, search, the persistent Ask entry points (8.0)
- Not-found, error and offline pages
```

---

## Prompt 4 — accounts, onboarding and money

```
Same system. Design, phone and desktop, light and dark, with every step and state in section 9 of the pack:
- Sign in (magic link + Google) and the verify page
- Onboarding (every step)
- You / profile, interests, watchlist
- Account and the whole subscription life: the plan card in every status, the cancel sheet with its one matched offer, pause, switching to yearly, invoices, and a failed payment in its grace period
- Plus pricing (/plus) with the launch offer and founding plan, the upgrade sheet at the Ask limit, and /plus/welcome
- The legal page layout (privacy, terms, refunds)
Prices are in the pack. Show prices inclusive of GST as the pack states, and add no testimonials or user counts.
```

---

## Prompt 5 — the labeller workspace

```
Same system. Design the labeller workspace (section 10 of the pack) — the people who label Prism's data, mostly on phones, reading Indian languages. Cover the whole journey:
- signed out → apply → waiting for approval → approved workspace (what is waiting, counted)
- guide primer → practice round with feedback → qualification test (pass mark) → work batches
- the task screen for EACH of the five task kinds, including keyboard shortcuts on desktop, "not sure", progress, and the language gate
- the batch finished, paused and removed states, and invite links
Guides are served only after sign-in and applying; never put guide text on a public page. Answers are words with an icon beside them, never colour alone. Design for speed: one decision per screen, thumb-reachable answers.
```

---

## Prompt 6 — the founders' admin dashboard

```
Same system, using the data-viz palette. Design the admin (section 11 of the pack), desktop-first but usable on a phone, light and dark:
- Overview: headline tiles, then chart panels per area — supply, visits, sign-ups, engagement, money, demand.
- Coverage: tables and the 3D network view.
- Labellers, Batches (with the round review/publish editor), People, Controls, Audit.
Every panel keeps its source behind an info control and can turn into its table. Days not counted are shaded, never drawn as zero. Below 30, show "k of n", never a percentage. Change is shown in words and an arrow, never red/green alone. Switches are read-only states, not toggles. Show empty states for a product with one day of data, as well as full ones.
```

---

## Prompt 7 — outside the app

```
Same system. Design:
- the share cards (1200×630 OG images) for a story, a quote and a trending group
- the favicon and app icon, using the existing mark unchanged
- every transactional email in section 12 of the pack (light only; must work in Gmail and Outlook)
```

---

## Prompt 8 — the audit (last)

```
Go through sections 7–12 of the context pack line by line and list every screen, state and component. Mark each one designed / partly designed / missing, and design everything marked missing. Then check every screen against the honesty rules (section 3) and the accessibility floors (section 4), and list any violations with fixes.
```

---

## Tips

- **One step at a time.** One giant prompt gets a shallow pass over 40 screens. Seven focused prompts get depth.
- **Correct in place.** If it drifts from the system in a later step, say: "This breaks the design system from step 1 (X). Redo it using the system."
- **Keep the pack attached.** If a later session loses context, re-attach `01-context-pack.md` and say "continue from step N".
- **Handoff:** when you're happy, export the system and the screens. Claude Code can then build the tokens and components into `design/tokens.json` and `web/`, the way the Lovable redesign was applied.
