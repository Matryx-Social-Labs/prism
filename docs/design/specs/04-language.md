# 04 · The language step

Built by T-054.

## Purpose

A reader says once which language Prism should speak to them in, and which languages they read the news in.
These are two different questions with different shapes — one answer, and several — and they are asked
separately. Every language is shown by its own name in its own script, with its name in the interface language
as a second line.

## Where it appears

- **Onboarding, step 1** (`/onboarding`). It comes first so every later step is read in the chosen language.
  The steps become: your languages · where you are · what you do · what you follow.
- **`/you` · Languages** — the same two questions as two rows, any time.
- **A one-time offer** on an English page when the browser asks for a language Prism speaks.

## Content, in order

### The step

1. Step indicator: `1 of 4`.
2. `Your languages` — the heading of the step.
3. **Question 1 · `Read Prism in`.** A radio group: one option per language that has a finished interface — at
   first `English` and `हिंदी`. Each option shows the language's own name in its own script; the chosen option
   is marked as chosen. Before the options, as the group's description: `Choosing one changes this page at
   once.` Under the group: `The menus and labels. More languages are being added.` The change happens in
   place and focus stays on the chosen control.
   Choosing a language re-renders the step in it at once; nothing waits for `Continue`. The choice replaces
   the address prefix and is stored on the device at that moment, so it survives `Skip for now`, a reload or
   leaving. The list of options does not re-order while the reader is on the step.
   **While only one interface language is finished, question 1 is not shown** and the step is question 2
   alone.
4. **Question 2 · `Read the news in`.** Under the question: `Headlines and quotes appear in these languages when
   an outlet printed them. Choose none to see every language.` Then a list of checkbox options, one per
   language Prism reads (13 today; the list is the one the app holds, never a number written in copy). Each
   option: the language's own name in its own script; under it, its name in the interface language (left out
   when the two are the same). A checked option is marked as checked.
   - Order: the interface language first, then English, then by the number of outlets Prism reads in each,
     most first (the order `/sources` already uses).
   - Pre-ticked: the interface language, and any language the browser lists (`navigator.languages`) that is
     in the list. Nothing else. English is not ticked for a reader who did not ask for it.
5. **The actions**, always within reach at the bottom of the step: the main action, then `Skip for now`.
   - The main action carries the count: `Continue with {k} languages` · `Continue with 1 language` · with none
     ticked, `Continue with every language`.
   - `Skip for now` leaves onboarding, as it does today, and keeps the defaults: the interface language as
     it stands (whatever the reader chose in question 1, else the address's `/hi/…`, else the browser's if
     Prism speaks it, else English); reading languages, **the interface language alone**.
   - A reader who has never seen the step is treated the same as one who skipped it. "Every language" is
     stored only when a reader presses `Continue with every language`.

### `/you` · Languages

Two rows:
- `Read Prism in` — the current language by its own name; a select of the finished interface languages,
  described by the same sentence (`Choosing one changes this page at once.`). Changing it applies at once and
  moves the reader to the same page under the new prefix, with focus back on the select. Like question 1,
  this row is not shown while only one interface language is finished.
- `Read the news in` — the ticked languages by their own names, comma-separated (`Every language` when none),
  and `Change`, which opens the list of options of question 2 in a panel titled `Read the news in` that blocks
  the page behind it, with `Save` and `Cancel`. Closing it any other way (Escape, a press outside it, back) is
  `Cancel`: nothing is stored.

States: `Saving…` replaces the value while it saves; `That did not save. Try again.` under the row on failure.

### The offer

On a page in English, when the browser's first language is one Prism speaks and the reader has made no
language choice: one message at the top of the content, in that language — for Hindi, `Prism हिंदी में भी
है।` then the link `हिंदी में पढ़ें` — with a Close button named `Dismiss`. Following the link sets the
interface language and goes to the same page under `/hi/`. Dismissed or followed, it does not return on this
device. It is not shown to crawlers and does not move the page after first paint (the server reserves the
space when the request's language asks for it).

## States

| State | What the reader is given / what happens |
|---|---|
| Empty | Does not apply: the list always has the languages Prism reads. |
| Loading (the saved choices or the language list have not arrived) | A loading state with no text in place of the options, announced as loading to assistive technology; the main action is disabled until they arrive. `Skip for now` works throughout. |
| Default | As above, with the pre-ticked options. |
| Interface language changed | The whole step re-renders in it at once (title, questions, the second-line names, the buttons). The ticks do not change, except that the new interface language becomes ticked. |
| None ticked | The main action reads `Continue with every language`. It is never disabled. |
| Busy | The main action reads `Saving…`, disabled. |
| Error (could not save) | An error message above the buttons: `That did not save. Try again.` The choices stay as set. |
| Signed out | The same step; stored on the device and in the address prefix. |
| At the free limit | Does not apply: nothing here is metered. |
| Returning to the step | It shows what was last saved, not the defaults. |
| Urdu | Its name carries `lang="ur"` and `dir="rtl"` (on the name, not the whole option, so the mark of the choice and the second line keep their side). |
| A language added to Prism later | It appears in the list with no change to copy; it appears in question 1 only when its interface is finished. |

## Copy

All strings above. The offer's sentence, as the catalogue key every language translates into itself:
`Prism is also in {language}.` · link `Read in {language}` — always shown in the offered language, never in
English. The Hindi strings shown in this spec are illustrations; T-054's catalogue and its native review write
the real ones. Rules for the catalogue that follow from this spec:

- A language is always written by its own name (`हिंदी`, `ಕನ್ನಡ`, `اردو`); the name in the interface language
  is the second line and is never the only label.
- The words "interface" and "locale" do not appear. The two questions are `Read Prism in` and `Read the news
  in`.
- The count in the button is a count: `2 languages`, `1 language`, `every language`.

## Rules

1. The two questions are asked in one step, question 1 first. Question 1 offers only languages with a finished
   interface; question 2 offers every language Prism reads.
2. Question 1 (and the `/you` row for it) is not shown while only one interface language is finished.
3. Choosing the interface language applies at once and is stored on the device at that moment; it replaces the
   address prefix. It survives `Skip for now`, a reload or leaving.
4. The order of the reading languages: the interface language first, then English, then by the number of
   outlets Prism reads in each, most first. It does not re-order while the reader is on the step.
5. Pre-ticked: the interface language, and any language in `navigator.languages` that is in the list. Nothing
   else; English is not ticked for a reader who did not ask for it.
6. The main action is `Continue with {k} languages` · `Continue with 1 language` · `Continue with every
   language` (none ticked). With none ticked it is never disabled; while saving it reads `Saving…`, disabled.
7. `Skip for now` leaves onboarding and keeps the defaults: the interface language as it stands (the reader's
   choice in question 1, else the address's `/hi/…`, else the browser's if Prism speaks it, else English), and
   reading languages = the interface language alone. A reader who never saw the step is treated as one who
   skipped it.
8. "Every language" is stored only when a reader presses `Continue with every language`.
9. On failure to save, the choices stay as set and the message `That did not save. Try again.` is shown.
10. Returning to the step shows what was last saved, not the defaults.
11. In the `Read the news in` panel on `/you`, only `Save` stores; Escape, a press outside it and back are
    `Cancel`.
12. The offer is shown only on an English page, when the browser's first language is one Prism speaks and the
    reader has made no language choice; once only per device, whether dismissed or followed; never to
    crawlers; following it sets the interface language and goes to the same page under `/hi/`.
13. A language added later needs no change to copy.

### What the choices do

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

## Accessibility behaviour

- Question 1 is a `<fieldset>` with its question as `<legend>` and real radio inputs; question 2 the same with
  checkboxes. Each option is the label of its input.
- Every language name carries its `lang` (and `dir` for Urdu), so a screen reader pronounces it. The second
  line is in the interface language.
- Changing the interface language in question 1 keeps focus on the chosen control; changing it on `/you` puts
  focus back on the select.
- The main action's changing count is its text; no live region announces each tick.
- The loading state is announced as loading.
- `<html lang>` changes with the interface language; pages carry `hreflang` alternates (T-054).

## Needs from the API

| Needs | From |
|---|---|
| The list of languages Prism reads, with each one's own name | `web/src/lib/languages.ts` today; the catalogue in `packages/core/i18n` after T-054 |
| Which interface languages are finished | T-054's catalogue |
| The profile fields for both choices; device storage when signed out | T-035 |
| `/hi/` addresses, `hreflang`, `<html lang>` | T-054 (D-01) |
| Translation of what the reader did not tick, labelled | T-054, T-066 (through T-018's gate) |

## Decided here

1. **One step, two questions**, kept apart — not two screens. Onboarding stays at four steps, and a reader
   sees that the two answers are different kinds before answering either.
2. **`Read Prism in` offers only finished interfaces**; question 2 offers every language Prism reads. Showing
   thirteen interface languages of which eleven fall back to English would promise what does not exist.
3. **No minimum and no forced English.** None ticked means every language, and the button says so. A reader
   who skips or never answers reads in the interface language alone; "every language" is only ever a choice
   the reader made.
4. **Own name first, the interface-language name second** (board E2), so a reader finds theirs by sight.
5. **The interface language applies at once**, not on `Continue`: the reader checks the result by reading
   the rest of the step in it.
6. **The offer is one line and one time**, never a modal and never a redirect: a reader sent a link keeps the
   page they were sent.

## References

`~/prism-program/design-refs/languages.md`; design audit §7.2 "Onboarding" (`board.md` rows E1, E2, E3, E4,
E5).
