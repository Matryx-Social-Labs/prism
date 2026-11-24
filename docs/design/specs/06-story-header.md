# 06 · The story page's "Where it stands" header

Built in two steps. **T-007** builds items 2, 3, 5, 6 and 7 below, `Share`, and the small-screen `Who reported
it` panel, in today's shell. **T-052** adds the returning line (4), `Began` (8), the Follow control, and the
open-beside-the-header form of `Who reported it` — each needs something T-007 does not have (read marks from
T-035, follow from T-050, the shell from T-042).

## Purpose

A reader arriving cold at a running story learns its shape in a few seconds — how long it has run, how much
has happened, how widely it is reported, the latest thing and the first — and a returning reader sees how
much is new. Everything in the header is counted or is a headline already on the record. The only words of
Prism's own are the story's name — the same name the Stories list gives it — and nothing is written for this
header.

## Where it appears

The top of a running story's page (`/trending/{slug}`), above the timeline. The timeline itself (the latest
three, then by day) is T-052's and is not in this spec.

## Content, in order

1. **Navigation:** the record's navigation (spec 05), including the way back, `Back to Stories` (or the surface
   the reader came from).
2. **Status and subject:** the status (`Verified` or `Provisional grouping`) · the subject.
3. **The story's name.** It is shown in full and is never truncated.
4. **The returning line**, only for a reader with unseen developments: the word `New`, `{k} new since you
   read`, and the day and time of the last read (spec 02).
5. **`Where it stands`** — four counted figures, each with its label, and each a link:

   | Figure | Label | Goes to |
   |---|---|---|
   | `{d}` | `days running` (`day running` for 1) | the first development's record, the same link as `Began`; from T-052, Day 1 of the timeline |
   | `{n}` | `developments` (`development` for 1; `records` / `record` while the grouping is provisional) | the top of the timeline |
   | `{k}` | `outlets` (`outlet` for 1) | Who reported it |
   | `{l}` | `languages` (`language` for 1) | Who reported it, at its first language group |

   A figure that is not counted yet keeps its label, prints `—` for the figure with `Not counted yet` beneath
   the label, and is not a link.

   Figures are grouped by `Intl` (`5,695`). The day count and the outlet count are the same numbers the
   Stories list prints for this story (T-007 makes them one query and tests it).
6. **The count of outlets**, `{k} outlets`, and `Who reported it`: on a small screen it opens the panel below;
   where the list is shown open beside the header there is nothing to open.
7. **`Latest`** — `Latest` and its time; the development's headline (the link to that record); the line that
   says whose headline it is, exactly as spec 01's headline states give it; `{k} outlets · {l} languages`. A
   latest development from one outlet is marked as coming from one source, in words: `One source so far`.
8. **`Began`** — `Began` and the date; the first development's headline, a link to it, with the same
   whose-headline line.
