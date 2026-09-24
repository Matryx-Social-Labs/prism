# Prism — context pack for the redesign

Everything a designer needs to redesign Prism completely without missing a
surface. This pack comes from the running product's code (September 2026), not
from memory. Sections 1–6 are the product and its rules. Sections 7–12 list
every component, page, state and feature that exists today. Section 13 lists
what is wrong with the current design.

---

## 1. What Prism is

Prism reads Indian news from many outlets in several languages (English, Hindi,
Kannada, Tamil, Telugu, Marathi, Gujarati, Urdu…). It clusters the coverage into
**one canonical story per event**: every outlet that reported it, in every
language. A reader can then re-read any story through a **lens**, a reading of
the same facts for a role (markets, cyber and more to come). Under each story
Prism shows **who said what, word for word**, each quote checked against the
article it came from.

- **Promise:** "Follow the story, not the headlines."
- **What makes it different:** it shows the record, not a verdict. Other
  products summarise (Inshorts, Particle) or rate bias (Ground News). Prism shows
  the evidence: counts of who reported it, verbatim quotes, named sources.
- **The memorable thing:** the **lens flip**. The same story re-sets itself in
  place for a different reader.
- **Live:** readprism.news (web; phone first). A React Native app will follow
  from the same design, so every phone screen must be designed as an app screen.
- **Company:** Prism Media Intelligence LLP, built with Matrix Social Labs. The
  legal copy names the LLP.

## 2. Who uses it

1. **The general Indian news reader.** On a phone, in the gaps of a day, mostly
   signed out, often arriving on a story page from a shared link or a search.
   Reads English first; many also read an Indian language and should never be
   shown a language they didn't choose.
2. **Paying professionals (Prism Plus).** Markets readers (traders, analysts,
   finance creators) and cyber/GRC readers. They read the same stories but pay
   for the lens reading: which tickers move and why, whether a CVE is exploited.
   They are not a separate front door. A story that earns a professional reading
   says so on the feed.
3. **Labellers.** People Prism recruits to label its data: whether two reports
   are the same story, who said a quote, whether two quotes are one statement
   in translation. Mostly on phones, reading Indian languages. They apply,
   train, pass a test, then work in batches.
4. **The founders and review team.** They use the admin dashboard to run
   labelling, read the product's numbers (which they show investors), and
   spot-check that the pipeline's facts are right. Desktop first.

## 3. The honesty rules (non-negotiable; every screen must follow them)

These are the product. A design that breaks one is wrong, however it looks.

1. **Verbatim or nothing.** A quote appears only in its exact words from the
   source article, with its speaker, outlet, time and a link to the line. A
   quote printed in another language is labelled as a translation. There are
   no paraphrased quotes.
2. **Counts are counts.** Structure is counted, never summarised by a model
   ("9 outlets · 2 languages", "4 developments"). No invented numbers anywhere.
3. **Small numbers stay counts.** Below 30, a share is printed as "3 of 4", never
   "75%". A change off a small base is "+3 from 4", never "+75%".
4. **No record is not zero.** A day or week not yet counted is shaded or blank,
   never drawn as zero.
5. **Provisional says so.** A grouping still under review is marked in words (and
   in line style), never hidden.
6. **Colour never carries meaning alone.** Every coloured bar has its count, every
   status pill has its word, every lens dot has its label.
7. **Never list lens names in generic copy** ("read it as a trader, a CISO…").
   The set of lenses grows, so pickers render whatever the lens API returns.
8. **Examples are marked.** Any example written for a guide or a demo carries the
   word ILLUSTRATION. Nothing invented is shown as real: no testimonials, no user
   counts, no press logos, no price data (there is none yet), no benchmarks.
9. **Publishers' photographs are not Prism's.** They appear only as a credited
   preview of their own report, never on a share card, never as Prism's image.
   Outlets are identified by their own favicon, with a two-letter monogram as
   the fallback.
10. **Today is a day.** The feed does not scroll forever; yesterday is a link.

## 4. Accessibility and language floors

- WCAG AA: 4.5:1 for text on both themes, 3:1 for UI and graphics.
- Touch targets at least 44px. Inputs 16px (no iOS zoom). Mono text never
  below 11px; body never below 14.5px.
- Reduced motion collapses every animation, the lens flip included, to an
  instant change.
- Light and dark themes, following the system setting with a manual toggle.
- Scripts that must render in the body and display voices without mismatched
  fallback: Latin, Devanagari (Hindi, Marathi), Kannada, Tamil, Telugu, Bengali,
  Gujarati (Urdu appears in the corpus too).
- Every chart has a text or table alternative.
- Everything works with a keyboard, and focus is always visible.

## 5. Brand — what stays and what is open

**Stays (do not change):**
- The name **Prism** and the **mark**: an equilateral prism, fill only, with a
  spectrum band attached to its base (the only gradient in the product). It
  appears on the masthead, the favicon and the share cards.
- **Three type voices, three jobs:** a display voice for the record (headlines,
  titles, quotes); a reading/UI voice for everything read or tapped; a monospace
  voice only for provenance (times, counts, outlet codes, citations, tickers,
  CVE ids). A word in the wrong voice is a bug.
- **The lens flip is the signature motion.** It re-typesets the lens block with a
  scan line in the lens's colour while the text re-inks behind it (~500–1100ms,
  at a constant pace for the block's height). It is never a crossfade, and body
  layout never moves.
- **Colour means something.** The chrome is neutral. Colour appears where the
  prism "splits light": the coverage bar (outlet origins), a lens (each lens has
  one discrete hue), and one interactive accent. Data colour is allowed inside
  the admin charts.
