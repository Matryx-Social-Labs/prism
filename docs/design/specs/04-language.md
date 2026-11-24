# 04 · The language step

Built by T-054. Comp: `comps/language.html`.

## Purpose

A reader says once which language Prism should speak to them in, and which languages they read the news in.
These are two different questions with different shapes — one answer, and several — and they are asked
separately. Every language is shown by its own name in its own script.

## Where it lives

- **Onboarding, step 1** (`/onboarding`). It comes first so every later step is read in the chosen language.
  The steps become: your languages · where you are · what you do · what you follow.
- **`/you` · Languages** — the same two questions as two rows, any time.
- **A one-time offer** on an English page when the browser asks for a language Prism speaks.

## Content, in order (the step)

1. StepIndicator: mono `1 of 4`.
2. `Your languages` — h1, record voice, display-l.
3. **Question 1 · `Read Prism in`** (h2, reading voice 600), under a 3px rule. A radio group: one large cell
   per language that has a finished interface — at first `English` and `हिंदी`. Each cell shows the language's
   own name in the record face of its script; the chosen cell has a 2px ink border and a Check. Before the
   cells, as the group's description: `Choosing one changes this page at once.` Under the group in `--ink-3`:
   `The menus and labels. More languages are being added.` The change happens in place and focus stays on the
   chosen control.
   Choosing a language re-renders the step in it at once; nothing waits for `Continue`. The choice replaces
   the address prefix and is stored on the device at that moment, so it survives `Skip for now`, a reload or
   leaving. The grid below does not re-order while the reader is on the step.
   **While only one interface language is finished, question 1 is not drawn** and the step is question 2 alone.
4. **Question 2 · `Read the news in`** (h2), under a 3px rule. In `--ink-3`: `Headlines and quotes appear in
   these languages when an outlet printed them. Choose none to see every language.` Then a grid of checkbox
   cells, one per language Prism reads (13 today; the grid renders the list the app holds, never a number
   written in copy). Each cell: the language's own name large, in the record face of its script; under it,
   small in the reading voice and `--ink-3`, its name in the interface language (left out when the two are the
   same). A checked cell has a 2px ink border and a Check at its top corner.
   - Order: the interface language first, then English, then by the number of outlets Prism reads in each,
     most first (the order `/sources` already uses).
   - Pre-ticked: the interface language, and any language the browser lists (`navigator.languages`) that is
     in the grid. Nothing else. English is not ticked for a reader who did not ask for it.
5. **A footer bar**, fixed to the bottom of the step: the primary button, then `Skip for now`.
   - The primary carries the count: `Continue with {k} languages` · `Continue with 1 language` · with none
     ticked, `Continue with every language`.
   - `Skip for now` leaves onboarding, as it does today, and keeps the defaults: the interface language as
     it stands (whatever the reader chose in question 1, else the address's `/hi/…`, else the browser's if
     Prism speaks it, else English); reading languages, **the interface language alone**.
   - A reader who has never seen the step is treated the same as one who skipped it. "Every language" is
     stored only when a reader presses `Continue with every language`.

## What the choices do

- **Read Prism in** sets the interface: labels, dates through `Intl`, and the address prefix (D-01: `/hi/`).
  Counts stay in Latin digits in every language.
- **Read the news in** decides which original-language headlines and quotes are shown as printed, on a record
  and on a story page:
  - where the same thing exists in a language the reader ticked (an outlet's headline, a quote printed in two
    languages), that one leads;
  - text that exists only in a language the reader did not tick is shown in the interface language, marked as
    a translation, with the original one tap away — **once translation is live** (T-066, through T-018's
    gate). Until then it is shown as printed with its language named, which is today's rule: Prism does not
    hide a quote, and does not show a translation it has not checked;
  - ticking none means no preference: everything is shown as printed. That is why the button says so.
- **The edition is not varied by reading languages.** It is one document per interface language, the same for
  every reader of it (T-038); its quote and headline are chosen for that language when the document is
  written (spec 01).
- A reader is never shown a script they did not choose without being told what it is: the language is always
  named beside it.
- Both are stored in the profile (T-035) and, signed out, on the device.

## States

| State | What the reader sees |
|---|---|
| Loading (the saved choices or the language list have not arrived) | Skeleton cells in the grid's shape; the primary is disabled until they arrive. `Skip for now` works throughout. |
| Default | As above, with the pre-ticked cells. |
| Empty · At the free limit | Do not apply: the grid always has the languages Prism reads, and nothing here is metered. |
| A cell: hover / focus / checked / pressed | `--sunken` ground · the 2px accent focus ring around the cell · 2px ink border and Check · the Button's pressed ground. |
| Interface language changed | The whole step re-renders in it at once (title, questions, the small names, the buttons). The ticks do not change, except that the new interface language becomes ticked. |
| None ticked | The primary reads `Continue with every language`. It is never disabled. |
| Busy | The primary reads `Saving…`, disabled. |
| Could not save | An error alert above the buttons: `That did not save. Try again.` The choices stay as set. |
| Signed out | The same step; stored on the device and in the address prefix. |
| Returning to the step | It shows what was last saved, not the defaults. |
| Urdu | Its name carries `lang="ur"` and `dir="rtl"` (on the name, not the cell, so the Check and the second line keep their side), set in Nastaliq with the taller line it needs; the cell does not clip the script's descenders. |
| A language added to Prism later | It appears in the grid with no change to copy; it appears in question 1 only when its interface is finished. |

