# make-interfaces-feel-better (screenshots only)

Caveat: `*-390-dark.png` are desktop frames; `*-390-full.png` are 37–82px wide. Phone dark theme unjudged.

## 1. Cold read

| device or word | where | first-time reading | certainty |
|---|---|---|---|
| "records" beside "All stories 60" | today | a news event; same as a story? | guess |
| mono numbers under days (467) | today | records that day; why is Today 60+? | guess |
| chip with grey number | today, story | filter and count | sure |
| "For you · pick subjects →" | today | personalise | guess |
| green dot "Has a professional read" | today | — | no idea |
| outlet badge on photo | today, record | photo credit | sure |
| EN·HI·OR | today | languages; OR? | guess |
| logo stack "+6" | today | outlets covering | sure |
| navy/orange bar | today | party split? language split? | no idea |
| thick black rule | all | section start | sure |
| blue tick over nav item | today | current tab | sure |
| scrolling tabs Brief / What changed… | record | page sections | guess |
| arrows, "1 / 8", thumbnails | record | outlets' photos | sure |
| "✓ Verified record" / "✓ Verified" | record, story | several outlets agree? fact-checked? | guess |
| "Headline by Prism · from 11 reports" | record | site-written headline | guess |
| blue-underlined names | record | link to that name | guess |
| number tiles 9 / 3 / 11 | record | counts; look tappable | guess |
| "9 of 41 monitored outlets · checked 4m ago" | record-y2 | 9 of their 41 covered it | sure |
| "Read it as [Reader]" | record-y2 | — | no idea |
| "The brief · Written by software" | record-y2 | AI summary | sure |
| pinned "Ask · 11 reports" | record | chatbot | guess |
| "developments" | story | records in this story? | guess |
| "Each development was checked against this story before it joined." | story | — | no idea |
| "Following" + name chips | story | names I follow? names involved? | no idea |
| dot, line, mono time, "1 source" | story | timeline, oldest first | sure |

## 2. Counts by eye (first screenful, 390)

| | today | record | story |
|---|---|---|---|
| things competing | 17 | 19 | 13 (21 tap targets) |
| meta lines | 5 | 5 | 4 |
| text styles | 13 | 14 | 11 |
| kinds of line or border | 9 | 10 | 6 |
| pinned bars | 13% | 19% | 6% |

## 3. Findings

| # | severity | element | what is wrong | seen in | verdict |
|---|---|---|---|---|---|
| 1 | critical | Story page opening | Nothing says what the story is or where it stands; 18 chips, then 5,695 rows oldest-first from 23 Sept; today's news is unreachable | story-390, story-390-y2, story-1440 | simplify to two-line summary + latest five developments |
| 2 | critical | Controls above Today's first headline | Five rows (counts, For-you, day strip, chips, floating pill), ~10 decisions; headline starts 65% down; pill clips the chips | today-390 | simplify to day strip + chips; remove pill |
| 3 | critical | Navy/orange bar on cards | No legend; fixed length, so no quantity; on party stories reads as a lean meter; identical grey bars on Stories are decoration | today-390, subject-390, stories-390 | remove from cards; keep once in record Coverage, with legend |
| 4 | high | Count repetition | Tiles, logo stack, bar, mono sentence, "from 11 reports", "Ask · 11 reports" restate three numbers; tiles are decoration | record-390, record-768 | merge with the mono sentence |
| 5 | high | Carousel before headline | Seven controls precede a headline at 58% depth; arrows cover faces; eighth thumbnail blank | record-390, record-768 | simplify to headline first, one credited photo |
| 6 | high | Pinned chrome and Ask | Header + clipped seven-tab strip + Ask/Share bar; Ask appears four times on one screen | record-390, record-390-end | merge: no tab strip on phone; one Ask |
| 7 | high | "What changed" | It is the report list, repeated in Coverage and the desktop Reports rail | record-390-y3, record-390-coverage, record-1440 | merge with Coverage |
| 8 | high | Vocabulary, disagreeing counts | Seven nouns for counted things; "60+ records" vs Yesterday 467; Politics 23 vs 15; "31 outlets" vs "Who reported it · 47" | today-390, today-390-y3, story-1440 | simplify to story/report/outlet; one number per fact |
| 9 | high | White rounded rectangle | One shape is filter, name link, stat tile, mode switch and button; tappability unreadable | story-390, record-390-y2, state-390 | simplify: chips for filters only |
| 10 | medium | Dashed border | Means single source, empty state, disabled button; single-source cards stack four signals and fill lists like placeholders | subject-390-y2, search-empty-390, plus-390 | keep for single source only |
| 11 | medium | "Professional read", "Markets read", "Read it as Reader", "↓ Down" | Unexplained jargon; a switch with one option | today-390, today-390-end, record-390-y2, record-hi-390-y2 | remove until a choice exists |
| 12 | medium | Quote footer | Four 12px text actions per quote, targets under 40px | record-390-quotes, record-ur-390-y2 | simplify to one source link + Share |
| 13 | medium | Navigation | Bottom nav vanishes on record/story; Pulse hides under Watchlist on phone; header slot echoes the page name (decoration); two search fields | story-390, pulse-390, search-390, search-1440 | keep nav everywhere; remove echo |
| 14 | medium | Desktop Today grid | Empty left column beside "Developing over days" | today-1440-y2 | simplify to one flow |
| 15 | low | Finish | Deks cut mid-word; pale thumbnails bleed without outline; mixed headline case; "Read 3m ago" ×41; "rain" matches "training" | today-390, subject-390-y2, sources-390, search-390 | simplify: word-boundary clamp, 1px inset image outline |

## 4. What is good and must survive

- Report row: logo, outlet, time, original-script headline, [n] — `record-390-coverage.png`
- Numbered "most reported" rows — `today-390-y2.png`
- A finite ending with one next step — `today-390-end.png`
- Blank search offering names and top stories — `search-blank-390.png`
- One question per step, skippable, no account — `onboarding-390.png`
- Verbatim quote, serif italic, speaker and source — `record-390-quotes.png`

## 5. Worst-case content

- Long outlet names: "The Hindu — Andhra Pradesh · 2h ago · [10]" nearly fills the report-row header; a longer Indic name wraps or pushes [n] off.
- 99+ counts: story chips already wrap to four rows; "+120" outgrows the 22px logo circle.
- One outlet: heaviest treatment: dashed frame, full-width bar, three "1" tiles (`record-single-390.png`).
- 40-word headline: ~12 lines beneath the carousel on record; thumbnail cards already spend four lines on nine words.
- Right-to-left: the Urdu row right-aligns but keeps a trailing "→" pointing the wrong way (`record-ur-390-y2.png`).
