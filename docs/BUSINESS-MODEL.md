# Prism — Business model, v1 (2026-09-20)

A concrete proposal to evaluate, not a decision. Every number below is either
measured on this repo and its production data today, or cited. Where I had to
assume, it says so.

---

## 0. What we actually know today

**Product state.** Reader-facing record per story (headline, brief as points, who
said what with roles, coverage by outlet origin, report cards with credited
photos, podcast clips, story route), Ask (cited RAG per story), two professional
lenses (Markets, Cyber) behind sign-in with 3 free Markets samples, watchlist,
Market Pulse, onboarding with state · languages · interests. Free to read
without an account. Web only; the design system is built to port to React
Native.

**Volume (prod, week to 2026-09-20).** ~2,300–2,700 articles/day on full days
from 42 sources, ~1,600–2,000 events/day, 12 publishers with photos. 3 user
accounts, 9 Ask questions ever. Pre-launch.

**Cost structure (measured).**

| Item | Cost | Scales with |
|---|---|---|
| Pipeline LLM (gate + classify + extract on gemini-3.1-flash-lite; briefs/analysis on glm-5.3-flash) | ≈ **$1.8–2.0 per 1,000 articles** → **$4–5/day ≈ $140/month** at today's intake (balance moved $22.6 → $13.4 over 2026-09-18 → 20) | **sources**, not readers |
| Ask answer (qwen3.7-plus, ~5k context + ~300 out + ~700 reasoning tokens) | ≈ **$0.003 per question** | questions |
| On-demand lens brief (glm) | ≈ $0.0004, cached per event forever | first reader of a lens |
| Podcast transcription (Groq via OpenRouter) | $0.04/h → ≈ $0.02–0.06/day | shows, not readers |
| Railway (Postgres, Redis, api, worker) | ≈ $25–40/month | traffic (slowly) |
| Vercel | Hobby today. **Hobby forbids commercial use** → Pro $20/month the day we charge | — |
| Resend (magic-link email), domain | ≈ $0–20/month | users |

So: **fixed ≈ $190–220/month** and **a paying reader costs well under ₹40/month
in inference even when heavy** (30 Ask questions a day for a month ≈ $2.7; a
normal 5/day ≈ $0.45). The margin question is entirely "how many subscribers
cover the fixed cost", not "does a user cost more than they pay".

**Machinery already built (no new code to charge):** `isLocked(lens)` and the
inline unlock prompt on the record; `common/quota.try_consume_sample` (atomic
freemium decrement, 3 Markets samples on signup); `lens_unlocks`, `usage_quota`,
`watchlist` tables; Ask caps `ANON_ASK_PER_SESSION = 3`, `USER_ASK_PER_DAY = 30`;
magic-link auth; profile with state, languages, interests. Missing: a
`subscriptions` table, a payment provider, per-IP limits, model tiering by plan.

---

## 1. Positioning and who pays

The market facts (Reuters Institute DNR 2026): **17% pay for online news** across
the 20 richer markets, flat for years; trust in news at a record low; weekly AI
chatbot use for news rose 7% → 10%, and people **trust chatbot answers less (20%)
than news itself (37%)**. India: consumer subscription is thin (older studies put
willingness to pay at roughly one in seven Indian-language readers), UPI Autopay
is the recurring rail, local price points sit 50–70% below US ones.

Two conclusions the rest of this model follows from:

1. **The free product is the funnel and the proof, and it must stay free.** The
   record, the sources, verbatim quotes, coverage, clips, the story route, and a
   metered Ask are what make Prism trustworthy — charging for them would starve
   the one thing a trust product cannot rebuy. (Founder decision D3 in the rebuild
   plan: free consumer news + paid prosumer tier.)
2. **The money attaches where the job depends on the information.** A retail
   trader deciding before the open, a security/GRC lead triaging the morning, an
   analyst who needs the exact quote and the exact source. India has ~180M demat
   accounts and a large infosec/GRC workforce; both groups already pay for tools
   at ₹200–1,000/month. That is the Markets and Cyber lens, plus the things a
   professional does repeatedly: watch, get alerted, ask without a cap.

**Do not** try to charge the general reader in year one. **Do** treat every general
reader as distribution (share cards, SEO) and as the pool the professional tier is
drawn from.

---

## 2. Tiers and prices

Benchmarks: The Hindu digital ₹299/month, ₹2,399/year; The Ken ₹2,750/year;
Ground News Vantage $99.99/year (≈ ₹700/month equivalent), Premium $3.99/month in-app;
Particle+ $2.99/month or $29.99/year (US). Indian professional tools the personas
already pay for: ₹300–1,000/month.