### `/you` · Languages

Two rows, hairline between, 56px+:
- `Read Prism in` — the current language by its own name; a select of the finished interface languages,
  described by the same sentence (`Choosing one changes this page at once.`). Changing it applies at once and
  moves the reader to the same page under the new prefix, with focus back on the select. Like question 1,
  this row is not drawn while only one interface language is finished.
- `Read the news in` — the ticked languages by their own names, comma-separated (`Every language` when none),
  and `Change`, which opens the grid of question 2 in a Sheet titled `Read the news in`, with `Save` and
  `Cancel`. Closing it any other way (Escape, the scrim, back) is `Cancel`: nothing is stored.

States: `Saving…` replaces the value while it saves; `That did not save. Try again.` under the row on failure.

### The offer

On a page in English, when the browser's first language is one Prism speaks and the reader has made no
language choice: one info alert at the top of the content, in that language — for Hindi, `Prism हिंदी में भी
है।` then the link `हिंदी में पढ़ें` — with a Close button named `Dismiss`. Following the link sets the
interface language and goes to the same page under `/hi/`. Dismissed or followed, it does not return on this
device. It is not shown to crawlers and does not shift layout after first paint (space is taken on the
server when the request's language asks for it).

## Copy

All strings above. The offer's sentence, as the catalogue key every language translates into itself:
`Prism is also in {language}.` · link `Read in {language}` — always shown in the offered language, never in
English. The Hindi strings shown in the comp are illustrations; T-054's catalogue and its native review write
the real ones. Rules for the catalogue that follow from this spec:

- A language is always written by its own name (`हिंदी`, `ಕನ್ನಡ`, `اردو`); the name in the interface language
  is the small second line and is never the only label.
- The words "interface" and "locale" do not appear. The two questions are `Read Prism in` and `Read the news
  in`.
- The count in the button is a count: `2 languages`, `1 language`, `every language`.

## Layout

| | Compact < 600 | Medium 600–1023 | Expanded ≥ 1024 |
|---|---|---|---|
| Chrome | bare: the lockup in a 52 bar; no tabs, no rail | bare | bare |
| Column | full width, gutter 16 | 640 centred | 640 centred |
| Question 1 | cells side by side, equal width, min-height 64 | same | same |
| Question 2 grid | 2 columns, gap 8, cells min-height 64 | 3 columns | 4 columns |
| Footer bar | fixed, paper with a hairline top; the primary takes the free width with `Skip for now` beside it, and the two stack (primary first) when the labels do not fit on one line; the grid has bottom padding equal to the bar so the last row is never covered | fixed; buttons side by side at the column's right | same |
| `/you` rows | value under the label | value at the right | value at the right |

With 13 languages the grid is seven rows on a phone and scrolls a little under question 1; the footer bar
stays in reach.

## Motion

A cell's border and Check change in 140ms. Changing the interface language swaps the text with no animation
(a crossfade between scripts reads as a glitch). Reduced motion: instant.

## Accessibility

- Question 1 is a `<fieldset>` with its question as `<legend>` and real radio inputs; question 2 the same with
  checkboxes. The inputs are visually hidden, the cell is the label, and focus is drawn on the cell.
- Every language name carries its `lang` (and `dir` for Urdu), so a screen reader pronounces it and the right
  face loads. The small second line is in the interface language.
- The primary button's changing count is its text; no live region announces each tick.
- Cells are at least 64px tall and half the column wide: comfortably over the 44px floor in every script.
- `<html lang>` changes with the interface language; pages carry `hreflang` alternates (T-054).

## Primitives

StepIndicator, Button, Checkbox and Radio (as cells), Alert, Sheet, SelectField, Text (script-aware: family
and line height by script — on native this is required). New: `LanguageCell`, `LanguageGrid`.

## Depends on

| Needs | From |
|---|---|
| The list of languages Prism reads, with each one's own name | `web/src/lib/languages.ts` today; the catalogue in `packages/core/i18n` after T-054 |
| Which interface languages are finished | T-054's catalogue |
| The profile fields for both choices; device storage when signed out | T-035 |
| `/hi/` addresses, `hreflang`, `<html lang>` | T-054 (D-01) |
| Translation of what the reader did not tick, labelled | T-054, T-066 (through T-018's gate) |

## Decided here

1. **One step, two questions**, each under its own rule — not two screens. Onboarding stays at four steps,
   and a reader sees that the two answers are different kinds before answering either.
2. **`Read Prism in` offers only finished interfaces**; the grid offers every language Prism reads. Showing
   thirteen interface languages of which eleven fall back to English would promise what does not exist.
3. **No minimum and no forced English.** None ticked means every language, and the button says so. A reader
   who skips or never answers reads in the interface language alone; "every language" is only ever a choice
   the reader made.
4. **Own name large, the interface-language name small** (board E2), in the record face of each script, so a
   reader finds theirs by sight.
5. **The interface language applies at once**, not on `Continue`: the reader checks the result by reading
   the rest of the step in it.
6. **The offer is one line and one time**, never a modal and never a redirect: a reader sent a link keeps the
   page they were sent.

## References

`~/prism-program/design-refs/languages.md`; design audit §7.2 "Onboarding" (`board.md` rows E1, E2, E3, E4,
E5).
