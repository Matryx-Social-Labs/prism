# 02 · Follow, "Following", the Following tab

Built by T-050. Comps: `comps/follow-b.html` (the form taken), `comps/following.html` (the tab, the free
limit, "new since you read"); the two forms not taken in `comps/follow-a.html` and `-c.html`.

## Purpose

The promise on the masthead becomes something a reader can do: follow a story, come back, and see only what
moved. One control, the same everywhere a story is named; one place that lists what the reader follows.

## Where it lives

- **The control:** the head of a story page (spec 06); a record's "Part of" block; an edition item's story
  line (spec 01); a row in Stories; the Following tab; a person, subject or company page.
- **The Following tab:** the fourth of the five destinations (D-20), replacing Watchlist. Tickers, sectors
  and Market Pulse live under it. T-050 chooses the address; `/following` with `/watchlist` redirecting is
  the recommendation.

## The control

| State | Looks like | Says |
|---|---|---|
| Default | secondary Button; small (36 drawn, 44 target) in rows, default size in a story head | `Follow` |
| Hover / pressed | the Button's own states; no lift | |
| Focus | the 2px accent focus ring | |
| Busy | the words change; `aria-busy`, disabled; no spinner | `Following…` / `Unfollowing…` |
| Following | the same shape with ink text and a 1px ink border (a solid line means on) and the ChevronDown icon; `aria-haspopup`, `aria-expanded` | `Following` |
| Following, open | see "What opens" | |
| Could not save | the control returns to what it was; under it, in `--danger`, reading voice | `That did not save. Try again.` |

The control never changes width class between states: `Follow` and `Following` + chevron fit the same row at
360px. It is never an icon alone and never the ▾ glyph. No bell on the control: whether alerts are on is said
inside, in words.

### What opens behind the chevron

The same two things at every width:

1. A switch: `Alerts for this story`, and under the label in `--ink-3`: `When a development is reported by 2
   or more outlets. At most 3 a day.` It is on when alerts are on for this device or email; turning it on with
   no permission yet opens the explanation (spec 03). On a person, subject or company there is no switch:
   Prism sends alerts for stories only.
2. `Unfollow` — a plain row, ink text. It is not styled as destructive: it can be undone.

- **Compact:** a bottom Sheet with the story's name as its title (reading voice 600, two lines) and a Close
  button; rows at least 56px tall. Scrim; Escape and a tap on the scrim close it; focus is trapped inside and
  returns to the control.
- **Medium and up:** a popover under the control's right edge, 280px wide, `--elevated`, 1px line, 8px radius,
  `--shadow-2`; rows at least 44px. Escape and a click outside close it; focus returns to the control.

### After the press

| Event | Toast (`role="status"`, 6 seconds, one at a time) |
|---|---|
| Followed, signed in | `Following. Changes to this story appear in Following.` — action `Turn on alerts`, shown only while alerts are off for this story |
| Followed, signed out | `Following on this device.` — action `Sign in to keep it` |
| Unfollowed | `Unfollowed.` — action `Undo` |

A signed-out follow works at once (T-035 keeps it on the device and the server); sign-in is offered, never
required. On a story page the first follow also shows the inline card of spec 03 under the header.

## The free limit (D-17)

Following and its alerts are free for 5 stories; people, subjects and companies do not count. The sixth
follow is not made. A Sheet opens instead:

1. `You follow 5 of 5 stories` — record voice, display-m.
2. Five square segments, all ink (the count, drawn).
3. `Following is free for 5 stories. Unfollow one to follow this, or follow without a limit on Plus.`
4. `Your 5 stories` — the five, one line each, each with `Unfollow`. Unfollowing one here makes the pending
   follow at once and closes the sheet with the toast `Following. Changes to this story appear in Following.`
5. `Plus adds` — four lines, each with a Check: `Unlimited follows` · `Alerts through a closer reading` ·
   `A weekly brief of what changed, per story` · `Ask across the whole story`.
6. Primary `See Plus` (to `/plus`, where the price and renewal terms are; none are restated here). Under it
   `Not now`.

**While Plus is not on sale** (checkout is hidden today): items 5 and 6's primary button are not drawn, and
the sentence is `Following is free for 5 stories. Unfollow one to follow this.` The limit is enforced on the
server; the sheet is how the refusal is explained, whichever surface the press came from.

## "New since you read"

On a story's timeline, newest first, for a reader who has read this story before:

- Above the first row: `{k} new since you read` and, in mono, the day and time of the last read.
- Each unseen development carries a badge with the word `New` (ink badge; a word, not a colour).
- Between the last unseen and the first seen row, a divider: a 1px `--line-strong` rule broken by
  `You read up to here` and the same day and time in mono.
- The same count is in the story header (spec 06). A notification opens the story at the top, where the
  count and the unseen rows are.
- The read mark moves when the divider has scrolled into view, or when the reader leaves the page having
  opened it; the badges stay for the rest of that visit.
- More unseen than one page holds (30, T-007): the count is the true count, the divider is on a later page,
  and `Older developments` loads toward it.
- First visit, or nothing new: no line, no badges, no divider.

## The Following tab

Content, in order:

