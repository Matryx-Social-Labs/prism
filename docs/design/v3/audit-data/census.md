# t080 census: reader-facing jargon and line/ornament devices

Scope: `web/src`, excluding `app/admin`, `app/label`, `components/admin`, `components/label`, `*.test.*`. Counts come from `grep` over the tree after one `graphify query`. "Places" means distinct components or routes that print the string to a reader, not grep lines. Where a count is approximate it says `~`. Paths are relative to `web/src`.

The only place a first-time reader gets any glossary is `/about` (`components/HowItWorks.tsx` step 09 "The words it uses", `WORDS` at L56, 7 entries: Report, Record, Monitored outlets, Single source, Coverage, Prism's reading, Lens). There is also a small legend in `components/today/TodayAside.tsx:48` ("How to read a record", desktop xl only) and `lib/faq.ts`. Nothing is explained inline at the point of use except tooltips (`title=`) on a few StatusPills.

## Part A: words a newcomer must learn

| # | term (exact string) | where it appears | places | explained in UI? |
|---|---|---|---|---|
| 1 | **Record** / "the record" / "a record" / "Records" / "The record for" / "Today's record" / "latest record" / "How to read a record" | Footer group title `components/SiteFooter.tsx` ("The record"); `Landing.tsx` eyebrow "India's verifiable news record"; `FrontPage.tsx` tablist `aria-label="Which record"`, tally "N records"; `app/search/page.tsx:261` heading "Records"; `app/feed/[date]/page.tsx:108` "The record for"; `StoryArc.tsx:129` "The latest record"; `app/pulse/page.tsx:62`, `app/signin/page.tsx:136` "Today's record"; `app/press`, `app/corrections`, `PlusPage.tsx` "The record stays free" | ~25 (346 text lines in 96 files) | Partly: `/about` WORDS "Record: Everything Prism holds on one story...". Not at point of use. Same word = product, one story, a feed day, a search result, and the whole archive. |
| 2 | **Verified record** | `StatusPill.tsx:6` (label), `lib/cards.tsx:33`, `lib/ogCard.tsx:306` (share cards) | 3 (pill is rendered in ~9 components) | No. Pill `title=` tooltip on `StoryView.tsx:525` only: "Story boundary verified; developments below are in sequence." Never says who verified or what. |
| 3 | **Verified** (short pill) | `StoriesPage.tsx:197`, `reading/StoryArc.tsx:81`, `reading/parts.tsx:98`, `app/search/page.tsx:79`, `lib/cards.tsx:82` | 5 | No. Also used for "verified quote" (a different thing). |
| 4 | **Provisional grouping** / "Grouping under review" / "Grouping provisional" | `StatusPill.tsx:7`, `today/TodayDesk.tsx:61`, `reading/StoryArc.tsx:81`, `lib/cards.tsx:33,82`, `StoryView.tsx:525` (tooltip) | 5 | No (only a `title=` tooltip and the dashed line in the TodayAside legend). Two phrasings for one state. |
| 5 | **One source so far** / "Single source · not yet corroborated" / "1 outlet · one source so far" / "A dashed row has one source so far." | `StatusPill.tsx:8`, `StoryCard.tsx:54`, `ChartRow.tsx:122`, `app/pulse/page.tsx:208`, `app/state/[slug]/page.tsx:205`, `StoryView.tsx:523`, `today/TodayAside.tsx:56`, `lib/cards.tsx:30` | 8 | Partly: `/about` WORDS "Single source", TodayAside line (desktop only). "Corroborated" itself is never defined (4 places: `StoryView.tsx:523`, `StatusGrid.tsx:8`, `app/press`, `HowItWorks.tsx:212`). |
| 6 | **Corrected** / "Corrected 12 Sept" / **Disputed** | `StatusPill.tsx` (disputed has no call site found), `StoryView.tsx:528`, `RecordHistory.tsx:41`, `app/corrections/page.tsx:52` | 3 | Yes: "Corrections and versions" section hint (`StoryView.tsx:708`), `/corrections`. |
| 7 | **Lens** / "lens" | "Read it as" row, `story/LensBrief.tsx:21`; `landing/LensFlip.tsx`; `Landing.tsx:336` eyebrow "Lenses"; `LensRegistry.tsx`; `app/onboarding/page.tsx:179`; `app/you/page.tsx:109` "Reads as"; `lib/lenses.ts`; aria "Cyber lens, free readings spent"; `HowItWorks.tsx` step 06 | ~10 (315 lines / 28 files) | Yes, at `/about` ("A lens is a professional reading of the record"), `Landing.tsx:342`, `LensRegistry`. Not on the story page itself. |
| 8 | **Read it as** (+ values Reader / Cyber / Markets) | `story/LensBrief.tsx:35,38`, `landing/LensFlip.tsx:56` | 2 | No. The tab names "Reader", "Cyber", "Markets" (`lib/lenses.ts` `short`) are unexplained on the story; the long names ("General reader", "Cybersecurity / GRC", "Finance / Trader") live in `LensRegistry` only. |
| 9 | **Professional read / reading** / "Has a professional read" / "Cyber read" / "Markets read" / "{short} read" / "paid read" | `FrontPage.tsx:199,214`, `ChartRow.tsx:38-39` (row badge), `StoryCard.tsx:44,55`, `story/LensBrief.tsx:116`, `Landing.tsx:342`, `PlusPage.tsx:271`, `app/plus/page.tsx:7`, `app/sources/page.tsx:116` ("a profession") | ~9 | Partly (`HowItWorks.tsx:250`). "Markets read" is a lens badge on feed rows with no gloss. |
| 10 | **Brief** / "The brief" / "A brief written from the reports below it." | `StoryView.tsx:268` (nav item "Brief"), `story/LensBrief.tsx:116`, `landing/LensFlip.tsx:88`, `HowItWorks.tsx:36,225`, `app/about/page.tsx:14` | 5 | Yes at `/about` step 05, not on the story page. "Brief" also appears as the Reader-lens tab content. |
| 11 | **Why it matters** (nav item, section, in brief) / "Why it matters here" (cyber table) | `StoryView.tsx:276,405,661`, `lib/lenses.ts:30`, `HowItWorks.tsx:225,243` | 3 | Yes: section hint "Who is affected first and what likely follows... never invented"; caveat "that is Prism's reading, not a reported fact" (`StoryView.tsx:463`). Nav id is `so-what`. |
| 12 | **Prism's reading** / "Headline by Prism · from N reports" / "Headline as filed by X" | `lib/headline.ts:13-15` via `StoryView.tsx:~540`, `StoryView.tsx:463`, `app/pulse/page.tsx:50,100` ("The read"), `HowItWorks.tsx` | 5 | Yes: `/about` WORDS "Prism's reading", accountability block. "Headline as filed" is not defined. |
| 13 | **Market Pulse** / "Market pulse" / "Pulse" | `app/pulse/page.tsx:47` (H1), `app/pulse/layout.tsx:6` (title), `HeaderNav.tsx:19` (nav "Pulse"), `app/watchlist/page.tsx:110,306`, masthead `datelineS "Pulse"` | 5 (3 distinct spellings: "Pulse", "Market Pulse", "Market pulse") | Partly: subtitle `app/pulse/page.tsx:50` "The listed companies and market-wide forces the last 24 hours of business reporting named". Nav label "Pulse" alone is unexplained. |
| 14 | **The read** (Pulse section) | `app/pulse/page.tsx:100` | 1 | Yes (hint "Written by Prism's model from the rows on this board"). Collides with "professional read". |
| 15 | **Watchlist** / "your watchlist" / "All signals" / "Stories on your signals" / "Recent on your signals" / "Nothing followed yet" / "follow" | `HeaderNav.tsx:18`, `BottomTabBar.tsx:17`, `app/watchlist/*` (H1, dateline, layout), `app/you/page.tsx:148,158`, `app/account/page.tsx:51`, `app/signin/page.tsx:27`, `app/pulse/page.tsx:131` | ~9 (42 lines / 17 files) | Partly: layout description "The stories that touch the tickers and sectors you follow." Three words for one thing: Watchlist / signals / follows. |
| 16 | **Today** | `HeaderNav.tsx:16`, `BottomTabBar.tsx:14`, `FrontPage.tsx:242,257` tab "Today" vs "For you" | 4 | No, but self-evident. Collides with "Today's record", "feed" (URL) and `/archive` days. |
| 17 | **Stories** (nav) vs **Developing stories** vs **Stories developing over days** vs **Developing over days** vs "Stories that run for days" vs "arc" | nav "Stories": `HeaderNav.tsx:17`, `BottomTabBar.tsx:15`; "Developing stories": `StoriesPage.tsx:117,138`, `TodayDesk.tsx:133`, `TodayAside.tsx:45`, `reading/parts.tsx:119`; "Developing over days": `TodayDesk.tsx:129`, `TodayAside.tsx:25`; "Stories developing over days": `app/trending/layout.tsx:4`; "Stories that run for days": `Landing.tsx:314`; masthead "Stories · 14:22 IST" | ~12 | No. `HeaderNav.tsx:9` comment: "/trending stays the URL; 'Stories' is what a reader calls the developing arcs". The route is `/trending`, the label is "Stories", the section is "Developing". |
| 18 | **Story** vs **record** vs **event** (internally `event`) vs "report" | `StoryView.tsx` (page is `/story/[id]` but called "this record" in the report-a-problem hint and "this story" in "Ask this story") | ~30 | `/about` WORDS: Record = everything on one story; Report = one article. Not at point of use. |
| 19 | **Developments** / "All developments" / "How it unfolded" / "How this story unfolded" / "Related reporting" / "Related stories" | `reading/StoryArc.tsx:102,109,121,196`, `StoryView.tsx:275,364,648,649,701`, `BranchTree.tsx:188`, `StoryTimeline.tsx`, stat chip "N developments" | ~10 | No. Section label flips between "How it unfolded" (verified) and "Related reporting" (provisional) for the same slot. "Related stories" = different stories; "developments" = parts of this one. |
| 20 | **Facet chips**: The event / Investigation / Response / Diplomacy / People / Reactions / Politics / Impact / Explainers | `StoryTimeline.tsx:55-59` (`FACETS`), chips via `FacetChips` | 1 component (9 chips) | No ("facet" is never printed; the chips are unlabelled). |
| 21 | **Main line and branches** / "main line" / branch rail / "You are here" / "You are reading this one" | `reading/StoryArc.tsx:109`, `BranchTree.tsx`, `StoryTimeline.tsx:108,151`, `RouteMap.tsx:134` | ~4 | No. |
| 22 | **Coverage** (section "Coverage"; nav "Coverage"; "Coverage bar"; "who has this story?") | `StoryView.tsx:277,668`, `reading/StoryArc.tsx:143`, `HowItWorks.tsx:34,212`, `components/Coverage.tsx` (CoverageBar + legend), `PhotoDeck.tsx` | ~6 (coverage 116 lines / 38 files) | Partly: `/about` WORDS "Coverage: Which kinds of outlet carry the story"; legend under the bar names the 4 classes. Internal id of the section is `sources`. |
| 23 | **Origin classes**: "English national" / "Indian-language" / "international" / "wire" | `lib/coverage.ts` `ORIGIN_LABEL`, `Coverage.tsx` legend, `app/sources/page.tsx:98` group heads | 4 | Yes (legend and `/about`). "Wire" is not defined. |
| 24 | **Outlet(s)** | "N outlets", "1 outlet", "monitored outlets", "2 of 27 monitored outlets", `app/sources/page.tsx` | ~35 places (251 lines / 59 files) | Yes: `/about` WORDS "Monitored outlets"; `lib/coverage.ts:58` denominator text. |
| 25 | **Source(s)** | "Sources" (footer, `/sources`), "Sources per day" (`StoryArc.tsx:138`, `Attention.tsx:66`), "N sources" (`StoryTimeline.tsx:50`, `lib/ticket.ts:23`), "Not in sources" (`AskShell.tsx:154`), "Reading the sources…" (`AskShell.tsx:266`), "Answers only from this story's N sources" (`AskShell.tsx:298`), "One source so far", "Single source" | ~12 | No. Means (a) a monitored publisher on `/sources`, (b) one article in Ask ("N sources"), (c) outlet-ness in "one source so far". |
| 26 | **Report(s)** | stat "N reports", "From the reports", "Every report on this story", "Headline ... from N reports", "Reading board" | ~20 | Yes at `/about` WORDS "Report: One article by one outlet". Also verb ("reported", "first reported"). |
| 27 | **Feed** | URL `/feed`, `/feed.xml`; `app/sources/page.tsx:98` "1 feed" as the unit under an outlet | 2 | No. |
| 28 | **Dateline** strip: "Wed 25 Nov · quiet since 24 Nov 14:22" / "Stories · 14:22 IST" / "Watchlist" / "Search" / "You" / "Pulse" in the sticky masthead | `components/Masthead.tsx`, set in `FrontPage.tsx:151`, `StoriesPage.tsx:113`, `app/pulse/page.tsx:40-45`, `app/search/page.tsx:195`, `app/you/page.tsx:201`, `app/watchlist/page.tsx:104,296` | 6 routes (mono, 11px, uppercase) | No. "quiet since" is unexplained. |
| 29 | **IST** | `istTime()` in `lib/dateline.ts`; "First reported 12 Sept, 14:22 IST"; "Counted by the month received · IST" | ~67 files import dateline; ~8 printed | No (comment says "the reader's newsroom clock"). |
| 30 | **First reported / Updated / Most reported / most-reported first / most reported first** | `StoryView.tsx:535` (First reported), `TodayDesk.tsx:86,123`, `FrontPage.tsx:243`, `app/search/page.tsx:228`, `app/pulse/page.tsx:73` | ~6 | No. Means "most outlets" but reads like "most clicks". |
| 31 | **Language codes** (EN·HI·KN…) | `ChartRow.tsx:75` (joins `l.toUpperCase()` with "·"), `app/sources/page.tsx:46` (code with `title=langName`), `app/story/[id]/quote/[n]/page.tsx:138`; native-script chips via `lib/languages.ts` | 3 places print raw codes; chips print native script (हिंदी, ಕನ್ನಡ) | Only on `/sources` and the quote page via tooltip (`title`). Feed rows: no. |
| 32 | **"N languages"** | `lib/coverage.ts:53` via `coverageText` (feed rows, story stat) | ~5 | No. |
| 33 | **Ask this story** / "Ask" / "Dig deeper" / "Not in sources" / "Limit" / "Ask the record" | `StoryView.tsx:720`, `AskBar.tsx:36`, `AskPanel.tsx:172-180`, `AskShell.tsx:145-154,306,308`, `HowItWorks.tsx:257`, `story/StoryActionBar.tsx` | 5 | Yes, a short line under the panel (`AskShell.tsx:298` "Answers only from this story's N sources, with citations"). "Ask this story" vs "Ask the record" vs "Ask" for the same feature. |
| 34 | **Plus** / "Prism Plus" / "Plus · monthly" / "Plus · yearly" | `SiteFooter.tsx`, `PlusPage.tsx:266`, `PlanCard.tsx:19`, `UpgradeSheet.tsx`, `PlusWelcome.tsx`, `app/plus/*` | 5 | Yes (`/plus` page, compare table). Not explained in nav; only in footer and lens gates. |
| 35 | **Founding member** / "Become a founding member" / "while seats last" | `PlanCard.tsx:19`, `UpgradeSheet.tsx:76,151`, `PlusPage.tsx:47,133-154`, `PlusWelcome.tsx:57` | 4 (41 lines / 8 files) | Yes on `/plus` (price and seats). Dashed top rule marks the founding card. |
| 36 | **Opens soon** / "Recommended" / "Free" / "Side by side" / "Before you pay" | `PlusPage.tsx:185,71,221,330,360` | 1 route | Self-explanatory. |
| 37 | **For you** / "Your state" scope / "National" / "Scope" | `FrontPage.tsx:242,257,279`, `StoriesPage.tsx:105,124`, `app/you/page.tsx:99` | 4 | Partly (`app/account/page.tsx:48` hint "Your subjects make the For you tab, your state a scope on Today"). |
| 38 | **You** (tab) | `BottomTabBar.tsx:18`, `app/you/page.tsx:201` | 2 | No. |
| 39 | **Verified quote** / "Who said what" / "Said" / "reported" (speech) / "translation" / "reported" pill on share card | `StoryView.tsx:272` nav, `Said.tsx`, `lib/ogCard.tsx:279-280`, quote page `quoteCheckLine` | ~6 | Yes (`/about` step 04 and refusals: "A quote appears only when the article it came from prints the same words inside quotation marks"). "reported" on the quote card is dashed with no gloss. |
| 40 | **Heard on** (clips) / **On X** / "First on X" / "Signal, not coverage" | `StoryView.tsx:273-274`, `XPosts.tsx:82`, `Clips.tsx`, `StoryView.tsx:638` | 4 | Partly (hint "Posts from the official accounts named in this story, as written. Signal, not coverage."). |
| 41 | **What changed** (list of every report, newest first) | `StoryView.tsx:269,601` | 2 | Yes (hint). The label does not say "reports". |
| 42 | **Named / Named in the reports / Companies named / Affected products / "Cast"** (internal term: related "by the cast they share") | `StoryView.tsx:676,746,385,701`, `app/subject/[...path]/page.tsx:135` | ~5 | Partly. "cast" is printed in the Related stories hint. |
| 43 | **Tickers / catalyst / KEV / CVSS / CVE / PoC / GRC / "Framework / Control"** | `StoryView.tsx:378-380,405,424`, `ChartRow.tsx`, `lib/lenses.ts` | ~6 (24 lines / 7 files) | No. Pro vocabulary, but shown to everyone inside lens panes and as chips. |
| 44 | **Not counted / "not read" / hatched day** | `Attention.tsx:12,54`, `ArchiveCalendar.tsx`, `app/archive/page.tsx` | 3 | Yes (legend label "not counted" beside the swatch). "Not read yet" on `/sources` is another phrasing. |
| 45 | **Hub / State / Sector / Subject / Entity / Archive / Browse by subject / "In the news now"** | `/state`, `/sector/[slug]`, `/subject/*`, `/entity/*`, `/archive`; footer "States" | ~6 routes | No. "Hub" appears only in code; readers see State/Subject. |
| 46 | **Digest** / "Email" / "Alerts" | `DigestToggle.tsx:52`, `PlanCard`, `app/you` | 3 | Yes (section copy). |
| 47 | **Monitored** (outlets) | 74 lines / 28 files | ~20 | Yes (`/sources`, `/about`). |
| 48 | **Denominator** | `HowItWorks.tsx:45`, `lib/coverage.ts:58` ("No count without its denominator.") | 1 (UI) | Yes in the sentence that follows. Jargon in a heading. |
| 49 | **Pinned**, **Earlier**, **Signal** | `StoriesPage.tsx:196`, `app/watchlist/page.tsx:185` | 2 | No. |
| 50 | **Abbreviations seen**: IST, EN/HI/KN codes, CVE, CVSS, KEV, PoC, GRC, GST/"Razorpay" in Payments, "d" in "30 d", "N d" streaks | see above | | mostly No |

### Synonym groups and collisions

1. **outlets vs sources vs reports vs publishers vs feeds.** Same readable thing, five names.
   - "outlets" is the count on a card ("2 outlets", "1 outlet · one source so far").
   - "sources" is the same outlet on `/sources`, in "Sources per day", in "Answers only from this story's N sources" (that N is *reports*, `AskShell.tsx:298` fed by `sourceCount`), and in "One source so far" / "Single source" (an outlet).
   - "reports" is one article (stat chip "N reports") and the headline byline "from N reports".
   - `StoryView.tsx:362` shows "N outlets" and "N reports" side by side in the header stats, and the same string on `StoryTimeline.tsx:50` ("N sources") means articles in a development.
   - Internal id `sources` sits under the visible label "Coverage" (`StoryView.tsx:277`).
2. **Stories vs Developing stories vs "Developing over days" vs "record" vs "event".** Nav "Stories" = the `/trending` arcs (multi-day), while every `/story/[id]` page is also a "story" and is also a "record". "Stories" the tab, "stories" the count in `Entity`, `Subject`, `Pulse` ("5 market stories") all mean different units.
3. **Record** means (a) the product ("The record" footer group, "India's verifiable news record"), (b) one story page ("the record for this story"), (c) a feed row ("N records"), (d) a day ("The record for 24 Nov"), (e) a search result group ("Records"). Plus "verified record" which is a status of (b).
4. **read** collides: "professional read", "Markets read", "Cyber read", "Read it as", "The read" (Pulse section), "Prism's reading", "Reads as" (`app/you:109`), "Reading board", "Reading the sources…", "Reading" (the app is "reading" outlets, "not read yet").
5. **verified** means: story boundary verified (grouping), verified quote, "verified" vs "Verified record" vs "Verified", and `verified · N developments` (`StoryView.tsx:649`). Never says what was checked.
6. **Provisional grouping** vs **Grouping under review** vs **Grouping provisional** vs **Related reporting**: one state, four strings.
7. **Watchlist / signals / follows / alerts**: one feature.
8. **Ask this story / Ask the record / Ask / Dig deeper**: one feature.
9. **Coverage** is both a section ("Coverage" = who covered it) and the word inside "not as coverage" (X posts) and "coverage bar".
10. **Today** is a tab, a feed day, and "Today's record" in text.

Count of jargon terms in Part A: 50 rows; ~32 distinct product terms after grouping synonyms; 10 collision groups.

## Part B: line and ornament devices

Reader-facing source only. Tokens are generated into `app/globals.css` L12-489 from `design/tokens.json`; the rest of the file is `.p-*` (v2 system), `.sc-*` (screens), and older `.chip`/`.row-card`/`.status-*` classes kept for components not yet rebuilt. Two parallel class families exist for the same shapes (`.p-status` + `.status-*`, `.p-chip` + `.chip`, `.p-eyebrow` + `.card-h`, `.p-lensdot` + `.lensdot`).

### Dashed borders: 76 lines in 29 files (14 in `globals.css`, 10 in `lib/ogCard.tsx` share cards; ~50 are live style rules, the rest comments)
- Meaning: "provisional / one source / not done / not counted". Stated in `globals.css:530`: "State is line form (solid / dashed / faded), never hue alone."
- Refs: `app/globals.css:569-570` (`.p-status--provisional`, `.p-status--single`), `:617` (`.p-row--single`), `:839` (`.row-card.single`, comment "the dash has to be visible to mean anything"), `:904` (`.rule-single`); `components/StoryCard.tsx:31` (`borderStyle: single ? "dashed"`); `app/search/page.tsx:77` (unverified result); `components/StatusGrid.tsx:39` (`RULE = {now:"solid", val:"dashed", next:"dotted"}`); `app/story/[id]/quote/[n]/page.tsx:112` (3px dashed = reported not verbatim); `components/PlusPage.tsx:65` (dashed top = founding plan), `:185` ("Opens soon" box); `components/Payments.tsx:52` (dashed = refunded); `app/sources/page.tsx:39` (dashed row = feed unreachable).
- So dashed carries **at least 7 meanings**: provisional, single-source, unverified, translated/reported quote, not-yet-built, founding plan, refunded, unreachable, empty state (`ui.tsx:17`, `Chart.tsx:46`), "Limit"/"Not in sources" (`AskShell.tsx:145-154`), disabled input (`globals.css:722`), uncounted day (`:896`).

### Dotted: 5 lines
- `app/globals.css:1166` (`.rm-stn.rm-dotted`, `stroke-dasharray: 2 2`), `components/RouteMap.tsx:191,250`, `components/StatusGrid.tsx:37-39` ("dotted is not built yet"). Meaning: station not yet built / not yet verified in the route map; "next" on the status grid. No CSS `dotted` border and no dotted leaders exist. `.p-meta__sep` (`globals.css:~612`) is a 3px round dot separator, not a leader.

### stroke-dasharray: 7 lines (`globals.css:1022,1027,1162,1166,1177,1183,1189`)
- Only `:1162` (`.rm-branch`, 4 4) and `:1166` carry state (branch line). `:1022`, `:1027`, `:1183` are draw-in animations; `:1177` is a focus ring; `:1189` resets for reduced motion.

### Hatching / stripes: 7 `repeating-linear-gradient` definitions, 3 consumers
- Defs: `globals.css:67,242,301,360,451` (`--data-uncounted`, 5 theme blocks, 135deg 4px/5px), `:601` (`.p-cov-wire`), `:848` (`.cov-wire`).
- Consumers: `components/Attention.tsx:85,98` (bar and legend), `globals.css:896` (`.sc-cal__day--off`, calendar), coverage "wire" segment.
- Meaning: hatched = "not counted" (Prism was not reading that day); wire segment hatched = "agency copy". No `hatch` or `stripe` class names.

### Thick rules (3px or more): 17 lines use `--rule-section`/`--rule-lens` (both 3px, `globals.css:144-145`), plus 8 others
- `.p-sechead` top rule (`globals.css:631`) is the base; `SectionHead` is used 51 times (all reader pages).
- Refs: `globals.css:619` (`.p-row--lead` 3px top), `:631`; `components/today/TodayDesk.tsx:123,129`; `components/reading/parts.tsx:72`, `reading/StoryArc.tsx:52` (RailHead); `components/LegalPage.tsx:131`; `components/StatusGrid.tsx:43,72`; `components/StoryView.tsx:738,746` (`border-b-[3px]`); `components/PlusPage.tsx:65` (4px accent top on the recommended plan); `lib/ogCard.tsx:132,271` (3px/6px in share cards).
- Meaning: ink 3px = "a section starts here / this is the lead"; 3px accent = "free" (`StatusGrid.tsx:72`); 4px accent = recommended plan; 3px dashed ink = quote reported, not verbatim. Also `border-l-2` (2px) quote rails ×6 (`Said.tsx:100,243,256`, `HowItWorks.tsx:102`, `AskShell.tsx:58`, `StoryNav.tsx:94`). No classes named `section-rule`; `.rule-live/.rule-single/.rule-stale` are 1px (`globals.css:903-905`).

### Hairlines (1px): ~126 lines (45 explicit `1px solid`, 51 `border-b`/`border-t`, plus `--line`/`--line-strong` tokens used in ~74 `className` borders)
- Refs: `globals.css:~567-580` (`.p-status`/`.p-badge--outline`), `.p-card`, `.p-row` (`:612`), `.p-chip`, `.p-input`; `SiteHeader.tsx:43,55` (border-b under sticky bar); `BottomTabBar.tsx:45` (border-t); `components/LegalPage.tsx:131` (row rules); `components/PlusPage.tsx:65`. Tokens: `--line` (soft) and `--line-strong` (control/dashed), `--rule-hair: 1px`; `--border-hairline` alias. No `divide-y`. No class named `hairline`.
- Meaning: card/row edge and separators; `--line-strong` doubles as the dashed-state colour.

### Gradients: 2 genuine `linear-gradient`, 1 scrim
- `globals.css:148` `--spectrum: linear-gradient(90deg, #EF4444, #F59E0B, #06B6D4, #8B5CF6)`, used at `:1083,1086` (progress/flip accent line); `components/SourceList.tsx:166` (photo caption scrim, white text on image). Plus 7 `repeating-linear-gradient` above. `color-mix()` used for `.glass` (`:881`, backdrop blur 12px on sticky bars, 11 refs), soft lens fills, `--up-bg`. No Tailwind `bg-gradient-*`. Meaning: spectrum = "the lens colours" (brand/prism mark), not a state.

### Pills / badges / chips: 7 distinct component families
| name | defined | call sites (reader) | radius / meaning |
|---|---|---|---|
| `StatusPill` / `.p-status` / `.status` | `StatusPill.tsx`, `globals.css:567`, `:864` | 13 lines in 9 files | 2px; verified = solid ink, provisional/single = dashed, corrected = red tint, disputed = amber (disputed has no call site) |
| `.p-badge` (+`--accent`, `--ink`, `--outline`, `--dashed`) | `globals.css:574` | 9 lines in 4 files (`StoryView.tsx:378-380,424`, `AskShell.tsx:145,154`, `PlusPage.tsx:71,267`, `XPosts.tsx:82`) | 2px; "Recommended", "Limit", "First on X", ticker/CVSS/KEV |
| `.p-tag-mono` | `globals.css:579` | 4 lines in 3 files (`Markets.tsx:20`, `PlanCard.tsx:141`, `Payments.tsx:52`) | 2px; ticker, payment status, mono |
| `.p-chip` / `.chip` / `.chip-q` | `globals.css:~590`, `:803` | 28 `p-chip` + 31 `chip` in ~30 files (`SectorStrip.tsx:36`, `app/watchlist/page.tsx:163`, `FollowSignals.tsx:62`, `StoryTimeline` facets, `AskShell` prompts) | 8px (`!important` override of the 9999px pill, `globals.css:~595`); 36px tall, 44px tap area; filter/scope/follow |
| `.p-seg` segmented | `globals.css:603`, `:874` | ~19 role="tab" in 6 files (`FrontPage.tsx:246`, `story/LensBrief.tsx:38`, `PlusPage.tsx:275`) | 8px/6px; tabs |
| `.p-lensdot` / `.lensdot` | `globals.css:582`, `:868` | 5 call sites (`StoryCard.tsx:44,55`, `ChartRow.tsx:126`, `app/onboarding/page.tsx:179`, `app/you/page.tsx:109`) | dot colour = lens; cyber = square, health = diamond, policy = triangle (shape for colour-blind) |
| `.p-kbd`, `.p-cite`, `.p-monogram` | `globals.css:~560,~658,~620` | 2, 2, 1 | keycap, citation number, outlet initials |
| `rounded-full` ad-hoc pills | tailwind | 14 lines in 12 files (`FollowSignals.tsx:62`, `SelectionAsk.tsx:47`, ...) | not routed through any shared pill |
Note: `.p-chip`, `.p-status`, `.p-badge`, `.p-tag-mono`, `.p-cite` are all forced to `--r-sm` or `--r-control` later in the file (`globals.css:709`), so the `rounded-full` pill form survives only in ad-hoc places.

### Uppercase eyebrow labels: `.p-eyebrow` 48 lines in 30 files (sans, 12.5px, 600, 0.08em tracking, uppercase, `--ink-3`); mono uppercase is separate, 12 lines
- `.p-eyebrow` is **sans, not mono** (`globals.css:634` `font: var(--t-label)`). Same style: `.card-h` (`:833`), `.p-table th` (`:701`), `.sc-cal__head` (`:890`).
- Uppercase mono (the "provenance strip", `globals.css:878` "the one place caps are allowed besides an eyebrow"): `components/Masthead.tsx:23` (dateline, 6 routes), `PlanCard.tsx:137`, `PlusWelcome.tsx:57,65`, `Payments.tsx:52`, `globals.css:1170,1173` (route map labels), `.meta-line`/`.p-meta__prov` 11-11.5px (non-uppercase; `shortDate(...).toUpperCase()` in `corrections/page.tsx:54`, `StoryTimeline.tsx:32`, `Attention.tsx:54`).
- Heaviest users: `StoryView.tsx` ×4, `Landing.tsx` ×4, `ui.tsx` ×3, `StatusGrid.tsx` ×3, `HowItWorks.tsx` ×3, `app/search/page.tsx` ×3. Meaning: section label; on `TodayDesk`/`StoryArc` it sits on a 3px ink rule and acts as a section head. Other uppercase: 20 lines total.

### Sticky and fixed bars (each)
| bar | component:line | routes |
|---|---|---|
| Desktop top bar `glass sticky top-0 z-40` (60px) | `components/SiteHeader.tsx:43,55` | all (hidden on app routes below lg for the masthead) |
| Mobile masthead `glass sticky top-0 z-30` (52px, dateline) | `components/Masthead.tsx:21` | `/feed`, `/trending`, `/pulse`, `/search`, `/watchlist`, `/you` |
| Phone back bar `sticky top-0 z-30` (52px) | `components/ui.tsx:209` (BackBar), `StoryView.tsx:489` | story, entity, state, subject, sector, quote pages |
| Bottom tab bar `glass fixed bottom-0 z-40`, 5 tabs | `components/BottomTabBar.tsx:45` | app routes, lg:hidden |
| Story action bar `fixed bottom-0 z-40` (Ask, Share) | `components/story/StoryActionBar.tsx:12` | `/story/[id]`, lg:hidden |
| Story section tabs `sc-tabs sticky top-[masthead] z-25` | `components/story/StoryNav.tsx:124` | `/story/[id]`, phone |
| Onboarding footer `fixed bottom-0 z-40 border-t` | `app/onboarding/page.tsx:244` | `/onboarding`, lg: static |
| Ask button `fixed bottom-5 right-5 z-45` (desktop FAB) | `components/AskPanel.tsx:169` | `/story/[id]`, lg |
| Selection popover `fixed z-44` ("Ask") | `components/SelectionAsk.tsx:47` | `/story/[id]` |
| Toast `fixed inset-x-0 bottom-[tabbar+16]` z-50 | `app/you/page.tsx:216`, `components/PlanCard.tsx:172` | `/you`, plus |
| Reading progress `.sc-progress fixed top-0 h-2px z-70` | `globals.css:763` | story |
| Mobile ask/upgrade sheets `fixed` + `.p-scrim` z-60/61 | `globals.css:664,919`, `story/Sheet.tsx:46` | story, plus |
| Skip link `fixed left-3 top-3 z-100` | `app/layout.tsx:106` | all |
| Sticky side rails (desktop, `top: topbar+24`) | `SectorStrip.tsx:85`, `LegalPage.tsx:93,157`, `StepRail.tsx:22`, `story/StoryNav.tsx:83`, `reading/parts.tsx:31-32`, `today/TodayAside.tsx:22`, `Rail.tsx:35`, `StoryView.tsx:725` | feed, trending, legal pages, `/about`, story |
Total: 14 distinct bar/overlay devices (7 true bars, 7 floating or sheet).

### Radii: 9 tokens, 10 distinct resolved values
- Tokens (`globals.css:136-142`): `--r-xs 1px`, `--r-sm 2px`, `--r-md 8px`, `--r-lg 8px`, `--r-xl 16px`, `--r-pill 9999px`, `--r-record 2px`, `--r-control 8px`, `--r-sheet 16px`.
- Resolved values in use: 0, 1, 2, 3 (`ogCard`), 6 (`:708,874`), 8, 13 (switch), 16, 50%, 9999 (`rounded-full`). Ad-hoc: `rounded-[2px]` ×7, `rounded-[8px]`, `rounded-[6px]`, `rounded-[var(--r-md)]` ×9, `border-radius: 0` ×9 (lens-shape squares, covbar).
- Meaning: 2px = "record" (status, badge, thumb), 8px = control/card, 16px = sheet.

### Font sizes: 33 distinct px values
- Tailwind arbitrary `text-[Npx]`: 10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14, 14.5, 15, 30, 40, 64, 104 (top: 13px ×29, 11px ×27, 13.5px ×16, 14.5px ×15, 12.5px ×14).
- Token fonts (`--t-*`, `globals.css:112-127`): 44, 30, 23, 18, 16.5, 15.5, 17, 16, 14.5, 15, 13.5, 12.5, 12, 11.
- Other CSS and inline: 8, 9.5, 20, 21, 22, 24, 26, 27, 28, 34, 92 (`ogCard`, `Landing`).
- Union: 8, 9.5, 10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14, 14.5, 15, 15.5, 16, 16.5, 17, 18, 20, 21, 22, 23, 24, 26, 27, 28, 30, 34, 40, 44, 64, 92, 104. About 14 of those are half-pixel steps within 11-16.5px.

### Colour tokens: 150 custom properties in `globals.css`; 105 hold a literal colour (hex / rgba / color-mix) and ~26 are var() aliases to a colour
- Families: surfaces (`--bg --surface --sunken --elevated --paper`), ink (`--ink --ink-2 --ink-3`), lines (`--line --line-strong`), accent (5), coverage (4 + 4 `--cov-*` aliases), lens (4 hues, 4 soft, 4 slot), status (4), danger, up/down, data (6), seq (7), `--data-uncounted`, `--scrim`, plus 5 theme blocks (light, dark via `prefers-color-scheme`, `data-theme=dark`, and two theme-override blocks at `:307`, `:398`). Alias layer (`--text-body`, `--border-hairline`, `--lens-finance`, `--ink-muted`, `--ink-faint` ...) duplicates ~25 of them.
- Raw hex outside tokens: `lib/ogFonts.ts` ×19, `lib/mark.ts` ×4, `GoogleSignIn.tsx` ×4 (Google brand), `app/press/page.tsx` ×2, `layout.tsx`, `manifest.ts`, `apple-icon.tsx` (all expected: icons, OG cards, brand).

### Totals
| device | count |
|---|---|
| dashed | 76 lines / 29 files |
| dotted | 5 |
| dasharray | 7 |
| hatching | 7 defs, 3 consumers |
| thick rules (>=3px) | 17 token uses + 8 others |
| hairlines | ~126 |
| gradients | 2 + 1 scrim (+7 hatch) |
| pill/badge/chip families | 7 (+ ad-hoc `rounded-full` ×14) |
| uppercase labels | `.p-eyebrow` 48 lines; mono caps 12 |
| sticky/fixed | 14 |
| radii | 9 tokens / 10 values |
| font sizes | 33 |
| colour custom properties | 105 literal + ~26 aliases (150 custom properties total) |
