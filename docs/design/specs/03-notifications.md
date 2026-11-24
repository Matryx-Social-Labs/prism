# 03 · The notification explanation and settings

Built by T-053 (the reader's side); T-036 sends and enforces the policy. Comp: `comps/notifications.html`.

## Purpose

A reader is told when a story they follow really moves, and once a day that the edition is ready, and nothing
else. Before the browser or the phone asks for permission, Prism says in plain words what will arrive, how
often, and what a notification contains — and the reader can say "Not now" without spending the one system
prompt.

## Where it lives

- **The explanation** is a Sheet. It is always opened by the reader, never by Prism:
  1. the inline card under a story's header after the reader's first follow — `Turn on alerts`;
  2. the action on the follow toast, where there is no room for a card (edition rows, Stories rows);
  3. `Tell me when tomorrow's edition is ready` on the edition's end block (spec 01);
  4. turning on `Alerts for this story` (spec 02) or a switch in settings while permission is not granted.
- **Settings** are a section of `/you`, `Notifications`, followed by `Email`.

Nothing is asked on arrival, on sign-in or on a timer.

## The inline card

Shown once, under the header of the first story a reader follows, until they answer it:

`Get told when this story moves.` — a Bell icon before it, then a small secondary button `Turn on alerts` and
a text button `Not now`. `Not now` removes the card for good on this device; the switch in the follow menu
and the settings remain the ways in. The card is a bordered row cut square, not a banner across the page.

## The explanation sheet

Content, in order:

1. **Title** (record voice, display-m), by where it was opened:
   `Get told when this story moves` (from a follow) · `Get told when tomorrow's edition is ready` (from the
   end block) · `Get told by email` (when this browser cannot notify).
2. **Two switches**, the one the reader came for first and on, the other off:
   - `Stories you follow` — `When a followed story gains a development reported by 2 or more outlets. At most
     3 a day.`
   - `The daily edition` — `Once a day at {HH:MM} IST, when the edition is ready.` (07:30 until the reader
     changes it; the zone is the reader's, printed.)
3. **A fact line** with the Info icon: `Nothing between 22:00 and 07:00. A notification carries a headline and
   the count of outlets, nothing else.`
4. **`What one looks like`** — one specimen row in the shape of a notification: the mark, `readPrism.news`,
   then real text. From a follow: the story's latest development that two or more outlets reported, and
   `{k} outlets · {l} languages`. From the end block: today's line, `Today: {n} stories · about {m} minutes ·
   lead reported by {k} outlets in {l} languages`. If there is nothing real to show (no such development
   yet), this block is left out.
5. **Primary** `Turn on`, full width. **Under it** `Not now`, a text button of the same width.

| State | What the reader sees |
|---|---|
| Default | As above. |
| Busy | The primary reads `Turning on…`, disabled, `aria-busy`. The system prompt is on screen. |
| Granted | The sheet closes; toast `Alerts are on.` The card, if any, goes. |
| Not now | The sheet closes. Nothing is stored against the reader except that the card was answered. The system prompt has not been spent. |
| Dismissed at the system prompt, or blocked earlier | Title `Notifications are blocked for this site`; `Your browser is set to block them. Allow notifications for readprism.news in the browser's site settings, then come back.`; secondary `Use email instead`; `Not now`. |
| This browser cannot notify (an in-app browser, iOS Safari outside the home screen) | Title `Get told by email`; `This browser cannot show notifications. The same two messages can come by email.`; the two switches; an `Email` field (filled and read-only when signed in); primary `Send by email`; `Not now`. |
| Email sent for confirmation (signed out) | The sheet's body becomes `Check {address} and confirm. Nothing is sent until you do.` with `Done`. |
| Both switches off | The primary is disabled; under it: `Choose at least one, or Not now.` |
| Could not save | An error alert above the buttons: `That did not save. Try again.` The switches keep what the reader set. |

## Settings (`/you` · Notifications)

In order:

1. Section head `Notifications`.
2. A status line: `On this device: on` / `off` / `blocked by the browser` — the last with the link `How to
   allow them`, which opens the blocked state of the sheet.
3. Switch `The daily edition` — `Arrives at {HH:MM} IST, or as soon as the edition is ready.` At its right the
   time: a select of half-hours from 07:00 to 21:30, the zone in mono beside it. Changing it saves at once
   (`Saving…` replaces the sentence, then the sentence returns with the new time).
4. Switch `Stories you follow` — `When a followed story gains a development reported by 2 or more outlets. At
   most 3 a day; the rest wait for the next morning.`
5. `Per story` — every followed story on a row with its own switch (`Alerts for {story}`). Off here is the
   same as off in the story's follow menu. With no follows: `You are not following a story yet.`
6. Section head `Email`. A segmented control `Daily` · `Weekly` · `Off`; under it the sentence for the
   choice: `Today's edition by email, at the time above.` / `The week's record by email, Sunday morning
   (IST).` / nothing. Signed out, an `Email` field appears above it and a choice other than `Off` sends a
   confirmation first. This replaces the weekly checkbox on `/account`.
7. A fact line: `Nothing is sent between 22:00 and 07:00.`

| State | What the reader sees |
|---|---|
| Loading | Skeleton rows with the rows' geometry. |
| Permission never asked | Status `off`; both switches off; turning one on opens the sheet. |
| Blocked | Status `blocked by the browser`; the switches are off and pressing one opens the blocked sheet. Email still works. |
| Cannot notify | The status line reads `This browser cannot show notifications.` and the two switches are not drawn; `Email` is first. |
| Could not load / save | `Your notification settings could not load.` with `Try again` / under the changed row, `That did not save. Try again.` and the control returns to what it was. |
| Signed out | Everything works on this device; under the section: `Sign in to use the same settings on every device.` |

## States

| State | Where it is specified |
|---|---|
| Empty | Settings · `Per story` with no follows; the sheet · nothing real to show in `What one looks like` |
| Loading | The sheet · Busy; settings · Loading |
| Error | The sheet · Could not save, Blocked, Cannot notify; settings · Could not load / save |
| Signed out | The sheet · Cannot notify and Email sent for confirmation; settings · Signed out |
| At the free limit | Not applicable: notifications are not metered. Alerts through a closer reading are a Plus feature (D-17) and get their own row when they exist; nothing here is locked. |

## Copy

- A notification's own text is not written here: T-036 builds it from a headline and counts. This spec's
  sentences describe it and must stay true to it — if the policy changes (the cap, the hours, the two-outlet
  rule), these sentences change in the same pull request.
- "Alerts" is the word for follow notifications; "the daily edition" for the daily one. Never "push".

## Layout

| | Compact < 600 | Medium 600–1023 | Expanded ≥ 1024 |
|---|---|---|---|
| Explanation | bottom Sheet, content scrolls inside, buttons pinned at its foot | dialog, 480 wide, centred in the content area | dialog, 480 wide |
| Inline card | full column width; buttons wrap under the sentence below 420 | one row | one row |
| Settings | full-width rows, 56px+, hairlines between; the time select under its sentence | 640 column; the select at the row's right | 640 column |

## Motion

The sheet arrives from its edge (220ms). A switch moves in 140ms. The card leaves by collapsing its height
over 220ms so the timeline does not jump. Reduced motion: instant.

## Accessibility

- The sheet is a modal dialog labelled by its title; focus starts on the title, is trapped, and returns to
  the control that opened it. Escape is `Not now`. If the opener no longer exists when the sheet closes (the
  toast has gone, the card was removed, the end block's button was replaced), focus goes to that story's
  Follow control, or to `Change` on the end block. When the sheet's body is replaced (blocked, email sent),
  focus moves to the new title.
- `Daily` · `Weekly` · `Off` is a radio group named `Email`, not tabs.
- The email field is `type="email"` with `autocomplete="email"`. Confirming an address is a link in the email,
  never a code to copy.
- While busy a button is `aria-busy` and `aria-disabled`, not `disabled`.
- Switches are `role="switch"`; each sentence is the switch's description.
- The time control is a native `<select>` with the label `Time`; the zone is text, not part of the value.
- `Not now` is a real button with a 44px target and the same width as the primary: declining is as easy as
  accepting (India's dark-pattern guidelines; DESIGN.md, the cancel sheet decision).
- The specimen row is marked as an example for screen readers (`aria-label="Example notification"`).

## Primitives

Sheet (bottom and dialog, with the focus trap), ToggleRow, Button, TextField, SelectField, Segmented, Alert,
Toast, Skeleton, SectionHead. New: `NotifyExplain`, `NotifyCard`.

## Depends on

| Needs | From |
|---|---|
| A device can be registered with no account; the per-follow switch; the daily time and zone | T-036 |
| The policy the sentences state: two or more outlets, at most 3 a day with the overflow held for the morning, nothing 22:00–07:00 | T-036 |
| Web-push keys | FA-16 |
| A daily email, and a confirmation step for an address typed by a signed-out reader | T-036 / T-053 |

## Decided here

1. **Prism never opens the explanation itself.** It is offered — a card at the first follow, an action on a
   toast, a button on the end block — and the reader opens it. PLAN §4.3 asks for the explanation "at the
   first follow"; the card is that ask, and it leaves the reader's page as it was.
2. **Quiet hours and the daily cap are stated, not settings.** They are policy in code (T-036); two more
   controls would be two more things to get wrong at 7 in the morning.
3. **The daily time is offered from 07:00 to 21:30**, so a chosen time can never fall inside quiet hours.
4. **The sheet does not promise "an outlet's own words".** D-18 allows Prism's labelled headline on a
   happening with two or more independent reports, so the sentence says what is always true: a headline and
   the count of outlets, nothing else.
5. **Email is the way on where the browser cannot notify**, and needs no account — an address and one
   confirmation.
6. **"Not now" costs the reader nothing** and is never followed by another ask from Prism.

## References

`~/prism-program/design-refs/notifications.md`; design audit §7.2 "Notifications" (`board.md` rows H1, H2, H3,
H4, H5, D3, J2).
