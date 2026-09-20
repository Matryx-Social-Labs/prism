# Prism — launch plan (2026-09-20)

Engineering and design plan for the founder's 2026-09-20 asks, in the order they
should be built. Every section says what exists, what changes, how it is judged,
and how long it takes. Companion to `docs/BUSINESS-MODEL.md`. Nothing here is
built yet except where marked ✔.

Status on the day (measured): 3 accounts, 9 Ask questions ever. Pipeline
≈ $4–5/day. Labellers: cross-language batch 37/150 (one labeller, last answer
Sept 19), stories live-window batch 0/121 (nobody has started), claim
attribution complete (0.983). Podcast clips: live since today; the hourly job
had not fired once because every deploy reset its timer (fixed ✔ e061881: first
run 90 s after start).

---

## 1. Pricing and the purchase funnel

**Price.** ₹149/month for the first 90 days after launch or the first 1,000
Plus subscribers, whichever comes first, then ₹199. Annual ₹1,199 during the
offer (₹100/month), then ₹1,499. Founding annual ₹999 locked for three years,
first 500. State the end date of the offer on the pricing page and in the app:
an offer without an end is a price.

**The funnel is the lens, not a pricing page.** Nobody in India buys a news
subscription from a pricing page; they buy at the moment the paid thing is
visibly better than the free thing they were just using. Prism already has
that moment built: the locked lens flip on the record (the scan line runs, the
text is behind the unlock). The plan makes that moment do the selling and adds
three more:

| Moment | Where | What the reader sees | Action |
|---|---|---|---|
| **Lens sample** | record, Markets/Cyber tab, 1st–3rd time | the full reading, and a quiet line "Sample 1 of 3 · Plus is ₹149/month" | none required |
| **Lens locked** | 4th time onward | the flip, the first sentence of the reading in the clear, the rest veiled, one button "Read with Plus · ₹149/month" | Razorpay checkout in a sheet; back on the same story, unlocked, in under a minute |
| **Ask cap** | 11th question of the day (free account) | the answer to the 10th, then "You've used today's 10. Plus has 100 a day on the stronger model." | same sheet |
| **Watchlist alert** | when a followed story changes | email: "what changed" (free) with "alerts in the app the minute it moves — Plus" | link |
| **Market Pulse** | /pulse | first paragraph free, the rest veiled with the same button | same sheet |

Rules: one price shown everywhere; the button says the price; cancel is one click on
/account; no countdown timers, no "limited seats" language except the honest
founding cap. Measure: sample→locked→checkout→paid, per moment.

**Implementation (payments):** as `BUSINESS-MODEL.md` §8 — Razorpay Subscriptions
(UPI Autopay, cards), `subscriptions` table, webhook → entitlement, `isLocked`
reads entitlement, GST-inclusive display, invoices by email, 3-day grace, 7-day
refund on annual. **5 working days.** Needs from you: Razorpay account, GSTIN,
Vercel Pro, Terms/Privacy/Refund pages approved.

---

## 2. Ask — a redesign, and what it should answer

**What is wrong today.** Ask is the last section of a long record; a reader who
never scrolls there never learns it exists. The panel is a plain transcript
(question bubble, answer bubble, `[n]`). It has no memory of where you are on
the page, no way to ask about a specific quote or paragraph, and its answers are
prose only — no structure an analyst can use.

**What good looks like (compared).** Perplexity: answer first, numbered
citations inline, source cards under the answer, follow-up questions as chips,
"related" at the end. Particle: per-story Q&A with three suggested questions
above the fold. Bloomberg/terminal habits: structured outputs — a timeline, a
table of who-said-what, a list of entities — not paragraphs. Our own constraint
(D6, brand): every sentence cites the story's own reports or says it can't.

### 2.1 Placement — three entry points, one panel

1. **The Ask bar, always visible.** On the record the bar lives in the thumb zone
   on the phone (it is there today as a button beside Share) and becomes a
   **persistent input** on desktop: a 44px pill pinned to the bottom of the
   reading column ("Ask this story…" with the three suggested questions as chips
   above it while the reader has not typed). It scrolls with the reader; it never
   covers the record's text (12px gap, `glass`). Scrolling into the Ask section
   at the foot hands over to the inline panel so nothing is duplicated.
