# Prism — Marketing and launch plan

**Version 1.1 · 29 September 2026 · owners: founder (Tejas ShylaShashidhara, CEO), eng (CTO)**

*1.1 adds the Marketing page in the admin (§5.3, §11.1): tracked links, short links, post
drafts and share images for every platform, and what each link brought.*

This is the team's plan for taking Prism from a working product to a public launch, and to a
paid launch after that. It comes from an audit of the whole product against all 50 skills in the
marketing-skills set (SEO, AI search, schema, programmatic SEO, site architecture, copywriting,
CRO, pricing, paywalls, signup, onboarding, email, analytics, launch, PR, social, competitors and
the rest; §13 lists every one and where it stands).

**Rules this document keeps.** Every number is either measured, and says where it came from, or
labelled an assumption. Nothing here invents a user count, a testimonial, a press mention or a
benchmark (`PRODUCT.md`, "Absences"). The repository is public, so nothing here is secret.

---

## 1. Summary

**Where Prism stands (29 September 2026).**

- The product is live at readprism.news: one record per story from a public list of **41
  monitored outlets (59 feeds) in English and 12 Indian languages**, quotes shown only when the
  exact words are in the article, coverage counted by where each outlet comes from, a public
  corrections log, and a free record for everyone.
- A first round of marketing work is **live in production** (release 0.0.114.0, PR #246):
  - a landing page that says what Prism is and answers a first visit's questions;
  - search engines now read each story page's title, canonical and robots tags;
  - every page type has its own share card;
  - the Google News sitemap lists every eligible story (107 today, up from 10);
  - "What <name> said" on person and organisation pages;
  - renewal terms beside every price.
- A second round is **built on the `feat/launch-readiness` branch** (release 0.0.115.0):
  - checkout hidden until the live payment keys;
  - the GST breakup shown beside every price;
  - Founding membership recommended while seats last;
  - a Grievance Officer page with a complaint queue;
  - state pages and a day-by-day archive;
  - an opt-in weekly email, plus attribution for launch links;
  - `/press`, `/for-publishers` and an Atom feed.

**What blocks the launch is operations, not marketing.**
- Ingestion has been paused since 28 September 02:11 UTC. The worker's budget guard stops
  collecting when the OpenRouter credit falls under $5.
- Until it runs for seven clean days, nothing below should be pushed publicly.
- The news sitemap empties 48 hours after the last story.

**The plan in five lines.**
1. **Unblock (days 0–14):** credit topped up and seven clean days; search owner steps done; soft
   launch to 20–50 hand-picked readers, with ten interviews.
2. **Free public launch (days 15–30):** Peerlist and LaunchPad India on a Monday, Product Hunt
   that week, then Show HN with an engineering write-up; directory batch 1; the daily social set.
3. **Velocity (days 31–60):** the first monthly counted report, the "Who covered it?" checker,
   comparison pages after counsel, journalism-school workshops.
4. **Paid launch (days 61–90):** the LLP's own merchant account, GST registration and live keys.
   Then Founding membership goes to the email list first.
5. **Every Monday:** a review of what moved, in counts.

**The numbers that decide the business** (§6):
- **Monthly running cost:** about ₹18,000 today.
- **Break-even at regular prices:** about 150 paying subscribers today, about 260 if the
  monitored outlets double.
- **Founding members:** 500 of them cover about 136% of today's running cost, and bring about
  ₹4.1 lakh net up front, roughly 23 months of today's costs.

---

## 2. What Prism is, and how to say it

**Category:** India's verifiable news record. Not "a better aggregator", not "AI news", not
"unbiased".

**Promise:** *Follow the story, not the headlines.*

**What no neighbouring product can truthfully copy:**

| Mechanism | What the reader sees |
|---|---|
| Verbatim or nothing | A quote appears only if the article prints the same words in quotation marks, linked to the line. Indian-language speech reported without quotation marks is labelled "reported", never set as a quote |
| A denominator on every count | "9 of 41 monitored outlets · checked 4m ago", and the full list is public at `/sources` |
| Thin evidence says so | A story only one outlet has is marked "one source so far, not yet corroborated" |
| No outlet ratings | Coverage is counted by where an outlet comes from (English national, Indian-language, international, wire), never left/right |
| Public corrections | `/corrections`, with every earlier version of a record kept |
| The evidence is free | The record, its reports, quotes, coverage and corrections are free forever; Plus sells depth (every professional reading, more questions) |

**Words to use:** record, report, monitored outlets, "k of n monitored outlets", who said what,
word for word, checked against the article, one source so far, correction, Prism's reading.

**Words never to use:** AI-powered, AI news, unbiased, neutral, balanced, fact-checked,
"every outlet", "all the news", both sides, blindspot, real-time, breaking, first, trusted (as
self-description), any lens list in generic copy (the set grows), any user count, testimonial,
press mention or benchmark. The address is written `readprism.news` in text; the lockup
(readPrism.news) is artwork. The context file every marketing skill reads is
`.agents/product-marketing.md`.

---

## 3. Who it is for

| Audience | What they want | What Prism gives them | Where they are |
|---|---|---|---|
| **The general Indian reader** (phone, signed out, arrives from a shared link or a search) | What happened, and to see that a story has more than one side without reading six outlets | One page per story; who said what, word for word; who covered it | WhatsApp groups, Google, X |
| **Markets professionals** (traders, analysts, finance creators) | The companies named, and what was actually said, before acting | The markets reading of a story; "Companies in today's reporting". No prices, no advice | LinkedIn, X finance, Telegram |
| **Cyber and GRC professionals** | Whether a reported incident matters to them | The security reading of a story | LinkedIn, infosec X |
| **Journalists, researchers, students** | Provenance: the exact words, where they were printed, how to cite | Quote pages with "Open at the quote", a citation format, the public outlet list | X, journalism schools |

**Not for:** readers who want US left/right bias ratings, a 60-word skim, a fully Indian-language
interface today, stock tips or prices, or fact-check verdicts.

**The gap to close first:** there is no customer language yet (no interviews, no reviews). The
soft launch (§8) exists to collect it; `.agents/product-marketing.md` v2 records it.

---

## 4. The competition

Prices as listed on the App Store (India) or the product's own site, checked 29 September 2026.
"Not stated" means the product's pages don't claim it, **not** that it is absent.

| | Job | Price in India | Rates outlets | Verbatim-quote rule | Public outlet list |
|---|---|---|---|---|---|
| **Prism** | One record per story, evidence attached | Record free; Plus not on sale yet | No, by design | Yes | Yes (`/sources`) |
| Ground News | Bias and factuality ratings; coverage comparison | ₹79–₹899 a month | Yes (averages three US rating bodies) | Not stated | Claims 50,000+ sources |
| Particle | AI summaries, bias spectrum, Ask | ₹299 a month | Bias spectrum | Not stated | Not stated |
| Google News | Discovery; Full Coverage | Free | No | Not stated | Not published |
| Inshorts | 60-word summaries | Free | No | Paraphrase-first | No |
| Dailyhunt | Vernacular feed, 14 languages | Gold ₹399 a month | No | Not stated | No |

**Where Prism loses:** breadth, reading in your own language (display is English-first;
translation is held, D-d), polish and audio, and habit. **Where it wins:** the mechanisms in §2,
which none of them state.

**Comparison pages** (`/compare/ground-news`, `/alternatives/ground-news`,
`/alternatives/inshorts`, `/compare/google-news`, `/compare/particle`) are outlined in the
audit and **wait on counsel**. Comparative advertising in India falls under the Trade Marks Act
s.29–30, the ASCI Code (Chapter IV) and the CCPA 2022 guidelines. Never publish a "vs" page
against an outlet Prism monitors: they are sources and partners. `/for-publishers` says what
Prism takes and gives back instead.

---

## 5. What has been built for the launch

### 5.1 Live in production (0.0.114.0, PR #246)

| Area | What changed |
|---|---|
| Landing copy and CRO | Category eyebrow; plain subhead; one label for the way in ("Read today's record"); "Free to read. No account, no sign-up." beside the buttons; the trust checks (public outlet list, public corrections, the LLP); "What Prism won't do"; nine-question FAQ with FAQPage structured data; "Live" only while the newest report is under three hours old; the typed "1 record per story" figure removed |
| Search engines | Story and arc pages had put their title, canonical and robots tags in `<body>`, where Google ignores a canonical, and answered missing stories with a 200. Fixed: tags in `<head>` for every crawler, real 404s and redirects |
| Share cards | Every page shares its own card and address (eleven page types used to share as the homepage) |
| Structured data | Organisation identity (`alternateName` readprism.news, corrections and feedback policies); publication date is the first report's time |
| Crawl budget | Links to pages that ask not to be indexed carry `nofollow`, so hubs spend links on pages that can rank |
| Site architecture | Sector pages list their sub-topics; stories link their subject (37 subject pages nothing linked to are reachable) |
| Google News sitemap | Every indexable story first reported in the last 48 hours (107, up from 10) |
| Person pages | "What <name> said": verbatim quotes checked exactly as the story page checks them |
| AI search | Training crawlers refused (Google-Extended, CCBot, GPTBot, ClaudeBot and others); citing crawlers allowed (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot); `llms.txt` rewritten |
| Plus and sign-in | Renewal terms beside the founding price and above the payment button; the welcome email sells the lenses and Ask, never a model; "3 a visit" where it said "3 a day" |
| Security | An open redirect after sign-in closed |

### 5.2 Built on `feat/launch-readiness` (0.0.115.0)

| Area | What it does |
|---|---|
| Checkout hidden | No checkout while production runs on test payment keys (`checkout_ready` false; checkout answers 503) |
| GST breakup | Every price offered for sale shows its GST, e.g. "₹149 a month, including ₹22.73 GST (18%)" |
| Founding membership | Recommended while seats last; "Limited to 500 members"; "Your price is kept for as long as you stay subscribed" |
| Plus page for crawlers | Prices in the server HTML; FAQPage structured data; "What does my subscription pay for?" |
| Grievance Officer | `/grievance`: Tejas ShylaShashidhara, Grievance Officer (Chief Executive Officer), grievance@readprism.news; a complaint form with a reference number, acknowledgement by email with a copy of the complaint, decision within 15 days, a public monthly count; "Something wrong?" on every story feeds the same queue |
| Legal pages | `/delivery` (Razorpay's required page); privacy and terms name the officer |
| State pages | `/state/<name>` for every state and union territory, indexed at 20 or more stories from two or more outlets in 30 days (15 pass today: Karnataka, Kerala, Telangana, Maharashtra, Delhi, Uttar Pradesh, Andhra Pradesh, Tamil Nadu, West Bengal, Odisha, Bihar, Madhya Pradesh, Gujarat, Jammu and Kashmir, Punjab), and `/state` as the index. A person page named after a state now redirects to its state page |
| Day archive | `/feed/<date>` and `/archive`; indexed at 20 or more stories from two or more outlets (18 of the 25 days Prism read pass); a day Prism did not read says so, and a partly read day prints its reading window |
| Weekly email | An opt-in "The week's record", Sunday morning IST, off until the founder switches it on; one-click unsubscribe; a welcome email for a new account |
| Attribution | Launch links carry `?ref=<channel>` and are counted; one inline "Where did you hear about Prism?"; a one-question "Could you check this story for yourself?" survey |
| Share cards | Story cards print "k of n monitored outlets"; every card has alt text |
| `/press`, `/for-publishers`, `/feed.xml` | A press page with the asset kit and how to cite; what Prism takes from and gives back to outlets; an Atom feed of stories from two or more outlets |
| `/healthz` | Reports the pipeline as stalled when nothing was read (liveness still "ok") |
| Plus FAQ and `llms-full.txt` | The Plus questions also feed `/llms-full.txt`, the long version of `llms.txt` for answer engines |

### 5.3 Built on `feat/admin-marketing` (0.0.116.0)

| Area | What it does |
|---|---|
| Marketing page | `/admin/marketing`, in the admin's left nav: pick any public page (a story, a quote, a person, a state, a day, the front page, Plus), pick a platform, add a campaign; get a tracked link and a short link |
| Short links | `readprism.news/go/<code>` opens the page with its tags. Six characters, no 0/o or 1/l/i, so it can be read off a phone and typed. A posted link keeps working after it is archived |
| Post drafts | Written only from the page's own facts ("Reported by 9 of 41 monitored outlets…"), cut to fit X (a link counts as 23 characters), no link in an Instagram caption; one tap opens X, WhatsApp, Telegram, LinkedIn, Facebook, Threads, Reddit or email with it |
| Share images | Every page's link preview, plus Instagram's post (1080 × 1350) and Story (1080 × 1920) shapes to download. People, state and day pages now have their own cards (their counts as figures; no coverage bar, since those pages list only their newest records) |
| What each link brought | Visits, then in the same tab: a second story, a sign-in asked for, an account made, the Plus page, the weekly email. On Marketing per link, by platform and by campaign; on the Overview as "Founder links"; on People as one line |
| Returning readers | A link to the front page keeps its tags when a returning reader is sent on to `/feed` (it used to drop them) |

---

## 6. Pricing and packaging

### 6.1 The plans (unchanged by this review)

| Plan | Price (GST included) | When |
|---|---|---|
| Free | ₹0, no account needed to read | Always. The record, reports, quotes, coverage and corrections are never paid |
| Plus, monthly | ₹149 a month at launch, then ₹199 | Launch price for 90 days after the paid launch or the first 1,000 subscribers |
| Plus, yearly | ₹1,199 a year at launch, then ₹1,499 | As above |
| **Founding member** | **₹999 a year, 500 seats** | Only during the launch offer and while seats last |

Every plan renews at the price the reader joined at, until they cancel (D-b). Yearly and
founding charges are refundable in full within 7 days.

### 6.2 What it costs to run Prism

| Input | Value | Where it comes from |
|---|---|---|
| Model spend for the news pipeline | $134.48 from 1 to 29 September, about $4.6 a day. That includes one-off repair backfills and 1.5 paused days. On 27 September, a full day after the cost cuts: $4.34 for about 4,100 articles, about **$1.05 per 1,000 articles** | OpenRouter key usage; the spend ledger (`/admin/spend`) |
| X (Twitter) API shadow poller | About $0.90 a day (about $27 a month). The feature is not live | Worker logs, 29 September |
| Vercel Pro | $20 a month base | Plan |
| Railway (API, worker, Postgres, Redis, Langfuse) | $40–80 a month. **Not measured**: the founder should read the billing page | Estimate |
| Resend (email) | $0 up to 3,000 emails a month, $20 above | Plan |
| Domain | About $3 a month | Estimate |
| Payment fees | Razorpay 2% plus 18% GST on the fee = 2.36% of each charge (verify at the LLP's signup) | `docs/BUSINESS-MODEL.md` |
| GST | 18%, inside every price | `docs/COMPLIANCE-INDIA.md` |
| Model spend per Plus subscriber | ₹10–40 a month. An answer costs about $0.003; lens readings are written ahead once per story | `common/quota.py` |
| Exchange rate | ₹88 = $1 (an assumption; update it on the day) | — |

**Monthly running cost:**

| Scenario | Monthly cost |
|---|---|
| Today, without the X poller | $203, about ₹17,900 |
| With the weekly email on Resend's paid plan and the X poller on | $250, about ₹22,000 |
| Monitored outlets doubled (about +$130 of model spend) | $353, about ₹31,100 |

### 6.3 What one subscriber brings in

Net = price ÷ 1.18 (GST) − 2.36% (fees). Contribution = net − ₹20 of model spend (the middle of
the ₹10–40 range).

| Plan | Net per month | Contribution per month |
|---|---|---|
| Monthly ₹149 (launch) | ₹123 | ₹103 |
| Monthly ₹199 (regular) | ₹164 | ₹144 |
| Yearly ₹1,199 (launch) | ₹82 | ₹62 |
| Yearly ₹1,499 (regular) | ₹103 | ₹83 |
| Founding ₹999 | ₹69 | ₹49 |

### 6.4 Break-even

| Paying subscribers needed | Today (₹17,900 a month) | Outlets doubled (₹31,100) |
|---|---|---|
| Launch mix (50% founding, 40% monthly, 10% yearly) | about 250 | about 430 |
| Regular prices (60% monthly, 40% yearly) | about 150 | about 260 |
| 500 founders alone cover | 136% | 78% |

**Sensitivity:**
- At ₹40 of model spend per subscriber, launch-mix break-even is about 350 today, and 500
  founders cover 80%.
- At ₹10, it is about 220, and founders cover 164%.

**Rule for adding sources:** each monitored feed brings about 70 articles a day and costs about
$2.2 (₹194) a month to read. **Every 10 new feeds need about 16 more subscribers at regular
prices.** Business and technology outlets are the exception worth prioritising: they are also
what makes more stories carry a markets or security reading. Today only 5 of 40 sampled stories
offer a professional lens, and that reading is what Plus sells.

### 6.5 Decision: keep the prices, reposition Founding

1. **Keep ₹999 for Founding.** It sits under the ₹1,000 line that Indian pricing clusters
   below. 500 seats cover today's running cost with a third to spare, and the ₹4.1 lakh net up
   front is roughly 23 months of today's costs. Raising it to ₹1,199 would make it the same price
   as launch Plus yearly, so it would stop being the reward for joining early.
2. **Founding is the recommended plan while seats last** (built). Before, the page recommended
   Plus yearly at ₹1,199 beside Founding at ₹999 for the same thing, which invites the reader to
   ask why, and could read as steering under the dark-pattern guidelines.
3. **The founding card sells the lock honestly:** "Your price is kept for as long as you stay
   subscribed, as Prism adds outlets and languages." The Plus FAQ says what a subscription pays
   for: reading more of India's news.
4. **Keep ₹149/₹199 monthly and ₹1,199/₹1,499 yearly.** Regular break-even is about 150
   subscribers today. The Hindu (₹299) and Particle (₹299) sit above; Ground News starts at ₹79.
   Never show a struck-through "regular" price that has not been charged for 30 days (the
   prior-price rule).
5. **Review at the end of the launch offer** (90 days or 1,000 subscribers). Re-run this model
   with measured Plus model spend, conversion and the annual share. Consider ₹249 regular only if
   lens coverage per story has grown with the sources.

### 6.6 Cost hygiene before any traffic

| Action | Why | Owner |
|---|---|---|
| Turn the X poller off until its gold gate is near | About $27 a month for a feature readers can't see | eng |
| Lower `ASK_DAILY_CEILING_USD` from $25 to $5 until revenue covers it | The worst case for free Ask is $25 a day (about $750 a month), more than all fixed costs | eng |
| Move Resend to the paid plan when the weekly email passes 3,000 sends a month | The free tier's daily cap would delay sends | founder |
| Watch Vercel function invocations against the 144–177k a day baseline | Crawler rendering caused the 27 September fair-use block | eng |

---

## 7. Channels

| Channel | Role | How | Caution |
|---|---|---|---|
| **Search (Google, Bing)** | The compounding channel | Hundreds of new story pages a day with sourced text and structured data; indexable only from a story's second outlet; person, subject, state and day pages; the four sitemaps; IndexNow for Bing | Nothing moves while ingestion is paused. Indexing, not ranking, is the first number to move |
| **Answer engines** (ChatGPT search, Perplexity, Copilot, Google AI Overviews) | Being cited | Citing crawlers allowed; `llms.txt` and `llms-full.txt`; FAQ and Quotation structured data; Bing Webmaster AI Performance report | Measure monthly with 3 runs per query (§11) |
| **WhatsApp Channel** | India's sharing rail | One record card and one quote card a day | Stories from two or more outlets and direct quotes only |
| **X** (journalism and media community) | Trust story, newsjacking | Founder builds in public; the brand account posts the daily set (§7.1) | Never dunk on outlets; never "fact-check" anyone |
| **LinkedIn** (markets and cyber) | The paid audience | Founder posts three times a week | **SEBI:** what was reported and said only; no direction, targets or "stocks to watch"; check every ticker by hand |
| **Peerlist, LaunchPad India** | Indian builders | Mondays | Launch from the founder's profile |
| **Product Hunt** | Backlink and credibility | 3-week warm-up; launch Tuesday–Thursday at 12:31 PM IST (1:31 PM after 1 November); ask for feedback, not upvotes | Global audience; little Indian readership |
| **Show HN, r/developersIndia, dev.to** | Technical credibility | An engineering write-up ("a quote appears only if its exact words are in the article") | Hype gets flagged; any internal figure needs founder sign-off with its n |
| **r/india** | Reach | Only a genuine "I built this" post if the sidebar allows it | **Never post as the brand in r/IndiaSpeaks** or any political community |
| **Email** ("The week's record") | Retention; the owned channel | Opt-in from the landing and the account page | Explicit consent; unsubscribe in every send |
| **PR** | Credibility and links | §7.3 | Grievance Officer page and a correction runbook first |
| **Paid ads** | Not now | Under the business model's own assumptions the ceiling is about ₹3.5 a visit; revisit after the paid launch | Never advertise a political record |

**Every post a founder makes uses a link from `/admin/marketing`**, one link per post, so each
post can be read on its own (§11.1). Reader shares keep their own `?s=` marker.

### 7.1 The daily social set (from live records only)

| When (IST) | Post | Template (edit the words, keep the counts) |
|---|---|---|
| 08:30–09:30 | Most-reported story this morning | "{headline} · {k} of {n} monitored outlets · {m} languages · first report {hh:mm} IST" + the story card |
| 12:30–13:30 | Quote of the day | "“{exact words}” — {speaker}, as printed by {outlet}, {date}. Checked against the article" + the quote card |
| 18:00–20:00, 3× a week | Reported mostly in Indian-language outlets | "Reported by {a} Indian-language and {b} English national outlets so far · {languages}" (never "ignored by English media") |
| Whenever one happens | Correction | "Correction: {what changed}. Reason: {why}. Every earlier version stays public" |
| Sunday | The week on the record | "{records} records · {k} of {n} monitored outlets reporting · {s} single-source · {c} corrections". A day not counted is printed "not counted", never 0 |

Voice checks for every post: no emoji; sentence case; a middle dot between facts; no lens list;
no percentage below 30; no "breaking" or "first"; `readprism.news` lowercase in links.

### 7.2 Directory submissions (after the blockers clear and `/compare` is live)

| Tier | Where | Note |
|---|---|---|
| 1. Launch fortnight | Product Hunt · Peerlist Launchpad · LaunchPad India · Show HN · Fazier · Uneed · Microlaunch | One afternoon |
| 2. Alternatives | AlternativeTo (as an alternative to Ground News, Google News, Inshorts and Particle) · SaaSHub · Indie Hackers | Pages rank for "[X] alternatives" |
| 3. Company profiles | LinkedIn company page · Crunchbase · Tracxn · Startup India (DPIIT; confirm LLP eligibility) | Wikidata only after independent coverage |
| 4. Search and news infrastructure | Google Search Console · Bing Webmaster Tools · Feedly, Inoreader and Feedspot (via `/feed.xml`) | Most important of all (§10) |
| 5. Tech content | dev.to (with a canonical link) · Hasgeek talk proposal | — |
| **Skip** | AI directories (they file Prism as an AI tool); G2, Capterra, TrustRadius (B2B, no fit); press-release farms; BetaList (Prism is live) | — |

Give every surface its own description. Log each submission (date, URL, status, dofollow).

### 7.3 PR

**Angles** (the story is the broken system, never a competitor):
1. **The unsourced quote.** "A news app that refuses to show a quote it can't find in the
   article."
2. **Show the denominator.** "An Indian news record that prints what it doesn't cover."
3. **The monthly counted report:** "What {n} monitored outlets reported in {month}", zeros and
   bad numbers included.
4. **How Indian-language outlets report speech**, and why Prism labels it "reported". This
   uses internal figures: the founder decides whether to publish them, with n and method.
5. **Founding story:** a small Indian team building an evidence layer and keeping the evidence
   free.

**Where to pitch:** MediaNama\*, The News Minute, Newslaundry (media beat), exchange4media,
afaqs!, Inc42\*, YourStory, Entrackr\*, The Ken; internationally Nieman Lab, Poynter, CJR, GIJN.
Before pitching, read each reporter's last five pieces. \*These are monitored outlets: disclose
that Prism aggregates their reporting and links back.

**Never pitch:** "unbiased", "AI-powered", "fighting fake news", "fact-checking", user numbers,
funding, "real-time".

### 7.4 Content

| Pillar | What | Status |
|---|---|---|
| Methodology and trust | How the verbatim check works; what "k of n monitored outlets" means; how corrections work; why Prism rates no outlet; how to cite | `/about` is the hub; the other pages are planned |
| India's news, counted | A monthly report at `/reports/<month>` | Start with October (published early November), **only if it never skips a month** |
| Who said what | Story, quote and person pages | Live |
| Comparisons | §4 | After counsel |
| Professional readings | Markets and security examples on live records | LinkedIn |

**Free tools, scored:**
- **"Who covered it?" checker** (paste a news link, see its Prism record): build at day 60.
- **Coverage badge embed:** at day 90, if the checker shows pull. Serve it from the API, never as
  a Vercel-rendered image.
- **Public API:** deferred (copyright exposure).
- **"Did X really say this?" checker:** never. Absence from n outlets proves nothing, and it
  drifts into fact-checking.

---

## 8. Launch plan

### 8.1 Blockers (no public push until these clear)

| # | Blocker | Owner | State |
|---|---|---|---|
| B1 | Top up OpenRouter; run seven days with no gap in `/healthz` and `/sources` | founder, eng | Open |
| B2 | `/healthz` reports a stalled pipeline | eng | Built (0.0.115.0) |
| B3 | Checkout hidden on test keys | eng | Built |
| B4 | Grievance Officer page, queue, monthly report | founder, eng | Built; the `grievance@` address must be created at the registrar, and the postal address added |
| B5 | Email capture (weekly email and welcome email) | eng, founder | Built. To switch on, set on the Railway **worker**: `PRISM_DIGEST_ENABLED=true` and `PRISM_API_URL=https://api.readprism.news` (the admin token, web URL and from-address are already set and match). The unsubscribe links are signed with `PRISM_ADMIN_TOKEN`: rotating it breaks links already emailed (the account toggle still works). The job refuses to run while `PRISM_API_URL` points at localhost |
| B6 | Data-quality floor for a first visit | eng + founder review | See below |

**What B6 covers:**
- A daily founder spot-check for the seven clean days, on the landing's lead story and the top
  ten `/feed` rows.
- **Check:** the one-outlet share of the newest 60 rows (58 of 60 at the audit); duplicate
  reports inside a record; person pages split across two spellings (`d-k-shivakumar` and
  `dk-shivakumar`).
- **Still open from the 27 September product audit:** the tech-news source The Register failing
  the relevance gate; passing mentions on Market Pulse; the lead row repeating in Today.

### 8.2 Pre-launch: founder

| # | Item |
|---|---|
| F1 | OpenRouter top-up (B1) |
| F2 | Search Console and Bing owner steps (§10) |
| F3 | Create `grievance@readprism.news` (like `hello@`) and route it to the Grievance Officer; add the LLP's full postal address (`LEGAL_POSTAL_ADDRESS` in `web/src/lib/legal.ts`); add the officer's account to `PRISM_ADMIN_EMAILS` so complaints can be decided at `/admin/grievances` |
| F4 | GST registration (CA), before the first sale |
| F5 | CERT-In point of contact and a six-hour incident runbook (in force now) |
| F6 | Counsel: the MIB Rule 18 filing (possibly overdue), the comparison pages, markets copy |
| F7 | Claim @readprism on X, LinkedIn and Instagram and a WhatsApp Channel; then `sameAs` and footer links |
| F8 | GitHub repository description and homepage (the public repo is the top result for the domain) |
| F9 | Soft launch to 20–50 readers and ten interviews (§8.4) |
| F10 | Product Hunt warm-up: comment on launches daily for three weeks from the maker account |
| F11 | Decide whether internal figures may be published, with n and method |
| F12 | An accountable-people line on `/about` (the founders' names and roles), and founder bios and headshots for `/press`. Google News asks for information about who is behind a publication; never an invented byline |
| F13 | The Plus FAQ "Who charges me?" still describes Matryx collecting for the LLP. Selling waits for the LLP's own merchant account (§8.5), so rewrite that answer the day the account is live |

### 8.3 Launch week

| Day | Action | Owner | Watch |
|---|---|---|---|
| Monday | Peerlist Launchpad; LaunchPad India (10:00 IST) | founder | `campaign:peerlist`, `campaign:launchpadindia` |
| Tuesday–Thursday | Product Hunt at 12:31 PM IST (1:31 PM after 1 November); gallery from live records; first comment is the founding story and the verbatim rule | founder | `campaign:producthunt`; accounts per day; email opt-ins |
| +1 day | Show HN, r/developersIndia, dev.to (canonical link) | eng writes, founder posts | `campaign:hn`, `campaign:devto` |
| Same fortnight | Directory batch 1 | founder | Tracker sheet |
| Daily | The social set (§7.1); a human picks every post | founder | Shares; arrivals from social |
| Daily | `/healthz` count above 0; Vercel invocations against baseline; grievances acknowledged within 24 hours; corrections recorded with `tools/correct_record.py` | eng, founder | — |

**Launch links always carry a channel word:** `https://www.readprism.news/?ref=producthunt`.
The recognised words are producthunt, hn, peerlist, launchpadindia, reddit, x, linkedin,
whatsapp, telegram, newsletter, digest, devto, press and other. The word is counted once per
visit and removed from the address bar, so shared links stay clean.

### 8.4 Soft launch and customer research (days 0–14)

- **Who:** 20–50 hand-picked readers. Journalism students and faculty, media-literate readers, a
  few markets and security professionals, and people who share news on WhatsApp.
- **Ask for three things only:** what they would call it, what they would share, and what looked
  wrong (through "Something wrong?", which now feeds the grievance queue).
- **Ten 20-minute interviews:**
  - The last time you wanted to check a news story, what did you do?
  - What would you call Prism to a friend?
  - What made you trust or distrust it?
  - Would you pay for anything here, and for what?
- **Record the exact words in `.agents/product-marketing.md` v2.** Change a persona only with at
  least five data points behind it.
- **The in-product survey** ("Could you check this story for yourself? Yes · Partly · No") and
  "Where did you hear about Prism?" report as counts; below 30 they stay counts.

### 8.5 Paid launch (days 61–90), in this order

1. The LLP's own Razorpay merchant account (no sale while Matryx collects for the LLP).
2. GST registration.
3. Live keys, which turn checkout on (`checkout_ready` becomes true automatically).
4. A consent log of the terms each subscriber saw.
5. The 7-day pre-renewal email for yearly and founding plans.
6. A webhook event-id ledger.
7. `Product` and `Offer` structured data.
8. Founding membership announced to the email list first.

---

## 9. 30/60/90 days

**Days 0–14: Unblock (no public push)**

| # | Action | Owner |
|---|---|---|
| 1 | Credit topped up; seven clean days of ingestion | founder, eng |
| 2 | Merge and promote 0.0.115.0 (grievance, checkout hidden, email capture, state pages, archive, attribution, press) | eng |
| 3 | `grievance@` alias; postal address; switch the weekly email on | founder |
| 4 | Search Console and Bing steps (§10) | founder |
| 5 | Claim handles; LinkedIn company page; Crunchbase; Tracxn | founder |
| 6 | Soft launch and ten interviews | founder |
| 7 | Product Hunt warm-up begins | founder |
| 8 | Cost hygiene (§6.6) | eng |
| 9 | `tools/social_candidates` (prints the day's post candidates; the founder picks by hand) | eng |

**Days 15–30: Free public launch**

| # | Action | Owner |
|---|---|---|
| 10 | Counsel reviews the comparison pages; build `/compare/ground-news` and `/alternatives/ground-news` from one data file | founder, eng |
| 11 | Peerlist and LaunchPad India (Monday); Product Hunt (Tuesday–Thursday) | founder |
| 12 | Engineering write-up: Show HN, r/developersIndia, dev.to | eng |
| 13 | Directory batch 1 | founder |
| 14 | The daily social set; LinkedIn three times a week | founder |

**Days 31–60: Velocity**

| # | Action | Owner |
|---|---|---|
| 15 | The October counted report, published early November, and pitches | eng, founder |
| 16 | "Who covered it?" checker | eng |
| 17 | `/alternatives/inshorts`, `/compare/google-news`; two methodology pages | eng, founder |
| 18 | Journalism-school workshop: trace a quote to where it was printed | founder |
| 19 | "Suggest an outlet" on `/sources` | eng |

**Days 61–90: Paid launch**

| # | Action | Owner |
|---|---|---|
| 20 | Paid-launch gates (§8.5); Founding to the email list | founder, eng |
| 21 | The November report with the reliability numbers (corrections, median time to correct, single-source share) | eng, founder |
| 22 | Publisher outreach with referral counts | founder |
| 23 | Pricing review (§6.5 item 5); keep, kill or double down on each channel | founder |

---

## 10. Showing up on Google, Bing and the answer engines

**Already automated:**
- **Sitemaps:** four of them, listed in `robots.txt` (pages; records; people and organisations;
  news for the last 48 hours).
- **One indexability rule everywhere:**
  - a story is indexed from its second outlet;
  - a person page from four records;
  - a developing story once verified.
- **Structured data:** NewsArticle with its sources, the organisation and its policies,
  breadcrumbs, lists, FAQ and quotations.
- **Head and status codes:** metadata in `<head>` for every crawler, and real 404s.
- **Share cards and crawler rules:** a share card per page; citing crawlers allowed.
- **IndexNow:** an hourly ping to Bing, Yandex and Naver. Google ignores it.

**Owner steps (founder):**
1. **Search Console:** add a **Domain** property for `readprism.news` (DNS TXT record), so www,
   the apex and http read as one site. Add the other founder as owner.
2. **Submit all four sitemaps:**
   - `https://www.readprism.news/sitemap.xml`
   - `https://www.readprism.news/records-sitemap.xml`
   - `https://www.readprism.news/entities-sitemap.xml`
   - `https://www.readprism.news/news-sitemap.xml`
3. **Request indexing** (URL Inspection → Request indexing) for `/`, `/about`, `/sources`,
   `/corrections`, `/feed`, `/grievance`, two stories reported by several outlets, two person
   pages, `/sector/politics` and `/state/karnataka`. Do this **only after ingestion is running
   again**, so Google's first look is a fresh page.
4. **Bing Webmaster Tools:** Import from Google Search Console. Check that the four sitemaps and
   the IndexNow key appear. Turn on the **AI Performance** report, which shows citations in
   Copilot and Bing's AI answers.
5. **Weekly, in Search Console:**
   - watch Pages → Soft 404 and "Duplicate, Google chose different canonical" fall for `/story/`
     (fixed in 0.0.114.0);
   - export "Crawled – currently not indexed" before theorising about what Google skips.

**Google News:** there is no application. It is automatic for publications that meet the
policies, and there are two honest gaps. The policies ask for information about the people
behind a publication (F12). Google's scaled-content policy also describes what Prism
superficially resembles, so keep the defences visible:
- counted coverage out of a public list;
- the verbatim check linked to the line;
- single-source marking and public corrections;
- indexing only stories from two or more outlets.

Expect ordinary web results on long-tail queries first (a person's quotes, a specific story, a
state, a day), and Top Stories later, if at all, in the first 30–90 days.

---

## 11. Measurement

**The weekly review (every Monday):**
- what moved;
- what broke;
- what to change.

Counts below 30 are printed as counts. Targets are set only once there is a baseline.

| Stage | Metric | Where |
|---|---|---|
| Acquisition | Search impressions and clicks by page family (`/story/`, `/entity/`, `/sector/`, `/subject/`, `/state/`, `/feed/<date>`); arrivals by `campaign:*`, search and AI; referring domains | Search Console, Bing, `/admin` |
| Activation | Visits reaching a second story; "Open at the quote" and source opens; landing buttons (`cta:*`); onboarding steps | `/admin` |
| Retention | Weekly-email opt-ins and unsubscribes; returning readers | `/admin`, Resend |
| Referral | Shares per story; share arrivals that reach a second story | `/admin` |
| Research | "Could you check this story?"; "Where did you hear about Prism?" | `/admin` |
| Revenue (after the paid launch) | Lens limit reached → Plus page → checkout → paid; annual share; churn reasons | `/admin` "The way to paying" |
| Trust | Corrections logged; median time to correct; grievances acknowledged within 24 hours and decided within 15 days; single-source share; `/healthz` | `/corrections`, `/grievance`, `/healthz` |
| AI visibility (monthly) | 15 queries × 4 platforms (ChatGPT search, Perplexity, Google AI Overviews, Copilot) × 3 runs; reported as "cited k of n" per platform, month on month | Manual probe log |

### 11.1 Founder links: making them and reading them

**Making one.** `/admin/marketing` → paste the page (or pick a story) → pick the platform →
a campaign if the post belongs to one (`launch-week`, `budget-2026`, one per partner or
community) → **Make the link**. Post the short link. One link per post: two posts sharing a
link cannot be told apart. The tags the link carries:

| Tag | Value |
|---|---|
| `utm_source` | The platform, from a fixed list (x, instagram, whatsapp, linkedin, facebook, threads, youtube, reddit, telegram, email, newsletter, producthunt, hn, peerlist, launchpadindia, devto, press) |
| `utm_medium` | social, message, email, community, launch, partner, press or paid; set from the platform, can be changed |
| `utm_campaign` | The campaign, lowercase with hyphens; left off when there is none |
| `utm_content` | The link's own code; every count is kept against it |

**Reading the numbers** (the analytics and attribution skills, applied):
- **Directional, not proof.** A visit came by the link; what it did next happened in the same
  tab. Nothing says the post *caused* an account.
- **A platform's click count will be higher than ours.** It counts bots, link previews and
  readers without JavaScript; Prism counts a visit whose first page ran.
- **Chats hide where a visit came from.** "Where did you hear about Prism?" sits beside the
  link counts on Marketing, and so does the platform word of every tagged link, hand-made ones included.
- **Below 30, counts only.** No percentages and no "winner" between two wordings until each
  has 30 visits.
- **Never who.** A link's code is counted as a daily total and is never stored on an account;
  the privacy policy says so.

**The Monday review** (with §11): which platforms and campaigns bring visits that read a
second story; archive links that no longer matter; retire a post format that brings visits
and nothing after them.

**The AI-visibility baseline:** 0 of 11 queries at one run each (29 September), including the
brand query. The brand is confused with an unrelated GitHub project called "readprism" and
several other products named Prism. `alternateName: readprism.news` is live; `sameAs` follows
once the founder confirms the handles.

---

## 12. Open founder decisions

1. The OpenRouter top-up date (blocks everything).
2. The LLP's full postal address for the grievance page, and creating `grievance@readprism.news`.
3. Switch the weekly email on (`PRISM_DIGEST_ENABLED=true` on the worker), and the Resend plan.
4. Whether to join a self-regulating body under IT Rules R11(2)(d) (counsel).
5. Whether internal figures may be published (attribution precision 0.983 on 59 claims; the
   direct-versus-reported quote drop), with n and method.
6. Whether the monthly counted report is a standing commitment.
7. An accountable-people line on `/about`.
8. Counsel on the comparison pages and on markets copy (SEBI).
9. The brand handles.
10. Retire the older tagline "One story. Every perspective." in favour of "Follow the story,
    not the headlines."
11. The Plus headline "Every lens on every story". Left as is for now; revisit when more sources
    raise lens coverage.

---

## 13. Every marketing skill, and where it stands

Status: **Live** (0.0.114.0) · **Built** (0.0.115.0 and 0.0.116.0) · **Planned** (this plan) ·
**Later** (after launch or after the paid launch) · **No** (does not apply, with the reason).

| Skill | Status | Where it stands |
|---|---|---|
| ab-testing | Later | Wait until the landing gets 2,000 first visits in 14 days; then hero A vs B |
| ad-creative | Later | Needs real reader language first (§8.4) |
| ads | Later | No paid acquisition before the paid launch; never a political record |
| ai-seo | Live | Crawler policy, `llms.txt`, structured data; `llms-full.txt` built; monthly probe planned |
| analytics | Built | Funnel counts fixed and extended; campaign words and survey; UTM links with a closed tag list and a register (`/admin/marketing`, 0.0.116.0) |
| aso | **No** | No app-store app; Prism installs as a web app (FAQ "Is there an app?" built) |
| attribution | Built | `?ref=` channel words, "Where did you hear about Prism?"; per-link visits and what followed in the same tab, by platform and campaign, never who (§11.1) |
| churn-prevention | Live | Cancel sheet honest; pre-renewal email before the first yearly renewal (paid launch) |
| co-marketing | Later | Newsletter swaps once the weekly email has subscribers; `/for-publishers` built |
| cold-email | Planned (narrow) | The founder's one-to-one outreach to press and faculty only, never for sales |
| community-marketing | Planned | "Something wrong?" feeds the grievance queue (built); "Suggest an outlet" at day 60 |
| competitor-profiling | Planned | Competitor facts re-checked quarterly, or at once on a complaint |
| competitors | Planned | Comparison pages after counsel |
| content-strategy | Planned | The monthly counted report; methodology pages |
| copy-editing | Live | Landing and Plus copy swept |
| copywriting | Live | Landing rewritten; FAQ; share cards |
| cro | Live | Re-score after two weeks of real first visits using `cta:*` counts |
| customer-research | Planned | Soft launch, ten interviews, in-product survey (built) |
| directory-submissions | Planned | §7.2, after the blockers clear |
| emails | Built | Weekly email (opt-in), welcome email; switch on at launch |
| events | Later | One journalism-school workshop at day 45 |
| free-tools | Later | "Who covered it?" checker at day 60 |
| image | Built | Share cards print "k of n monitored outlets" and carry alt text; press asset kit; Instagram post and Story shapes for every card; people, state and day cards |
| influencer-marketing | Later | No paid creators; SEBI and ASCI limits for finance creators |
| launch | Planned | §8 |
| lead-magnets | Built | The weekly email is the magnet; the monthly report follows |
| marketing-council | Done | Its session concluded: restore ingestion and build the list before any launch |
| marketing-ideas | Done | Covered by this plan; use its idea bank only when a channel stalls |
| marketing-loops | Planned | Instrument the share loop (built); the Monday link review (§11.1) |
| marketing-plan | Done | This document |
| marketing-psychology | Live | Zero-risk line, honest scarcity for Founding, no fake social proof |
| offers | Built | Founding recommended while seats last; no struck-through reference price |
| onboarding | Live | Sign-ups at a story or at Plus skip onboarding; "Skip" keeps picks |
| paywalls | Live | Lens wall opens the upgrade sheet; meter unchanged until counts are real |
| popups | **No** | A trust-first record read on phones: modals cost trust and risk Google's intrusive-interstitial rules. Every prompt is inline |
| pricing | Built | §6: prices kept, Founding repositioned, GST breakup, checkout hidden |
| product-marketing | Live | `.agents/product-marketing.md`; v2 after interviews |
| programmatic-seo | Built | Person quotes (live); state pages and day archive (built) |
| prospecting | Planned (narrow) | Find soft-launch readers where professionals post; business lists wait for a Teams product |
| public-relations | Built / Planned | `/press` built; pitches after the blockers clear |
| referrals | Later | No programme before 20 paid subscribers; the share loop instead |
| revops | **No** | Self-serve consumer product with no sales team; revisit only with a Teams product |
| sales-enablement | Later | `/press` and `/for-publishers` now; a deck only with a Teams product |
| schema | Live | Organisation, NewsArticle, breadcrumbs, FAQ, Quotation; `Offer` only after live keys |
| seo-audit | Live | Head metadata, status codes, canonicals, sitemaps; owner steps in §10 |
| signup | Live | Mobile sign-in shows what an account adds; email typo hint built |
| site-architecture | Live / Built | Sub-topic links, subject trail, footer groups, state and archive hubs |
| sms | **No** | No phone numbers are collected; commercial SMS in India needs TRAI DLT registration; WhatsApp is the sharing rail |
| social | Planned | §7.1; claim handles first; every post from a Marketing link with its draft and card |
| video | Planned | One 20–30 second captioned screen recording of a real record for the Product Hunt gallery and LinkedIn |

---

*Sources: the six audit reports behind this plan (technical and AI SEO; programmatic SEO and
architecture; landing copy and CRO; monetisation and activation; go-to-market and competitors;
skill coverage) are kept outside the repository. Competitor facts cite the products' own pages
and App Store (India) listings, checked 29 September 2026.
`docs/COMPLIANCE-INDIA.md`, `docs/BUSINESS-MODEL.md`, `docs/SEO.md` and `PRODUCT.md` hold the
decisions this plan relies on.*
