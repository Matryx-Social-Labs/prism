# 02 · Follow, "Following", the Following tab

Built by T-050.

## Purpose

The promise on the masthead becomes something a reader can do: follow a story, come back, and see only what
moved. One control, the same everywhere a story is named; one place that lists what the reader follows.

## Where it appears

- **The control:** the head of a story page (spec 06); a record's "Part of" block; an edition item's story
  line (spec 01); a row in Stories; the Following tab; a person, subject or company page.
- **The Following tab:** the fourth of the five destinations (D-20), replacing Watchlist. Tickers, sectors
  and Market Pulse live under it. Its address is `/following`; `/watchlist` redirects to it.
- **What opens from `Following`:** pressing the control once the reader follows.

## Content, in order

### The control

| State | What the reader is given / what happens | Says |
|---|---|---|
| Default | The control | `Follow` |
| Busy | The words change; the control is busy and cannot be pressed again (`aria-busy`, `aria-disabled`) | `Following…` / `Unfollowing…` |
| Follow state not loaded yet | `Follow`, busy (`aria-busy`) | `Follow` |
| Follow state failed to load | `Follow`; nothing is said. Pressing it follows, or finds the reader already follows and shows `Following`. | `Follow` |
| Following | The control says `Following`; `aria-haspopup`, `aria-expanded` | `Following` |
| Following, open | see "What opens from `Following`" | |
| Could not save | The control returns to what it was. In a story head the sentence is shown under it. In a row there is no room for a sentence without moving the row's neighbours, so there it is a brief confirmation message with the action `Try again` | `That did not save. Try again.` |

Whether alerts are on is said in words inside what opens, never by a second symbol on the control.

### What opens from `Following`

The same two things at every size:

1. A switch: `Alerts for this story`, and under the label: `When a development is reported by 2 or more
   outlets. At most 3 a day.` It shows the story's own setting, which is the reader's and the same on every
   device (spec 03, `Per story`). When `Stories you follow` is off on this device, `Alerts are off on this
   device.` is shown under it. Turning it on with no permission yet opens the explanation (spec 03). On a person, subject or company there is no switch: Prism
   sends alerts for stories only.
2. `Unfollow` — a plain row. It is not shown as destructive: it can be undone.

- **At compact** a panel opens that blocks the page (modal) and names the story, with a `Close`
  button. Escape and a tap outside the panel close it; focus is trapped inside and returns to the control.
- **From medium up** a panel opens that does not block the page. Escape and a click
  outside close it; focus returns to the control.

T-083 draws both.

### After the press

| Event | Brief confirmation message (`role="status"`, one at a time) |
|---|---|
| Followed, signed in | `Following. Changes to this story appear in Following.` — action `Turn on alerts` |
| Followed, signed out | `Following on this device.` — action `Turn on alerts` |
| Followed a person, subject or company | `Following. Stories on {name} appear in Following.` — no action |
| Unfollowed | `Unfollowed.` — action `Undo` |

`Turn on alerts` is offered on the message, signed in or signed out, only while alerts are off for this story,
no offer of the same thing is on screen (spec 03), and the reader has never pressed `Not now` on this device. After a `Not now`,
Prism does not raise alerts again; the switch inside what opens and the settings remain.

A message with no action leaves after 6 seconds. A message that carries an action (`Undo`, `Turn on alerts`)
stays until the action is used, the reader dismisses it (`Dismiss`), or the next message
replaces it: an action a reader cannot reach in time is not an action. Unfollowing is final when its message
goes; until then `Undo` restores the follow and its alert setting.

A signed-out follow works at once (T-035 keeps it on the device and the server); sign-in is offered on the
Following tab, never on the follow itself. On a story page the first follow also shows the offer of spec 03, in place under the story's header.

### The first follow on a device: remembering what was read

"New since you read" needs Prism to keep which developments a reader has seen. That is reading history, and
it is kept only with the reader's agreement (D-12). So the first follow on a device asks once, where the
follow was pressed — an offer in place under the header on a story page (ahead of the alerts offer, which
waits for this answer), a panel elsewhere. The panel blocks the page; focus moves to it and returns to the
control that was pressed. Closing it without an answer is 'Not answered'.