2. **Ask from a selection.** Select any text in the brief or a quote → a small
   "Ask about this" chip appears at the selection (like a highlight menu). The
   selection is quoted into the question. This is how an analyst asks "is this
   number confirmed elsewhere?" without retyping.
3. **Ask from an entity or a quote.** The entity card gains "Ask about {name} on
   this story"; each quote card gains "Ask about this quote" → prefilled: "What
   else did {speaker} say, and does any other report contradict it?"

Opening any of the three slides up the **Ask sheet**: phone — a bottom sheet to
85% height over the record, the record dimmed, swipe down closes; desktop — a
right-side panel 400px wide inside the evidence rail's column, the record stays
readable beside it. The sheet is one component (`AskSheet`), the section at the
foot renders the same component inline.

### 2.2 The answer — shape, not just words

Every answer has the same anatomy, in this order:

1. **The answer** — 2–5 sentences in the reading voice, every sentence ending in
   one or more `[n]` chips; hovering/tapping `[n]` opens the report card (outlet,
   headline, time) and "Open at the quote ↗" when the citation is a claim.
2. **Structure when the question asks for it** (the model chooses one, or none):
   - *timeline* — "when / what changed": dated rows from the story's route;
   - *who said what* — a two-column table speaker · verbatim quote (`[n]`);
   - *comparison* — "how do outlets differ": one row per outlet, what each
     reported, what only it reported;
   - *numbers* — a small table of figures with the report each came from.
   These are rendered from a typed JSON block the agent emits after the prose
   (`{"table": …}` / `{"timeline": …}`), never free-form markdown tables.
3. **"What the reports don't say"** — one line, when the question reaches
   beyond the sources: "None of the 16 reports gives the number of arrests."
   This is the product's honesty made visible and it prevents the model
   guessing.
4. **Follow-ups** — three chips generated from the answer (and from the
   story's cast), e.g. "What did the Election Commission say?", "How did
   Congress respond?".
5. **Sources used** — the report cards cited, in `[n]` order.

Refusals keep the same anatomy with the answer replaced by the refusal line.

### 2.3 What different readers get to ask

| Reader | Questions Ask must handle well | How |
|---|---|---|
| **Everyone** | What happened? Why does it matter? Who is X? What did X say? What changed since yesterday? | today's RAG + the route + claims; suggested questions do this |
| **Analyst / journalist** | Which outlets reported X and which didn't? Where do the numbers disagree? Give me every quote by X across this story. Timeline of the last 7 days. What did the same speaker say last month? | *comparison* and *who-said-what* structures; retrieval extended from the event to **its story** (all developments' reports) for Plus; "across stories" needs the QID ledger (rebuild step 5) — say "not yet" honestly |
| **Trader (Markets lens)** | Which listed companies are named? What did the company say vs what the report says? Any regulatory action? | entities → validated securities (exists), claims filtered to the company's own statements |
| **Security (Cyber lens)** | Which CVEs, is it exploited, who is affected, what's the vendor's statement? | cyber lens fields already on the record |

**Correlation and "dig deeper" — what we can honestly show now:** the story
route (developments in order), the coverage split, quote-vs-quote across
outlets, the entity's other stories (search), and the podcast clips. What we
must **not** show yet: cross-story position changes and "who is silent" — both
gated in the rebuild plan on claim recall ≥ 0.9. Dig-deeper items, in the Ask
sheet under the answer as chips: "Timeline", "Every quote", "How outlets
differ", "All stories about {entity}".

### 2.4 Cost and limits (from the business model)
Anonymous 3/day per IP, free 10/day on glm-5.3-flash, Plus 100/day on qwen3.7-plus;
selection/entity/quote entry points count as questions. Story-wide retrieval only
for Plus (5× the context).

**Build:** sheet + bar + entry points 3 days; structured answers (schema, renderer,
prompt) 3 days; story-wide retrieval 1 day; limits 1 day. **8 working days.**
Judged by: the groundedness judge (exists) on 50 questions ≥ 0.95, plus a
20-question analyst set written by you.

---

## 3. Sign-in: Google and Apple

Magic link stays (works everywhere, no vendor). Add:

- **Google** — one tap on Android and desktop; Google Identity Services with the
  server verifying the ID token, account keyed on the verified email (merges with
  an existing magic-link account of the same email). 1 day. Needs a Google Cloud
  OAuth client (you own the project; I'll give the exact redirect URIs).
- **Apple** — required by App Store rules once there is an iOS app that offers any
  third-party sign-in; on the web it is a small win (Safari users). Sign in with
  Apple needs an Apple Developer account ($99/yr) and a Services ID; email may be a
  private relay address. 1 day, **after** Google, and only if you already hold the
  developer account for the app.
- No phone OTP for now (per-SMS cost, fraud handling); revisit when the app ships.

Onboarding after sign-in is the six-step flow in `BUSINESS-MODEL.md` §7, with one
addition from §5 below: the reading language is asked **first**, before the state.

---

## 4. The story feature, labellers, and readiness

**Where it stands.** The story layer (timeline, "how it unfolded", related
stories) is the part of the product most likely to be wrong: the rebuild plan's
own measure is F1 0.47 against the 45-story gold set, and the "provisional
grouping" state on the arc page is the honest face of that. The September
batches were meant to move it: **"Stories · the live window" has 0 of 121 tasks
answered — no one has opened it**; "Same happening, across languages" has 37 of
150 by one labeller.

**What it takes to rectify.**

| Step | Who | Time |
|---|---|---|
| Both batches labelled by two people each (they are ~60–90 minutes per batch per person) | labellers | this week — needs your push |
| Adjudicate disagreements (`tools/gold_stories`) | you + me | half a day |
| Re-score the current partition; sweep the L2 parameters against the enlarged gold (`tools/sweep_partition --cv`) | me | 1 day |
| Ship only if it beats F1 0.47 on both folds; otherwise keep "provisional" honest and move the effort to the embedding swap (rebuild step 3, already measured as the real lever) | me | 2–4 days |

Realistic: **two weeks to a measurably better story layer, one week of it
waiting on labels.** It is not a launch blocker because the record, quotes,
coverage, clips and Ask do not depend on it; the arc page already says
"provisional" where it is unsure.

**Podcasts:** live, ~0.8 precision on nine clips today, hourly job now fixed to
actually run. Launch-ready as a labelled beta ("Heard on" shows only where a
clip exists). Two more weeks of labels reach a real precision number.

**Launch readiness, honestly.** Ready: the record, coverage, quotes with roles,
photos, clips, Today with scopes, /about, ingestion (cap removed today), CI/branch
protection. Not ready: payments, Google sign-in, Ask limits and the redesign,
analytics (there is none), legal pages, Vercel Pro. **Three weeks** to a paid
launch if the order in §7 is followed; a **free public launch could be next
week** once analytics, limits and legal pages exist.

---

## 5. Indic languages — the record in Hindi, Kannada, Tamil, Telugu

**Why this is the biggest market decision in the plan.** English readers are
perhaps 10–15% of India's news audience; the Reuters/other studies put paying
intent among Indian-language readers at roughly one in seven, and the
population that "would not know English" is the majority. Prism already
*ingests* Kannada, Tamil, Telugu, Hindi, Marathi, Bengali, Gujarati sources and
already shows their quotes verbatim. What it does not do is *speak* those
languages: the headline, brief, section names and the interface are English.

**Design decision: one record, many renderings.** The record (facts, quotes,
coverage) is language-independent. The *reading* of it — headline, brief points,
watch points, section labels, the Ask answer — is rendered in the reader's
language. Quotes stay verbatim in the language they were said in, with a
translation beneath (the record never rewrites a quote).

**Where the language lives (the WhatsApp case).**
- The language is **in the URL**: `/kn/story/<id>`, `/te/feed`, `/hi/about`.
  A Telugu reader who shares gets a `/te/…` link; the receiver opens it in
  Telugu with no account, no cookie, no guess. The share card (OG image) is
  rendered in that language too.
- The language is remembered: a `prism.lang` cookie set by the first visit to a
  prefixed URL, by the switcher, and by onboarding; `/story/<id>` without a
  prefix redirects to the cookie's language (English when there is none).
  `hreflang` links between the renderings so search sends Telugu queries to
  `/te/`.
- Onboarding asks the reading language **first**, in every language at once
  ("English · हिन्दी · ಕನ್ನಡ · தமிழ் · తెలుగు" as five large chips, each in its
  own script), before the state. The languages-you-read list (exists) stays for
  ranking.
- The switcher is one control in the top bar and the You tab; switching keeps
  the reader on the same page in the other language.

**How the text is produced.**
1. **Interface strings:** ~300 strings (nav, section heads, buttons, empty states,
   onboarding) via `next-intl` message files, translated once by a human
   translator per language (₹3–5k per language; machine draft first). Hind and
   its script siblings are already loaded, the record voice per script was
   added on 2026-09-20, so the type system is ready.
2. **Generated text (headline, brief points, watch points, entity kinds,
   status words):** translated per event per language **on first request** by
   glm-5.3-flash (≈ 350 tokens ≈ $0.0002 per event per language), cached in
   `events.projection.i18n[lang]`, produced from the English record so the
   facts are identical across languages. Never pre-translate the whole corpus:
   at 1,800 events/day × 4 languages that is $1.4/day for text mostly unread;
   on-demand costs cents. Translations carry the same "written from N reports"
   line; a language-specific judge sample of 50 events per language before the
   language goes public (groundedness ≥ 0.95, no added facts).
3. **Quotes:** verbatim as said; a translation line beneath in the reading
   language when the two differ, marked "translated", generated the same way.
4. **Ask:** answers in the reader's language; retrieval unchanged (mE5 is
   cross-lingual); the citation chips unchanged.
