# 00 · Design audit — what is on the screen today, and what goes

2026-11-25 · task T-080 · decision D-23 · audited: the live site `www.readprism.news`, signed out, on
2026-11-25 between 00:35 and 01:00 IST.

This is a verdict on the interface as it is, and the brief the new design system is built from. It proposes
no new look: that is T-081. Nothing in the app was changed.

**The finding in one paragraph.** The founder's judgement holds, and it is larger than lines. The first
screen of Today carries 39 pieces of text in 18 type styles and 20 controls before a reader reaches a
headline; a record prints the same count five to eight times; a running story opens on 18 chips and its
oldest entry out of 5,695. Four independent design critiques, working only from screenshots, could not say
what the coloured bar under every card means, what "Verified" verifies, or what "Has a professional read"
is. The decoration the founder named is real but sits lower than the first screen: no hatching is drawn on
any page measured, and no dashed line is on the first screen of Today, the lead record or the
story. Dashed lines start below it (48 on Today's page, 71 on Search's) and in the code the dashed line
carries twelve different meanings. What clutters the first screen is repetition, small grey text, and
controls nobody asked for. **The redesign starts by removing those.**

## 1. How this was done

| Step | What | Where the evidence is |
|---|---|---|
| Capture | 88 screenshots of every reader route at 390×844 and 1440×900, plus 768×1024 for Today, a record and a story; dark theme; Hindi, Kannada and Urdu records; a one-outlet record; a record with three lens readings | names and exact addresses in [`audit-data/capture-log.md`](audit-data/capture-log.md); the 18 shots this document cites are in [`audit-shots/`](audit-shots/) |
| Count | A script counts what is visible on the first screen: text, controls, pictures, type styles, colours, kinds of line, pinned bars | [`audit-data/measure.js`](audit-data/measure.js) → [`counts.json`](audit-data/counts.json), 12 runs |
| Accessibility | A second script measures contrast, text size and target size on nine first screens | [`audit-data/a11y.js`](audit-data/a11y.js) → [`a11y.json`](audit-data/a11y.json) |
| Census | Every word a reader must learn, and every line and ornament device in `web/src`, counted | [`audit-data/census.md`](audit-data/census.md) |
| Five critiques | Five fresh reviewers, each with one method (`impeccable`, `design-taste-frontend`, `emil-design-eng`, `make-interfaces-feel-better`, an accessibility audit), given the screenshots and nothing else: no code, no DESIGN.md, no earlier findings. Each first wrote down what every device seemed to mean (the **cold read**) | [`audit-data/critiques/`](audit-data/critiques/) |
| References | 37 Mobbin searches across two files: how leading reading products show the same information, and what they leave out | `~/prism-program/design-refs/board.md` (rows A1–L6) and `audit-subtraction.md` (rows 1.1–14.4) |

**The rule for a finding.** A clutter finding stands when at least three of the four design critiques reached
it independently. An accessibility finding stands on its own when it is measured against a fixed constraint
(AA contrast, 44 px targets, state never by colour alone). What only one critique saw is in the appendix.

**Limits.** Signed-in states were not captured (there is no test account on production), so Following and You
are judged signed out. Mobbin holds iOS and web only: nothing here is evidence for Android or tablet
patterns. The scripts see only the first screen; text over photographs, borders' contrast, and everything
lower on the page were judged by eye. The live site changes by the minute, so a count in one screenshot can
differ from another taken minutes later; where this document says two numbers disagree, both are in the same
screenshot or the difference is too large to be timing.

## 2. The baseline — the numbers the new design must beat

First screen at 390×844, light theme, not scrolled. Measured by `measure.js` and `a11y.js`
(2026-11-24 19:21 UTC); the rows marked *by eye* are the range across the four design critiques.

| | Today | A record | A running story |
|---|---|---|---|
| Pieces of text | 39 | 39 | 47 |
| Controls (things to tap) | 20 | 25 | 14 |
| Pictures (photos, logos, icons) | 13 | 28 | 3 |
| Type styles (family × size × weight × case) | 18 | 16 | 11 |
| Font sizes | 13 | 12 | 9 |
| Pieces of text in monospace | 14 | 5 | 18 |
| Text under 12 px | 19 of 39 | 11 of 39 | 17 of 47 |
| Smallest text | 9.5 px | 10.5 px | 11 px |
| Text colours · fill colours | 4 · 9 | 6 · 9 | 4 · 6 |
| Targets under 44 px | 7 | 4 | 13 |
| Pinned bars, share of the screen | 110 px, 13% | 161 px, 19% | 52 px, 6% |
| Things competing for attention, *by eye* | 14–17 | 17–20 | 9 groups to 27 items (18 chips) |
| Meta lines (small grey lines of facts), *by eye* | 5–6 | 4–6 | 4–5 |
| Kinds of line and border, *by eye* | 7–9 | 8–10 | 5–6 |
| Where the first headline starts, *by eye* | 65% down | 58% down | title at 15%; first entry at 91% |
| Length of the whole page | 12 screens | 25 screens | 697 screens |