`Prism can remember what you have read in the stories you follow, so it can show you what is new. Prism keeps
it until you turn this off.` — `Remember` · `Don't remember`. Neither is pre-selected and the two are offered equally.

| Answer | What follows |
|---|---|
| `Remember` | Read marks are kept (T-035). Everything in "New since you read" and the counts in Following work. |
| `Don't remember` | The follow stands. No read marks are sent or kept. A story page shows no "new" line, no `New` words and no divider; Following lists every followed story under one heading, `Your stories`, newest development first, each with `latest {time}` in place of a count of new. Alerts still work: they depend on the story moving, not on what was read. |
| Not answered (closed, or left) | Treated as `Don't remember`; asked again at the next follow, once. |

Signed in, the answer belongs to the account and is asked once, not once per device. T-035's rule for a
child's account applies: it is never asked and nothing is kept.

The answer can be changed on `/you` · Privacy: `Remember what I read in followed stories` (a switch). Turning
it off deletes what was kept. Counsel reads the wording of this ask, and of the email step in spec 03, before
either ships (FA-02).

### The free limit (D-17)

Following and its alerts are free for 5 stories; people, subjects and companies do not count. The sixth
follow is not made. A panel opens instead, in this order:

1. `You follow 5 of 5 stories`.
2. `Following is free for 5 stories. Unfollow one to follow this, or follow without a limit on Plus.`
3. `Your 5 stories` — the five, one line each, each with `Unfollow` (named `Unfollow {story}` for assistive
   technology). Unfollowing one here makes the pending follow at once and closes the panel with the message
   `Following. Unfollowed {story}.` with `Undo`, which restores that follow and withdraws the new one. The
   swap is one request: both happen or neither. If it fails the panel stays open with `That did not save.
   Try again.`
4. `Plus adds` — up to four lines: `Unlimited follows` · `Alerts through a closer reading` · `A weekly brief of
   what changed, per story` · `Ask across the whole story`. A line is shown only when its feature is live for
   a Plus reader today; the list never promises what Plus does not yet do.
5. The main action `See Plus` (to `/plus`, where the price and renewal terms are; none are restated here).
   Under it `Not now`.

**While Plus is not on sale** (checkout is hidden today): item 4 and the main action are not shown, and the
sentence is `Following is free for 5 stories. Unfollow one to follow this.` The limit is enforced on the
server; the panel is how the refusal is explained, whichever surface the press came from.

**Over the limit.** A reader can hold more than 5 without having broken a rule: follows made on a device and
on an account are merged at sign-in, and a Plus plan can end. Nothing is ever unfollowed for them. The count
in Following reads `{k} stories · 5 are free`; alerts keep working for all of them; and a further follow opens
the panel titled `You follow {k} stories`, with the sentence `Following is free for 5 stories. Unfollow {k−4}
to follow this, or follow without a limit on Plus.` and every followed story in the list. There the panel
stays open after an unfollow and recounts, until the reader is at 4 and the follow is made.

### "New since you read"

On a story's timeline, newest first, for a reader who has read this story before:

- Following a story sets its read mark to that moment. `New since you read` exists only on stories the
  reader follows and has agreed to have remembered; a story that is not followed never shows it.
- Each unseen development carries the word `New`.
- Between the last unseen and the first seen row, a divider labelled `You read up to here`, with the day
  and time of the last read.
- A notification opens the story at the top; with newest first the unseen developments are the first rows,
  and the header carries the count. The page does not scroll down to the divider.
- The read mark moves when the divider has scrolled into view, or when the reader leaves the page having
  opened it; the `New` words stay for the rest of that visit.
- More unseen than one page holds (30, T-007): the count is the true count, the divider is on a later page,
  and `Older developments` loads toward it.
- First visit, or nothing new: no line, no `New` words, no divider.

### The Following tab

1. `Following` — the page heading. With it: `{k} of 5 stories` on the free plan, `{k} stories` on Plus.
2. `Moved since you read` — a heading. Stories with unseen developments, newest movement first. Each row: the
   story's name (the link, opening the story at the top); `{k} new · latest {time}`; the latest
   development's headline; the `Following` control. A latest development from one outlet is
   marked in words: `One source so far`.