| Tier | Price (incl. 18% GST) | Net to Prism¹ | What it includes |
|---|---|---|---|
| **Reader** | ₹0, no account needed | — | Today · Stories · Search · the full record (brief, who said what, coverage, reports, photos, clips, route) · Ask **10 questions/day** signed-in (3/day anonymous) · Watchlist (account) · 3 Markets samples · one Cyber sample |
| **Prism Plus** | **₹199/month** or **₹1,499/year** (₹125/month effective) | ₹165 / ₹1,241 | Markets and Cyber readings on every story · Market Pulse in full · Ask **100/day** on the stronger model · watchlist alerts (email; push when the app exists) · "what changed since you last read" · original-language quotes beside the translation when built |
| **Founding member** (first 500, then closed) | **₹999/year, price locked 3 years** | ₹827 | Plus, a name on /about, a say in the roadmap |
| **Teams / API** (from month 6+) | quote, from ₹4,999/month | — | seats, Slack/email alerts, the events + claims API |

¹ Net after GST (÷1.18) and payment fees (Razorpay UPI Autopay 2% + GST on the
fee ≈ 2.36%; 0% platform fee promotion for merchants activated after
2026-07-01 — verify at signup). Sold on the web via Razorpay, which avoids app-store
cuts (15–30%) entirely until a native app exists; when it does, keep web as the
place to subscribe.

**Why ₹199 and not ₹299.** You asked for minimal profit. ₹199 is 33% below The Hindu's
₹299 for a product that is not yet a habit, sits under the "don't think" threshold for
UPI Autopay, and still clears the fixed cost at a small subscriber count (§6). ₹149 as
a **first-90-days launch price** is defensible; do not go below — the DNR's clearest
recent lesson (USA Today Co.) is that heavy discounting buys subscribers who churn and
that ending it raised revenue per user 27% while cutting subscribers 30%.

**Monthly vs one-off.** Offer both monthly and annual; **no day passes or per-story
unlocks** in v1 — they create a second pricing mental model, generate support load,
and the DNR shows news-only micro-payments rarely stick. The one-off variant that does
work is the **founding annual**, because it is a commitment, not a sample.

---

## 3. Where the paywall sits (and where it never does)

Free, forever, no account: reading everything on the record. The paywall is **depth
on the same story**, never access to the story. Concretely:

| Moment | Anonymous | Free account | Plus |
|---|---|---|---|
| Read any record, sources, quotes, coverage, clips | ✓ | ✓ | ✓ |
| Ask | 3/day (per IP+session) | 10/day | 100/day, stronger model |
| Markets / Cyber reading | prompt to sign in (the flip still happens, the text is behind the unlock — existing) | 3 samples, then the upgrade prompt | ✓ |
| Watchlist, follow a story | sign in | ✓ | ✓ + alerts |
| Daily brief email (7:00 IST) | — | ✓ (opt-in) | ✓ with lens |
| Market Pulse | headline + first paragraph | first paragraph | full |

---

## 4. Limits on the expensive calls (do this before any marketing)

Today the only brakes are the LLM budget floor ($5) and two Ask caps. Before traffic
arrives, add these — all small, all in `common/quota.py` + Redis:

| Control | Rule | Why |
|---|---|---|
| **Per-IP anonymous Ask** | 3/day per IP, 1/minute | the session cap resets on a new tab; an IP cap does not |
| **Per-account Ask** | free 10/day, Plus 100/day; 6/minute | the daily cap is the plan; the minute cap stops scripts |
| **Model tiering** | free Ask → `glm-5.3-flash` (≈ $0.0005/question); Plus → `qwen3.7-plus` | a free question costs ⅙ of a paid one; quality still cited and grounded |
| **Question length** | ≤ 500 characters; context window capped at 6 sources | bounds the input tokens |
| **Per-user monthly inference budget** | ₹40 (≈ $0.45) free, ₹200 Plus; soft stop with a message | a hard ceiling per person, whatever the mix |
| **Global daily spend ceiling** | $25/day; at 80% degrade Ask to the light model, at 100% Ask off for anonymous | the budget floor is a floor on balance, not a ceiling on burn |
| **Lens briefs** | generate on demand once per event per lens (already cached); never for anonymous | first-reader cost only |
| **Podcast judge** | already cached per pair | — |
| **Bot filter** | require a session token issued on page load for Ask; block UA-less clients | stops curl loops |

Estimated effect: worst-case daily inference spend is bounded at fixed pipeline
($5) + $25 ceiling, independent of traffic.

---

## 5. How to gain users (India, 2026, zero ad budget)

Ranked by expected yield per hour of founder time. Instrument first: today there is
**no analytics at all**; add Plausible or PostHog (free tiers) before day one so the
funnel below is measured, not guessed.

1. **Every record is a shareable object.** The share card (OG image) and the
   canonical `/story/<id>` with JSON-LD already exist. Add a **"who said what" quote
   card** (speaker, role, the verbatim quote, the outlet) as a 1200×630 image —
   WhatsApp and X carry these on their own. WhatsApp is the distribution channel in
   India; every quote card carries the Prism mark and the story link.
