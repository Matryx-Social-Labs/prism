# Design-taste critique (screenshots only)

## 1. Cold read

| Device or word | Where | What I think it means | Confidence |
|---|---|---|---|
| Navy + orange split bar | today card, record | Two shares of something: language? leaning? | no idea |
| "records" | today meta | A news item merged from several articles | guess |
| "stories", "developments", "reports" | chips, story, record | Three more nouns for news units | guess |
| Day strip numbers (467, 400) | today | Records that day; yet Today says "60+" | guess |
| "Has a professional read" + green dot | today | Unknown filter | no idea |
| "For you · pick subjects" pill | today | Personalise | guess |
| EN·HI·OR | card meta | Languages covering it | guess |
| Logo stack "+6" | card | Outlets reporting | sure |
| Outlet pill on photo | card, record | Photo credit | sure |
| 3px black rule | today, story, lead card top | New section; on the card, "lead"? | guess |
| "Verified record" / "Verified" black badge | record, story | Checked by whom, against what? | no idea |
| "Headline by Prism · from 11 reports" | record | Machine-written headline | guess |
| Blue-underlined words | record summary | Links to topic pages | guess |
| Stat tiles 9 / 3 / 11 | record | Labels cut off; outlets, languages, reports? | guess |
| "9 of 41 monitored outlets · checked 4m ago" | record y2 | Denominator of coverage | guess |
| "Read it as [Reader]" | record y2 | Switcher with one option | no idea |
| "The brief · Written by software" | record y2 | AI summary | sure |
| Brief / What changed / Who said what tabs | record | Jump links | guess |
| "Ask · 11 reports" | record, pinned | Chatbot over the reports | guess |
| "The event 1969" and other counted chips | story | Filter by kind; "The event" unclear | guess |
| "Following" + name chips | story | People I follow? I am signed out | no idea |
| Dot-and-rail list, "1 source" | story | Timeline, oldest first | sure |
| Monospace text | everywhere | "This is data", but used for sentences too | guess |

## 2. Counts by eye (first screenful, 390)

| Screen | Things competing | Meta lines | Text styles | Line/border kinds | Pinned share |
|---|---|---|---|---|---|
| today | 14 | 6 | 12 | 8 | 13% |
| record | 17 | 6 | 13 | 8 | 19% |
| story | 9 groups (18 outlined chips) | 4 | 10 | 6 | 6% |

## 3. Findings

| # | Severity | Element | What is wrong | Seen in | Verdict |
|---|---|---|---|---|---|
| 1 | critical | Navy/orange coverage bar | On every card, never explained; the only legend is the desktop story rail. On Stories the slot holds identical grey bars: decoration | today-390, entity-390, stories-390, story-1440 | simplify to words ("5 English · 4 Indian-language"); remove grey bar |
| 2 | critical | record / story / development / report | Four nouns; "60+ records" above an "All stories 60" chip | today-390, search-390, story-390 | merge to two: story, report |
| 3 | high | Story page opening | 18 chips, then a 5,695-item timeline starting at day one; no summary, latest unreachable; "Following" mislabels | story-390, story-390-y2 | simplify to latest + brief first, newest first, one chip row |
| 4 | high | One count printed six times | 11 reports in tiles, mono line, byline, rail header, nav, Ask button; language codes repeat "3 languages" | record-1440, record-768 | remove tiles and codes; keep one line |
| 5 | high | "Verified" badge | Heaviest object on the row, on every row, so it says nothing; meaning never given | stories-390, today-390-y2 | remove from lists; mark only the exception |
| 6 | high | "Has a professional read" pill | Floats over the chip row and hides chips at every width; phrase is opaque; decorative dot | today-390, today-768, today-390-dark | remove |
| 7 | high | Record chrome on phone | Header + tabs + Ask/Share hold 19%; content slides clipped under tabs | record-390, record-390-y2 | simplify: tabs not sticky, Share into header |
| 8 | medium | Record photo block | Carousel, counter, caption, "Their report", thumbnails precede the headline | record-390 | simplify to one photo under the headline |
| 9 | medium | Monospace prose | "most-reported first", "one source so far", "Kept in this browser…" set in mono; three dots per line | today-390, you-390, pulse-390 | simplify: mono for numbers and times only |
| 10 | medium | "Read it as [Reader]" | A switch with one choice, plus a "1" keycap | record-390-y2, record-1440-y2 | remove until two choices exist |
| 11 | medium | Header right label | Date, clock, "SEARCH", "WATCHLIST", "YOU": repeats the title | search-390, watchlist-390 | remove |
| 12 | medium | Today desktop lead | Photo pushes the headline to the fold; empty column beside "Developing" | today-1440, today-1440-y2 | simplify: cap photo height |
| 13 | medium | Landing hero | "How Prism works" explains mechanism before reason; "STEP 01" eyebrows, ten-step index | landing-390, landing-1440 | simplify to promise + one example |
| 14 | low | Plus plans | "Monthly" selected above a yearly card; both CTAs "Opens soon"; "lens", "free box rests" | plus-390, plus-390-y2 | simplify |

## 4. What is good and must survive

- Dashed card for one-outlet items, with "one source so far" (search-390).
- Report list: outlet, time, original-language headline, [n] (record-390-lens).
- Quote card with its rule "only words found exactly" (record-390-y4).
- Serif headline over sans body; one blue, kept for actions (today-390, signin-390).
- Plain, honest empty states (search-empty-390, corrections-390).
- Archive calendar with a count per day (archive-390).

## 5. Worst-case content

- Long outlet names: the photo pill will cover a 108px thumbnail and collide with time and [n] in report rows.
- 99+ counts: counted chips already wrap to four rows; nine language codes take their own line (entity-390-y2).
- One outlet: tiles reading 1, 1, 1 over a full-width single-colour bar already look broken (record-single-390).
- 40-word headline: no clamp visible on the lead card or the record headline; the brief drops two screens down.
- Right-to-left (UR is listed): timeline rail, trailing arrows, [n] refs and mono times assume left-to-right.
