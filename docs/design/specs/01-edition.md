# 01 · Today's edition and its end block

Built by T-051 from the document T-038 writes.

## Purpose

A reader opens Today, reads the day's five to seven most-reported happenings in about three minutes, reaches
"You're up to date", and can stop. The edition is the same for every reader of a language; it is finite, it
says how long it is before the reader starts, and it says when it is over.

## Where it appears

`/feed` (the tab "Today"), above everything else on the page. The chart Prism has today (most reported, by
state, by subject) stays on the same page, one step below the end block, under its own heading. `/` still
sends a returning reader to `/feed`. The explanation of spec 03 is opened from the end block.

## Content, in order

1. **Navigation** for the size class (spec 05), which prints the date where it has a masthead.
2. **Breaking strip — a reserved slot.** If T-021 ships a breaking strip (D-10 is open), it sits here, above
   the edition head, and is outside the edition's count. This spec gives it no design; until T-021, the slot
   is empty and takes no space.
3. **Edition head.**
   - `Today` — the page heading.
   - One provenance line: `{n} stories · about {m} min · updated {HH:MM}`. `{m}` is the reading time the
     edition document carries; when the document has none, the middle fact is left out, not estimated in the
     browser. `updated` is the document's version time, in the reader's zone.
   - Beside that line, once the reader has read at least one item: reading progress, `{k} of {n} read`. It is
     always available as text.
