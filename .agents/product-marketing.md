# Product Marketing Context

**Document version:** v1
**Last updated:** 2026-09-29

> Every line here comes from `PRODUCT.md`, `DESIGN.md`, `CLAUDE.md`, `docs/BUSINESS-MODEL.md`,
> `docs/PLAN-LAUNCH.md`, `docs/COMPLIANCE-INDIA.md`, the code, prior research in `.context/research/`
> and `.context/research.txt` (the 2026-09-24 strategy report), or a live public endpoint read on
> 2026-09-29. Anything not found there is marked **Unknown — founder to fill**. Competitor detail,
> citations and the GTM plan live in `.context/marketing/05-gtm-competitors.md`.

## Product Overview
**One-liner:** Follow the story, not the headlines. Prism keeps one record per news story, built from the reports of monitored Indian and international outlets, with the evidence attached.
**What it does:** Prism reads a public list of monitored outlets (41 outlets, 59 feeds, English and 12 Indian languages, per `/api/v1/sources` on 2026-09-29) and groups their reports into one record per story. Each record shows which outlets reported it, counted by origin (national English, Indian-language, international, wire), who said what word for word (a quote appears only if its exact words are found in the article), the reports behind it, and any correction. A reader can re-read the same record through a lens, a professional reading of the same facts. The record and its evidence are free; Plus sells depth and convenience.
**Product category:** India's verifiable news record (founder, strategy report, 2026-09-24). The shelf readers search on is "news aggregator / news app India", "Ground News alternative", "Inshorts alternative", "full coverage of a story". Prism is found on that shelf but never describes itself as an AI news app.
**Product type:** Consumer web product, mobile-first, installable (web manifest; no native app). Web: www.readprism.news; API: api.readprism.news. Under the IT Rules 2021 Prism is likely a "news aggregator", which the Rules count as a publisher of news and current affairs content (`docs/COMPLIANCE-INDIA.md`, a legal inference, not a determination).
**Business model:** Free record for everyone, no account needed to read. Paid **Plus** (prices in `common/billing.py`): launch offer ₹149/month or ₹1,199/year, open for 90 days after the paid launch or until the first 1,000 Plus subscribers, whichever comes first; then ₹199/month or ₹1,499/year. **Founding member** ₹999/year, first 500 only. Every plan renews until the reader cancels, at the price they joined at (founder, 2026-09-28). Yearly and founding plans can be refunded within 7 days. **Plus is not on sale yet.** Production runs on Razorpay test keys, and the LLP's own merchant account, GST registration and renewal disclosures must come before any charge (paid-launch checklist, 2026-09-24; `docs/COMPLIANCE-INDIA.md` #14). Teams/API from month 6 onward is a proposal (`docs/BUSINESS-MODEL.md` §2), not a decision. Owner: Prism Media Intelligence LLP. Technology partner: Matrix Social Labs (legal entity Matryx Social Labs Pvt Ltd).

## Target Audience
**Target companies:** Mainly B2C. Consumers: the general Indian news reader (D1). Paid prosumers: individual professionals whose work depends on the news (markets readers; cyber/GRC readers). No B2B buyer yet. Team seats are a later proposal.
**Decision-makers:** For the free product, the reader. For Plus, the individual professional paying for themselves. Company buyers: Unknown — founder to fill (none sold, none interviewed).
**Primary use case:** Understanding one story as it develops (what happened, who said what, which outlets reported it) without reading six outlets, and being able to check it.
**Jobs to be done:**
- "Tell me what happened, once, instead of the same headline from ten apps."
- "Show me exactly what was said and where it was printed, so I can check it or quote it."
- "Tell me whether this is widely reported or rests on one outlet."
- (Professional) "Read this story for my work: which listed companies are named, whether a vulnerability matters to me." Lens facts need a quality check before they are marketed (see Proof Points).
**Use cases:**
- A reader arrives on one story from a shared link or a search result, signed out, on a phone (PRODUCT.md § Operating Context).
- A reader checks whether a quote circulating on WhatsApp was printed, and by whom.
- A reader who reads English and an Indian language sees one story reported across both (display is English-first).
- A markets reader scans the companies named in today's reporting (Market Pulse board: counts and sources, never prices).
- A security reader flips a tech story to the cyber reading.
- The founder and a review team spot-check the live site against the pipeline (internal, not a marketing audience).

## Personas
*B2C first. These are illustrative personas from `PRODUCT.md` and `docs/PERSONAS.md`, not interview-derived. Validate them before using them in copy.*

