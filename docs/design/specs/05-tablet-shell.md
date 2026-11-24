# 05 · The shell by width, with a navigation rail on tablets

Built by T-042. Comp: `comps/shell.html` (the rail's states); every other comp sits in this shell, so
`comps/edition.html` at 390, 768 and 1024 shows the three tiers with real content.

## Purpose

The same five destinations at every width — Today · Stories · Search · Following · You (D-20) — in the form
that suits the width. Today a tablet gets the phone's tab bar stretched to 834px and a reading line that runs
to 975px. This spec gives the middle tier its own shell: a navigation rail.

## The shell at each size class

| | Compact < 600 | Medium 600–1023 | Expanded 1024–1279 | Large ≥ 1280 |
|---|---|---|---|---|
| Navigation | bottom tab bar, 58 tall, fixed | **navigation rail**, 80 wide, fixed left, full height | top bar, 60 tall, sticky | top bar, 60 |
| The five | icon over label, five equal cells | icon over label, 64-tall cells, top-aligned under the mark | `Today` · `Stories` · `Following` as links; Search is the field; You is the avatar or `Sign in` | same |
| Brand | lockup (mark 20) in the masthead | the mark alone (24) at the head of the rail; the lockup (mark 20) in the masthead | lockup (mark 24) at the left of the top bar | same |
| Date | mono dateline at the masthead's right | same | not shown in the bar (the edition head carries the time) | same |
| Masthead | 52, sticky, paper at 92% with the 12px blur | 52, sticky, to the right of the rail | — | — |
| Content | full width, gutter 16 | beside the rail; one 640 reading column, centred in the remaining width, gutter 24 | 640 column + evidence beside it (320), gutter 32 | + the subject rail (220) where a page has one |
| Sheets | from the bottom | centred dialog, 480 | centred dialog or right drawer | same |

Width alone decides: a phone held sideways (for example 740 × 360) is medium and gets the rail, which is
what a short, wide screen needs. xlarge (≥ 1536) is large with the wider rails `DESIGN.md` · Layout gives;
content never exceeds 1600 and prose never exceeds 640.

## The navigation rail (medium)

- **Box:** 80 wide, the full height of the viewport, fixed; paper ground; a 1px `--line` rule on its right; no
  shadow. It scrolls on its own (`overflow-y: auto`) if the viewport is shorter than its content.
- **Head:** the mark alone at 24 in a 56-tall box, linking to Today. Below 16px the mark stands alone by the
  wordmark rule; the rail is the one place a 24px mark does, because the lockup is 12px away in the masthead.
- **Destinations:** five cells, each 80 × 64, in the fixed order. A 24px icon above a label in the reading
  voice at label size (12.5px). The label may wrap to two lines (Hindi and Malayalam labels do); the cell
  grows, the rail does not widen.
- **Nothing else is in the rail.** No theme control (it is in the footer's Appearance row), no Plus link, no
  sign-in (You is a destination).

| State of a destination | Looks like |
|---|---|
| Default | icon and label in `--ink-2` |
| Hover (a pointer) | a `--sunken` pill, 56 × 32, 8px radius, behind the icon; no lift |
| Pressed | the pill one step darker (`--line`) |
| Focus | the 2px accent ring, 2px offset, around the cell |
| Current | icon and label in the accent; an `--accent-soft` pill behind the icon; `aria-current="page"` |
| With a count | on Following only, when followed stories have moved: the number in mono (11px) in a square-cut box at the icon's top right — ink on `--surface`, 1px `--line-strong`. `9+` above nine. A number, never a bare dot. The same badge sits on the Following tab at compact. |

Which destination is current on a leaf page: the one the reader came through, as today's tab bar decides it
(a record opened from Today keeps Today current; opened from a link, none is current).

## Chrome a route may declare

T-042 replaces the route-prefix arrays with a declaration per route. What each means at each width:

| Chrome | Compact | Medium | Expanded and up | Routes |
|---|---|---|---|---|
| `app` | masthead + tab bar | rail + masthead | top bar | Today, Stories, Search, Following, You and their sections |
| `record` | a back bar (arrow alone, named "Back to …", the lockup centred) and the page's own action bar; no tab bar | the rail stays; the back bar sits to its right | top bar | a record, a story, a quote, a person or subject page, Sources, legal, Corrections |
| `bare` | the lockup in a 52 bar; nothing else | same | same | onboarding, sign-in |
| `own` | the page draws its own | same | same | the landing and `/about`, `/plus`, the labeller, the admin |

At medium a story's Ask · Share bar is fixed to the bottom of the content area (left edge at 80), the width
of the reading column — it never slides under the rail. A leaf page keeps the global navigation from medium
up; only compact trades it for the back bar.

## States of the shell

| State | Behaviour |
|---|---|
| Empty · At the free limit | Do not apply: the shell is never empty and nothing in it is metered. |
| Signed out | Identical. You opens the signed-out You page (`Sign in` is there). At expanded the top bar's right end is `Sign in`. |
| Loading a destination | The shell does not change; the content area shows that surface's skeleton. The pressed destination becomes current at once. |
| Offline or the API unreachable | The shell stays; the content area shows the surface's error state. No banner is added to the shell. |
| Resizing or rotating across 600 or 1024 | The form changes with no animation and the scroll position of the content is kept. |
| Keyboard open on a tablet | The rail is unaffected. |
| A sheet or dialog open | The rail is inert behind the scrim. |
| Printing | No rail, no bars. |
| Reduced motion | Nothing in the shell animates anyway. |

## Copy

| Where | String |
|---|---|
| The five labels | `Today` · `Stories` · `Search` · `Following` · `You` |
| The navigation's name | `Primary` |
| The mark's link in the rail | `Today` (its accessible name) |
| Skip link, first in the page | `Skip to the content` |
| Search field (expanded) | placeholder `Search stories, people, places` |
| Count badge, for a screen reader | `Following, {k} stories moved` · `Following, 1 story moved` |

## Motion

None in the rail: hover and current are changes of ground, at once. The masthead's blur and the top bar are
as `DESIGN.md` · Layout has them.

## Accessibility

- One `<nav aria-label="Primary">` is in the accessibility tree at a time; the forms not shown at this width
  are `display: none`, not hidden by position.
- The rail is before the content in the document; the skip link is before the rail.
- Every destination is a link with a visible label at every width — there is no icon-only form.
- Cells are 80 × 64: over the 44px floor. The focus ring is never clipped by the rail's edge (2px inset on the
  right).
- The count is text inside the link, so it is read with the label.

## Primitives

`AppShell` (new; chooses the form by size class and by the route's declared chrome), `NavRail` (new),
BottomTabBar, TopBar (`SiteHeader` + `HeaderNav`), Masthead, SkipLink, Badge. Icons: `TodayIcon`,
`StoriesIcon`, `SearchIcon`, `YouIcon`, and for Following the present `WatchlistIcon` until T-043 draws one.

## Depends on

| Needs | From |
|---|---|
| Size-class tokens and the reading-measure rule | T-040, T-042 |
| The five destinations and Pulse under Following | D-20; T-050 (Following), T-044 |
| The count of followed stories that moved | T-035 |
| Until T-050 ships Following | the fourth destination is already labelled `Following`, opens today's `/watchlist`, and carries no count |

## Decided here

1. **The rail runs from 600 to 1023, with labels.** Material's guidance moves to a wider form at 840; Prism's
   top bar begins at 1024 (PLAN §4.2), so one form covers the whole middle tier. The design audit suggested
   an icon-only rail at medium; labels stay, because a destination named only by a glyph is meaning without a
   word, and 80px holds them.
2. **One reading column at medium.** No second column until expanded: 768 − 80 leaves 688, which is a column
   and its gutters and nothing more, and one rule for the whole tier is one T-042 cannot misread.
3. **The rail holds the five and the mark, nothing else.**
4. **The Following count is a number.** A dot would be colour carrying meaning alone.
5. **At expanded, Search is the field and You is the avatar** — still five destinations, in the form a wide
   bar gives them.
6. **A sideways phone gets the rail.** Height is not consulted; a bottom bar on a 360px-tall screen would take
   16% of it.

## References

`~/prism-program/design-refs/tablet-shell.md`; design audit §7.2 "Tablet / desktop shell" (`board.md` rows
L3, L4; L5 and L6 are from memory, not Mobbin — Mobbin holds no tablet screens).
