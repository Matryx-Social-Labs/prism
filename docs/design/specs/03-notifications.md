# 03 · The notification explanation and settings

Built by T-053 (the reader's side); T-036 sends and enforces the policy.

## Purpose

A reader is told when a story they follow really moves, and once a day that the edition is ready, and nothing
else. Before the browser or the phone asks for permission, Prism says in plain words what will arrive, how
often, and what a notification contains — and the reader can say "Not now" without spending the one system
prompt.

## Where it appears

- **The explanation** is a panel. It is always opened by the reader, never by Prism:
  1. the offer under a story's header after the reader's first follow — `Turn on alerts`;
  2. the action on the follow confirmation message, where there is no room for the offer (edition items,
     Stories rows);
  3. `Tell me when tomorrow's edition is ready` on the edition's end block (spec 01);
  4. turning on `Alerts for this story` (spec 02) or a switch in settings while permission is not granted.
- **Settings** are a section of `/you`, `Notifications`, followed by `Email`.

## Content, in order

### The offer after a first follow

An offer shown in place, under the header of the first story a reader follows, until they answer it:

`Get told when this story moves.` — with two answers: `Turn on alerts` and `Not now`. `Not now` removes the
offer for good on this device; the switch inside what opens from `Following` and the settings remain the ways
in.

### The explanation

In order:

1. **Title**, by where it was opened: `Get told when this story moves` (from a follow) · `Get told when
   tomorrow's edition is ready` (from the end block) · `Get told when your stories move` (from a switch in
   settings) · `Get told by email` (when this browser cannot notify).
2. **Two switches**, the one the reader came for first and on, the other off:
   - `Stories you follow` — `When a followed story gains a development reported by 2 or more outlets. At most
     3 a day.`
   - `The daily edition` — `Once a day at {HH:MM} IST, when the edition is ready.` (07:30 until the reader
     changes it; the zone is the reader's, printed.)
3. **A fact line**: `Nothing between 22:00 and 07:00. An alert carries the development's headline and how
   many outlets and languages reported it; the daily one carries the edition's counts. Nothing else.`
4. **`What one looks like`** — one specimen in the shape of a notification: the mark, `readPrism.news`, then
   real text. From a follow: the story's latest development that two or more outlets reported, and
   `{k} outlets · {l} languages`. From the end block: today's line, `Today: {n} stories · about {m} minutes ·
   lead reported by {k} outlets in {l} languages`. If there is nothing real to show (no such development
   yet), this block is left out.
5. **The main action** `Turn on`. **Under it** `Not now`, a button giving the same ease of choice.

### Settings (`/you` · Notifications)

In order:

1. Heading `Notifications`.
2. A status line: `On this device: on` / `off` / `blocked by the browser` — the last with the link `How to
   allow them`, which opens the blocked state of the explanation.
3. Switch `The daily edition` — `Arrives at {HH:MM} IST, or as soon as the edition is ready.` With it the
   time, chosen from half-hours from 07:00 to 21:30, the zone shown beside it. Changing it saves at once
   (`Saving…` replaces the sentence, then the sentence returns with the new time).
4. Switch `Stories you follow` — `When a followed story gains a development reported by 2 or more outlets. At
   most 3 a day; the rest wait for the next morning.`
5. `Per story` — every followed story on a row with its own switch (`Alerts for {story}`). Off here is the
   same as off in the alerts switch inside what opens from `Following`. With no follows: `You are not
   following a story yet.`
6. Heading `Email`. A choice of `Daily` · `Weekly` · `Off`; with it the sentence for the choice: `Today's
   edition by email, at the time above.` / `The week's most-reported stories by email, Sunday morning (IST).`
   / nothing. Signed out, an `Email` field appears above it and a choice other than `Off` sends a
   confirmation first. This replaces the weekly checkbox on `/account`.
7. A fact line: `Nothing is sent between 22:00 and 07:00.`

## States

The explanation:

| State | What the reader is given / what happens |
|---|---|
| Default | As above. |
| Busy (Loading) | The main action reads `Turning on…`, disabled, `aria-busy`. The system prompt is on screen. |
| Granted | The panel closes; the offer, if any, goes. A brief confirmation message, by what was turned on: `Alerts are on.` (follow alerts, with or without the daily one) · `You'll be told at {HH:MM}.` (the daily one alone). `Turn on` with `Stories you follow` on sets alerts on for every story the reader follows now and for later follows; each can be switched off on its own. |
| Permission was already granted (a second press, another story) | No panel. That story's alerts turn on at once; message `Alerts are on for this story.` |
| Not now | The panel closes. Nothing is stored against the reader except that the offer was answered. The system prompt has not been spent. |
| Dismissed at the system prompt (closed without an answer) | Permission is still undecided. The panel returns to Default with the switches as the reader set them; nothing is said. |
| Blocked (denied at the system prompt now, or earlier) | Title `Notifications are blocked for this site`; `Your browser is set to block them. Allow notifications for readprism.news in the browser's site settings, then come back.`; a second action `Use email instead`; `Not now`. |
| This browser cannot notify (an in-app browser, iOS Safari outside the home screen) | Title `Get told by email`; `This browser cannot show notifications. The same two messages can come by email.`; the two switches; an `Email` field (filled and read-only when signed in); the main action `Send by email`; `Not now`. |
| Email, signed in | `Send by email` reads `Sending…`, then the panel closes with the brief confirmation message `These will come to {address}.` No confirmation step: the address is the account's. |
| Email, an address that is not one | Under the field: `Enter a valid email address.` Nothing is sent. |
| Email sent for confirmation (signed out) | `Send by email` reads `Sending…`; then the panel's body becomes `Check {address} and confirm. Nothing is sent until you do.` with `Done`. |
| The confirmation link is opened | It opens `/you` · Notifications with `Email confirmed.` above the section — or, when the link is more than 24 hours old, `That link has expired.` with `Send another`. |
| Both switches off | The main action is disabled; under it: `Choose at least one, or Not now.` |
| Error — could not save | An error message above the buttons: `That did not save. Try again.` The switches keep what the reader set. |

Settings:

| State | What the reader is given / what happens |
|---|---|
| Loading | A loading state with no text, shaped like the rows; announced as loading to assistive technology. |
| Permission never asked | Status `off`; both switches off; turning one on opens the explanation. |
| Blocked | Status `blocked by the browser`; the switches are off and pressing one opens the blocked state. Email still works. |
| Cannot notify | The status line reads `This browser cannot show notifications.` Both switches and the time stay, and act on email: their sentences end `by email` (`Arrives by email at {HH:MM} {zone} …`, `… At most 3 a day, by email.`). Turning one on with no confirmed address asks for one. |
| A second device | The status line and the two switches are per device: each device is turned on by its own press. The daily time, `Per story` and `Email` are the reader's and are the same everywhere when signed in. |
| `Stories you follow` off | The `Per story` switches are disabled and keep their positions; under `Per story`: `Alerts are off for every story.` |
| Error — could not load / save | `Your notification settings could not load.` with `Try again` / under the changed row, `That did not save. Try again.` and the control returns to what it was. |
| Empty | `Per story` with no follows: `You are not following a story yet.` The explanation, with nothing real to show: `What one looks like` is left out. |
| Signed out | Everything works on this device; under the section: `Sign in to use the same settings on every device.` |
| At the free limit | Does not apply: notifications are not metered. Alerts through a closer reading are a Plus feature (D-17) and get their own row when they exist; nothing here is locked. |

## Copy

Every string is given where it appears above.

- A notification's own text is not written here: T-036 builds it from a headline and counts. This spec's
  sentences describe it and must stay true to it — if the policy changes (the cap, the hours, the two-outlet
  rule), these sentences change in the same pull request.
- "Alerts" is the word for follow notifications; "the daily edition" for the daily one. Never "push".

## Rules

1. Prism never opens the explanation itself. It is offered — an offer at the first follow, an action on a
   confirmation message, an action on the end block — and the reader opens it. PLAN §4.3 asks for the
   explanation "at the first follow"; the offer is that ask, and it leaves the reader's page as it was.
2. Nothing is asked on arrival, on sign-in or on a timer.
3. Quiet hours 22:00–07:00 and at most 3 alerts a day are policy, not settings; the rest wait for the next
   morning. An alert needs a development reported by 2 or more outlets. They are policy in code (T-036); two
   more controls would be two more things to get wrong at 7 in the morning.
4. The daily time is offered from 07:00 to 21:30 in half-hours, so a chosen time can never fall inside quiet
   hours. It is 07:30 until the reader changes it; the zone is the reader's and is printed. Changing it saves
   at once.
5. Declining is as easy as accepting, and is never followed by another ask from Prism. `Not now` costs the
   reader nothing: nothing is stored against the reader except that the offer was answered, and the system
   prompt has not been spent (India's dark-pattern guidelines).
6. Per device: the status line and the two switches (each device is turned on by its own press). Per reader,
   the same everywhere when signed in: the daily time, `Per story` and `Email`.
7. `Turn on` with `Stories you follow` on sets alerts on for every story the reader follows now and for later
   follows; each can be switched off on its own. Off in `Per story` is the same as off in the story's own
   alerts switch.
8. With `Stories you follow` off, the `Per story` switches are disabled and keep their positions.
9. With both switches off, the main action is disabled.
10. A notification carries a headline and its counts (the daily one, the edition's counts) and nothing else.
    The sentences do not promise "an outlet's own words": D-18 allows Prism's labelled headline on a
    happening with two or more independent reports, so the sentence says what is always true.
11. The specimen is real text or is left out; it is never invented.
12. Permission already granted: no panel, that story's alerts turn on at once. Dismissed at the system
    prompt: permission stays undecided and nothing is said.
13. Email is the way on where the browser cannot notify, and needs no account — an address and one
    confirmation. Signed in, no confirmation step. Signed out, nothing is sent until the address is
    confirmed from a link in the email, never a code to copy; a link more than 24 hours old has expired.
14. "Alerts" is the word for follow notifications, "the daily edition" for the daily one; never "push".
15. If the policy changes (the cap, the hours, the two-outlet rule), the sentences here change in the same
    pull request.

## Accessibility behaviour

- The explanation is a modal dialog labelled by its title; focus starts on the title, is trapped, and
  returns to the control that opened it. Escape is `Not now`. If the opener no longer exists when the panel
  closes (the confirmation message has gone, the offer was removed, the end block's action was replaced),
  focus goes to that story's Follow control, or to `Change` on the end block. When the panel's body is
  replaced (blocked, email sent), focus moves to the new title.
- `Daily` · `Weekly` · `Off` is a radio group named `Email`, not tabs.
- The email field is `type="email"` with `autocomplete="email"`. Confirming an address is a link in the email,
  never a code to copy.
- While busy a button is `aria-busy` and `aria-disabled`, not `disabled`.
- Switches are `role="switch"`; each sentence is the switch's description.
- The time control is a native `<select>` with the label `Time`; the zone is text, not part of the value.
- `Not now` is a real button: declining is as easy as accepting (India's dark-pattern guidelines).
- The specimen is marked as an example for screen readers (`aria-label="Example notification"`).
- Loading states are announced as loading.

## Needs from the API

| Needs | From |
|---|---|
| A device can be registered with no account; the per-follow switch; the daily time and zone | T-036 |
| The policy the sentences state: two or more outlets, at most 3 a day with the overflow held for the morning, nothing 22:00–07:00 | T-036 |
| Web-push keys | FA-16 |
| A daily email, and a confirmation step for an address typed by a signed-out reader | T-036 / T-053 |

## Decided here

1. **Prism never opens the explanation itself.** It is offered — an offer at the first follow, an action on a
   confirmation message, an action on the end block — and the reader opens it. PLAN §4.3 asks for the
   explanation "at the first follow"; the offer is that ask, and it leaves the reader's page as it was.
2. **Quiet hours and the daily cap are stated, not settings.** They are policy in code (T-036); two more
   controls would be two more things to get wrong at 7 in the morning.
3. **The daily time is offered from 07:00 to 21:30**, so a chosen time can never fall inside quiet hours.
4. **The explanation does not promise "an outlet's own words".** D-18 allows Prism's labelled headline on a
   happening with two or more independent reports, so the sentence says what is always true: an alert is a
   headline and its counts, the daily one is the edition's counts, and neither carries anything else.
5. **Email is the way on where the browser cannot notify**, and needs no account — an address and one
   confirmation.
6. **"Not now" costs the reader nothing** and is never followed by another ask from Prism.

## References

`~/prism-program/design-refs/notifications.md`; design audit §7.2 "Notifications" (`board.md` rows H1, H2, H3,
H4, H5, D3, J2).