4. **The items, 1 to n**, an ordered list. Each item shows its position, 1 to n. Each item, top to bottom:
   1. **The headline.** It wraps; it is never truncated. It is the link to the record, and the whole item is
      its target. Items the reader has read are marked as read (in words or a mark with a text equivalent,
      never by colour alone).
   2. **Whose headline it is** — one of the four states in "Headline states" below.
   3. **The count, as a sentence**: `Reported by {k} outlets in {l} languages`, then ` · ` and the time of the
      latest report. One language prints `in 1 language`. Directly under it, the split by kind of outlet,
      each part with its count in words. (When T-014 lands and counts become independent origins, the words
      follow T-046's vocabulary; the position does not change.)
   4. **One exact quote**, when the document carries one — only direct speech in the language it was printed
      in; never reported speech and never an outlet's translation: the words inside quotation marks, in the
      language they were printed in; then one provenance line — speaker · role · the language's own name when
      it is not the interface language · outlet · time. No quote in the document: nothing is shown.
   5. **The story it belongs to**, when it belongs to one: `Part of` · the story's name as a link ·
      `{d} developments`, and the Follow control (spec 02). No story: nothing is shown.
5. **The end block:**
   1. `You're up to date`.
   2. `{n} of {n} · updated {HH:MM}`, and, when the reader went from the first item to the end block in one
      sitting of under 15 minutes, ` · {m} min` (measured, whole minutes, "under 1 min" below one). A longer
      or interrupted sitting prints no time.
   3. `Tomorrow's edition is ready at {HH:MM}.` — the hour from the document. Omitted when the document does
      not carry it.
   4. **Your stories** — the per-reader slot (one request; everything above it came from the document).
      Up to three followed stories, moved ones first: the story's name, then `{k} new since you read`, or
      `Nothing new since {day HH:MM}`. Then the link `Following →`. A reader who follows nothing sees one
      line: `Follow a story and its changes appear here.` This slot is not one of the `n` items and does not
      move the count. While its request is in flight it is a loading state with no text; if the request fails
      the slot is left out and nothing is said — the edition is complete without it.
   5. The main action: `Tell me when tomorrow's edition is ready` (opens the explanation in spec 03). Once the
      daily notification or the daily email is on, the action is replaced by the line `You'll be told at
      {HH:MM}.` (the reader's own daily time) and the link `Change`, which opens `/you` · Notifications.
   6. `Share today's edition` — a second action. It is the ShareButton the app has: the system share sheet
      where there is one, otherwise it copies the link to `/feed` and says so in a brief confirmation
      message.
6. **`Everything reported today`** — a heading, then the chart as it is today. Its loading, empty and error
   states are its own and unchanged.

### Headline states (D-18)

| State | When | The headline | The line under it |
|---|---|---|---|
| Prism's | two or more independent reports, and Prism's headline has passed its check (T-018) | Prism's | `Prism's headline, from {k} reports` |
| An outlet's own | one independent report, or before the check exists | the lead outlet's, as printed | `{Outlet}'s headline` |
| An outlet's, in the reader's language | an outlet wrote one in the interface language | that outlet's, as printed | `{Outlet}'s headline` (in the interface language) |
| Translated | no outlet wrote it in the interface language | a translation of the lead outlet's | `Translated from {Language} · {Outlet}'s headline · See the original` — `See the original` swaps the original in, in place; the line then reads `{Outlet}'s headline in {Language} · See the translation` |

Which state an item is in, first match wins: Prism's headline when it exists and has passed its check; else
an outlet's own in the interface language; else Translated, once translation is live; else the lead outlet's
as printed, with the language named. Until T-018 is live the edition shows only the second and third states
and that last fallback.

## States

| State | What the reader is given |
|---|---|
| Loading | The head with a loading state with no text for the provenance line, and five items' worth of loading state with no text. No spinner, no words. It is announced as loading to assistive technology. |
| Ready | As above. |
| Empty — no edition at all (nothing qualified, and no yesterday) | The head, then `No edition today.` and the chart directly below. |
| A quiet day (fewer than five qualified) | The edition prints what there is: `3 stories`, three items, `3 of 3`. Never padded. |
| Not ready yet (before the day's first edition) | A message (not an error): `Today's edition is not ready yet.` / `It is written at {HH:MM}. Yesterday's is below.` Then yesterday's edition under the head `Yesterday · {Mon 23 Nov}`. Its end block says `You're up to date with yesterday`, then `Today's edition is ready at {HH:MM}.` and the action `Tell me when today's edition is ready`; it has no Share, and reaching it is not a finish (T-058 counts only the current day's edition). |
| Error — could not load | An error message: `Today's edition could not load.` with `Try again`. The chart below loads on its own request and still shows. |
| Partly read (returning the same day) | Read items stay marked as read; reading progress and `{k} of {n} read` are restored from the read marks (T-035), on any device when signed in. |
| Finished earlier today | Under the head: `You finished today's edition at {HH:MM}.` and the link `Jump to everything reported today`. The items stay, all marked as read. |
| Changed since the reader read it | A line between the head and item 1: `{k} new since you read · Show`. The list does not reorder until the reader presses `Show`. After `Show`: `n` is the new edition's count; items the reader had read stay marked as read; new items are unread; and "finished" no longer holds if any item is unread — the end block is reached again to finish. |
| Offline (the app; the web has no offline copy yet) | A message (not an error): `You are offline.` / `This is the edition saved at {HH:MM}.` Then the saved edition. On the web, offline is "Could not load". |
| Signed out | Identical. Read marks and follows are kept on the device (T-035). |
| The reader has not agreed to Prism remembering what they read (spec 02, first follow) | Read marks stay on this device and are not sent; the edition works the same on this device and starts unread on another. |
| At the free limit (follow limit) | The Follow control on an item opens the limit panel (spec 02). The edition itself is never metered. |
| A muted subject | Its items are not in the list; `n` is the number shown. No gap, no notice. |

## Copy

Every string is given where it appears above. The rest:

| Where | String |
|---|---|
| Tab and top-bar link | `Today` |
| Share text | `Today on Prism: {n} stories. {lead headline} — {k} outlets, {l} languages.` then the link |
| Name of the list for assistive technology | `Today's edition, {n} stories` |
| Text for assistive technology on a read item | `Read` |

`Record`, `lens` and `coverage` do not appear on this surface (T-046's vocabulary).

## Rules

1. The edition is finite: five to seven items, the same for every reader of a language. A quiet day prints
   what there is and is never padded.
2. The reading time is the document's; the time taken is measured. Either is left out rather than guessed.
3. An item is **read** when its last line has scrolled above the middle of the viewport, or it was opened.
   The edition is **finished** when half of the end block has been on screen for one second (the event T-058
   counts).
4. The time taken to reach the end block is printed only for one sitting of under 15 minutes, in whole
   minutes ("under 1 min" below one); otherwise none.
5. Which headline state an item is in follows the precedence above, first match wins.
6. A quote is direct speech, in the language it was printed in; never reported speech, never an outlet's
   translation. No quote, or no story: nothing is shown in its place.
7. The followed-stories slot is in the end block and outside the count, so "6 of 6" means the same six for
   everyone. It is one request; if it fails, nothing is said.
8. A changed edition is pulled in by the reader (board A3); items never move under the reader's hand.
9. Yesterday's edition stands in before today's is written, labelled as yesterday's; reaching its end is not
   a finish.
10. The breaking strip, when it exists, is above the edition head and outside the count.
11. A muted subject's items are left out; `n` is the number shown; no gap, no notice.
12. Read marks are kept on the device and are sent only when the reader has agreed (spec 02, first follow);
    when signed in they follow the reader to any device.
13. The edition itself is never metered; the Follow control on an item opens the limit panel at the free
    limit.
14. Once the daily notification or the daily email is on, the end block says when the reader will be told,
    and offers `Change`, instead of offering to turn it on.
15. Sharing uses the system share sheet where there is one; otherwise it copies the link to `/feed` and says
    so in a brief confirmation message.
16. The chart below keeps its own loading, empty and error states.

## Accessibility behaviour

- The items are an ordered list with an explicit list role (so the list is announced where the marker is
  hidden); each is an `<article>` whose h2 is the headline link. The position is conveyed by the list.
- `See the original` is a `<button aria-pressed>`; the headline it swaps in carries its `lang` (and `dir`).
- When the reader presses `Show`, focus moves to the first new item's headline.
- `{k} of {n} read` is plain text, not a live region: it must not announce while the reader scrolls.
- The end block is a `<section>` labelled by its heading. Reaching it moves no focus.
- Follow, the story link and the headline are separate tab stops in reading order.
- The split by kind of outlet always has its count in words; a quote in another script carries its `lang`.
- A read item is also marked as read for assistive technology (`Read`).
- Loading states are announced as loading.

## Needs from the API

| Needs | From |
|---|---|
| Per item: headline and whose it is, outlet and language counts, the split by kind of outlet, latest report time, one quote with speaker / role / outlet / time / language, the story's name, slug and development count | T-038's document |
| Reading time, version time, tomorrow's hour | T-038's document (each optional; the line that prints it is omitted without it) |
| Read marks, the followed-stories line | T-035 |
| The Follow control and the limit panel | spec 02, T-050 |
| The explanation | spec 03, T-053 |
| Prism's headline passing a check; translation | T-018; T-054 and T-066 |

## Decided here

1. **The order within an item is: headline, whose headline it is, the count as the sentence `Reported by {k}
   outlets in {l} languages`, one exact quote, the story it belongs to — and reading progress is always shown
   as `{k} of {n} read`.** It is the order a first-time reader needs no key for, and it is the order the
   existing list of the day's reports already uses (the chart's own rows), so the edition and the chart below
   it read alike. Three arrangements were drawn: one opened each item with a count line above the headline,
   one with the headline first and the count as a plain sentence, one with an index of the n headlines before
   the items. The headline-first order read best: what happened, then who reported it in words. An index
   above the items made a phone reader meet every headline twice and pushed the first quote a screen down.
2. **No photographs in the edition.** The chart below keeps its thumbnails. The edition is read to be
   finished, its document has a 150KB ceiling, and the reference phone is a low-end Android. This departs from
   the 2026-09-20 decision (a thumbnail on every story row) for this one list; if the lead should carry its
   credited photograph, that is one optional field in T-038's document and one line here.
3. **The reading time is the document's, the time taken is measured**, and either is left out rather than
   guessed.
4. **The followed-stories slot is in the end block and outside the count**, so "6 of 6" means the same six
   for everyone.
5. **A changed edition is pulled in by the reader** (board A3); items never move under the thumb.
6. **Yesterday's edition stands in before today's is written**, labelled as yesterday's.

## References

`~/prism-program/design-refs/edition.md`; design audit §7.2 "Front page (Today)" (`board.md` rows A1, A3, A4,
B1, B3, J1, J2).
