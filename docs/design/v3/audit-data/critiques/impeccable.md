# Impeccable critique (screenshots only)

Method: single context, screenshots only.

## 1. Cold read

| Device or word | Where | First-read meaning | Confidence |
|---|---|---|---|
| Thick black rule | above Today, All developments, lead card, brief | section start; on the card "lead"? | guess |
| "60+ records · 24 outlets · most-reported first" | today | size and sort; "records" are news items? why "60+"? | guess |
| "For you · pick subjects →" | today | personalise | guess |
| Day strip with 467, 400… | today | items that day; Today has none | guess |
| Chips "All stories 60", "Politics 23" | today | topic filter | sure |
| Green dot "Has a professional read" | today, over the chips | expert commentary? paid? | no idea |
| "Aaj Tak" pill on photo | lead card | photo credit or first reporter | guess |
| `EN·HI·OR` | card meta | languages; OR is Odia? | guess |
| Logo circles "+6" | card foot | outlets covering | sure |
| Navy and orange bar | card foot | political leaning? language split? | no idea |
| Blue tick above tab bar | today | active tab; looks stray | guess |
| Brief / What changed / Who said what / How it unfolded | record | jump links | guess |
| "Verified record", "Verified" | record, story | verified by whom? same thing? | no idea |
| Blue-underlined names | record text | topic links; "India" too? | guess |
| Tiles 9 / 3 / 11 | record, cut by bar | outlets, languages, reports | guess |
| "Ask · 11 reports" | pinned bar | chatbot over the reports | guess |
| "Read it as [Reader]" | record | switch with one option | no idea |
| "The brief · Written by software" | record | machine summary | sure |
| "5695 developments", "63 days" | story | updates, age | guess |
| Chips "The event 1969"… "Explainers 12" | story | filter by kind | guess |
| "Following" plus name chips | story | I follow nobody | no idea |
| Hollow dot on a line, `23 SEPT 03:43`, "1 source" | story | timeline, oldest first | sure |

## 2. Counts by eye (first screenful, 390)

| | today | record | story |
|---|---|---|---|
| Things competing | 16 | 19 | 25 (18 chips) |
| Meta lines | 6 | 5 | 5 |
| Text styles | 12 | 13 | 11 |
| Kinds of line or border | 9 | 8 | 5 |
| Pinned share | 13% | 20% | 6% |

## 3. Findings

| # | Sev | Element | What is wrong | Seen in | Verdict |
|---|---|---|---|---|---|
| 1 | critical | Story page top | Never says where the story stands: a process sentence, 18 chips, then 5,695 rows oldest-first from 23 Sept. | story-390, story-390-y2, story-1440 | simplify to a "where it stands" paragraph and the latest five, newest first |
| 2 | critical | Navy/orange coverage bar | No legend except landing step 03 and desktop story; reads as political leaning. At one outlet, a full single-colour bar is decoration. | today-390, search-390, subject-390-y2 | keep only with its legend; remove at one outlet |
| 3 | high | "11 reports" and sibling counts | Repeated up to seven times a screen: tiles, meta line, both rails, byline, brief note, Ask button. | record-1440, record-768 | merge with the meta line; remove tiles |
| 4 | high | "professional read", "Markets read", "Read it as", "Reads as", "lens" | Five names for one unexplained feature; a one-option picker; the pill overlaps the chips. | today-390, today-768, today-1440-y2, record-390-y2, you-390, plus-390 | simplify to one name; hide the picker at one choice |
| 5 | high | Grey bar under story titles | Same length on every row. Decoration posing as data. | stories-390, stories-1440 | remove |
| 6 | high | "Verified" badge | On every row, so it distinguishes nothing; two wordings; heaviest ink above the headline. | stories-390, today-390-y2, story-390 | remove; keep the dashed exception |
| 7 | high | Counts that disagree | "63 days" against the list's "53 days"; "31 outlets" against "Who reported it · 47". | stories-1440, story-1440 | simplify to one definition per number |
| 8 | high | Record top on phone | Carousel, thumbnails, caption and link come before the headline; the bar cuts the tiles. | record-390 | simplify to headline first, one photo |
| 9 | medium | Mono meta lines | Five or six a screen in one grey; language codes wrap and repeat "9 languages". | entity-390-y2, today-390 | merge with the foot line; remove codes |
| 10 | medium | Header right slot | Date, clock, both, or the page name echoing the heading below. | today-390, stories-390, pulse-390, you-390 | remove |
| 11 | medium | Bottom bar | Tabs on lists, Ask/Share on record, nothing on story; Pulse hides under Watchlist; content shows through. | story-390, record-390, pulse-390, today-768 | simplify to one opaque bar |
| 12 | medium | "What changed" | Promises a diff, lists outlet headlines; "Reports · 11" duplicates it. | record-390-y3, record-1440 | merge with Reports |
| 13 | medium | "Following" chips | The same names repeat as "Who is in it"; near-duplicate names. | story-390, story-1440-y2, search-blank-390 | merge with "Who is in it" |
| 14 | medium | Desktop Today grid | Left column blank after the lead card while the rail continues. | today-1440-y2 | simplify to one flow |
| 15 | low | Jargon | "catalyst", "free box rests", "CVE id". | watchlist-390, plus-390-y2, search-blank-390 | simplify to plain words |

## 4. Good, must survive

- Dashed border with "Single source · not yet corroborated": state without colour (record-single-390, search-390).
- Serif headlines over sans text; the headline wins every card (today-390-y3).
- Verbatim quotes with speaker, role and count (record-390-y4).
- Plain provenance: "Headline by Prism", "Written by software" (record-390, record-390-y2).
- Coverage legend with counts; sources-per-day chart (story-1440).
- Archive calendar and blank search: real numbers, no filler (archive-390, search-blank-390).

## 5. Worst-case content

- Long Indian-language outlet names: timeline rows (name, time, `[n]`) wrap; the photo pill covers the picture.
- 99+ counts: story chips already take three rows at 5695; "+20" logo stacks widen.
- One outlet: three tiles reading 1, a one-colour bar, a one-option picker (record-single-390). Already broken.
- 40-word headline: no clamp visible; rows beside a thumbnail run past ten lines.
- Right-to-left (`UR` already appears): timeline rail, `↗`, `[n]` and bullets are left-anchored.