3. `Nothing new` — a heading. The rest, one row each: the name, then `Nothing new since {day HH:MM}`, and the
   control.
4. `People, subjects and companies` — a heading. One row per followed person, subject or company: its name and
   the `Following` control. Then `Stories on what you follow`, as story rows. Then the link `Market Pulse →`.
   With none followed, the section is only the link `Market Pulse →`. A ticker followed today is listed as its
   company, a sector as its subject; nothing a reader follows on today's Watchlist is dropped.

## States

| State | What the reader is given / what happens |
|---|---|
| Loading — the control | Busy: the words change to `Following…` / `Unfollowing…` (see The control). |
| Loading — the Following tab | The heading and a loading state with no text in place of three rows; announced as loading to assistive technology. |
| Empty — nothing followed yet | `You are not following a story yet.` / `Follow a story to see only what changed since you last read.` Then `Most reported this week`: the three most-reported running stories (live, from the stories list), each with `{d} developments · {k} outlets` and `Follow`. |
| Empty — followed, nothing moved | No `Moved since you read` section; the `Nothing new` rows. |
| Empty — "New since you read", first visit | No line, no `New` words, no divider. |
| Follow state not loaded / failed | See The control: `Follow`, busy while not loaded; `Follow`, nothing said, if it failed. |
| Error — the control | Could not save: see The control. |
| Error — the Following tab | An error message: `Your stories could not load.` with `Try again`. |
| Signed out — a follow | `Following on this device.` with the action `Turn on alerts` (see After the press). |
| Signed out — the Following tab | The tab as above, with a message (not an error) first: `You follow these on this device only.` — link `Sign in to keep them everywhere`. |
| At the free limit | The count reads `5 of 5 stories`; nothing else changes until a sixth follow is tried, which opens the panel in "The free limit" (both forms: Plus on sale, Plus not on sale). |
| A followed story that has ended or merged | It stays in `Nothing new` under its current name; a merged story opens its successor. Nothing is removed silently. |

## Copy

Every string is given where it appears above. Names for assistive technology:

| Where | String |
|---|---|
| The control | `Follow {story}` · `Following {story}` |
| The panel's close button | `Close` |
| The alerts switch | `Alerts for this story` |

"Follow" is the only verb: never "subscribe", "track", "save" or "watch". The destination is `Following`.

## Rules

1. One control, the same everywhere a story is named. "Follow" is the only verb; the destination is
   `Following`.
2. There is no separate alert control on it: whether alerts are on is said in words inside what opens, never
   by a second symbol on the control.
3. What opens holds the same two things at every size: the alerts switch (stories only; none on a person,
   subject or company) and `Unfollow`. At compact it blocks the page and names the story; from medium up it
   does not block the page.
4. Unfollow is plain and undoable, not shown as destructive and not confirmed. `Undo` restores the follow and
   its alert setting until its message goes.
5. A message with no action leaves after 6 seconds; a message with an action stays until the action is used,
   it is dismissed, or the next message replaces it. One message at a time.
6. `Turn on alerts` is offered on the message only while alerts are off for this story, no offer of the same
   thing is on screen, and the reader has never pressed `Not now` on this device; this holds signed in or signed
   out. After `Not now` Prism does not raise alerts again.
7. A signed-out follow works at once and is kept on the device and the server (T-035). Its message is
   `Following on this device.`, with the action `Turn on alerts` on the conditions of rule 6; sign-in is offered
   on the Following tab, never on the follow itself.
8. The first follow on a device asks once whether Prism may remember what was read (D-12); no answer counts
   as `Don't remember` and the ask is repeated once at the next follow. The answer is changed on `/you` ·
   Privacy; turning it off deletes what was kept. Signed in, the answer belongs to the account and is asked
   once, not once per device; T-035's rule for a child's account applies: it is never asked and nothing is
   kept. Counsel reads the wording of this ask, and of the email step in spec 03, before either ships (FA-02).