5. **Search:** query in any language against the multilingual embedding
   (already cross-lingual) plus the translated headlines.
6. **Email brief:** in the reader's language.

**Order and timing.** Hindi first (largest audience, most sources, best model
quality), then Kannada and Telugu together (our strongest regional source base
and the Karnataka reader we already serve), then Tamil. **Hindi in three weeks
of work after §2–3; each further language ≈ one week** (translator turnaround
included). Release each language when its 50-event judge sample passes, with
a public "beta" tag for a month. Marketing per language: the quote share card
in that language, in that language's WhatsApp groups and X communities, with a
`/hi/` link.

**What the population needs, that we should build for them specifically** (not
in scope this month, on the roadmap): audio of the brief in the language
(browser TTS is poor in Indic; a real TTS voice per language is ₹ per minute —
test Sarvam/Bhashini first), a lighter page for 3G (the record is already text,
photos are lazy), and WhatsApp itself as a delivery channel (a daily brief via
WhatsApp Business API, ₹0.8–1 per message — paid tier only).

---

## 6. What to add to attract readers (beyond §5)

- **The quote card** (WhatsApp/X image): speaker, role, verbatim quote, outlet,
  Prism mark, story link in the reader's language. 1 day. Highest share yield.
- **"What changed since you read it"** on followed stories — the one feature
  no aggregator has and the reason to come back. 3 days (route + last-seen).
- **Daily brief email 7:00 IST** in the reading language. 2 days.
- **State pages** (`/kn/karnataka`, `/te/telangana`): the state slice as a
  shareable landing, in the state's language. 1 day each once §5 exists.

---

## 7. Order of work

| Week | Build | Gate |
|---|---|---|
| 1 | Analytics (Plausible) · Ask limits + model tiering · Google sign-in · legal pages · Vercel Pro · **free public launch** (X, LinkedIn, r/india) | limits verified with a scripted client |
| 2 | Ask redesign: sheet + bar + entry points; structured answers; story-wide retrieval for Plus | groundedness ≥ 0.95 on 50 + the analyst set |
| 3 | Razorpay + entitlement + pricing page · lens funnel copy · quote card · **paid launch at ₹149 / ₹1,199 / founding ₹999** | one real purchase end-to-end, one refund |
| 4–6 | Hindi: `next-intl` shell, `/hi/` routing + cookie + hreflang, on-demand translation, judge sample, share card in Hindi · daily brief email · "what changed since you read" | 50-event judge ≥ 0.95 |
| 7–9 | Kannada + Telugu (parallel translator), then Tamil · state pages · Apple sign-in if the app is in motion | per-language judge |
| ongoing | labels → story layer re-score (§4); clip labels → precision | F1 > 0.47 both folds; clips ≥ 0.9 |

Decisions needed from you now: (1) ₹149 for 90 days or first 1,000 — agree the
end condition; (2) Razorpay account + GSTIN + Vercel Pro; (3) Google Cloud OAuth
client (or let me create it under a Prism project you own); (4) push the two
labelling batches this week; (5) Hindi first — confirm.
