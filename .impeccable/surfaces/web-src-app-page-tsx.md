---
version: 1
slug: "web-src-app-page-tsx"
primary_target: "web/src/app/page.tsx"
related_targets: ["web/src/app/feed/page.tsx","web/src/app/story/[id]/page.tsx","web/src/app/sector/[slug]/page.tsx","web/src/app/trending/page.tsx","web/src/app/pulse/page.tsx","web/src/app/search/page.tsx","web/src/app/watchlist/page.tsx","web/src/app/you/page.tsx","web/src/app/onboarding/page.tsx"]
---

## Scope
The complete product, mobile-first: front page (`/`, the chart), sector, story (the ticket), trending, pulse, search, watchlist, you, onboarding, unlock. Visitor mode: Read on the chart and the ticket; Operate on search, watchlist, the form. Founder decisions binding this build: D1 general reader leads; D2 Today + For you; D3 six sectors, no "Other"; D4 Perspectives cards retired; D5 `/` is the chart; D6 bottom bar Today · Trending · Pulse · Search · You with the sector strip as subject nav.

## Direction contract

THESIS: The day's news as the reservation chart pinned at the platform — one public list, every name on it, read the same way by everyone, re-sorted rather than rewritten when the reader changes how they read. It refuses the category default: a cream broadsheet with a serif lead and cards beneath.

OWN-WORLD: Pale continuous-stationery ground (#F2F4EE / surfaces #FAFBF8 / sunken #E8ECE2; dark #141613 / #1B1E19 / #23271F), one ink (#141414), print grey (#5C5F58), faded (#8A8D85), rule (#D6DBCF). No colour in chrome; the three lens hues (amber #F59E0B, cyan #06B6D4, violet #8B5CF6) are the only colour, and only where a lens speaks. Three voices: Teko for structure (masthead labels, sector strip, section heads, big numbers), Hind and its Indic siblings for everything read, Martian Mono for provenance only. A strict table: hairlines, codes, a fixed label grid on every row (sources · time · origin). State is line form — solid live, dashed single-source, half-weight stale — never hue. Never perforations, never a dot-matrix face, never distressing.

STORY: "This is today's list. The number at the left is how many outlets reported it; the code is the subject. Open a row and I see the route the story took, who said what, and which outlets. A coloured mark means there is a professional reading I can unlock." The reader trusts the list because it is the same list for everyone and every row shows its evidence.

FIRST VIEWPORT (phone, 390 wide): masthead — the logo left, theme toggle right; line two in mono: date · sources · stories; scope control. The sector strip: six codes, active underlined, sticky. Tabs: TODAY (and FOR YOU when interests exist). The lead row: sources count large in Teko at the left, headline in Hind 22px, lens markers, label grid beneath; image only if the story has one, never a placeholder. Then rows at 15px with the count at the left in mono. The primary action is a row: tap opens the ticket. Bottom bar: Today · Trending · Pulse · Search · You.

FORM: The reservation chart — candidate 6 of 7 on my grounded list, assigned by the roll. Seed key 31b3f17c. Raised by six donations: state as line form (emission rail), reading position persists (cutting bench), the day is the unit (magazine), single-source stands labelled (ice press), one label grid per row (archive wall), yesterday's chart archived (cloud quarry). Signature interactions: sector re-sort in place on the chart; the lens flip on the ticket, unchanged.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