Across the whole product (code census): **33** font sizes, 14 of them half-pixel steps between 11 and
16.5 px · **150** colour properties · **7** families of pill, badge and chip, plus 14 one-off pills ·
**14** pinned or floating bars and overlays · dashed borders on 76 lines in 29 files, carrying **12**
meanings · 3 px rules in 25 places, the section heading that draws one used 51 times · about **32** product
terms a newcomer must learn, in 10 groups where one word means several things or several words mean one.

Accessibility, nine first screens: text contrast passes AA everywhere except one chip count (2.94:1, the
"5695" inside the selected chip on the story page). **52** targets are under 44 px; 37 of those are 32–42 px
tall chips and pills, which pass WCAG's 24 px minimum and fail only the 44 px house rule. On the record,
161 of 844 px is pinned, and text scrolls sliced under the tab strip.

*Trap for T-081:* use the script's **kinds** of line, not its per-kind totals; the "solid 2 px" totals look
too high and may include borders drawn in the background colour.

## 3. The ten worst problems

Ordered by how much of the product they spoil. "4 of 4" is the number of design critiques that reached the
finding on their own.

### 3.1 A running story never says where the story stands
<img src="audit-shots/story-390.png" width="250" alt="Story page at 390: a title, one sentence about process, 18 chips, then the first entry from 23 September">

The page opens with a sentence about Prism's process ("Each development was checked against this story
before it joined"), ten filter chips, eight name chips under the word "Following" (the reader is signed out
and follows nobody), and then entry one of 5,695, dated 23 September, oldest first. There is no summary and
today's news is 697 screens away. **4 of 4, critical in three.** T-007 is fixing the order on the live page;
the behaviour is specified in [`../specs/06-story-header.md`](../specs/06-story-header.md). The design still
has to make "what is this, and what is the latest" the first screen.

### 3.2 The coloured bar under every card means nothing to a new reader
<img src="audit-shots/search-390.png" width="250" alt="Search results at 390: each card ends with a short orange bar beside '1 outlet' or '2 outlets'">

All four design critiques wrote "no idea" for the navy-and-orange bar; three guessed a political or party
split, which is the one thing Prism must never appear to rate. Its key is on no card: it is printed inside a
record's Coverage section, on the desktop story page and on the About page. It has a fixed length, so it shows no quantity; at one
outlet it is a full bar of one colour; in dark the two colours are near-equal in lightness, so the split
rests on hue alone (fails 1.4.1). On the Stories list the same slot holds an identical grey bar on every
row, which is decoration. **4 of 4, plus accessibility.**

### 3.3 One count is printed five to eight times on a record
<img src="audit-shots/record-single-390.png" width="250" alt="A one-outlet record at 390: 'from 1 report', three tiles each reading 1, a one-colour bar, '1 of 41 monitored outlets', '1 report', 'the 1 report below', 'Ask · 1 report'">

On the lead record "11 reports" appears in the byline, a tile, the grey line under the bar, the brief's
note, the pinned button and, on desktop, twice more in the side rails
([`record-1440.png`](audit-shots/record-1440.png)). On a one-outlet record the screen says "1" eight times.
The three tiles borrow a button's outline and look tappable; they are not. **4 of 4.**

### 3.4 Today asks for about ten decisions before the first headline
<img src="audit-shots/today-390.png" width="250" alt="Today at 390: a count line, a 'For you' pill, a day strip with numbers, a chip row with a floating pill over it, then the lead photo; the headline starts 65% down">

Five rows sit above the lead: a count line, "For you · pick subjects →", a strip of days with bare numbers,
a row of subject chips, and a floating pill. The headline starts 65% of the way down. The numbers puzzle
rather than inform: "60+ records" beside "Yesterday 467", and "60+ records" above a chip reading "All
stories 60". All four critiques counted 14 to 17 things competing on this screen; one rated it critical.
The behaviour that replaces it is in [`../specs/01-edition.md`](../specs/01-edition.md): a short, finishable
edition.

### 3.5 One feature has five names, a pill that hides other controls, and a switch with one option
<img src="audit-shots/record-390-y2.png" width="250" alt="A record at 390, scrolled: 'Read it as' beside a single button 'Reader'; text sliced under the tab strip"> <img src="audit-shots/record-lens-390-on.png" width="250" alt="A record with three readings: Reader, Cyber, Markets, with Markets selected">

