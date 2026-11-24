# 06 · The story page's "Where it stands" header

Built in two steps. **T-007** builds items 2, 3, 5, 6 and 7 below, `Share`, and the phone's `Who reported it`
sheet, in today's shell. **T-052** adds the returning line (4), `Began` (8), the Follow control, and the wider
forms of `Who reported it` — each needs something T-007 does not have (read marks from T-035, follow from
T-050, the shell from T-042). Comp: `comps/story-header.html`.

## Purpose

A reader arriving cold at a running story learns its shape in a few seconds — how long it has run, how much
has happened, how widely it is reported, the latest thing and the first — and a returning reader sees how
much is new. Everything in the header is counted or is a headline already on the record. The only words of
Prism's own are the story's name — the same name the Stories list gives it — and nothing is written for this
header.

## Where it lives

The top of a running story's page (`/trending/{slug}`), above the timeline. The timeline itself (the latest
three, then by day) is T-052's and is not in this spec.

## Content, in order

1. **Chrome:** `record` (spec 05) — on a phone the back bar; from medium the rail or top bar.
2. **Meta line:** the StatusPill (`Verified` or `Provisional grouping`) · the subject.
3. **The story's name** — h1, record voice, display-l. It wraps and is never truncated.
4. **The returning line**, only for a reader with unseen developments: a `New` badge, `{k} new since you
   read`, and the day and time of the last read in mono (spec 02).
5. **`Where it stands`** — eyebrow, under a 3px ink rule. Four counted stats in one row. Each is a figure in
   the record voice (600, display-m) over a label in the reading voice (label size, `--ink-3`), and each is a
   link:

   | Figure | Label | Goes to |
   |---|---|---|
   | `{d}` | `days running` (`day running` for 1) | the first development's record, the same link as `Began`; from T-052, Day 1 of the timeline |
   | `{n}` | `developments` (`development` for 1; `records` / `record` while the grouping is provisional) | the top of the timeline |
   | `{k}` | `outlets` (`outlet` for 1) | Who reported it |
   | `{l}` | `languages` (`language` for 1) | Who reported it, at its first language group |

   A stat that is not counted yet keeps its label, prints `—` for the figure with `Not counted yet` under the
   label, and is not a link.

   Figures are grouped by `Intl` (`5,695`). The day count and the outlet count are the same numbers the
   Stories list prints for this story (T-007 makes them one query and tests it).
6. **The coverage bar**, large, with its count beside it in mono (`{k} outlets`), and `Who reported it` with
   the ChevronDown icon: on compact and medium it opens the sheet below; at expanded the list is already
   beside the header and the button is not drawn.
7. **`Latest`** — under a 1px rule: the eyebrow `Latest` and its time in mono; the development's headline
   (record voice, title; the link to that record); the line that says whose headline it is, exactly as spec
   01's headline states give it; mono `{k} outlets · {l} languages`. A latest development from one outlet has
   the dashed left rule and the words `One source so far`.
8. **`Began`** — under a 1px rule: the eyebrow `Began` and the date in mono; the first development's headline
   in the reading voice (`--ink-2`, two lines at most), a link to it, with the same whose-headline line.
9. **Actions:** the Follow control at its default size (spec 02), and `Share` (ghost, with the Share icon).
   Where the page already has a fixed bar that carries Share (the story's Ask · Share bar on a phone and a
   tablet), the header's row is Follow alone: Share is on the page once.

### Who reported it

- **Compact and medium: a Sheet** (from the bottom on compact, a 480 dialog on medium). Title `Who reported
  it`; mono `{k} outlets · {l} languages`; the coverage bar with its legend in words and counts —
  `English national {a} · International {b} · Indian-language {c} · Wire {d}` — then every outlet, grouped by
  language (the language's own name as each group's eyebrow, with its count), one outlet per line with the
  number of its reports in mono. Groups are ordered by their number of outlets, most first; outlets inside a
  group by their number of reports, most first; ties by name. The sheet scrolls inside; Close at the top
  right.
- **Expanded: the evidence rail** beside the header (320): the same title, counts and legend, then the twelve
  outlets with the most reports and the link `All {k}`, which opens the full grouped list in a right drawer.
  Here the `outlets` and `languages` stats move focus to the rail's heading rather than opening anything.

## States