9. Following and its alerts are free for 5 stories. Only stories count toward 5; people, subjects and
   companies are today's free Watchlist and stay free. The sixth follow is not made; the limit is enforced on
   the server.
10. The limit offers two ways on (unfollow one, or Plus), and one while Plus is not on sale. Unfollowing one
    from the panel completes the follow the reader asked for. A Plus line is shown only when its feature is
    live.
11. Nothing is ever unfollowed for a reader who is over the limit (follows merged at sign-in, a Plus plan that ended); their
    alerts keep working.
12. Following a story sets its read mark to that moment. `New since you read` exists only on stories the
    reader follows and has agreed to have remembered; a story that is not followed never shows it.
13. Newest first, so "new" is at the top. The divider marks where the reader had got to rather than where
    new begins. The read mark moves when the divider has scrolled into view, or when the reader leaves the
    page having opened it.
14. With more unseen developments than one page holds (30, T-007), the count is the true count and the
    divider is on a later page.
15. In Following, stories with unseen developments are first, newest movement first; the rest follow under
    `Nothing new`. A story that has ended or merged is never removed silently.
16. `Don't remember` changes what is shown, not whether alerts work: they depend on the story moving, not on
    what was read.

## Accessibility behaviour

- The control is a `<button>`; in the following state it has `aria-haspopup="dialog"` and `aria-expanded` at
  every size — what opens holds a switch and a button, not menu items, so it is never announced as a menu.
  Its name includes the story: `Follow {story}`, `Following {story}`.
- What opens is a dialog named by the story: modal at compact, non-modal from medium up. On open,
  focus moves to the switch, or to `Unfollow` where there is no switch. The non-modal panel follows the
  control in tab order.
- While busy the control is `aria-busy` and `aria-disabled`, not `disabled`: it keeps focus and stays
  readable.
- The alerts row is `role="switch"` with `aria-checked`; its sentence is its description.
- The modal panels (what opens at compact, the limit panel, the first-follow ask panel) trap focus and restore it; the non-modal
  panel closes on Escape and on focus leaving it.
- Confirmation messages appear in one region named `Notifications`, announced politely; a message's action is
  reachable by keyboard, and the message stays while it has focus or the pointer.
- "New" is a word; the divider's text is real text, not a pseudo-element.
- Loading states are announced as loading.

## Needs from the API

| Needs | From |
|---|---|
| Follows and read marks for signed-in and signed-out readers; the count of unseen developments per story | T-035 |
| The limit enforced on the server, with a refusal the client can explain | T-050 (D-17) |
| Whether Plus can be bought today | the billing configuration the Plus page already reads |
| Alert switch per follow | T-036 (stores it), T-053 (asks permission) |
| Unfollow-one-and-follow-another as one request (both or neither) | T-050 |
| Deleting kept read marks when the reader turns remembering off; one answer per account | T-035 |

## Decided here

1. **One control; the same two things open at every size.** At compact they open in a panel that blocks the
   page and names the story; from medium up they open in a panel that does not block the page. Three forms were
   drawn: a non-modal panel at every size, this one, and one that opens in place under the control. The first
   covers the row it belongs to and is cramped on a phone; the third pushes the page down, which in an
   edition item or a Stories list moves everything the reader was about to tap.
2. **No separate alert control on the Follow control.** A second symbol would carry meaning without a word;
   the alert state is one row inside, in words.
3. **Unfollow is plain and undoable**, not shown as destructive and not confirmed.
4. **The limit offers two ways on, and one while Plus is not sold.** Unfollowing one from the panel
   completes the follow the reader asked for.
5. **Only stories count toward 5.** D-17 says "5 stories"; people, subjects and companies are today's free
   Watchlist and stay free.
6. **Newest first, so "new" is at the top**; the divider marks where the reader had got to rather than where
   new begins. A notification therefore opens the story at the top. This replaces 'opens at the marker' in
   T-050, T-053 and T-083: with newest first, the top is where the unseen developments are.

## References

`~/prism-program/design-refs/follow.md`; design audit §7.2 "Story page", "You / account" (`board.md` rows D1,
D2, D4, D5, C2, K3). The unread divider is from memory, not Mobbin.