| Persona | Cares about | Challenge | Value we promise |
|---------|-------------|-----------|------------------|
| General Indian reader (phone, signed out, English first; many also read Hindi, Kannada, Tamil or Marathi) | Knowing what happened; seeing a story has more than one side without the work | Repeated headlines, forwards with no source, not knowing what to trust | One record per story, counted coverage, exact words with their source, free |
| Markets reader (traders, analysts, finance creators) | The companies named, what the company actually said, before acting | Hunting exact quotes and sources across outlets | The same record read for markets; companies in today's reporting, counted and sourced (no prices, no advice) |
| Cyber/GRC reader | Whether a reported incident or vulnerability matters to them | Triage across many outlets | The same record read for security (sourced from news outlets, not vulnerability feeds, per founder 2026-09-27) |
| Journalist / researcher / student (PERSONAS.md "Go deep") | Provenance, citing correctly, who reported first | Tracing a claim to its first printed source | Public outlet list, verbatim quotes with "Open at the quote", `NewsArticle` JSON-LD with `isBasedOn`, a citation format (`/llms.txt`) |

## Problems & Pain Points
**Core problem:** News reaches Indian readers repeated, fragmented and hard to verify. The same event arrives as many headlines, quotes travel without their source, and a reader cannot tell whether a story is widely reported or rests on one outlet.
**Why alternatives fall short:** (factual framing only; see `05-gtm-competitors.md` for the cited detail)
- Short-summary apps (Inshorts, Way2News) are built for speed: one summary, one source link.
- Bias-rating products (Ground News, AllSides) grade outlets on a political spectrum drawn from US-built rating organisations, which is a different job from showing an Indian story's record.
- AI summary readers (Particle, Perplexity Discover) lead with a generated summary. Prism leads with the record and labels its own inference as "Prism's reading".
- Google News has far greater breadth, but it publishes no monitored-outlet denominator, no verbatim-or-nothing quote rule and no public corrections log for its groupings. Say this as what Prism does, never as "Google fails".
**What it costs them:** Time spent reading several outlets to confirm one story; the risk of repeating a misattributed quote. Quantified cost: Unknown — founder to fill (no user research).
**Emotional tension:** Distrust and fatigue. Context from the Reuters Institute DNR 2026 (cited in `.context/research/news-product-gap-2026-09-17.md`): global trust in news 37%, news avoidance 42%; the India sample shows 52% avoidance and 39% trust, but that sample is mainly English-speaking and not nationally representative. IAMAI/Kantar: 36% of Indian internet users surveyed distrust AI-bot responses (strategy report). These are market context, never claims about Prism's readers.

## Competitive Landscape
**Direct:** Ground News: rates outlet bias and factuality (averaged from AllSides, Ad Fontes Media, Media Bias/Fact Check) over 50,000+ sources and sells Vantage in India. Its frame is a political spectrum, not a counted Indian record with verbatim quotes. Particle: AI summaries, bias spectrum, "Opposite Sides", Ask, sold in India at ₹299/month. It is summary-first. Google News (Full Coverage): free, huge breadth, 10 Indian languages including English. It is a discovery layer with no published denominator.
**Secondary:** Inshorts (60-word English/Hindi summaries); Dailyhunt (14 Indian languages, vernacular volume); Way2News (hyperlocal short news, 8 languages); Perplexity Discover (answer engine with sources; Airtel gave its subscribers free Pro). Each does a different job (skim, vernacular entertainment, local, ask-anything) and none leads with a verifiable record.
**Indirect:** Reading The Hindu or Indian Express apps directly, subscriber-funded independents (Newslaundry, Scroll), and WhatsApp forwards. Several of these (The Hindu, Indian Express, Scroll.in, MediaNama, Inc42, Entrackr) are **monitored outlets, meaning sources and partners, not targets.** Prism links out to their reporting. Never publish "vs" pages against a monitored outlet.

## Differentiation
**Key differentiators:**
- **Verbatim or nothing.** A quote is displayed only if its exact words are found in the source article, with speaker, outlet, time and "Open at the quote ↗". Indian-language reported speech is labelled "reported", never styled as a quote (DESIGN.md, 2026-09-28).
- **Counts with a denominator.** "k of n monitored outlets · checked Xm ago" on the record header and landing, linking to `/sources`, the public list of monitored outlets by language with when each was last read. The story share card currently prints "N outlets · M languages" without "of n" (gap noted in the GTM doc).
- **Single-source stories say so:** "Single source · not yet corroborated", drawn on a dashed rule.
- **Coverage by outlet origin**, not a bias or tone rating. Prism rates no outlet. The tone label was removed (D-a).
- **Corrections in public:** `/corrections` plus every earlier version of a record (event_revisions). The log had 0 entries on 2026-09-29.
- **The lens flip:** the same record re-typesets for a professional reading. It is the signature and brand moment.
- **The evidence is never the premium feature:** the record, its reports, quotes, coverage and corrections stay free.
**How we do it differently:** Prism counts structure instead of summarising it, keeps the reporting attached, and marks what is provisional ("Provisional grouping", "Grouping under review") instead of inventing a chronology.
**Why that's better:** A reader can check any line in one tap and see how thin or broad the evidence is before believing the headline.
**Why customers choose us:** Unknown — founder to fill (no customers or interviews yet). Hypothesis: people who share or quote news and want to be right.

