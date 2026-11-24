# Behaviour specs for the new surfaces

Six surfaces Prism does not have yet. Each spec says **what the surface does and says**: its purpose, its
content and the order of it, every state, the exact copy, the rules and policies, and what it needs from the
API. None says how anything looks. The design system is being redesigned from scratch (D-23); these specs are
written to survive any visual direction and are what T-083 draws the screens from.

| # | Surface | Spec | Drawn by | Built by |
|---|---|---|---|---|
| 1 | Today's edition and its end block | [01-edition.md](01-edition.md) | T-083 | T-051 (document: T-038) |
| 2 | Follow, Following, the free limit, "new since you read" | [02-follow.md](02-follow.md) | T-083 | T-050 |
| 3 | The notification explanation and settings | [03-notifications.md](03-notifications.md) | T-083 | T-053 (sending: T-036) |
| 4 | The language step | [04-language.md](04-language.md) | T-083 | T-054 |
| 5 | Navigation at each size class | [05-navigation.md](05-navigation.md) | T-083 | T-042 |
| 6 | The story page's "Where it stands" header | [06-story-header.md](06-story-header.md) | T-083 | T-007, then T-052 |

**Standing.** A spec here is binding on the task that draws the surface and the task that builds it: neither
adds a state, a sentence or a rule the spec does not give, and neither drops one. D-21 delegates sign-off to
the review inside the task that wrote them; the founder reads them and may overrule any line, and work
proceeds meanwhile. Each spec ends with "Decided here": the choices most likely to be questioned, each with
its reason.

## How to read a spec

Every spec has the same sections: purpose · where it appears · content, in order · states · copy · rules ·
accessibility behaviour · needs from the API · decided here · references.

- **Content, in order** is a decision. A screen may group or space it as the visual system likes; it may not
  reorder it, add to it or leave part of it out.
- **Copy** is the exact English sentence, with slots in braces: `{k} outlets`. A slot is filled from live data
  or it is not printed; a spec never supplies a figure. Every counted noun takes its singular (`1 story`,
  `1 outlet`, `1 language`, `your 1 story`), through `Intl` plural rules in every language. A time on the
  reader's current day prints as `{HH:MM}`; on another day, `{Mon HH:MM}`. Where a spec writes `IST` in a
  sentence, the product prints the reader's own zone. Counts stay in Latin digits in every language (D-01).
  Hindi strings are written by T-054's catalogue and reviewed by a native reader, not here.
- **A state the spec lists is required.** A state it does not list does not exist: ask, do not invent.
- **Size classes**, where a spec mentions them, are the programme's (PLAN §4.2): compact < 600 · medium
  600–1023 · expanded 1024–1279 · large 1280–1535 · xlarge ≥ 1536. Specs name a size class only where behaviour
  differs by width.
- **Words for containers are neutral on purpose.** "A panel opens" means something opens that holds the
  listed content; whether it rises from the bottom, sits beside the control or fills the screen is T-083's.
  What the spec fixes is what is in it, whether it blocks the page behind it, how it closes and where focus
  goes.

## What holds on every surface

These are fixed whatever the product comes to look like (D-23), and every spec assumes them:

1. Counts are counted and printed as numbers. Below 30 a share is "3 of 4", never a percentage. A figure not
   yet counted is `—` with `Not counted yet`, never 0.
2. A quote is the exact words, in the language it was printed in, with its speaker, outlet and time — or it
   is absent. A translation says it is one.
3. Nothing Prism writes is shown as fact unless it has been checked against the reports, and it is labelled
   as Prism's.
4. One source versus many is always visible, in words (`One source so far`), never by colour alone. The same
   holds for every state: provisional, no longer current, read, new, current.
5. Nothing on a screen is a placeholder. A section with nothing real to show is absent.
6. How states are announced: a "could not …" or "did not save" message is `role="alert"`; `Saving…`,
   `Following…` and the result that follows are `role="status"`; a loading state with no text is
   `aria-busy="true"` with a visually hidden `Loading`; a busy control is `aria-busy` and `aria-disabled`,
   never `disabled`, so it keeps focus. A focused control is never left hidden under anything fixed to the
   screen.
7. Every script Prism reads carries its `lang` (and `dir` where it runs right to left).
8. Declining is always as easy as accepting, and is not asked again.
9. What a reader has read is kept on their device. It is kept by Prism only for stories they follow, and only
   if they agreed (spec 02).

## For the visual system: what the reviews of the first draft found

The first draft of these specs was drawn on the old visual language and reviewed for accessibility before
the redesign was decided. Four findings were about looks, so they are not in the specs — but the new system
(T-082) must not repeat them:

- A boundary that is the only thing showing a control exists (an unselected option, an unfilled part of a
  progress indicator) needs 3:1 against its ground. The old hairline colour gave 1.3:1.
- "Current" and "not current" in navigation differed by hue alone (1.6:1 between them). A second, non-colour
  difference is required.
- Fading a whole block to show it is no longer current took its secondary text below 4.5:1. Fade nothing
  that must be read; say it in words.
- At 400% zoom (a 320 × 256 viewport) fixed bars took 44% of the height. Nothing may stay fixed when the
  viewport is under about 480 high.

## References and material

- `~/prism-program/design-refs/` — one file per surface (`edition`, `follow`, `notifications`, `languages`,
  `tablet-shell`, `story-header`) on top of `board.md`, the design audit's §7. Structure and interaction
  only.
- `~/prism-program/design-refs/sample-records-2026-11-24.json` — six real records with quotes, one running
  story with its counts, and the list of running stories, as the public API returned them on 2026-11-24 at
  about 17:50 UTC. For drawing screens on real content instead of invented news. A snapshot, not live; the
  story's day count in it is in IST.