"Has a professional read", "Markets read", "Read it as", "Reads as" and "lens" are one feature. All four
critiques wrote "no idea" for "Has a professional read", and the pill is pinned over the chip row, cutting
"Politics 23" in half at every width and in both themes. On most records "Read it as" offers one choice,
"Reader": a switch with nothing to switch to. Where three readings exist (second shot) the control is
understandable. **4 of 4, plus accessibility (one control covers another).**

### 3.6 "Verified" is on every row, so it tells a reader nothing
<img src="audit-shots/stories-390.png" width="250" alt="The Stories list at 390: every row has a black 'Verified' badge and an identical grey bar">

The black badge is the heaviest thing on each row and it is on every row, in two wordings ("Verified",
"Verified record"). No screen says who verified what. Meanwhile the thing a reader does need is missing:
the list says "23 moving now" and marks no row as moving or settled, which the product's own rule requires
in words. **3 of 4 for removing the badge from lists; the missing state is an accessibility finding.**

### 3.7 On a phone, a record shows a photo gallery before the headline and keeps 19% of the screen pinned
<img src="audit-shots/record-390.png" width="250" alt="A record at 390: tab strip, photo with arrows and a counter, caption, link, thumbnail strip, then the headline at 58% down, and a pinned Ask and Share bar cutting three tiles">

Seven controls come before the headline: two arrows over the faces in the photo, a counter, a credit, "Their
report", and a strip of thumbnails. Three bars are pinned at once: the header, a seven-item tab strip that
clips its fourth label ("How it unfolde"), and Ask and Share. Together they hold 161 px, and the bottom bar
cuts the tiles in half. One reviewer counted "Ask" four times on one screen. Desktop already leads with the headline.
**4 of 4, plus accessibility (2.4.11).**

### 3.8 Four nouns for one news item, and numbers that disagree
<img src="audit-shots/story-1440.png" width="520" alt="Story page at 1440: '31 outlets' in the header and under the bar, 'Who reported it · 47' beside it">

A reader meets *record*, *story*, *development* and *report* for news items, and *outlets*, *sources* and
*reports* for who published them; "record" alone means five things (the product, one page, a row, a day, a
search result). Numbers that should match do not: "31 outlets" beside "Who reported it · 47" in one
screenshot; "63 days" on the story and "53 days" for the same story in the list; "24 outlets" at the top of
Today and "25" at its foot. A product whose promise is counting cannot print two counts for one thing.
**On the words: a finding in 2 of 4, a guess at "record" in all four cold reads, and the census. On the
numbers: 3 of 4.** The word list is in §7.

### 3.9 Half the text on a first screen is small grey facts
On Today, 19 of 39 pieces of text are under 12 px, down to 9.5 px; on the Stories list, 26 of 50. Each
screen carries four to six grey meta lines, most in monospace, and monospace is also used for whole
sentences ("most-reported first", "one source so far"). Language codes ("EN·HI·OR") were a guess for every
critic. Dots strand at line ends when a line wraps. **3 of 4, plus accessibility (text size).**
See [`today-390.png`](audit-shots/today-390.png) and [`today-390-dark.png`](audit-shots/today-390-dark.png).

### 3.10 The same shape and the same line mean many things
<img src="audit-shots/today-390-end.png" width="250" alt="The end of Today at 390: two dashed-bordered cards, each with a one-colour bar, '1 outlet' and 'one source so far'">

A dashed border means one source here. Elsewhere it means provisional, unverified, reported speech, an empty
state, something not open yet, the founding plan, a refunded payment, an unreachable feed, a limit reached, a
disabled field and a day not counted: twelve meanings in the code. A one-source card stacks four signals
for one fact (dashed frame, one-colour bar, "1 outlet", "one source so far"), and where such cards run
together they read as placeholders. The white rounded rectangle is likewise a filter, a name link, a
figure tile, a mode switch and a button, so a reader cannot tell what is tappable. **2 of 4 on each, and
the census; this is also the founder's own complaint.**

## 4. The ledger — every recurring device, with a verdict

**Understood cold** is the cold read of the four design critiques (and the accessibility reviewer where
noted): *sure*, *guess* or *no idea*. **Verdict:** keep · simplify · merge · remove. References are rows in
`design-refs/board.md` (A1–L6) and `design-refs/audit-subtraction.md` (1.1–14.4).

