# 01 · Today's edition and its end block

Built by T-051 from the document T-038 writes. Comp: `comps/edition-a.html`; the other states in
`comps/edition-states.html`; the two arrangements not taken in `comps/edition-b.html` and `-c.html`.

## Purpose

A reader opens Today, reads the day's five to seven most-reported happenings in about three minutes, reaches
"You're up to date", and can stop. The edition is the same for every reader of a language; it is finite, it
says how long it is before the reader starts, and it says when it is over.

## Where it lives

`/feed` (the tab "Today"), above everything else on the page. The chart Prism has today (most reported, by
state, by subject) stays on the same page, one step below the end block, under its own heading. `/` still
sends a returning reader to `/feed`.

## Content, in order

1. **Chrome** for the size class (spec 05). On compact and medium the masthead prints the date.
2. **Breaking strip — a reserved slot.** If T-021 ships a breaking strip (D-10 is open), it sits here, above
   the edition head, and is outside the edition's count. This spec gives it no design; until T-021, the slot
   is empty and takes no space.
3. **Edition head.**
   - `Today` — h1, record voice, display-l.
   - One provenance line in mono: `{n} stories · about {m} min · updated {HH:MM}`. `{m}` is the reading time
     the edition document carries; when the document has none, the middle fact is left out, not estimated in
     the browser. `updated` is the document's version time, in the reader's zone.
   - At the right of that line, once the reader has read at least one item: `{k} of {n} read` in mono.
4. **The progress rule.** A 3px rule fixed directly under the masthead (compact, medium) or the top bar
   (expanded), in `n` equal segments with 2px gaps: read segments ink, unread `--line`. It is decoration
   (`aria-hidden`); the count in the head is the accessible form.