- Voice: editorial, direct, factual. No marketing copy inside the app.

**Open (redesign freely):**
- Typefaces (today: Libre Baskerville / IBM Plex Sans with Hind's Indic
  siblings / JetBrains Mono).
- Every colour value (today: warm off-white ground, deep teal accent `#006B62`,
  coverage amber / red-orange / cyan / grey, lens green (markets) and blue
  (cyber)).
- Radii, shadows, cards vs hairlines, density, the grid, the icon set, the
  component shapes, illustration, and the landing's art direction.

## 6. Product facts the design depends on

- **Subjects (sectors)** in a permanent nav on every surface. The founders' six
  are Politics · Business & Markets · Sports · Tech & Cyber · Health & Science ·
  Entertainment; the nav also shows Education and Civic & Safety today, so
  design it for a list from data (6–10 items, each with today's count). "Other"
  is never a heading. Scope: All / the reader's state / National / World.
- **Lenses:** Reader (free, neutral, no colour), plus professional lenses —
  Markets and Cyber today, with more drafted (health, policy). Access by level:
  - **signed out:** Reader only; a professional lens is locked, but it still
    flips and shows what the reader is missing;
  - **signed in (free):** a few free reads of the professional lenses (3 at
    sign-up), then "You've used your free reads";
  - **Plus:** the professional readings.
  The brief is gated on the server. The lens set comes from an API and grows.
- **A story row** always carries: subject/region · time since the last report ·
  languages; the headline; what changed (two lines); outlet monograms (max 3 +
  "+N"); the coverage bar with its count; a lens dot ("Markets read") when the
  story earns one; a credited thumbnail when one exists. A single-source story
  is visibly different (today a dashed border), and single-source stories never
  lead the front page.
- **Coverage bar:** a story's reporting split by outlet origin, in a fixed order:
  national (English) · international · regional (Indian-language) · wire
  (reserved). Always followed by its count.
- **Ask:** grounded Q&A on a story, answered from that story's own sources (or
  it says it can't). Limits: 3 questions per anonymous session, 10 per day on a
  free account, 100 per day on Plus. Hitting the limit opens the upgrade sheet.
- **Prism Plus** (Razorpay; UPI autopay or card; prices include GST):
  - launch offer: ₹149/month or ₹1,199/year, held for 12 months;
  - Founding member: ₹999/year, locked for 3 years (the first 500);
  - regular: ₹199/month, ₹1,499/year.
  Subscriptions can be paused and cancelled, with one matched offer at
  cancellation. Paid time is kept. A failed charge gets grace days.
- **Personalisation:** state, role, interests (sector or sub-sector), languages
  in order of preference. Nobody is forced through onboarding to read. A "For
  you" view appears once interests are picked.
- **Signal, not coverage:** posts from official accounts on X (ministries,
  regulators, exchanges) attached to a story, as written, in their own section.
  They count toward nothing and never appear on a feed row or share card.
- **Podcast clips:** short clips where a podcast discusses the story, with a
  transcript that inks as it plays.
- **Scale today:** ~42 sources (27 feeds active), thousands of stories a month,
  ~45% with at least one verbatim quote, ~3% with a validated ticker.
- **Days are IST.** Times print in India time, tagged IST when shown to a device
  elsewhere.


## 7. Components (the design system must include every one, with all its states)

**Chrome.**
- Skip link; desktop top bar (brand, nav, search field with `/`, Plus link, theme toggle, Sign in / avatar); phone masthead (brand, mono dateline, theme); phone back bar ("← Today"); bottom tab bar (Today · Stories · Search · Watchlist · You); desktop footer.
- Subject navigation (chip rail on the phone, left rail with codes and counts on desktop); scope chips (All / your state / National / World); section head with its counted subline; the Today / For you switch; a step indicator.

**The story atoms.**
- **Story row:** normal, lead, single-source, "read", stale, with and without a photo.
- **Coverage bar:** row and large sizes, the draw-in, and the single-colour variant; its legend; the outlet favicon stack with monogram fallback and "+N".
- **Status pills:** Verified record, Provisional grouping, One source so far, Single origin, Corrected / Disputed.
- **Small marks and chips:** lens dots; language tag (EN·HI, or native script); meta line; entity mark and entity card; CVE / CVSS / KEV / PoC chips; ticker chip; catalyst; price read; "Follow $TICKER" toggle.
- **Quote card:** speaker header; the quote; language label; translation label; "other renderings" group; "in the article" expander; actions.
- **Other record blocks:** report card (full, compact, with thumbnail); the "What changed" timeline; impact row ("Why it matters"); framework/control table (cyber).
- **Lens:** the lens switch (segmented, with a locked tab); the lens brief block (writing / empty / locked-signed-out / samples-used); the brief player (Listen / Pause / Stop, highlighting the spoken sentence).
- **Media:** photo deck (stage, peek cards, credit bar, counter, thumbs); photo pile; podcast clip card, transcript window and now-playing bar; X post card.
- **Story structure:** route map (main line, branches, side stories, stations, tooltip card, vertical on phones); branch tree (MAIN / ALL, collapsed branches); story timeline; related stories; attention chart (sources per day).
- **Pulse:** market digest card; movers list.

**Ask.** Ask bar with suggested questions; the phone Ask button; the "Ask about this" selection chip; the panel (phone bottom sheet / desktop right drawer); "Dig deeper" chips; streaming answer with caret; citation chips and list; answer table; the "Not in sources" refusal; limit notes; error.

**Money.** Plan card (all 8 states, plus inline confirms); payment row; pricing card (recommended / free / founding / sold out); Monthly / Yearly switch with its saving; comparison table; FAQ accordion; trust line; cancel sheet; upgrade sheet; welcome.

**General UI.**
- **Buttons:** primary (one per screen), secondary, ghost, text, destructive, icon.
- **Fields:** text/email input, native select, grouped select, checkbox, toggle rows that open sub-chips, textarea with a limit, consent checkbox.
- **Other:** segmented control; chips; badges; alerts (error, info); toast ("Link copied"); sheet, dialog and drawer; skeletons; empty states; the legal page blocks ("In short", on-this-page list, info cards); 404 / error / offline.

**Labeller.** Task header with count and progress; candidate toggle row; the answer-button set (yes / none / not sure / can't read); highlighted quote in context; practice feedback (Right / Not quite); guide blocks (In short, Do / Do not, verdict-marked examples, How to decide); result screen; batch row; qualify row with status.

**Admin.** KPI tile; chart panel (info control, table toggle, empty); trend chart with the previous period and the uncounted band; stacked bars with legend; ranked bar list; funnel; cohort grid; dot plot; activity strip; k-of-n progress bar; filter switch with counts; search box; ON/OFF state row; audit timeline; data table; "needs you" links; the 3D network frame.

**Outside.** Share-card templates (site, story, quote, trending); email layout.

## 8. Reader surfaces

### 8.0 Chrome and navigation
- **Desktop top bar:** Today · Stories · Pulse · Watchlist; search ("Search stories, people, places", `/` to focus); Plus (hidden for Plus readers and on the landing); theme; Sign in, or an avatar that goes to Account. On the landing, also the primary "Open today's record".
- **On a phone** the top bar is replaced by a masthead or back bar on app screens, plus the bottom tab bar (Today · Stories · Search · Watchlist · You). There are no tabs on the landing, the story page, the entity and subject pages, sign-in, onboarding, Plus or the legal pages.
- **Footer (desktop):** "Prism · Prism Media Intelligence LLP · built with Matrix Social Labs" · About · What's live · Plus · Privacy · Terms · Refunds.
- **Back behaves as back** when the reader came from inside Prism, and goes to Today otherwise.
- **Subjects in the nav today:** All stories, Politics, Business & Markets, Sports, Tech & Cyber, Health & Science, Entertainment, Education, Civic & Safety — each with today's count. (The founders' rule is six first-class subjects; design for a list that comes from data, 6–10 long.)

### 8.1 Landing (`/` for a first visitor; returning readers go to Today) and How it works (`/about`)
Built from live data; nothing is invented.

**The landing:**
1. **Hero:** a kicker ("The live record · India"); "Follow the story, not the headlines."; a pitch; **Open today's record** / How it works; three counted figures (outlets in today's record, languages read, "1 record per story"); the prism light-split figure; the live lead story row with "Live · updated Xm ago". If the data can't load, a fallback card.
2. **What you get on every story — "The record, not a verdict":** three cards running real components on a real story:
   - What changed: the 3 newest reports;
   - Exact words, exact source: a verified quote card;
   - Who covered it: a large coverage bar, legend and outlets.
   Each has its own "live example unavailable" state.