| # | Device (where, how many) | The job it does for a reader | Understood cold | What calm products do instead | Verdict and reason |
|---|---|---|---|---|---|
| 1 | **3 px ink rule** above sections and on the lead card (25 places; the section heading used 51 times) | "A section starts here" | guess ×3, sure ×1; on the lead card "lead?" | Whitespace separates; one hairline or one heavy rule per page at most (12.1, 12.2); NYT settings use one heavy rule per section and no hairlines between rows (5.2) | **Simplify.** A heading and space already start a section. One meaning only; off the lead card |
| 2 | **Dashed border** (76 lines, 29 files, 12 meanings; none on the first screen of Today, record or story; 48 on Today's page, 71 on Search's) | "One source so far" | Not on a first screen, so not cold-read. Where critics met it with its words, three called it the right idea | State is a word plus a time: "LIVE 30m ago", "The End" (9.1, 9.2). **No reference found** for a one-source label in any news product | **Simplify.** The state stays and is said in words (fixed). At most one meaning for any line form, always beside its words; the other eleven uses go. Whether a line form survives at all is T-081's |
| 3 | **Dotted line** (5 lines: the route map and status grid on `/about`) | "Not built yet" | Not seen on a reader page | Onboarding is one card and one promise (6.3, E6) | **Remove.** It reports the state of the product, not of the news |
| 4 | **Hatching** (7 definitions, 3 uses: days not counted in a chart and the archive, the wire segment of the bar; none drawn on any page measured) | "Prism was not reading that day" | Not seen | An empty state says its window in words (K3) | **Merge** into the words "Not counted", which are already printed beside it. The wire hatch goes with the bar |
| 5 | **Coverage bar**, navy and orange, on every card, record and story | Which kinds of outlet carry the story | no idea ×4 | A count and a time as one line: "13 ARTICLES · 4 HR AGO" (8.1, 8.2, A4); where a split is drawn, the count heads it and the bar is secondary (8.3); a split with labelled segments only inside the story (C5) | **Remove** from cards and rows. In one place inside a record, the split by kind of outlet is said in words with its counts; its form is open. Never drawn at one outlet. Problem 3.2 |
| 6 | **Grey bar** under each title on the Stories list | None: it is the same on every row | read as decoration ×4 | Count as an eyebrow (8.2) | **Remove** |
| 7 | **Outlet-logo stack** "+6" on cards and records | Which outlets | sure ×4 that outlets are meant; logos are 16–22 px and unnamed, so not which | No logos on the card; the count is the credential (8.1). Who reported is a plain list with names (8.4) | **Merge** into the one count line. Logos stay only beside an outlet's name |
| 8 | **Language codes** "EN·HI·OR" on card meta lines | Which languages reported it | guess ×4 ("OR is Odia?") | Languages by their own names (E2) | **Remove** from rows; "in 3 languages" where it matters, names inside the record |
| 9 | **Monospace meta lines and uppercase eyebrows** (14 mono items on Today's first screen; 4–6 meta lines a screen; eyebrow class on 48 lines) | Time, counts, where a fact came from | "this is data, but used for sentences too" | One meta line per row, two items (1.1, 1.2, 1.3, 4.1) | **Simplify.** One meta line per row, at most two items, 12 px or more, never a sentence in monospace. Whether monospace survives is T-081's. Problem 3.9 |
| 10 | **Stat tiles** (9 · 3 · 11) on a record | Outlets, languages, reports | guess ×3, no idea ×1; "look tappable" | One number, one sentence (12.3); the count heads the section (8.3) | **Remove.** The line beneath them already says it. Problem 3.3 |
| 11 | **Status pills**: "Verified record", "Verified", provisional, single, corrected (9 components) | The state of a record or story | no idea ×2, guess ×2 for "Verified" | A state is a word and appears only when true (9.1, 9.2, 1.2) | **Simplify.** No badge for the normal state. Words for the exceptions (one source, not yet confirmed as one story, corrected) and for moving or settled. Problem 3.6 |
| 12 | **Chip rows**: subjects with counts on Today and Search, 10 kinds and 8 names on a story (59 uses in about 30 files) | Filter the list | sure ×3 for subject chips; guess for "The event 1969"; no idea ×4 for "Following" | One "Filter by" control (10.1–10.4); or text tabs for kinds (4.2, 4.4) | **Simplify.** At most one row a screen, never wrapping; a story's kinds behind one control; the name chips merge with "who is in it" |
| 13 | **"Has a professional read" toggle** on Today | Show only items with a specialist reading | no idea ×4 | An affordance appears on the row it is true for (1.2) | **Remove** from the first screen. Problem 3.5 |
| 14 | **Day tabs with bare numbers** on Today | Move to another day | guess ×4; the numbers contradict the line above | One text control or a dated heading reaches any date (11.1–11.3); the date is the masthead (A2) | **Simplify.** One way to reach another day; no bare number. The archive calendar already does this well |
| 15 | **Photo deck and thumbnail strip** on a record (arrows, counter, credit, link, 8 thumbnails) | See the outlets' photographs | sure ×2, guess ×2 | Photograph under the headline and summary, with its credit (2.3); a small thumbnail on a list row; none on a timeline entry | **Simplify.** Headline first; one credited photograph; the rest on request. Problem 3.7 |
| 16 | **Section tabs** on a record (seven, pinned, clipped on a phone) | Jump within the page | guess ×4 | While reading, the chrome is one control (2.1, 2.2) | **Remove** as a pinned bar on a phone. "What changed" is the list of reports again: **merge** it with who reported it |
| 17 | **Ask and Share bar**, pinned on a record | Ask a question of the reports; share | guess ×4 for "Ask · 11 reports" | One action surface, never two (14.1–14.3; 14.4 is the counter-example); a single floating Ask (C7) | **Simplify.** One action surface on a record; Ask offered once, with no count on the button |
| 18 | **Lens switch** "Read it as" | Read the same reports for a profession | no idea ×4 at one option; understood at three | Two modes are one pill; three or four are text tabs (13.1–13.3) | **Simplify.** Shown only when a second reading exists; one name everywhere. Whether the lens flip survives is T-081's |
| 19 | **Header's right slot**: the date, a clock, or the page's own name in capitals (6 routes) | None on five of the six | read as an echo ×4 | The date is the title, once (A2) | **Remove**, except the date on Today |
| 20 | **Footers**: the site footer (two groups, 15 links, hidden inside the app on a phone); the end blocks of Today and a record | The legal pages; "you have finished" | The end block was read correctly | "You're caught up" as a closing block (B1) | **Keep.** The end block is one of the best things on the site. Retitle the group "The record" (§7) |
| 21 | **Bottom tab bar** (5 tabs, see-through; absent on record and story; "Watchlist", with Pulse behind it) | Reach the five destinations | sure ×2, guess ×1 for the blue tick | Four or five tabs with an icon and a word (L1, L2) | **Simplify.** Opaque, so no page text shows through it; the five fixed names; leaf pages as [`../specs/05-navigation.md`](../specs/05-navigation.md) says |
| 22 | **"For you · pick subjects →"** pill on Today | Personalise | guess ×3 | Ask later, in context (6.1, H3) | **Remove** from the first screen; it lives in You and in onboarding |
| 23 | **Timeline rail** (dot, time, headline, "1 source") | Order of events | sure ×4 | A time gutter and one line per entry (3.1–3.4, C3); newest first (C4) | **Keep** the idea, newest first, one page at a time |
| 24 | **Quote cards** and their actions | The exact words, who said them, where | understood | — | **Keep** the quote. **Simplify** its four small text actions (about 14–17 px tall, 8–12 px apart) to targets of 44 px |
| 25 | **Report rows** (logo, outlet, time, headline in its own script, [n]) | One outlet's report | understood | A plain list of who reported (8.4) | **Keep** |

## 5. What is good and must survive

Agreed by at least three of the five reviewers unless marked.

1. **The headline wins.** A serif headline over plain sans text, and one blue kept for actions.
2. **One source is said in words.** "One source so far" beside the item: state without colour.
3. **Quotes.** The exact words, the speaker and role, the outlet, and the rule printed above them: "Only
   words found exactly in the article are shown." Reported speech is upright and labelled, never styled as
   a quote ([`record-390-quotes.png`](audit-shots/record-390-quotes.png),
   [`record-ur-390-y2.png`](audit-shots/record-ur-390-y2.png)).
4. **The report row**: outlet, time, the headline in the language it was printed in, and its number
   ([`record-390-coverage.png`](audit-shots/record-390-coverage.png)).
5. **Plain statements of who wrote what**: "Headline by Prism · from 11 reports", "Written by software from
   the 11 reports below". Cold readers were sure what these mean.
6. **Honest empty and blank states, with real numbers and no filler**: the archive calendar with a count in
   each day, blank search offering names and top stories
   ([`archive-390.png`](audit-shots/archive-390.png), [`search-blank-390.png`](audit-shots/search-blank-390.png)).
7. **An ending.** "That's today's record", with one next step
   ([`today-390-end.png`](audit-shots/today-390-end.png)). *(Two reviewers, and reference B1.)*
8. **Onboarding**: one question a step, every step skippable, no account
   ([`onboarding-390.png`](audit-shots/onboarding-390.png)). *(Two reviewers.)*
9. **The denominator sentence**: "9 of 41 monitored outlets · checked 4m ago" was read correctly; a count is
   printed beside every bar. *(Two reviewers.)*
10. **Text contrast** already passes AA on every measured first screen but one chip count.
11. **The timeline as a form**: a time, a line, a headline. Everyone read it correctly.

## 6. Subtraction targets

Every direction in T-081 is scored against these with the same script, at 390×844, not scrolled.

| Measure | Today | Target |
|---|---|---|
| Pieces of text on Today's first screen | 39 | 20 or fewer |
| Controls on Today's first screen | 20 | 10 or fewer |
| Type styles on any first screen | 18 · 16 · 11 | 6 or fewer |
| Font sizes on any first screen | 13 · 12 · 9 | 5 or fewer |
| Font sizes in the whole scale | 33 | 8 or fewer, no half-pixel steps |
| Where the first headline starts (Today, record) | 65% · 58% down | in the top 40% |
| A running story's first screen | 18 chips; first entry is the oldest | says what the story is and its latest entry; 5 chips or fewer |
| Meta lines per row | up to 3 | 1, with at most 2 items |
| Times one count is printed on a screen | 5–8 | 1 |
| Ways to show how widely something was reported | 5 (logo stack, bar, tiles, count line, language codes) | 1, in words and numbers |
| Kinds of line in the whole product | solid at 1, 2 and 3 px, dashed, dotted, hatched | 2 or fewer |
| Meanings of any one line form or shape | 12 (dashed) · 5 (rounded rectangle) | 1 |
| Hatching · dotted lines | 3 uses · 5 | 0 · 0 |
| Chip rows on a screen | up to 4 wrapped rows | 1 or fewer, not wrapping |
| Families of pill, badge and chip | 7, plus 14 one-offs | 2 or fewer |
| Pinned bars | up to 3 at once, 19% of 844 px, see-through | 1 action surface; 15% or less of 360×640; opaque |
| Text under 12 px | 19 of 39 | 0 |
| Targets under 44 px, or closer than 8 px | 52 on nine screens | 0 |
| Names for one thing | 5 for the lens; 4 for a news item | 1 each (§7) |
| Pairs of numbers that disagree on one page | 3 found | 0: one definition per number |
| States shown by hue alone | the coverage bar | 0; each passes in a greyscale screenshot, in both themes |

## 7. Words — what a newcomer must learn today, and the plain replacement

T-046 applies these. The census found about 32 product terms; the ones a general reader meets are below.
Professional readings may keep their own vocabulary inside the reading.

**Four nouns, one meaning each** (recommended; T-046 confirms):
*story* — something that runs over days · *development* — one thing that happened, as one entry in a story
· *report* — one article by one outlet · *outlet* — a publisher. In a list a single item needs no noun: the
count is "60 today".

| Today's word or phrase | What a newcomer makes of it | Plain replacement |
|---|---|---|
| record · the record · Records · Today's record · The record for 24 Nov | five meanings; "a news item?" | No noun for a single item. "Today", "24 Nov", "Results". Not used for the product in running labels |
| Verified · Verified record | "verified by whom?" | Removed as a badge. Say the fact: "Reported by 9 outlets" |
| verified quote | a third meaning of "verified" | "Exact words" |
| Provisional grouping · Grouping under review · Grouping provisional · Related reporting | one state, four strings | One string: "Not yet confirmed as one story" |
| Single source · not yet corroborated · one source so far | "corroborated" is never explained | "One source so far" (the specs' fixed string) |
| lens · professional read · Markets read · Read it as · Reads as | no idea | "A closer reading"; "Markets reading", "Cyber reading"; the control is "Read as" |
| The brief | understood with its note | "Summary", keeping "Written by software from the 11 reports below" |
| Prism's reading · Headline by Prism · Headline as filed by {outlet} | "as filed" is unclear | "Headline written by Prism from 11 reports" · "Headline from {outlet}" |
| Coverage · coverage bar | a section, a bar and a concept | "Who reported it" (already used on the story page) |
| monitored outlets · denominator | jargon | "9 of the 41 outlets Prism reads" · "out of how many" |
| source · sources (an outlet, an article, or a feed) | three meanings | "outlet" for a publisher, "report" for an article; kept only in "One source so far" |
| wire | not defined | "news agency" |
| What changed | promises a comparison, lists the reports | "Latest reports", merged with "Who reported it" |
| developments · All developments · How it unfolded · How this story unfolded | one list, four labels | Count noun "developments"; one heading, "How it unfolded" |
| The event · Investigation · Response … (unlabelled chips) | "The event" is a guess | Label the control "Show"; "The event" becomes "What happened" |
| Following + name chips on a story | no idea (signed out) | "Who is in it" |
| main line · branches · cast | internal | Not shown. "People and organisations named" |
| Stories · Developing stories · Developing over days · Stories developing over days | one thing, four labels | "Stories"; one sub-heading, "Stories that run for days" |
| Watchlist · signals · your signals · follows | one feature, three words | "Following" (the fixed destination) |
| Pulse · Market Pulse · Market pulse · The read | three spellings | "Markets" · "Summary" |
| most-reported first · Most reported | reads like "most clicked" | "Reported by the most outlets first" |
| EN·HI·OR | a guess | "in 3 languages"; inside a record, "Hindi, English, Odia" |
| Ask this story · Ask the record · Ask · Dig deeper · Not in sources · Limit | one feature, four names | "Ask about this story" · "Not in the reports" · "Daily limit reached" |
| reported (on a quote) · translation | easily missed | "Reported, not a direct quote" · "Translated" |
| On X · First on X · Signal, not coverage · Heard on | "signal" is internal | "Posts on X" · "Posts, not news reports" · "From podcasts" |
| Not counted · not read · Not read yet | one state, three phrasings | "Not counted" |
| quiet since 24 Nov 14:22 | unexplained | Removed with the header slot; if kept, "Nothing new since 14:22" |
| Scope · National | internal | "Where": "All India" or the state's name |
| Hub · Sector · Subject · Entity | page types | "Subject"; a person, organisation or place by its name |
| catalyst · tickers · KEV · CVSS · CVE · PoC · GRC | professional terms shown to everyone | Only inside a closer reading, never on a general row or chip |
| "Each development was checked against this story before it joined." | no idea | Removed from the header; the summary takes its place |
| "free box rests" (Plus page) · "30 d" | unreadable | Rewrite in full words; "30 days" |

## 8. The brief for T-081

**The task.** Three directions that each remove what §3 and §4 condemn, meet every target in §6, and keep
everything in §5. Each is scored with `audit-data/measure.js` on the same four screens.

### Principles
1. **Subtract first.** The default answer to "should this element be here?" is no. An element stays when a
   first-time reader can say what it means without a key: run the cold read on every new device.
2. **A number is printed once**, in words and digits, with one definition wherever it appears.
3. **Words carry state.** One source, not yet confirmed, moving, settled, corrected: each is a word. Form
   may repeat what the word says; it never replaces it, and one form never means two things.
4. **The headline first, and the latest first.** On every screen the reader's answer comes before Prism's
   controls: the headline before the photograph, where a story stands before its history.
5. **One of each**: one meta line a row, one chip row a screen, one action surface, one name for a thing,
   one way to show how widely something was reported.
6. **Whitespace before lines.** A line is used when space cannot do the job.
7. **Thirteen scripts are first-class.** Sizes, line heights and direction are set per script, not inherited
   from Latin.
8. **Dark is designed, not inverted.** One reviewer's reading of today's dark theme: it loses the paper's
   warmth, turns three devices louder than the headline, and lets borders vanish (appendix A). Each direction
   is drawn in both themes regardless.

### Fixed — the product, not the style
- The name Prism; the wordmark is the address `readPrism.news`. How it is drawn is open.
- Counts are counted and printed as numbers; below 30 a share is "3 of 4". Quotes are verbatim or absent.
  Nothing Prism writes is shown as fact unless checked, and it is labelled as Prism's. No outlet or tone
  ratings, and nothing that can be read as one.
- One source versus many, and settled versus still moving, are visible **in words**, never by colour alone.
- Thirteen languages and their scripts, Urdu right to left. The low-end Android budget. Reduced motion.
- The five destinations: Today · Stories · Search · Following · You; the reader loop in the programme plan.
- The behaviour in [`../specs/`](../specs/) (the edition, follow, notifications, language, navigation, the
  story header): what each surface contains and says is decided; how it looks is not.

### Accessibility constraints, as numbers
1. Targets at least 44×44 px and 8 px apart, at 360×640.
2. Text at least 4.5:1 (large text 3:1) in both themes, sampled over photographs and blur.
3. No text under 12 px.
4. Every state passes in a greyscale screenshot, in both themes, and has a word.
5. Lines that carry state, and control borders, at least 3:1.
6. Pinned chrome at most 15% of 360×640, opaque, and none at 200% zoom.
7. Line height at least 1.6 for Indic scripts and 1.8 for Urdu; no clipped glyph in any of the 13 scripts.
8. Italics on Latin text only.
9. Urdu blocks start-aligned, with arrows mirrored.
10. With reduced motion: no moving transition and no auto-advance.

### Open — decide on merit
Palette; typefaces; the mark's drawing; every line and rule; whether any dashed form survives; whether
monospace survives; how the split by kind of outlet is shown inside a record; how a closer reading looks and
whether the lens flip survives; density; rows or cards; photographs; chips and tabs; the landing page; the
character of dark.

### What each direction must answer, on the same screens
| Question | Why it is asked |
|---|---|
| How is "reported by k outlets in l languages" shown on a row, once? | Problems 3.2, 3.3; ledger 5, 7, 8, 10 |
| How does a reader tell one source from many, and moving from settled, in a greyscale screenshot? | Fixed; problem 3.6; no reference exists for the one-source label, so this is original work |
| What is on Today's first screen, and where does the first headline start? | Problem 3.4; `specs/01-edition.md` |
| The edition's lead item **with and without** a credited photograph | The founder's request (answered request for T-047); settled with D-24 |
| What is on a story's first screen? | Problem 3.1; `specs/06-story-header.md` |
| What is on a record's first screen on a phone, and what is pinned? | Problem 3.7 |
| How does a closer reading appear when there is one, and when there is none? | Problem 3.5 |
| What separates sections, and how many kinds of line exist? | Ledger 1–4 |
| What does dark look like as its own design? | Appendix A |

### Worst-case content every direction is tested with
A long Indian-language outlet name in a report row and on a photograph's credit; a count over 99 and a story
of 5,695 developments; a one-outlet record (today the heaviest treatment on the site); a 40-word headline
(no clamp exists today); a row in Urdu among Latin rows; Odia and Devanagari headlines on two lines; a
record with no photograph; a signed-out reader on Following.

### Inputs
- Real records for the screens: `~/prism-program/design-refs/sample-records-2026-11-24.json`.
- References: `~/prism-program/design-refs/board.md`, `audit-subtraction.md`, and the per-surface files.
  The patterns that recur across the calm products are listed at the end of `audit-subtraction.md`.
- The baseline and the scripts: `audit-data/`.
- Not evidenced here, so to be designed with care: signed-in states; Android and tablet patterns (Mobbin
  has none: say "from memory, not Mobbin"); a label for one-source or unconfirmed news (no reference found).

## Appendix A — seen by one or two reviewers only

These did not meet the rule in §1. They are leads, not findings.

| Lead | Seen by | Shot |
|---|---|---|
| Dark theme is an inversion: the warm paper becomes a cool blue-black; the 3 px rule, the selected chip and the Verified badge turn solid white and out-shout the headline; card borders and tiles nearly vanish; the bar turns lavender, close to the link colour; photographs are not dimmed; page text shows through the bottom bar | emil; accessibility for the bar and the see-through bar | [`today-390-dark.png`](audit-shots/today-390-dark.png) |
| The Urdu headline in a report row is set left to right: its second line hugs the left and the arrow points against the reading direction | emil, accessibility; two others listed it as a worst case | [`record-ur-390-y2.png`](audit-shots/record-ur-390-y2.png) |
| Odia and Devanagari headlines use Latin line height; below-base forms nearly touch the next line | accessibility | [`record-390-coverage.png`](audit-shots/record-390-coverage.png) |
| Desktop Today leaves the left column empty beside "Developing over days"; two search fields on desktop Search | 4 of 4, low severity; desktop layout is T-042 and T-044's | in the workspace's capture folder |
| The landing page explains how Prism works before why to read it; "STEP 01" labels and a ten-step index | design-taste | — |
| Plus: "Monthly" selected above a yearly card; both buttons say "Opens soon" | design-taste | — |
| Summaries cut mid-word; pale thumbnails bleed into the page; headline capitalisation is mixed; "rain" matches "training" in search | make-interfaces-feel-better | [`search-390.png`](audit-shots/search-390.png) |
| A 2 px reading-progress line at the top of a record; a keycap "1" beside the reading switch; three theme switches | emil, design-taste | — |
| Outlet logos at 16–22 px with no name; arrows on see-through plates over photographs | accessibility | [`record-390.png`](audit-shots/record-390.png) |
| A clipped word is the only sign that a row of tabs, days or chips scrolls sideways | accessibility, emil | [`record-390.png`](audit-shots/record-390.png) |

## Appendix B — where the reviewers disagreed

- **The dashed border.** Three reviewers listed "dashed plus the words *one source so far*" among the things
  that work; two said the dash is overloaded and that one-source cards in a run look like placeholders. Both
  are true: the words work, the line is carrying too much. The verdict (ledger 2) keeps the state and the
  words and leaves the line to T-081.
- **The coverage bar.** Verdicts ranged from "remove from cards, keep once with its key" to "replace with
  words" to "a bar scaled by count, with a key". All four agree it cannot stay on cards as it is.
- **The day strip.** One reviewer would keep it and drop the pill and the "For you" row; none defended the
  bare numbers.
- **Navigation on a record.** One reviewer wants the tab bar on every page; the references remove it while
  reading (2.1, 14.1). The behaviour is already decided in `specs/05-navigation.md`.