9. **Actions:** the Follow control (spec 02), and `Share`. Where the page already carries Share elsewhere (the
   story's Ask · Share bar on a phone and a tablet), the header's actions are Follow alone: Share is on the
   page once.

### Who reported it

- **On a small screen it opens as a panel that blocks the page.** Where there is room it may be shown open
  beside the header (T-083 decides); then the `outlets` and `languages` figures move focus to it instead of
  opening anything.
- Contents, in order: the title `Who reported it`; `{k} outlets · {l} languages`; the split by kind of outlet,
  in words and counts — `English national {a} · International {b} · Indian-language {c} · Wire {d}` — then
  every outlet, grouped by language (the language's own name as each group's heading, with its count), one
  outlet per line with the number of its reports.
- Sort orders: groups by their number of outlets, most first; outlets inside a group by their number of
  reports, most first; ties by name.
- The panel scrolls inside itself and has a Close control. When shown open beside the header it lists the
  twelve outlets with the most reports and the link `All {k}`, which opens the full grouped list in a panel.

## States

| State | What the reader is given / what happens |
|---|---|
| Empty | Does not apply: a running story always has developments. |
| Loading | A loading state with no text, announced as loading to assistive technology, standing in for the status, the name, the four figures and the count of outlets. |
| Verified | As above. |
| Provisional grouping | The status says `Provisional grouping`; under the story's name: `These reports may belong together. Prism has not confirmed an order of events.`; the second figure's label is `records`. Follow is still offered. |
| Returning, something new | The returning line is shown; the control reads `Following`. |
| Returning, nothing new | No returning line. |
| One day old | `1` `day running`; `Began` and `Latest` may be the same development — then only `Latest` is shown. |
| Gone quiet (no development in 7 days or more) | Under the figures: `Nothing new in {d} days.` The `Latest` block is headed `Last development`, with its date, and is marked as no longer current in words: `Last development`. |
| A figure not counted yet | `—` in place of the figure, its label kept, `Not counted yet` beneath; not a link; never 0. |
| Very large counts | Four- and five-digit figures are shown whole and grouped by `Intl`, never abbreviated or cut. |
| One outlet in total | `1` `outlet`, `1` `language`; the whole header is marked as coming from one source, in words: `One source so far`. |
| Error (could not load) | An error message: `This story could not load.` with `Try again` and the link `All stories`. |
| Gone (merged or retired) | A merged story redirects to its successor. A story that no longer exists gets the record's own 404 page. |
| Signed out | Identical; Follow works at once (spec 02). |
| At the free limit | Follow opens the limit message (spec 02). |
| Hindi interface | Labels and headings from the catalogue; figures stay in Latin digits; plural forms through `Intl`. The story's name is shown in Hindi when an outlet wrote one, else marked as a translation (spec 01, headline states). |

## Copy

All strings above. Also:

| Where | String |
|---|---|
| The way back | `Back to Stories` (or the surface the reader came from) |
| Share text | `{story name} — {n} developments, {k} outlets, {l} languages.` then the link |
| A figure's accessible name | the figure and label together: `100 developments` |

The header never prints a sentence about what the story is. The story's name and the two headlines are the
only prose. Each headline is an outlet's or Prism's, and says which (D-18; spec 01, headline states). The
story's name is Prism's label for the story, as everywhere a story is named.

Share text uses the same singulars as the figures: `1 development`, `1 outlet`, `1 language`.

## Rules

1. Nothing is generated: no "the story so far" sentence. The header is four counts, the count of outlets and
   two headlines.
2. Each count opens what it counts (table in Content, item 5).
3. A figure that is not counted yet is shown as `—`, keeps its label with `Not counted yet` beneath, is not a link, and is never 0.
4. Figures are grouped by `Intl`; digits stay Latin in every language; plurals and singulars follow the table
   and the Share text.
5. The day count and the outlet count are the same numbers the Stories list prints (one query, tested).
6. `Latest` and `Began` are both in the header, newest first. On a one-day-old story they may be the same
   development, and then only `Latest` is shown.
7. Quiet is 7 days or more without a development: `Nothing new in {d} days.`, `Last development` with its
   date. The threshold is this spec's; if the stories list later defines "ended" from data, the header follows
   that definition.
8. While the grouping is provisional the second figure reads `records` / `record`, the sentence under the
   name is shown, and Follow is still offered.
9. A story from one outlet, or with one outlet in total, is marked `One source so far`.
10. Share is on the page once.
11. A returning reader sees the returning line only when there are unseen developments; the Follow control
    then reads `Following`.
12. `Who reported it` sort orders: groups by number of outlets, most first; outlets by number of reports, most
    first; ties by name.
13. A merged story redirects to its successor; a story that no longer exists gets the record's own 404 page.
14. Figures are shown complete; they never animate up from zero.

## Accessibility behaviour

- The figures are a list; each item's name is its figure and label together, and the order is the reading
  order. `days running` and `developments` are links. `outlets` and `languages` open a panel when it is not
  shown open, so there they are `<button aria-haspopup="dialog">`; when it is shown open they move focus to
  its heading.
- The returning line is text, not a live region.
- The count of outlets and the split by kind of outlet are always given in words and counts, never only as a
  graphic.
- `Who reported it` is a `<button aria-haspopup="dialog">`; the panel is a labelled modal dialog with a focus
  trap; language group names carry their `lang`.
- A story that is no longer current is marked in words (`Last development`); one source is marked in words
  (`One source so far`).
- The loading state is announced as loading.

## Needs from the API

| Needs | From |
|---|---|
| Days running, developments, outlets, languages — one query shared with the Stories list; the latest and the first development with their outlet and language counts | T-007 |
| Outlets grouped by language with report counts; the split by kind of outlet | T-007 (today's payload lists outlets with reports and language; the split by kind of outlet must be added) |
| Unseen count and last-read time | T-035, T-050 |
| A story's name in the interface language | T-054 |

## Decided here

1. **Nothing generated.** No "the story so far" sentence. The header is four counts, the count of outlets and
   two headlines.
2. **The figures are the navigation.** Each count opens what it counts, as the record's stats already do.
3. **`Latest` and `Began` are both in the header**, newest first: a cold reader wants the latest; the first
   says what the story is without Prism describing it.
4. **Who reported it is reachable from the header**, not only at the foot of the page: a button opens it on a
   small screen.
5. **Quiet is 7 days**, said in words and marked as no longer current. The threshold is this spec's; if the
   stories list later defines "ended" from data, the header follows that definition.
6. **Figures are shown complete; they never animate up from zero**: a number is a fact, and it is there when
   the page is.

## References

`~/prism-program/design-refs/story-header.md`; design audit §7.2 "Story page" (`board.md` rows C1, C2, C3,
C5). The count strip is Prism's own counted-stats pattern, not a borrowed one.