| State | What the reader sees |
|---|---|
| Loading | Skeleton blocks with the header's geometry: the pill, two title lines, four stat blocks, a bar; cut square. |
| Verified | As above; the header sits on the solid 3px rule. |
| Provisional grouping | The pill says so; under the h1, in the reading voice: `These reports may belong together. Prism has not confirmed an order of events.`; the second stat's label is `records`; the rule under the header is dashed, 1px. Follow is still offered. |
| Returning, something new | The returning line is shown; the control reads `Following`. |
| Returning, nothing new | No returning line. |
| One day old | `1` `day running`; `Began` and `Latest` may be the same development — then only `Latest` is drawn. |
| Gone quiet (no development in 7 days or more) | Under the stats: `Nothing new in {d} days.` The `Latest` block's eyebrow reads `Last development`, with its date, and the block is at 62% (stale). |
| A figure not counted yet | `—` in place of the figure and `Not counted yet` as its label; never 0. |
| Very large counts | Four- and five-digit figures hold on one line at 360px; the row becomes 2 × 2 below 420px. |
| One outlet in total | `1` `outlet`, `1` `language`; the whole header carries the one-source form: dashed rule, `One source so far`. |
| Could not load | Error alert: `This story could not load.` with `Try again` and the link `All stories`. |
| Gone (merged or retired) | A merged story redirects to its successor. A story that no longer exists gets the record's own 404 (SystemPage). |
| Signed out | Identical; Follow works at once (spec 02). |
| At the free follow limit | Follow opens the limit sheet (spec 02). |
| Hindi interface | Labels and eyebrows from the catalogue; figures stay in Latin digits; plural forms through `Intl`. The story's name is shown in Hindi when an outlet wrote one, else marked as a translation (spec 01, headline states). |
| Reduced motion | The coverage bar does not draw in; nothing else moves. |

## Copy

All strings above. Also:

| Where | String |
|---|---|
| Back bar's arrow | `Back to Stories` (or the surface the reader came from) |
| Share text | `{story name} — {n} developments, {k} outlets, {l} languages.` then the link |
| A stat's accessible name | the figure and label together: `100 developments` |

The header never prints a sentence about what the story is. The story's name and the two headlines are the
only prose. Each headline is an outlet's or Prism's, and says which (D-18; spec 01, headline states). The
story's name is Prism's label for the story, as everywhere a story is named.

Share text uses the same singulars as the stats: `1 development`, `1 outlet`, `1 language`.

## Layout

| | Compact < 600 | Medium 600–1023 | Expanded ≥ 1024 |
|---|---|---|---|
| Column | full width, gutter 16 | 640 beside the rail | 640 + the evidence rail 320, gap 48 |
| Stats | four in a row; 2 × 2 below 420 | four in a row | four in a row |
| Actions | a row under `Began`; Follow first | same | at the right end of the meta line's row, above the h1; the h1 keeps the full column |
| Who reported it | the button, opening a bottom sheet | the button, opening a dialog | the evidence rail, open; no button |
| First viewport at 390 × 740 | the name (up to three lines), the stats, the bar and the start of `Latest` are above the fold; a name longer than three lines pushes `Latest` down and that is accepted | | |

From large, the "On this story" left navigation of `DESIGN.md` · The story record joins as it does on a
record.

## Motion

The coverage bar draws in once. The figures do not count up: a number is a fact, and it is there when the
page is. The sheet arrives from its edge (220ms). Reduced motion: instant.

## Accessibility

- The stats are a `<ul>`; each item's name is its figure and label together, and the order is the reading
  order. `days running` and `developments` are links. `outlets` and `languages` open a sheet below expanded,
  so there they are `<button aria-haspopup="dialog">`; at expanded they move focus to the rail's heading.
- The returning line is text, not a live region.
- The coverage bar is never the only carrier: its count is beside it and the legend is in the sheet.
- `Who reported it` is a `<button aria-haspopup="dialog">`; the sheet is a labelled modal dialog with a focus
  trap; language group names carry their `lang`.
- Stale is 62% opacity and the words `Last development`; one source is a dashed rule and the words.
- Contrast holds at 62%: `--ink` at 62% is 5.0:1 on paper and 7.0:1 on the dark ground; the mono line in that
  block uses `--ink`, not `--ink-3`, so it holds too.

## Primitives

StatusPill, MetaLine, Coverage (bar, legend), Badge, FollowButton, Button, ShareButton, Sheet, Alert,
Skeleton, SectionHead. New: `StoryStats`, `WhoReported`.

## Depends on

| Needs | From |
|---|---|
| Days running, developments, outlets, languages — one query shared with the Stories list; the latest and the first development with their outlet and language counts | T-007 |
| Outlets grouped by language with report counts; the coverage split by slot | T-007 (today's payload lists outlets with reports and language; the split by slot must be added) |
| Unseen count and last-read time | T-035, T-050 |
| A story's name in the interface language | T-054 |

## Decided here

1. **Nothing generated.** No "the story so far" sentence. The header is four counts, a bar and two headlines.
2. **The stats are the navigation.** Each count opens what it counts, as the record's stats already do.
3. **`Latest` and `Began` are both in the header**, newest first: a cold reader wants the latest; the first
   says what the story is without Prism describing it.
4. **Coverage comes up from the foot of the page** into the header: a button and a sheet on a phone and a
   tablet, the evidence rail on a desk.
5. **Quiet is 7 days**, said in words and shown as stale. The threshold is this spec's; if the stories list
   later defines "ended" from data, the header follows that definition.
6. **No count-up animation.**

## References

`~/prism-program/design-refs/story-header.md`; design audit §7.2 "Story page" (`board.md` rows C1, C2, C3,
C5). The stat strip is Prism's own counted-stats pattern, not a borrowed one.