## Objections
| Objection | Response |
|-----------|----------|
| "Is this AI-generated news?" | Prism writes the headline and brief and labels its own inference as Prism's reading. Quotes are the outlets' printed words, checked against the article, and every report links out. Never answer "no AI"; answer with the mechanism. |
| "Only 41 outlets? Google has thousands." | True, and the list is public at `/sources`, with the languages not yet read named. Every count says "of n". Prism claims monitored outlets, never "every outlet". |
| "Whose side are you on? Is it biased?" | Prism rates no outlet and assigns no left/right label. It counts which outlets reported a story, by origin, and prints what was said in their words. Never answer "we're unbiased". |
| "Is it real-time?" | Do not claim speed. Freshness targets are "In validation" on the landing's own status grid. |
| "Can I read it in Hindi or Tamil?" | Prism reads 12 Indian languages and prints quotes in the language they were printed in. Translating Prism's own writing is held (D-d) and the interface is English (D-f), so never promise translation. |
| "Why would I pay?" | You don't need to for the evidence. Plus is for depth: every lens on every story, more questions, answers drawn from the whole story. Not on sale yet. |
| "Aren't you taking publishers' work?" | Every report card, photo and quote credits and links to the outlet. Photos are credited previews behind a kill switch (DESIGN.md 2026-09-18/20). |

**Anti-persona:** Readers who want US left/right bias ratings (Ground News, AllSides serve them); readers who only want a 60-word skim; readers who need a fully Indian-language interface today; traders who want prices, signals or tips (Prism has no price data and must not give advice); readers who want fact-check verdicts (Prism is not a fact-checker).

## Switching Dynamics
*Hypotheses from PRODUCT.md and the research, not interview data. Replace them with verbatims after the soft launch.*
**Push:** Repeated headlines across apps; forwards with no source; not knowing whether one outlet or many reported something.
**Pull:** One record per story; the exact words and where they were printed; "k of n monitored outlets"; free, with no account needed.
**Habit:** Inshorts or Dailyhunt for the skim, the newspaper app for depth, WhatsApp for what friends share, Google News on Android.
**Anxiety:** "Is this AI slop?" "Is it partisan?" "Will it be up to date?" "Will it ask me to pay or sign in?"