2. **SEO on the record.** 1,600+ new URLs a day with unique, sourced text and
   structured data is a real asset; make sure `/story` pages are indexable, fast,
   and that the sitemap and `last_updated_at` are exposed. This compounds.
3. **The daily brief email at 7:00 IST** (Resend is wired): Today's top record as
   points, one link per story. Email is the retention channel that does not need an
   app. Opt-in at onboarding.
4. **Markets persona, where they already are:** X/Twitter finance, Telegram trading
   groups, Zerodha Varsity forums, r/IndianStockMarket. The hook is not "news" — it
   is "the exact quote, the exact source, before the open", i.e. the Markets lens on
   one live story, screenshot-able. Two posts a day of real records for 90 days.
5. **Cyber persona:** LinkedIn and infosec Twitter with the CVE/KEV records and the
   Cyber reading; the Indian CERT-In advisory audience is concentrated and vocal.
6. **Launches:** Product Hunt, Hacker News ("Show HN: a news record where every
   quote is verbatim and linked to the line"), r/india, and the Indian tech
   newsletters (Finshots, The Ken's readers overlap with the Markets persona).
7. **Campus:** free Plus for students with a .edu/.ac.in address — future
   professionals, high share rate, near-zero marginal cost.
8. **Publisher relationships:** Prism sends outbound clicks with credit (every
   report card, photo and quote links out). Tell the publishers; a couple of
   "as seen on" quotes and a friendly relationship with The Hindu / HT matters when
   scraping questions come up.

Funnel to measure: visit → 2 records read → sign-up prompt seen → account →
onboarding complete → D7 return → lens sample used → Plus. Targets for the first 90
days after launch (assumptions, not promises): 20k visits/month, 8% account
conversion, 25% D7, 3% of accounts to Plus.

---

## 6. Unit economics and break-even

Net per Plus subscriber ≈ ₹165/month (₹199 incl. GST, minus fees) ≈ $1.90.
Marginal inference per Plus subscriber ≈ ₹10–40/month. Fixed ≈ $210/month.

| Scenario | Subscribers | Monthly revenue (net) | Monthly cost² | Margin |
|---|---|---|---|---|
| Break-even | **~120** | $230 | $230 | 0 |
| Small | 500 | $950 | $290 | $660 |
| Working | 2,000 | $3,800 | $550 | $3,250 |
| Scale | 10,000 | $19,000 | $2,000 | $17,000 |

² Fixed $210 + inference ≈ $0.15/subscriber/month + infra growth. Pipeline cost
grows with **sources added**, roughly $3.5/month per additional daily feed of 60
articles.

Sensitivity: at ₹149 break-even is ~160 subscribers; at ₹299, ~80. Annual plans
pull cash forward and cut churn; assume 30% of Plus take annual.

Founding members: 500 × ₹827 net = ₹4.1 lakh (≈ $4,900) — roughly two years of
today's fixed costs, collected up front.

---

## 7. Onboarding: what, when, and when to ask for the account

**Principle:** nobody signs up to read. The account is asked for at the moment it
does something for the reader, and the ask names that thing.

**Sign-up triggers (soft, dismissible, once per trigger):**
1. After the **third record read in a session** — "Save your state and languages so
   Today is yours on every device" (today those live in localStorage only).
2. On the **first Ask** — answer it, then "Sign in for 10 questions a day".
3. On **Follow / Watchlist** — required, because it has nowhere to live without an
   account.
4. On a **locked lens** — the existing flip-then-unlock moment; this is the upgrade
   path, not the sign-up path, so it shows the price.

**Sign-in method:** magic link exists. Add **Google sign-in** (one tap, no password,
the dominant identity in India on Android). Skip phone OTP for now (₹0.15–0.25 per
SMS and fraud handling).

**Onboarding (after sign-up, ≤ 60 seconds, every step skippable, order matters):**
1. **Your state** (exists) — drives the state pill and the local tier.
2. **Languages you read** (exists) — drives ranking and the Indic record voice.
3. **What you follow** (exists as interests) — six subjects as chips.
4. **What do you read for?** — *Just the news* / *Markets* / *Security* → sets the
   default lens and which sample to offer first. New, one screen.
5. **The daily brief at 7:00** — one toggle, email prefilled from sign-in.
6. **Follow three** — three live stories/entities from today's record in the chosen
   subjects, pre-ticked. This is what makes D7 return: something is waiting.

Then land on Today with the state pill active and a one-line "Your Markets sample:
open any story and press 2".

**Upgrade moment copy** (on the locked lens): the price, "cancel any time", and the
one sentence of what the lens is — never a feature list.

---

## 8. Payments: implementation plan (≈ 1 week)

1. **Razorpay Subscriptions** (UPI Autopay + cards + net banking). Plans:
   `plus_monthly_199`, `plus_yearly_1499`, `founding_999`. UPI Autopay mandates under
   ₹15,000 need no per-debit approval.
2. **`subscriptions` table**: user_id, provider, provider_sub_id, plan, status
   (trialing/active/past_due/cancelled), current_period_end, cancel_at. Webhooks
   (`subscription.activated/charged/halted/cancelled`) update it; **entitlement =
   status in (active, past_due within 3-day grace)**. `isLocked(slug)` and
   `has_unlocked` read entitlement, not the session alone.
3. **GST**: prices displayed inclusive; invoice PDF by email on each charge (Razorpay
   does this; our GSTIN on it). Register for GST before the first charge.
4. **Dunning**: 3 retries over 7 days, email at each; grace access during.
5. **Refunds**: 7-day no-questions refund on annual; monthly non-refundable. Written on
   the pricing page.
6. **Legal**: Terms, Privacy (DPDP Act 2023 — consent, purpose, deletion on request),
   refund policy, a support address. Move Vercel to Pro.
7. **Account page**: plan, next charge, cancel, invoices — cancellation must be one
   click (it is also what makes the first charge easy to accept).

---

## 9. What to measure weekly

- Records read per visit; % visits with ≥ 2 records.
- Sign-up prompt shown → accounts (by trigger).
- Onboarding completion by step; D1/D7/D30 return.
- Lens sample used → Plus conversion; monthly churn; annual share.
- Inference $/day split pipeline vs Ask vs briefs; Ask questions per active user.
- Share-card clicks (UTM), search impressions on `/story`.

---

## 10. Sequence (what to do in which order)

| Week | Do |
|---|---|
| 1 | Analytics; Ask limits and model tiering (§4); Vercel Pro; Google sign-in |
| 2 | Onboarding steps 4–6; daily brief email; quote share card |
| 3 | Razorpay + `subscriptions` + entitlement; pricing page; legal pages; GST |
| 4 | Founding-member launch to the first 500 (X, LinkedIn, Product Hunt, HN); Markets-persona posting cadence begins |
| 5–12 | Weekly funnel review; price test ₹149 vs ₹199 by cohort; add sources only where a persona asks |

---

## Assumptions to challenge

- That the Markets persona will pay ₹199 for a *reading* rather than for *data* —
  the reading is only worth paying for once the story layer is right more often
  than not (the rebuild plan's F1 gate). Charge after that gate, not before.
- That WhatsApp share cards drive meaningful traffic without a native app.
- That 3% of free accounts convert — Ground News and Particle do not publish theirs;
  news-industry norms for free-to-paid sit at 1–5%.
- That the fixed cost stays near $200: each new daily feed adds ≈ $3.5/month, and a
  Hindi/regional expansion of 20 feeds would double the pipeline bill.

### Sources
- Reuters Institute, [Digital News Report 2026 — executive summary](https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2026/dnr-executive-summary): 17% pay for online news; chatbot use 7% → 10%; trust 37% news vs 20% chatbots; NYT bundling; USA Today Co. discount lesson.
- The Hindu digital pricing: [App Store listing](https://apps.apple.com/app/id771672321) (₹299/month, ₹2,399/year; All Access ₹399 / ₹2,799).
- The Ken pricing: [TechCrunch](https://techcrunch.com/?p=1675483) (₹2,750/year).
- Ground News pricing: [StationX review, Sept 2026](https://www.stationx.net/ground-news-review/) (Vantage $99.99/yr; Pro from $0.99, Premium from $3.99 in-app).
- Particle+ pricing: [App Store listing](https://apps.apple.com/us/app/particle-personalized-news/id6683283775) ($2.99/month, $29.99/year).
- Razorpay: [recurring billing costs compared](https://razorpay.com/blog/cheapest-payment-gateway-for-recurring-billing-e-nach-upi-autopay-and-subscription/), [UPI Autopay guide](https://razorpay.com/blog/master-recurring-payments-upi-autopay-guide/) (2% platform fee + GST; ₹15,000 mandate limit without AFA; 0% promotion for new merchants from 2026-07-01).
- Business Standard: [1 in 7 Indian-language news consumers ready to pay online](https://www.business-standard.com/india-news/1-among-7-indian-language-news-consumers-ready-to-pay-for-it-online-study-123050400725_1.html).
- OpenRouter model prices (2026-09-20): gemini-3.1-flash-lite $0.25/$1.50 per M; glm-5.3-flash $0.09/$0.30; qwen3.7-plus $0.32/$1.28; gemini-3.5-flash $1.50/$9.00.
- Internal: `common/quota.py`, `common/budget.py`, `common/config.py`, prod counts on 2026-09-20, balance movement 2026-09-18 → 20, `.claude/plans` rebuild plan §Revenue model.