1. `Following` — h1, record voice, display-l. At its right in mono: `{k} of 5 stories` on the free plan,
   `{k} stories` on Plus.
2. `Moved since you read` — section head (3px rule). Stories with unseen developments, newest movement
   first. Each row: the story's name (record voice, title; the link, opening the story at the top);
   mono `{k} new · latest {time}`; the latest development's headline (reading voice, `--ink-2`, two lines);
   the `Following` control (small) at the right. A latest development from one outlet gets the dashed rule
   and `One source so far`.
3. `Nothing new` — section head. The rest, one row each: the name, then `Nothing new since {day HH:MM}` in
   `--ink-3`, the control at the right.
4. `People, subjects and companies` — section head. The chips Watchlist has today (followed ones with a
   Check), then `Stories on what you follow` as rows, then the link `Market Pulse →`.

| State | What the reader sees |
|---|---|
| Loading | The h1 and three skeleton rows with a row's geometry. |
| Nothing followed yet | `You are not following a story yet.` / `Follow a story to see only what changed since you last read.` Then `Most reported this week`: the three most-reported running stories (live, from the stories list), each with mono `{d} developments · {k} outlets` and `Follow`. |
| Followed, nothing moved | Under the h1: `Nothing new on your {k} stories since {HH:MM}.` Then the `Nothing new` rows. No `Moved` section. |
| Signed out | The tab as above, with an info alert first: `These are kept on this device.` — link `Sign in to keep them everywhere`. |
| Could not load | Error alert: `Your stories could not load.` with `Try again`. |
| At the limit | The count reads `5 of 5 stories`; nothing else changes until a sixth follow is tried. |
| A followed story that has ended or merged | It stays in `Nothing new` under its current name; a merged story opens its successor. Nothing is removed silently. |

## Layout

| | Compact < 600 | Medium 600–1023 | Expanded ≥ 1024 |
|---|---|---|---|
| Control in a row | at the row's right; the name wraps beside it | same | same |
| What opens | bottom Sheet | popover | popover |
| Limit sheet | bottom Sheet, scrolls inside | dialog, 480 wide | dialog, 480 wide |
| Following tab | one column, gutter 16; sections stacked | 640 column beside the rail | 640 column (stories) + 320 right rail holding `People, subjects and companies`, gap 48 |
| Toast | above the tab bar, 16 from the edges | bottom centre of the content area | bottom centre |

## Motion

The control changes state without moving its neighbours. Sheets arrive from their edge (220ms); the popover
fades in 140ms. The toast rises 8px over 220ms. A `New` badge does not pulse. Reduced motion: instant.

## Accessibility

- The control is a `<button>`; in the following state it has `aria-haspopup="dialog"` (compact) or `"menu"`
  (popover) and `aria-expanded`. Its name includes the story: `Follow {story}`, `Following {story}`.
- The alerts row is `role="switch"` with `aria-checked`; its sentence is its description.
- The sheet and the dialog trap focus and restore it; the popover closes on Escape and on focus leaving it.
- A toast is announced politely; its action is reachable by keyboard and the toast stays while it has focus.
- "New" is a word; the divider's text is real text, not a pseudo-element.

## Primitives

Button, Sheet (with a focus trap — today's does not have one), Popover, ToggleRow, Toast with one host for
the whole app (today each component keeps its own), Badge, SectionHead, Skeleton, Alert, Chip, EmptyState.
New: `FollowButton`, `NewSinceDivider`, `LimitSheet`.

## Depends on

| Needs | From |
|---|---|
| Follows and read marks for signed-in and signed-out readers; the count of unseen developments per story | T-035 |
| The limit enforced on the server, with a refusal the client can explain | T-050 (D-17) |
| Whether Plus can be bought today | the billing configuration the Plus page already reads |
| Alert switch per follow | T-036 (stores it), T-053 (asks permission) |

## Decided here

1. **One control; what opens is a sheet on a phone and a popover from 600.** Three forms were drawn. A is a
   popover at every width; B is this one; C opens in place under the control. A's popover is a 280px box with
   a switch and a sentence inside, hanging off a 36px button at the edge of a 360px screen — the targets are
   reachable but cramped, and it covers the row it belongs to. C pushes the page down, which in an edition
   row or a Stories list moves everything the reader was about to tap. B gives a phone a thumb-height sheet
   that names the story it is about, and gives a pointer a menu next to the control.
2. **No bell on the control.** A second icon would carry meaning without a word; the alert state is one row
   inside.
3. **Unfollow is plain and undoable**, not red and not confirmed.
4. **The limit sheet offers two ways on, and one while Plus is not sold.** Unfollowing one from the sheet
   completes the follow the reader asked for.
5. **Only stories count toward 5.** D-17 says "5 stories"; people, subjects and companies are today's free
   Watchlist and stay free.
6. **Newest first, so "new" is at the top**; the divider marks where the reader had got to rather than where
   new begins.
7. **Following uses the Watchlist icon** until T-043 draws a Following glyph.

## References

`~/prism-program/design-refs/follow.md`; design audit §7.2 "Story page", "You / account" (`board.md` rows D1,
D2, D4, D5, C2, K3). The unread divider is from memory, not Mobbin.