## Customer Language
**How they describe the problem:**
- Unknown — founder to fill (no interviews, reviews or support tickets yet). Collect verbatims from soft-launch readers and "Something wrong?" reports.
**How they describe us:**
- Unknown — founder to fill.
**Words to use:** record; report; outlet; monitored outlets; "k of n monitored outlets"; coverage; outlet origin; who said what; word for word / verbatim; "Open at the quote"; checked against the article; single source · not yet corroborated; provisional grouping; correction; earlier versions; Prism's reading; follow the story; the evidence is free.
**Words to avoid:** AI-powered, AI news, "powered by AI"; unbiased, neutral, balanced, impartial; fact-checked, fact-check (Prism is not a fact-checker); "every outlet", "all sources", "all the news"; "both sides", "every side", "blindspot" (Ground News's frame, and binary); real-time, fastest, first, breaking (until freshness is proven); "trusted", "trustworthy" as self-description; "what happens next" or predictions; verified timeline or story chronology (still provisional); translation or "in your language" promises (D-d); revolutionary, game-changing, disruptive; any user count, testimonial, customer name, press mention or benchmark claim (none exist); percentages below 30; "we" on record surfaces.
**Glossary:**
| Term | Meaning |
|------|---------|
| Record | One story's page: all reports of one event, its quotes, coverage, corrections, versions |
| Report | One outlet's article that the record is built from |
| Monitored outlets | The public list at `/sources`; the denominator for every count |
| Coverage bar | Outlet origin in fixed order: English national · international · Indian-language · wire, always with its count |
| Verbatim quote | Exact words found in the article, with speaker, outlet and time |
| Reported | Indian-language speech an article attributes with a speech verb and no quotation marks; shown upright, labelled "reported", never as a quote |
| Single source · not yet corroborated | A record with one outlet so far (dashed rule) |
| Provisional grouping | Related coverage under review, not a verified chronology |
| Lens | A professional reading of the same record; the set grows (pickers read `/api/v1/lenses`) |
| Prism's reading | Anything Prism infers, such as "why it matters", labelled as such |
| Plus | The paid plan: depth and convenience, never the evidence |
| Ask | Grounded questions on one story, answered from its own reports, or it says it cannot |

## Brand Voice
**Tone:** Editorial, direct, factual. Calm, never breathless.
**Style:** Plain words and counts. Speaks to the reader as "you". On record surfaces Prism is "Prism", never "we" ("we" is allowed in account, legal and email copy). Sentence case; a middle dot " · " between facts; no emoji; CAPS only in mono provenance strips.
**Personality:** Exact, accountable, unshowy, useful, quietly confident.

**Hard copy rules (binding, from PRODUCT.md, DESIGN.md and CLAUDE.md):**
1. **Never "AI-powered". Never "unbiased".** No outlet or tone rating, ever.
2. **Never enumerate lens names in generic or marketing copy.** The set grows. A post about one reading may name that one lens; never list the set.
3. **The wordmark is the address.** The lockup is the mark plus **readPrism.news** ("read" and ".news" quiet, "Prism" heavy), used as rendered artwork only. In running text the name is **Prism** and the address is written `readprism.news`, lowercase. Never "Prism.news" (not ours), never "Prism" alone as a lockup, never "ReadPrism" or "Read Prism" as the name, never a space or capital R in the address.
4. **Counts, not adjectives.** "9 outlets · 2 languages". Below 30 a share is "3 of 4", never "75%". A change off a small base is "+3 from 4". Anything not counted is "Not counted yet", never 0.
5. **Every count has its denominator:** "k of n monitored outlets", and "monitored outlets", never "every source".
6. **Verbatim or nothing.** Quotes are exact or absent. A translation says "translation". Reported speech is labelled "reported" and is never set in quotation marks.
7. **Provisional says so.** No verified-chronology claims while stories are "related coverage under review".
8. **No invented numbers or examples, anywhere.** Design-mock sample data never ships. No testimonials, customer names, user counts, benchmark claims, press or market prices (PRODUCT.md § Absences).
9. **Promise:** "Follow the story, not the headlines." The older tagline "One story. Every perspective." is a promise about evidence, not tone. Use it sparingly: "every perspective" can read as completeness Prism does not claim.
10. **The evidence is free.** Never position the record, quotes, coverage or corrections as paid.

## Proof Points
**Metrics:** Publishable (live, counted, time-stamped; re-read before each use): 41 monitored outlets · 59 feeds · English and 12 Indian languages (Hindi, Malayalam, Marathi, Tamil, Telugu, Urdu, Odia, Kannada, Assamese, Bengali, Gujarati, Punjabi), per `/api/v1/sources` read 2026-09-29. **Internal only until the founder approves publication with n and method** (PRODUCT.md forbids benchmark claims): 1,285 verbatim-verified claims across 755 articles; attribution precision 0.983 on a 59-claim adjudicated gold set (`tools/gold_claims.py`).
**Customers:** None. Do not fabricate.
**Testimonials:** None. Do not fabricate.
> Unknown — founder to fill once real readers say something quotable, with written permission.
**Value themes:**
| Theme | Proof |
|-------|-------|
| Exact words, checkable | "Who said what" on every record; "Open at the quote ↗"; quote pages `/story/<id>/quote/<n>` with a share card that states VERBATIM or TRANSLATED |
| Coverage you can count | "k of n monitored outlets · checked Xm ago"; `/sources` public list with last-read times and the languages not read yet |
| Honest about thin evidence | "Single source · not yet corroborated"; provisional groupings labelled |
| Accountable | `/corrections` public log (0 entries on 2026-09-29); every earlier version of a record kept |
| Free evidence | Landing: "The evidence is free and stays free"; no account needed to read |
| Machine-readable and citable | `NewsArticle` JSON-LD with `isBasedOn`; `/llms.txt` citation guidance; citing crawlers allowed |

## Goals
**Business goal:** (1) Build a free Indian readership as distribution and as public proof of the record (share cards, search), then (2) convert professionals to Plus after the paid launch. Break-even is roughly 120 subscribers at ₹199 on about $210/month fixed cost (`docs/BUSINESS-MODEL.md` §6; a proposal with stated assumptions).
**Conversion action:** Open a record → come back (D7) → free account (state, languages, interests) → lens sample → Plus once on sale. Before Plus is on sale: email opt-in (not built yet; see the GTM doc).
**Current metrics:** Internal, never for marketing: 3 accounts and 9 Ask questions ever as of 2026-09-20 (`docs/PLAN-LAUNCH.md`). Traffic, indexed pages, returning readers: Unknown — founder to fill (Search Console and first-party analytics in `web/src/lib/analytics.ts`). Plus is not on sale. No Grievance Officer page is published (`docs/COMPLIANCE-INDIA.md` N1).

## Changelog
*Newest first. One line per revision: what changed and why.*
- v1 (2026-09-29) — Initial context, drafted from PRODUCT.md, DESIGN.md, CLAUDE.md, docs/, `.context` research and live `/sources` and `/healthz`; customer language and interview data left for the founder.