3. **Live now:** story rows 2–5.
4. **See what changed:** a verified story's development list, when one exists.
5. **The signature — "The same facts, read for your work":** the lens list from the API; a lens-flip demo (lenses not yet live are tagged "next"); a scripted Ask demo labelled Illustration (it types, streams an answer with citations, then shows a refusal; reduced motion shows the finished exchange).
6. **"Honest about what's live":** Available now / In validation / Next. Then what's free (the record, sources, verified quotes, story status) versus paid (professional readings, watchlists, alerts).
7. **Final call:** Open today's record — Read today / Set up my feed — "Free. No account needed to read."

**How it works (`/about`):**
- An opening with today's live example story.
- A sticky step rail (desktop) and eight steps. Each step has a RULE chip and a live example fading in on scroll: reports come in → one record → who covered it → who said what → the brief → read it through a lens → ask the record → what Prism refuses to do.
- Step 09: who writes this and how to correct it (a corrections email). Then "Where Prism stands today" (anchor #status) and a final call.

### 8.2 Today (`/feed`) and subject pages (`/sector/[slug]`)
- **The phone masthead dateline** gives the day in IST, and "quiet since {time}" when nothing new has arrived for 12 hours.
- **Controls and heading:** subject navigation with counts; scope chips (All · your state · National · World). The heading "Today" / "For you" / the subject, with "N records · M outlets · newest reporting first". The Today / For you switch appears once the reader has interests.
- **The chart:** story rows, the lead first. On a wide desk, two columns with the lead across both. The row last opened is marked "· read". Scroll position is kept per view.
- **States:** skeleton rows; "Today's record could not load"; empty states worded per filter ("No Politics records today", "Nothing from Karnataka yet today"…).
- **Right rail (wide desktop):**
  - "Developing over days": up to 5 stories with a small coverage bar, "N developments · M outlets · Xh ago", and All developing stories →.
  - "How to read a record": a sample bar and legend, the Verified and Provisional pills, and "A dashed row has one source so far".
- **Story row:**
  - the meta line: subject (or region, never "Other") · time since the last report · language tag;
  - the title in the record voice, and a 2–3 line summary;
  - the outlet's photo with its credit, when it has one;
  - the foot: outlet favicons, coverage bar, "N outlets · M languages", "Heard on N shows", lens dots ("Markets read", "Cyber read").
- A single-source row is visibly different.

### 8.3 The story page (`/story/[id]`, and `/story/[id]/quote/[n]`, which is the same page with its own share card)
**Phone:** a back bar; the sections in one column; a bottom bar with **Ask · N reports** and **Share**.

**Desktop:**
- a left rail "On this story", with counts and the section in view highlighted;
- the 640px reading column;
- a right rail (wide desktop) with "Reports · N" (compact report cards) and "Named in the reports" (entity chips).

**Header:**
- the meta line: status pill (Verified record / Provisional grouping) · updated Xm ago · subject · CVE ids;
- the title;
- the byline ("Headline by Prism · from N reports" or "Headline as filed by {outlet}");
- the summary, with entity marks;
- outlet favicons, the large coverage bar and "N outlets · M languages · K reports · English, Hindi…";
- "One source so far" when it applies;
- the photo deck;
- Share (desktop) and the lens switch ("Read it as", with 1 · 2 · 3 keys on desktop).

**Sections, in this order** (each shown only when it has content):
1. **The record:**
   - The lens brief. Reader: "Written from the N reports below. Nothing here is unsourced." Other lenses: "The same reports, read for …".
   - Bullet points under "What to watch" / "What to check".
   - The brief player.
   - Cyber adds a CVSS chip, KEV listed, PoC public, the attack vector, affected products, a "Required action" box and a framework/control table. Markets adds ticker chips, the catalyst, a price read and Follow toggles.
   - States: writing; none yet; locked (signed out: "Free with an account — Sign in to unlock"); samples used ("You've used your free {lens} reads… Back to the reader view").
2. **What changed:** every report as a timeline, newest first (favicon, outlet, time, [n], headline → the article). 5 shown, then Show all N.
3. **Who said what:** quote cards (section 7).
   - One card per speaker, with their role as the article gave it and "N quotes · M outlets · K languages".
   - Each quote: italic, [n], a native-script language label (+ "translation"), outlet, time, "Open at the quote ↗" (opens the article at the line), Share, "Ask about this quote", and "In the article" context.
   - Other renderings of the same statement are nested: "At most one is the words as spoken."
4. **Heard on:** podcast clips (a card rail; one player; a transcript that follows the spoken word; "Keep listening"; now-playing bar; the lock screen shows the show).
5. **On X:** official posts as written, "First on X" when a post came before any report; "Signal, not coverage: never counted among the outlets."
6. **How this story unfolded / Related reporting:**
   - Verified: a compact route map, "All developments" (the branch tree) and "The whole story →".
   - Provisional: a related-reporting list, "Open this coverage group →".
7. **Why it matters:** impact rows (direction arrow, affected party, effect, time horizon, nested); "Extracted from the reports, never invented."
8. **Coverage:**
   - a large bar with its count and legend, and where the outlets filed from;
   - "No {region} outlet has covered this yet" (personalised);
   - a Single origin tag;
   - "Named" people and places;
   - report cards (8, then All N reports).
9. **Related stories.**
10. **Ask this story:** "Answers cite the reports above, or say they can't." The Ask bar is sticky on desktop.

Footer: ← Today's record · The whole story →.

**Ask** is opened from the bar, the phone button, a text selection ("Ask about this"), a quote, or an entity card.
- It is a bottom sheet on phones and a 420px right drawer on desktop.
- Before the first question: "Dig deeper" chips (Timeline · Every quote · How outlets differ) and suggestions. After an answer: its follow-up questions.
- Answers stream in ("Reading the sources…"), with [n] citation chips, a source list, sometimes a table and a "Not in the reports" line. A refusal is labelled "Not in sources".
- Limit states are listed in section 9.8.

**Entity mark:** the first mention is underlined; hover, or tap on touch, opens a card: the name, kind, their role if quoted, "Quoted N times on this story ↓", "Ask about X on this story", and "All stories about X →".

**Also design:** the loading skeleton (no spinner) and "Story not found".

### 8.4 Stories (`/trending`) and a story arc (`/trending/[slug]`)
**List:**
- Subject filter; state / National scope. "Stories — N developing stories · M moving now · ranked by new reporting."
- **Each row:**
  - the meta line: subject · "moving now" or "moved Xh ago" · "N days";
  - the label, and "N developments across M outlets. Named: …" (for provisional groupings, "related reports");
  - a route glyph (verified only);
  - a fanned photo pile;
  - a coverage bar, "N outlets · M reports" and a Verified / "Grouping under review" pill.
- Stale rows are faded; single-source rows are dashed.
- States: skeleton, error, empty per subject.

**Arc page:**
- **Header:** the pill; subject · moving now · N days; the label; an explanation (verified: "written from its developments"; provisional: "related reporting… no chronology implied"); a large bar with "N outlets · N developments · N branched off · N also reported · N days"; the photo deck; Share.
- **Body:** "How this story unfolded" (the route map + an "Attention · sources per day" chart), then "All developments" (the branch tree or a timeline) or "Related reporting" (a dated list).
- **Rails:** "Who reported it" (outlets with counts); "Who is in it" (entity chips).
- Related stories; ← All stories · Today's record →; loading skeleton; not found.

### 8.5 Market Pulse (`/pulse`)
- A dateline with the update time; Market Pulse, with a Watchlist link.
- **The digest card** (in the markets lens hue): "Markets read · written from N stories · updated …", a headline and the narrative.
- **Movers:** ticker chips with a note (link to the watchlist when signed in, to search when signed out).
- **Written from:** story rows.
- States: loading, unavailable. Free to everyone. (There is no price data; never show prices.)

### 8.6 Search (`/search`)
- A large field ("Search stories, people, places", Escape clears, a Clear button), live after 2 characters.
- The hint "Stories · people · tickers · CVE ids", or "N results · M outlets".
- With no query: "In the news now" (names) and "Try" examples.
- A subject filter.
- **States:** searching; unreachable; no match; none in this subject. Results are story rows.

### 8.7 Entity (`/entity/[slug]`) and subject (`/subject/[...path]`) pages
- **Entity:** "{type} · N records", the name, "Also written …" (aliases), story rows (the first as lead), and an empty state.
- **Subject:** breadcrumb, label, "N stories", child-subject chips, story rows, and an empty state.
- These use the site header on phones today (no tab bar). Decide the phone chrome for them.

## 9. Accounts, onboarding and money

**9.1 Sign in (`/signin`).**
- "Sign in to Prism": "Enter your email and we'll send a one-time sign-in link. No password."
- Email field + **Email me a sign-in link** (Sending…); errors in words.
- Success: "Check your inbox — a link is on its way to {email}. It expires in 15 minutes." The same answer is given whether or not the account exists.
- "or" + **Continue with Google**, with its own error and busy states.
- Small print linking the Terms and the privacy policy. A way out: "Keep reading without an account" / "Back to the story, without an account".

**9.2 Verify (`/auth/verify`).** "Signing you in…" → a new reader goes to onboarding, a returning one back where they were. Error: "Couldn't sign you in", the reason, and **Request a new link**.

**9.3 Onboarding (`/onboarding`)** — three steps with a step indicator (Where you are · What you do · What you follow). Earlier steps can be revisited; "Skip for now" is on every step.
- **Step 1:** "Which state are you in?" — the states grouped as "Local coverage available" and "All states & UTs".
- **Step 2:** "What do you do?" — your name (signed in only); a profession picker (7 groups, ~35 professions). A line under it says which reading it picks ("Reads as …") and that it pre-sets your subjects.
- **Step 3:** "What do you follow?" — six subject rows to toggle, each opening sub-topic chips. Signed in: a consent checkbox (Terms + account creation).
- Buttons: Back / Continue / **Build my feed** (Saving…). Under the card: "Signed in as {email}" or "No account needed. Your profile lives in this browser."
- Languages are not asked today (English only); the API supports languages in order of preference, so the design should allow for a languages step.

**9.4 You (`/you`)** — the phone "You" tab.
- Profile form: state, profession, subjects → **Save and re-sort my record**.
- **Following:** followed tickers and sectors as chips, and up to 3 recent matching stories. Signed out: "Sign in to follow".
- **Account:** theme; the compact plan card; Sign out / Sign in; links to Privacy · Terms · Refunds.

**9.5 Watchlist (`/watchlist`).**
- Signed out: an explanation + Sign in.
- Signed in: a "N followed" dateline and a Market Pulse link.
- Add form: Ticker / Sector + a text field (e.g. RELIANCE) + **Follow**. Followed items as chips with remove.
- Stories on your signals: subject · time · catalyst, the title, up to 4 ticker chips; filter to one ticker ("On RELIANCE" + All signals).
- Empty states for no follows, no stories and no stories for one ticker.

**9.6 Account (`/account`)** — email, **Your plan** (the full plan card), **Payments**, **Your record** (links to profile and watchlist, theme), Sign out. Account deletion is by writing in, which is stated.
- **Payments:** one row per charge — date, plan, amount, PAID / REFUNDED, a link to the Razorpay invoice. Error text if Razorpay can't be reached.
- **The plan card has one status line and one action per state:**

  | State | Status line | Action |
  |---|---|---|
  | Free | "Every record, source, quote and clip. 10 questions a day." | Get Plus |
  | Active | "Renews {date}"; while the 7-day refund window is open, "Full refund open until {date}" | Cancel, and Refund inside the window |
  | Ending | "Ends {date} · no further charges", or "then Plus · yearly from {date}" after a switch | — |
  | Paused | "Plus stays on until {date} · resumes {date}" | Resume now |
  | Past due | "the last charge did not go through · Plus stays on while Razorpay retries" | "Check your email" tag |
  | Halted | "Paused after repeated failed charges · reading stays free" | — |
  | Refunded | "Refunded ₹X · reaches your bank in 5–7 working days" | Get Plus |
  | Lapsed | "Your Plus ended on {date}." | Get Plus |

  Cancelling a yearly or founding plan, and a refund, are confirmed inside the card ("Yes, cancel" / "Keep Plus"). Errors are shown in words.
- **The cancel sheet** (monthly; a bottom sheet on phones, a dialog on desktop):
  - "Before you go" — "You keep Plus until {date}".
  - An optional reason: Not using it enough · Too expensive · Missing something (opens a one-line box) · Something else.
  - **One offer matched to the reason:** pause 1 / 2 / 3 months, or switch to yearly (price, saving, "starts {date}, nothing charged twice", 7-day refund).
  - **Cancel anyway** is always beside the offer, with "One click, any time · no calls, no forms".
  - Done states for pause / cancel / switch. A declined card: "try UPI or another card".

**9.7 Plus (`/plus`).**
- "Prism Plus · Launch offer · until {date}", the headline "Ask more of every story."
- Monthly / Yearly switch (Yearly is the default and shows "save ₹X").
- **Three plans:**
  - **Plus** (recommended): 100 questions a day, the stronger model, answers from the whole story, Ask stays on when the free tier rests.
  - **Free**: ₹0; everything to read; 10 questions a day with an account, 3 without.
  - **Founding member**: ₹999/year, "{left} of 500 seats · price locked 3 years". When the seats are gone: "All seats are taken. Thank you."
- **What the plan buttons say, depending on who's looking:** Your plan / loading / Opens soon / Sign in to continue / Opening…
- A "Side by side" comparison table (6 rows); "Before you pay" FAQ (6 questions); a closing call to action; the trust line (Razorpay · UPI Autopay, cards, net banking · GST included · cancel any time · Refund policy · Terms).
- Payment is Razorpay's own sheet.

**9.8 The upgrade sheet at the Ask limit.**
- **Ask's limit notes:** "You have asked N of N questions today — Plus is 100 a day →"; "Ask is resting for free readers today. Back at midnight UTC — Plus stays on →"; for anonymous readers, "That was your last free question here — Sign in for 10 a day →"; "One question at a time — try again in a minute".
- **The sheet:** "Prism Plus · N of N today", a heading matched to the reason, three check lines, **Get Plus · ₹X a month** (or Sign in to get Plus), "All plans →", small print, and a done state.

**9.9 Welcome (`/plus/welcome`).** "You're on Plus." — what is now on, next charge, where the receipt is, how to change your mind. Buttons: Continue reading / Back to the story + Your account.

**9.10 Legal pages (`/privacy`, `/terms`, `/refunds`).**
- **Desktop:** an "On this page" numbered list with the current section highlighted as you scroll.
- **Main column:** "Last changed {date}", the title, the intro, then each section with an "In short" one-liner before its paragraphs.
- **Wide screens:** an "In short" card, a "Who is behind it" card (the LLP, contact, date), and an "Also" card.
- **Phone:** section chips and the "In short" card above the text.

**9.11 Not in the product today** (design only if asked; mark it PROPOSED): notifications/bell, push, in-app account deletion, changing your email, a daily brief email, custom 404 / error / offline pages (Next.js defaults are used today — **design these**), and loading skeletons beyond the story and trending pages (**design these**).

## 10. The labeller workspace (`/label`, `/label/learn/[kind]`, `/label/[key]`)

Private: not linked from the site, not indexed; a labeller is given the URL. It has no site navigation on phones. Today it is a single 720px column of rules and type. The five task kinds, each a question:
- **story_boundary:** "Is this the same story?"
- **event_identity:** "Is this the same happening?"
- **topic_relation:** "Is this the same topic?" (useful related context)
- **claim_attribution:** "Who said this?"
- **quote_rendering:** "Same statement, or a translation?"

**10.1 Signed out.** "Label for Prism", a short pitch ("each task is one question, about a minute"), and one button: **Sign in to apply**. No guide content is visible to anyone who hasn't applied.

**10.2 Apply** (signed in, not applied).
- "Which languages do you read well?" — checkboxes for 10 languages (English, Hindi, Kannada, Tamil, Telugu, Marathi, Bengali, Gujarati, Punjabi, Urdu), each with its native name. Helper text: "You will only be given tasks in these."
- An optional note (500 characters) and an **Apply** button (disabled until a language is ticked).
- Error alert. The line "A short guide to each kind opens once you have applied".

**10.3 Applied, waiting.** "Your application is in — a founder reads every application." A "You read: … · Change" line reopens the language form. Links to the five guides ("Learn the tasks").

**10.4 The workspace** (approved).
- **Waiting for you:** counted links ("N tasks ready in your languages", "N tests you can take"), or "Nothing right now".
- **Ready to label:** one row per batch (name, its question, notes, "answered of eligible done · N labellers", How this task works, Start / Continue).
- **Done:** finished batches.
- **Learn and qualify:** per kind — status (Passed / Best so far X%, retake after [date] / Not passed yet / Not taken yet / Test coming soon), then Read the guide, Practise, Take the test. The intro reads "Pass it (90%) and that kind of work appears above".
- **Learn the tasks.**
- **Errors in words:** pass the test first; batch closed; no tasks in your languages; access revoked; retake after 24 hours; not enough questions in your languages yet; storage blocked.

**10.5 The guide** (`/learn/[kind]`, and a primer shown once before the first task of each batch).
- The question as the title, "About N minutes to read", **In short** (one-sentence rule), the lede, **Do** (check icons) and **Do not** (dash icons).
- **Examples** with a verdict word beside an icon (WRONG / MISSED / TICK / DO NOT TICK / SAME / TRANSLATED / NOT SURE…). Invented examples are marked ILLUSTRATION.
- **How to decide:** worked yes/no blocks, told apart by rule weight, not colour.
- Buttons: "I have read this — start" / "Back to your workspace".
- States: signed out, must apply, loading, failed with Try again.

**10.6 The task screen** (common frame).
- Header: batch name, a mono count ("005 / 40") and a thin progress rule.
- States: loading, error + Try again, batch closed, done ("That's everything — N judgements. Thank you"), "can't label this right now" (checks below 80% or paused, with Open your workspace), and the round result.

**10.7 The task screen, per kind.**
- **Story / happening / topic:**
  - The seed headline (for a happening, also the outlet's own native-language headline), with provenance (date IST, outlets, up to 3 actors) and a prompt.
  - Candidate rows are toggles: marker, headline, provenance, the signals that proposed them (never a score), and a number.
  - Actions: **Yes — N selected** / None of these; Not sure; Can't read this.
  - On desktop: keys 1–N toggle, Enter submits. A footer rule and a collapsible How to decide.
- **Who said this:**
  - The article title; "Does this article attribute the highlighted words to [speaker]?"; how the article opens; the quote highlighted in its surrounding text; "Read the whole article" expander.
  - Actions: **Yes — [speaker] said it** / No — someone else, or nobody / Not sure / Can't read this. How to decide is open on question 1.
- **Same statement or a translation:**
  - One or two quotes in italic, each captioned with its language and outlet; the question "Is this the same statement by X?" or "Did X say this in [language]?"; a rule line.
  - Actions: Yes / No in the task's words, Not sure, and "I can't read [language]" (only when a quote isn't English).
- Answer buttons disable while saving.

**10.8 Practice, tests, hidden checks.**
- **Practice:** unlimited, with feedback after each answer — "Right." / "Not quite." (icon + rule weight), the expected answer, the explanation, Next question.
- **Test:** 15 questions in the labeller's languages, no feedback until the end, pass mark 90%, retake after 24 hours with new questions. Result: "You passed." / "Not this time." with "X of Y right", the misses with explanations, and Back to your workspace.
- **Hidden checks** inside work: if accuracy on the last 20 falls below 80%, the kind is withdrawn and the labeller must retake the test.

**10.9 Paused and removed.** "Your labelling is paused" or "Your labelling has ended", with a contact email. No batches.

**10.10 Invite and self-join links** (`/label/[key]#token`).
- A founder's named invite: greeted by name; anonymous (no account, no language gate); answers can be changed.
- A self-join link: "Help us teach Prism what one story is", "Your first name", Start. "Your name is only used to remember where you got to".

**Design asks for this area:** one decision per screen; answers thumb-reachable and large; verdicts in words with an icon, never colour; a clear route back to the workspace from every end state (missing today); language shown on every quote; fast on a mid-range Android phone on a slow connection.

## 11. The founders' admin dashboard (`/admin/*`)

Founders only: a signed-in account whose email is on an allowlist. States: checking access; signed out ("Sign in with a founder account"); forbidden ("This area is for Prism's founders"); cannot reach the API. Every change made here is written to an audit log with the founder's email. Desktop first, and it must work on a phone. Nav: Overview · Coverage · Labellers · Batches · People · Controls · Audit, plus the signed-in email.

**11.1 Overview (`/admin`).**
- Title, the date range in IST, and when visit counting began. Period switch: 7 / 28 / 90 days. "Weekly CSV" download (for investors).
- **Needs you:** counted links to what is waiting (applications to read, practice rounds or tests not published, work batches without a language gate). Says "Nothing is waiting on you" when empty, and "Could not check" (never "nothing") when the check fails.
- **8 headline tiles:** visitor-days, new accounts, active accounts, questions asked, paying subscriptions, MRR (₹), reports fetched, stories formed. Each shows the figure, its change against the previous period ("+3 from 4" below 30, "+12%" above; arrow and words, not red/green), a sparkline, and an info control naming where the number is counted. An uncounted figure is "—" with "Not counted yet".
- **Sections, each a grid of chart panels; supply first:**
  - **Supply:** reports fetched (trend, previous period dashed); stories formed (trend); stories two or more outlets reported (trend); what happened to the reports fetched (stacked daily: kept, duplicate, not relevant, not read yet); relevant reports by language (ranked bars); in figures (reports kept, outlets with a relevant report, LLM balance in $, last report taken in); **who reports first** (dot plot: each outlet's median hours behind the first report of a shared story, dot size by stories, "first on k of n").
  - **Visits:** visitor-days, page views, arrivals, shares (trends); where visits came from (stacked daily by source); views by kind of page; what was shared (ranked bars).
  - **Sign-ups:** new accounts (trend + previous period); all accounts (running total); accounts by profession; accounts by state.
  - **Engagement:** active accounts; questions asked; lens opens (trends); how Ask was opened; lens opens by lens (stacked); **retention cohort grid** (sign-up week × weeks after, cells shaded by share but printing counts; a week with no full record is blank with a dashed edge).
  - **Money:** the way to paying as a funnel (saw the upgrade prompt → opened the Plus page → started checkout → paid, with "k of n went on" between steps); paying by plan; in figures (paying, MRR, complimentary, started, ended).
  - **Demand:** hit the free question limit (trend); who hit the limit; locked lenses opened; languages accounts read; in figures (opened a locked lens, saw the upgrade prompt, applied to label).
- **Every panel:** a title, an info control (where it is counted, plus a note), a "Table" toggle that turns the chart into its numbers, and an empty state in words ("Not counted yet: counting begins with the first visit"). Days before counting began are shaded "not counted". Charts have hover tooltips (value first) and a legend whenever there are two or more series.

**11.2 Coverage (`/admin/coverage`).**
- Which outlets reported the same stories. Period switch.
- Tables: stories reported in two languages (a language pair, stories in both, and each language's total); strongest links (outlet pairs, stories both reported); outlets (language, stories, "also reported elsewhere" as k of n).
- **A 3D network**, loaded only when opened: an outlet is a sphere sized by its stories and coloured by language; lines join outlets that share stories, darker the more they share. Drag to turn, scroll to zoom; it turns slowly unless reduced motion is on. Labels on the largest outlets and on hover; a language legend. Outlets with no shared story are left out, with a line saying so. Without WebGL it shows a sentence instead.

**11.3 Labellers (`/admin/labellers`).**
- **Waiting for approval:** email, name, the languages they read, their note, when they applied, answers so far; Approve / Decline.
- **Labellers:** search by email or name; filter by status (All / Active / Paused / Removed, each with its count); Pause / Resume / Restore / Remove (with a confirm: answers are kept, every kind is withdrawn).
- **Standing per kind:** a card per labeller. For each task kind: passed / granted / not passed; hidden checks right as a bar with "k of n"; best test score; attempts; who granted it; Grant / Withdraw.
- **Forms:** "Qualify without a test" (pick a labeller and a kind; recorded as a grant, never a score); "Add a labeller" (account email + the languages they read; active at once).

**11.4 Batches (`/admin/batches`, `/admin/batches/[key]`).**
- A progress board in three groups: Work, Practice rounds, Tests. Search by name or key; filter All / Open / Closed / On the dashboard, with counts.
- Each batch: name, the task's question, badges (Open/Closed, On the labeller dashboard, Anyone with the link can join), bars for tasks answered (k of n) and tasks with a language gate, then key · answers · people · created.
- Actions: work batches — List on / take off the dashboard, Open / Close, Fill in languages. Practice rounds and tests — Review and publish, Unpublish.
- **The review editor** for a practice round or test: every item (speaker, quote, the answer) with an editable explanation; a quality check (can a constant strategy pass? items missing? scores) that must pass before publishing; Save.

**11.5 People (`/admin/people`).**
- Every account, newest first: email; what they told us (name, profession, state, languages); a plan badge (Plus / Given / Free, with the plan and its status below); a 28-day activity strip (one mark per day active); days active and the last day; labeller status; the day they joined.
- Search (email, name, profession, state) and a plan filter with counts. The title never shows a total above rows that aren't all loaded ("newest 500 of 812").

**11.6 Controls (`/admin/controls`).**
- **Collect now:** asks the worker to collect new reports (with a confirm; recorded; says so if collection is switched off).
- **Switches:** read-only, never toggles (they are changed in the server's environment). Each is a row: what it does, its name, and ON (solid) or OFF (dashed), plus a count of how many are on. Numeric limits are listed apart.

**11.7 Audit (`/admin/audit`).**
- A timeline grouped by IST day, with the count per day. Each change: the time, what it was in words ("Filled in a batch's languages"), the target, then the code, the founder and its details in mono. Filter by area (Labellers / Batches / Collection) with counts.

## 12. Outside the app

**12.1 Share cards (1200×630 Open Graph images)** — for the site, a story, a quote (every quote has its own address and card) and a trending group. They show the record's voices and the coverage bar in its slot colours. Never a publisher's photograph.

**12.2 Icons** — the favicon and the app icon (1024) from the mark unchanged. The lockups exist in charcoal and ivory (`web/public/brand/`).

**12.3 Transactional emails** (light only; must render in Gmail and Outlook; each has a plain-text twin).
- **Shared layout:** preview text; a 520px card with the mark + "Prism" and the site host in mono; a divider; a mono line (plan · price · date); a title; paragraphs; a facts table with mono labels; one accent button; an optional mono aside; a footer saying why it was sent; and the closing line "Prism · Prism Media Intelligence LLP · Follow the story, not the headlines."

| # | Subject | Sent when | Facts | Button |
|---|---|---|---|---|
| 1 | Your Prism sign-in link | sign-in requested | "one-time link · 15 min"; the link to paste | Sign in to Prism |
| 2 | You're on Prism Plus | first charge | plan, next charge, receipt, changing your mind | Your account |
| 3 | Your yearly Plus is set | yearly set to start later | plan, starts, first charge | Your account |
| 4 | Prism Plus is back on | pause ended | plan, next charge | Back to the record |
| 5 | A Prism Plus charge did not go through | payment failed (grace) | plan, Plus stays on until | Your account |
| 6 | Prism Plus is paused | halted after failed charges | — | Plus |
| 7 | Your Prism Plus will not renew | cancelled outside the app | — | Plus |
| 8 | Your Prism Plus has ended | ended | — | Plus |
| 9 | Your Prism Plus is set to end | reader cancelled | ends, further charges: none | Your account |
| 10 | Prism Plus is paused | reader paused | stays on until, no charges, resumes | Your account |
| 11 | Refunded: ₹X for Prism Plus | 7-day refund | refund + reference, reaches you, Plus ended | Back to the record |

Razorpay sends its own receipts and invoices.

## 13. What is wrong with the current design (fix in the redesign)

- The founder's brief for earlier redesigns: the product read as dull, and readers couldn't tell what Prism is for from the first screen.
- Contrast misses: light `ink-3` on the page ground is 4.34:1, and white on the accent fill in dark mode is 4.02:1 (both need 4.5:1).
- A second gradient crept into the header line (the mark's band should be the only one), and some eyebrows/labels are set in the mono voice, which breaks the three-jobs rule.
- The labeller workspace and admin were styled separately from the reader product; the new system should cover all three as one family.
- Desktop underused the screen before the wide-desk layout. Width should buy evidence beside the record, never longer lines.
- **Inconsistencies in today's product to resolve, not copy:**
  - The landing lists watchlists as paid, while the watchlist page says "Free with an account".
  - The refunds page says paid plans are not on sale yet, while Plus is live.
  - Entity marks link to search instead of the entity page.
  - On a story arc on a phone, the share bar and the tab bar can overlap.
  - `/you` does not show the saved profession.
  - Onboarding never asks for languages.
  - The labeller "done" and "closed" screens have no way back.
  - There are no designed 404, error or offline pages.
