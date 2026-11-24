# Critique: emil-design-eng lens

`*-390-dark.png` are 1280-wide desktop frames; phone dark not judged.

## 1. Cold read

| device or word | where | first-time reading | confidence |
|---|---|---|---|
| "record" | today, record | one news-event page | guess |
| 3px black rule | above sections | section start | guess |
| "60+ records · 24 outlets · most-reported first" | today | day's size, sort order | guess |
| day tabs with a number | today | records that day | guess |
| chips with mono count | today, story | filter, item count | sure |
| green dot "Has a professional read" | today | nothing | no idea |
| outlet pill on photo | today, record | photo's source | guess |
| "EN·HI·OR" | card meta | coverage languages | guess |
| logo stack "+6" | card | outlets covering it | sure |
| navy/orange bar | card | some split, no key | no idea |
| blue stub over tab icon | tab bar | active tab | sure |
| "Watchlist", trend icon | tab bar | followed stocks | guess |
| Brief / What changed / … | record | page sections | guess |
| "1 / 8", arrows, thumbnails | record | photo deck | sure |
| "✓ Verified record" / "✓ Verified" | record, story | several outlets agree? | guess |
| "Headline by Prism · from 11 reports" | record | machine-written headline | guess |
| blue-underlined names | record body | topic links | guess |
| boxed 9 / 3 / 11 | record | counts; tappable? | no idea |
| "Ask · 11 reports" | pinned bar | question an AI | guess |
| "Read it as [Reader]" | record y2 | one-option switch | no idea |
| thin black line, top edge | record y2 | scroll progress | guess |
| "5695 developments" | story | events in the story | guess |
| "Following" + name chips | story | whose following? | no idea |
| rail, hollow dots, mono times, "1 source" | story | timeline, oldest first | sure |

## 2. Counts by eye (first screenful, 390)

| | today | record | story |
|---|---|---|---|
| things competing | 17 | 20 | 27 (18 chips) |
| meta lines | 5 | 4 | 4 |
| text styles | 12 | 13 | 9 |
| kinds of line/border | 7 | 8 | 5 |
| pinned share | 13% | 19% | 6% |

## 3. Findings

| # | sev | element | what is wrong | seen in | verdict |
|---|---|---|---|---|---|
| 1 | critical | Record count cluster: tiles, stack, bar, mono line, Ask label | One number said five to eight times a screen ("1" eight times on a single-source record). Tiles borrow the button outline, so look tappable | record-390, record-1440, record-single-390 | merge with the one mono line; remove tiles |
| 2 | high | Coverage bar | No key on cards. Fixed length, so one outlet draws a full bar. On Stories every row has the same grey bar: decoration | today-390, search-390, record-single-390, stories-390 | remove on Stories; elsewhere simplify to a bar scaled by count, with key |
| 3 | high | Counts that disagree | Today: 24 outlets on top, 25 at foot. Story: "31 outlets" beside "Who reported it · 47"; 53 days in the list, 63 on the page. Day strip skips a day | today-390, today-390-end, story-1440, stories-390, story-390 | keep; one source per number |
| 4 | high | Story chip wall | 18 chips before the first development. "Following" means nothing signed out and repeats "Who is in it". Timeline opens at the oldest of 5,695 | story-390, story-1440-y2 | simplify to one scrolling row, newest first; merge Following with "Who is in it" |
| 5 | high | "Has a professional read" chip | Pinned over the chip row, slicing "Politics 23" and "Civic & Safet"; no fade | today-390, today-390-dark | merge with the chip row |
| 6 | medium | Dashed border | Means single-source record, empty state, disabled "Opens soon" and unread day | today-390-end, search-empty-390, plus-390, archive-390 | keep for single source only |
| 7 | medium | Verified badge | On every Stories row and Developing card, in two wordings: decoration | stories-390, today-390-y2 | remove from lists |
| 8 | medium | Record pinned chrome | Tab strip clips "How it unfolde" without a fade; Ask is both a tab and a bar | record-390 | simplify to the bar; fade the strip edge |
| 9 | medium | "Read it as [Reader]" | A selected switch with nothing to switch to | record-390-y2, record-1440-y2 | remove until a second option shows |
| 10 | medium | Quote actions | Three rows, three styles; "Share" and "Ask about this quote" are ~17px tall, 8px apart | record-390-quotes, record-ur-390-y2 | simplify to one row of 44px actions |
| 11 | medium | Urdu headline | Set left-to-right: second line hugs left, arrow at the wrong end | record-ur-390-y2 | keep; direction per item |
| 12 | medium | Meta separators | Wraps strand "•" at line ends and starts; "•" and "·" mixed | record-390, record-hi-390, entity-390-y2 | simplify to one glyph, wrapped as units |
| 13 | medium | Phone photo deck | Arrows over faces, counter, thumbnails and credit push the headline 58% down; desktop leads with it | record-390, record-1440 | simplify to one swipeable photo under the headline |
| 14 | low | Header right slot | Mono "SEARCH", "WATCHLIST", "YOU" repeat title and tab; three theme switches | search-390, you-390-y2, notfound-390 | remove labels; one theme control |
| 15 | low | Desktop grid | Empty column beside the rail; uneven card footers; two search fields | today-1440-y2, search-1440 | simplify |

## 4. Good, must survive

- Serif headline, sans interface, mono counts, one blue: today-1440.
- Outlet rows, name left, last-read right: sources-390.
- Calendar with a count in each day: archive-390.
- Reported speech upright behind a dashed rule, quotes italic: record-ur-390-y2.
- Report rows with outlet, age and [n]: record-390-coverage.
- Three steps, big targets, skip: onboarding-390.

## 5. Worst-case content

- Long outlet names: the photo credit already wraps, dropping "Their report" a row (record-390); photo pill and [n] collide next.
- 99+ counts: eight language codes already take a second meta line (entity-390-y2).
- One outlet: full bar, three tiles of "1" (record-single-390).
- 40-word headline: no clamp; eight words already take four lines beside a thumbnail (entity-390).
- Right-to-left: finding 11, plus left-pinned rails and "→" arrows.

## 6. Dark theme

- **Character:** an inversion. Same layout and weights; the warm paper becomes a cool blue-black, so the one thing light had (warmth) is lost and nothing replaces it.
- **Louder:** the 3px rule, the selected chip and the Verified badge all flip to solid white and out-shout the headline (story-390-dark). The coverage bar turns lavender and bright orange and glows. Photos are undimmed: the white screenshot in record-hi-390-dark is the brightest thing on screen. The cobalt Ask button stays fully saturated.
- **Disappear:** card borders, chip outlines, stat tiles and the timeline rail sink to near-invisible; header and tab bar merge with the page, so content reads through their edge (the blue tab stub sits on "MOST REPORTED TODAY", today-390-dark).
- **Breaks:** the lavender bar is nearly the link blue, so a data colour reads as interactive; links are periwinkle while buttons stay cobalt (two blues); outlet logos drawn for white sit dull in dark circles; the pinned chip still slices "Politics 16".
- **Must survive:** white serif headlines on blue-black with hairlines this quiet.