5. **The items, 1 to n**, an ordered list. Item 1 sits under a 3px ink rule; the rest under 1px rules. Each
   item, top to bottom:
   1. **Its numeral** in a left gutter: record voice 600, display-m. A rank is not provenance, so it is not
      mono. Under the numeral, once read, a Check icon.
   2. **The count line:** the coverage bar, then mono `{k} outlets · {l} languages`, then the time of the
      latest report in mono. One language prints `1 language`. (When T-014 lands and counts become
      independent origins, the words follow T-046's vocabulary; the position does not change.)
   3. **The headline** — h2, record voice; display-m on item 1, title on the rest. It wraps; it is never
      truncated. It is the link to the record, and the whole row is its target.
   4. **Whose headline it is**, reading voice, label size, `--ink-3` — one of the four states in "Headline
      states" below.
   5. **One exact quote**, when the document carries one: the words in record italic inside quotation marks,
      in the language they were printed in; then one provenance line — speaker (reading voice 600) · role ·
      the language's own name when it is not the interface language · outlet · time (mono). No quote in the
      document: nothing is drawn.
   6. **The story it belongs to**, when it belongs to one: `Part of` · the story's name as a link · mono
      `{d} developments`, and the Follow control (small) at the right (spec 02). No story: nothing is drawn.
6. **The end block**, under a 3px ink rule:
   1. Check icon and `You're up to date` — h2, record voice, display-m.
   2. Mono: `{n} of {n} · updated {HH:MM}`, and, when the reader went from the first item to the end block in
      one sitting of under 15 minutes, ` · {m} min` (measured, whole minutes, "under 1 min" below one). A
      longer or interrupted sitting prints no time.
   3. `Tomorrow's edition is ready at {HH:MM}.` — the hour from the document. Omitted when the document does
      not carry it.
   4. **Your stories** — the per-reader slot (one request; everything above it came from the document).
      Up to three followed stories, moved ones first: the story's name, then mono `{k} new since you read`,
      or reading voice `Nothing new since {day HH:MM}`. Then the link `Following →`. A reader who follows
      nothing sees one line: `Follow a story and its changes appear here.` This slot is not one of the
      `n` items and does not move the count.
   5. One primary action: `Tell me when tomorrow's edition is ready` (opens the explanation in spec 03).
      Once it is on, the button is replaced by the line `You'll be told at {HH:MM}.` and the link `Change`.
   6. `Share today's edition` — ghost button with the Share icon.
7. **`Everything reported today`** — section head (3px rule), then the chart as it is today. Its loading,
   empty and error states are its own and unchanged.

### Headline states (D-18)

| State | When | The headline | The line under it |
|---|---|---|---|
| Prism's | two or more independent reports, and Prism's headline has passed its check (T-018) | Prism's | `Prism's headline, from {k} reports` |
| An outlet's own | one independent report, or before the check exists | the lead outlet's, as printed | `{Outlet}'s headline` |
| An outlet's, in the reader's language | an outlet wrote one in the interface language | that outlet's, as printed | `{Outlet}'s headline` (in the interface language) |
| Translated | no outlet wrote it in the interface language | a translation of the lead outlet's | `Translated from {Language} · {Outlet}'s headline · See the original` — `See the original` swaps the original in, in place |

Until T-018 is live the edition shows only the second and third states.

## States

| State | What the reader sees |
|---|---|
| Loading | The head with a skeleton bar for the provenance line; five skeleton rows with a row's geometry (numeral block, count line, two headline lines), cut square. No spinner, no words. |
| Ready | As above. |
| Not ready yet (before the day's first edition) | An info alert: `Today's edition is not ready yet.` / `It is written at {HH:MM}. Yesterday's is below.` Then yesterday's edition under the head `Yesterday · {Mon 23 Nov}`, complete with its own end block. |
| A quiet day (fewer than five qualified) | The edition prints what there is: `3 stories`, three rows, `3 of 3`. Never padded. |
| No edition at all (nothing qualified, and no yesterday) | The head, then `No edition today.` and the chart directly below. |
| Could not load | An error alert: `Today's edition could not load.` with `Try again`. The chart below loads on its own request and still shows. |
| Partly read (returning the same day) | Read items keep their Check; the progress rule and `{k} of {n} read` are restored from the read marks (T-035), on any device when signed in. |
| Finished earlier today | Under the head: Check icon, `You finished today's edition at {HH:MM}.` and the link `Jump to everything reported today`. The rows stay, all checked. |
| Changed since the reader read it | A pill between the head and item 1: `{k} new since you read · Show`. The list does not reorder until the reader presses it. |
| Offline (the app; the web has no offline copy yet) | An info alert: `You are offline.` / `This is the edition saved at {HH:MM}.` Then the saved edition. On the web, offline is "Could not load". |
| Signed out | Identical. Read marks and follows are kept on the device (T-035). |
| At the free follow limit | The Follow control on a row opens the limit sheet (spec 02). The edition itself is never metered. |
| A muted subject | Its items are not in the list; `n` is the number shown. No gap, no notice. |
| Reduced motion | No print-in, no rule animation; state changes are instant. |

An item is **read** when its last line has scrolled above the middle of the viewport, or it was opened. The
edition is **finished** when half of the end block has been on screen for one second (the event T-058 counts).

## Copy

All strings above are the copy. The rest:

| Where | String |
|---|---|
| Tab and top-bar link | `Today` |
| Share text | `Today on Prism: {n} stories. {lead headline} — {k} outlets, {l} languages.` then the link |
| Screen-reader name of the list | `Today's edition, {n} stories` |
| Screen-reader text on a read item | `Read` |

`Record`, `lens` and `coverage` do not appear on this surface (T-046's vocabulary).

## Layout

| | Compact < 600 | Medium 600–1023 | Expanded ≥ 1024 |
|---|---|---|---|
| Chrome | masthead 52 + bottom tabs 58 | rail 80 + masthead 52 | top bar 60 |
| Column | full width, gutter 16 | 640 column centred in the space beside the rail, gutter 24 | 640 column + a 320 right rail, gap 48, centred |
| Numeral gutter | 32 | 48 | 48 |
| Progress rule | under the masthead | under the masthead | under the top bar |
| Right rail | — | — | `In this edition`: the n headlines as an ordered list (reading voice, ui-s, two lines), each a link to its item, a Check on read ones, mono `{k} of {n} read`. Sticky under the top bar. After the end block scrolls in, nothing replaces it. |
| End block | stacked, buttons full width | stacked, buttons at their own width | stacked in the 640 column |
| The chart below | as today | as today | as today (its subject rail and two columns begin at its own heading, not beside the edition) |

Fixed chrome on a 740px-tall phone: masthead 52 + progress rule 3 + tab bar 58 = 113px, 15% of the height
(T-042's ceiling is 20%).

## Motion

Rows print in once (200ms, 40ms stagger) on first load. A progress segment fills in 220ms on the standard
ease. The end block reveals once when it first enters. Nothing celebrates: no confetti, no count-up, no sound.
The `Show` pill swaps the list in place with the row print-in. Reduced motion: all instant.

## Accessibility

- The items are an `<ol>`; each is an `<article>` whose h2 is the headline link. The numeral is the list
  marker's visual form and is `aria-hidden`; the order is conveyed by the list.
- `{k} of {n} read` is plain text, not a live region: it must not announce while the reader scrolls.
- The end block is a `<section>` labelled by its h2. Reaching it moves no focus.
- Follow, the story link and the headline are separate tab stops in reading order; every target is 44px.
- The coverage bar always has its count beside it; a quote in another script carries its `lang`.

## Primitives

SectionHead, MetaLine (count line), Coverage (bar), QuoteCard (compact form), FollowButton (spec 02), Button
(primary, ghost), Alert (info, error), Skeleton, Chip (the `Show` pill), OnThisPage (the right rail), Toast.
New on this surface: `EditionItem`, `EditionProgress`, `EndBlock`.

## Depends on

| Needs | From |
|---|---|
| Per item: headline and whose it is, outlet and language counts, the coverage split, latest report time, one quote with speaker / role / outlet / time / language, the story's name, slug and development count | T-038's document |
| Reading time, version time, tomorrow's hour | T-038's document (each optional; the line that prints it is omitted without it) |
| Read marks, the followed-stories line | T-035 |
| The Follow control and the limit sheet | spec 02, T-050 |
| The explanation sheet | spec 03, T-053 |
| Prism's headline passing a check; translation | T-018; T-054 and T-066 |

## Decided here

1. **Arrangement A, "count first".** Three arrangements of the same content were drawn. A puts the numeral in
   a gutter and the count above the headline, with a fixed 3px progress rule. B puts the headline first and
   prints progress only as "k of n" on each item. C opens with an index of the n headlines, then the rows.
   A is taken because the count is the product's credential and the eye meets it before the claim (board A4);
   the numeral shows position without a second device; and the fixed rule costs 3px. B reads as an ordinary
   news list — the count becomes a footnote — and loses the sense of how much is left. C makes a phone reader
   meet every headline twice and delays the first quote by a screen. From C, the index is kept where width is
   free: the right rail at expanded.
2. **No photographs in the edition.** The chart below keeps its thumbnails. The edition is read to be
   finished, its document has a 150KB ceiling, and the reference phone is a low-end Android. This departs from
   the 2026-09-20 decision (a thumbnail on every story row) for this one list; if the lead should carry its
   credited photograph, that is one optional field in T-038's document and one line here.
3. **The reading time is the document's, the time taken is measured**, and either is left out rather than
   guessed.
4. **The followed-stories slot is in the end block and outside the count**, so "6 of 6" means the same six
   for everyone.
5. **A changed edition is pulled in by the reader** (board A3); rows never move under the thumb.
6. **Yesterday's edition stands in before today's is written**, labelled as yesterday's.

## References

`~/prism-program/design-refs/edition.md`; design audit §7.2 "Front page (Today)" (`board.md` rows A1, A3, A4,
B1, B3, J1, J2).
