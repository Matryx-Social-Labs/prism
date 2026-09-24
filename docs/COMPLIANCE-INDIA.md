# Prism: India compliance — what applies, what to do, what to decide

> **This is research to support a decision, not legal advice. Confirm every "Yes/Likely/Unclear" with Indian counsel before relying on it.**
> Researched 2026-09-24. Law moves; each section says what was checked and when.

**How to read the tags**

- **[V]** verified: read in the primary text (Gazette, ministry/regulator PDF, court order, the Act).
- **[S]** secondary: law-firm note, LiveLaw/MediaNama/IFF, or a reproduction. Probably right, not checked at source.
- **[I]** our inference from the facts about Prism. This is the part counsel must test.
- **UNVERIFIED**: could not confirm.

**Who "we" are in this document.** Prism Media Intelligence LLP (Bengaluru) publishes Prism and is the data fiduciary. Matryx Social Labs Pvt Ltd builds and operates the technology, and is *temporarily* named as the collector of Razorpay payments. Paid plans are not on sale (Razorpay test mode).

---

## 1. One-page summary

"Effort" is our engineering estimate (days of work), not a quote. Lawyers' and self-regulatory-body fees are UNKNOWN unless stated.

| # | Obligation | Applies to us? | Why | What we'd need | Effort / cost | Deadline / urgency | Decision needed |
|---|---|---|---|---|---|---|---|
| 1 | IT Rules 2021 Part III: Grievance Officer based in India, 24h acknowledgement, 15-day decision, published on site (R10, R11) | **Likely** | An aggregator is expressly a "publisher of news" (R2(1)(t)) [V]; R10–11 not stayed [V] | Named officer, /grievance page, intake + tracker | ~2–3 days + officer's time | **In force now** (since 2021) | Who is Grievance Officer |
| 2 | Part III: furnish entity details to MIB within 30 days of starting (R18(1)–(2)) | **Likely** | Same; not stayed [V]. MIB still runs the process (forms re-issued 30.05.2025) [V] | File MIB form | ~1 day | **Possibly overdue** if our public launch counts as "commencing operations" [I] | File or not (counsel) |
| 3 | Part III: monthly compliance report + public grievance disclosure (R18(3), R19(1)–(2)) | **Likely** | Same [V] | Monthly page, even if the count is zero | ~1 day build | Monthly, now | None; do it |
| 4 | Part III: keep records of content for at least 60 days (R19(3)) | **Likely** | Same [V] | Keep every published record, headline and brief version ≥60 days | ~1 day | Now | Keep 60 days or longer |
| 5 | Part III: join a self-regulating body (R11(2)(d), R12) | **Unclear** | R11(2)(d) is not stayed, but the three-tier structure (R9(3)) it serves *is* stayed [V]. Enforceability is disputed [S] | Membership of one of MIB's 9 registered news SRBs [V] | Fees UNKNOWN | No regulator deadline known | Join / not / which (counsel) |
| 6 | Part III: Code of Ethics (R9(1)) | **No (stayed)** | Bombay HC stay 14 Aug 2021, pan-India per Madras HC; continues after transfer to Delhi HC [V/S] | Nothing mandatory. Following PCI norms voluntarily is cheap protection | 0 | None | No |
| 7 | Part III: MIB blocking orders (R15, R16) | **Yes** | Not stayed [V] | Process to comply with an order | Runbook only | When an order arrives | No |
| 8 | Intermediary duties (Part II) for Ask | **Unlikely** | Ask answers are our own generated output, so we are the publisher of them, not an intermediary [I] | Nothing extra beyond #1 | 0 | none | No |
| 9 | IT Amendment Rules 2026 (AI "synthetically generated information" labels) | **No** | Covers audio/visual only. MeitY FAQ: "Pure text / written outputs, by themselves, are not SGI" [V] | Keep our "software-written" label anyway | 0 | none | No |
| 10 | DPDP Act + Rules 2025, main duties | **Yes, from 13 May 2027** | We are a data fiduciary [V] | Itemised notice, withdrawal, security, breach notices (72h to Board), 1-year log/data retention (R8(3)), contact person, 90-day grievances, children | ~1–2 weeks spread over months | **13 May 2027** (Gazette signed 14 Nov 2025; plan to the 13th) | Retention policy; minors |
| 11 | IT Act s.43A + SPDI Rules 2011 (until DPDP repeals them, May 2027) | **Likely, in part** | Still in force until s.44(2) DPDP commences [V]. r.5(9) says to name a Grievance Officer [S] | Named officer (#1 covers it), reasonable security | 0 extra | Now | No |
| 12 | CERT-In Directions 2022: Point of Contact, 6-hour incident reporting, 180-day logs, clock sync | **Yes** | An LLP is a "body corporate" [V/S]. The MSME grace period ended 25 Sep 2022 [V] | Point of Contact filed with CERT-In, incident runbook, log drain to ≥180-day store, time sync | ~2–4 days + small storage cost | **In force now**. Fine up to **₹1 crore** [V] | Where logs live; who is Point of Contact |
| 13 | CERT-In FAQ 36: "logs and records of financial transactions in Indian jurisdiction" | **Unclear** | Railway has **no India region** [V], so our Postgres (subscription status and amount) is abroad | Either keep billing records in India or rely on Razorpay (India) as the system of record | Unknown | Before sale | Counsel |
| 14 | Consumer Protection (E-Commerce) Rules 2020 | **Likely, once selling** | Selling our own digital subscription online = inventory e-commerce [I, on V text] | Legal name + address, grievance officer (48h / 1 month), no pre-ticked consent, show how to cancel regular payments, one total price with tax breakup | ~1–2 days | Before sale | None |
| 15 | E-Commerce Amendment Rules 2026 (Gazette 10 Sep 2026) | **Likely** | Same | Join National Consumer Helpline convergence, **yearly dark-pattern self-audit + displayed certificate**, copy of complaint to complainant, prior-price rule | ~1 day + audit time | **1 Jan 2027** | Who signs the self-audit |
| 16 | Dark Patterns Guidelines 2023 | **Yes, once selling** | Apply to "all platforms systematically offering goods or services in India" [V] | Renewal terms shown before the mandate; cancel as easy as subscribe; founding-price renewal disclosed | Design decisions | Before sale | **Renewal terms** |
| 17 | RBI e-mandate (Framework 2026, 21 Apr 2026) | **Via Razorpay** | Issuer sends the 24h pre-debit notice. ₹15,000 limit without extra authentication covers our prices [V] | Our disclosures + Razorpay's required policy pages (incl. a delivery/shipping page) | ~0.5 day | Before sale | None |
| 18 | **Matryx collecting payments for the LLP** | **High risk** | Razorpay terms bar letting "third parties, including Your affiliates" use the account [V]. Looks like unlicensed payment aggregation [V text / I]. GST invoice must come from the supplier [S] | LLP's own merchant account **before** going on sale | Delay only | **Before sale** | Don't sell until the LLP account is live? |
| 19 | GST | **Yes, once selling** | 18% on online news subscriptions (SAC 998431) [V]. Registration compulsory above ₹20 lakh [S] | CA; decide voluntary registration. Our Terms already say "price includes GST" | CA fees | Before sale | Register now or at threshold |
| 20 | Copyright (full-text storage, quotes, briefs, translation) | **Yes (risk)** | Fair dealing for "reporting of current events" s.52(1)(a)(iii) [V]; no Indian aggregator case [S] | Retention limits, opt-out list, short quotes, counsel opinion | ~1–2 days + counsel | Ongoing; ANI appeal next listed 8 Dec 2026 [S] | Retention; licensing |
| 21 | Publisher RSS terms / robots.txt | **Yes (contract risk)** | TOI, HT and IE RSS terms: personal, non-commercial only. The Hindu's terms ban scraping, caching and AI use [V] | Per-source review, licences or drop, honour opt-outs | Counsel + ops | Before paid launch | Per-source |
| 22 | Press & Registration of Periodicals Act 2023 | **No** | "Periodical" = published **and printed** [V] | Nothing | 0 | — | No |
| 23 | FDI rules for digital news | **Yes, if raising money** | News aggregators are expressly within the 26% government-route cap [S]. **An LLP can take foreign money only in 100%-automatic sectors, so none here** [S] | Counsel before any foreign or NRI money | 0 now | Before any fundraise | Entity structure |
| 24 | SEBI Research Analyst rules (Markets lens) | **Unclear** | "Research report" excludes general market commentary [S]. Stock-specific opinions for a fee could fall inside [I] | Keep Markets to news; no buy/sell or price views | Copy review | Before a paid Markets lens | Counsel |
| 25 | Defamation (BNS s.356; civil) | **Yes** | Machine-written headlines are our publication; no safe harbour [I] | Corrections policy, fast takedown, keep versions | ~1 day | Now | None |
| 26 | Karnataka draft bills (misinformation, digital safety, hate speech) | **Not in force** | Drafts; hate-speech bill reserved for the President [S] | Watch | 0 | — | No |
| 27 | Karnataka Shops & Establishments, professional tax | **Likely, if LLP has an office/staff** | [S] | CA | Small | — | CA |

**What changes our assumptions or the external report (most important first)**

1. **Payments via Matryx look like the biggest near-term risk**, not the IT Rules. Razorpay's terms and RBI's 2025 Payment Aggregator directions both cut against one company collecting for another (§3.5).
2. **The external report's Part III list is accurate, clause by clause** [V]: SRB membership R11(2)(d), MIB filing R18, monthly report R18(3), 60-day preservation R19(3). It omitted three things:
   - Bombay HC stayed R9(1) and R9(3) on 14 Aug 2021. The Madras HC order records the government's lawyer accepting pan-India effect.
   - The Supreme Court moved all challenges to the **Delhi High Court on 22 Mar 2024**. The stay continues and the case is pending there [S].
   - Rules 10–19 are **not** stayed [V].
   - Our own plan file (`.claude/plans/trust-india-indic.plan.md`) says the stay covers "the three-tier mechanism". That is only half right: R9(3) *creates* the three tiers and is stayed, but the grievance officer, MIB filing and monthly report rules are separately in force.
3. **Two things neither of us had, now live** [V]:
   - The old privacy regime (IT Act s.43A + SPDI Rules 2011) runs until DPDP replaces it in May 2027.
   - The CERT-In fine is **up to ₹1 crore** (raised by the Jan Vishwas Act 2023), not ₹1 lakh.
4. **DPDP Rule 8(3)** [V] requires every data fiduciary to keep "personal data, associated traffic data and other logs of the processing" for **at least one year**, from 13 May 2027. That clashes with our instant account deletion and short hosting logs.
5. **New in September 2026** [V]: the E-Commerce Rules amendment (in force 1 Jan 2027) requires a **yearly dark-pattern self-audit and a displayed certificate**, and National Consumer Helpline participation.
6. **CERT-In FAQ nuance** [V]:
   - Q35 allows logs abroad if we can produce them "in a reasonable time".
   - But Q36 says "logs **and** records of financial transactions in Indian jurisdiction", which can be read as covering logs too.
   - Railway has no India region, so our database, including billing rows, is abroad.
7. **ANI v OpenAI** [V via LiveLaw]: on **24 Jul 2026** the Delhi HC refused ANI an interim injunction. It held that storage in a "closed space" for training is prima facie fair dealing (private use / research), and that outputs were not substantial reproduction. ANI appealed; the next date is 8 Dec 2026 [S]. This helps us by analogy only.
8. **FDI** [S]: a digital-news LLP cannot take foreign investment at all. This matters before any fundraise.

---

## 2. No-regret actions vs counsel-dependent actions

### 2a. No-regret: cheap, sensible whatever counsel says

| # | Action | Satisfies (at least in part) | Effort |
|---|---|---|---|
| N1 | **Name a Grievance Officer** who lives in India (a partner is fine; no employee requirement found [V]). Publish name, designation, postal address and a dedicated email (e.g. grievance@readprism.news) on a /grievance page and in the footer | IT Rules R11(2)(a)–(b); E-Com R4(4); SPDI r.5(9); DPDP s.8(9) | hours |
| N2 | **One SLA for every complaint:** acknowledge within 24h, send the complainant a copy of the complaint as we recorded it, decide within 15 days. This is the strictest of all regimes, so one clock covers all | IT R10(2), R10(3)(a), R11(2)(c); E-Com R4(5) (48h / 1 month; copy from 2027); DPDP R14(3) (≤90d) | ~2 days (form + table + admin view) |
| N3 | **Monthly public grievance report** (received, resolved, median time, outcomes; publish zeros) | IT R18(3), R19 | ~1 day |
| N4 | **Keep every published version** of each record's machine headline and brief, and a log of Ask answers served, for at least 60 days. We suggest 1 year, which also matches DPDP R8(3) and the 1-year limitation for civil libel [I, not re-verified] | IT R19(3); defamation defence; DPDP R8(3) | ~1 day |
| N5 | **CERT-In basics:** file a Point of Contact (Annexure II to info@cert-in.org.in); a one-page 6-hour incident runbook (incident@cert-in.org.in, 1800-11-4949); a log drain from Vercel + Railway to storage kept ≥180 days (1 year from May 2027), preferably in an India region; note the time zone in logs | CERT-In (i)–(iv); DPDP R6, R8(3) | ~2–4 days |
| N6 | **Do not go on sale until the LLP's own Razorpay account is live.** Remove the "collected by Matryx" arrangement rather than paper over it | Razorpay terms; RBI PA directions; GST invoicing | delay only |
| N7 | **Decide and print renewal terms before sale.** Before the mandate screen: renews automatically, at what price (including what the ₹999 founding plan renews at), how often, and "cancel in one click". Keep a log of each consent (Razorpay requires it). No pre-ticked boxes; no guilt-trip copy in the cancel sheet | Dark Patterns (subscription trap, SaaS billing, drip pricing, confirm shaming); E-Com R4(9), R7(1)(c) | ~1 day |
| N8 | **Show one total price including GST**, with the tax breakup, only once the LLP is GST-registered (see §3.5). Until then our Terms' "price includes GST" line must not go live | E-Com R7(1)(e); CGST | copy |
| N9 | **Add Razorpay's required pages:** About, Contact, Pricing, Terms, Privacy, Cancellation & Refunds (we have these), **plus a short "Delivery" page** ("digital access starts immediately on payment") | Razorpay onboarding [V] | hours |
| N10 | **Written processor contracts:** LLP ↔ Matryx (processor on the LLP's instructions, with security terms), and confirm vendor data-processing agreements (Vercel, Railway, Resend, OpenRouter + providers, Google). **Labeller agreements** cover confidentiality, data handling and ownership of labels. Add labeller applicant data to the privacy notice | DPDP s.8(2), R6(1)(f); SPDI | ~2 days + review |
| N11 | **Privacy copy fixes:** "written ahead of the Act's phased commencement (main duties from 13 May 2027)"; name the Grievance Officer; list labeller data | Accuracy of our own notice | hours |
| N12 | **Breach playbook:** CERT-In within 6h now. From May 2027, notify the Data Protection Board and affected users "without delay", with a detailed report to the Board in 72h. One document, two clocks | CERT-In; DPDP R7 | ~0.5 day |
| N13 | **Corrections policy + visible correction notes** on records; voluntarily follow the Press Council's accuracy norms (not mandatory while R9(1) is stayed) | Defamation risk; the ethics code if the stay lifts | ~1 day |
| N14 | **Source hygiene:** keep a per-source opt-out list; honour an outlet's written objection within days; delete full article text once it is no longer needed for extraction/Ask (set a number); turn on zero-retention routing at the LLM provider where offered | Copyright s.52(1)(c) notice logic; RSS terms; DPDP-style minimisation | ~1–2 days |
| N15 | **No foreign or NRI money into the LLP** without counsel | FDI | 0 |
| N16 | **Markets lens copy:** no buy/sell/hold, no price targets, keep the "information, not a recommendation" line | SEBI RA boundary | copy |

### 2b. Counsel-dependent: don't do these until counsel answers (questions in §5)

- **C1** Whether to file the Rule 18 information with MIB, and whether it is "overdue".
- **C2** Whether and which self-regulating body to join (R11(2)(d)).
- **C3** Whether our billing rows must live in India (CERT-In FAQ 36), which decides whether to move billing tables to an India-region database or rely on Razorpay as the record.
- **C4** Any interim payment structure if the team insists on selling before the LLP account exists.
- **C5** Copyright/RSS strategy: rely on fair dealing, drop sources, or seek licences. Also full-text retention length and quote translation.
- **C6** Scope of DPDP R8(3) one-year retention against erasure requests (what exactly to keep after an account is deleted).
- **C7** Whether the paid Markets lens needs SEBI guardrails beyond N16.
- **C8** Entity structure for fundraising (LLP vs company; FDI cap).
- **C9** GST: register voluntarily before the ₹20 lakh threshold?

---

## 3. Regime by regime

### 3.1 IT Rules 2021, Part III (Digital Media Ethics Code)

**What the law says** [V: MeitY consolidated text updated 10.02.2026; MIB copy May 2026]

- **R2(1)(o) "news aggregator"**: "an entity who, performing a significant role in determining the news and current affairs content being made available, makes available to users a computer resource that enable such users to access the news and current affairs content which is aggregated, curated and presented by such entity."
- **R2(1)(t) "publisher of news and current affairs content"**: "an online paper, news portal, **news aggregator**, news agency and such other entity … functionally similar … but shall not include newspapers, replica e-papers … and any individual or user who is not transmitting content in the course of systematic business, professional or commercial activity."
- **R2(1)(m)** "news and current affairs content" includes "newly received or noteworthy content, including analysis, especially about recent events primarily of socio-political, economic or cultural nature".
- **R8(2)**: Part III applies to a publisher that "operates in the territory of India" (deemed where it "has a physical presence") or "conducts systematic business activity of making its content available in India".

**What Rules 9–19 require** [V]

| Rule | Requirement | Status |
|---|---|---|
| 9(1) | Follow the Code of Ethics (Press Council "Norms of Journalistic Conduct"; Cable TV Programme Code; no content prohibited by law) | **Stayed** |
| 9(3) | Three tiers: self-regulation → self-regulating body → MIB oversight | **Stayed** |
| 10 | Anyone may complain. **Acknowledge within 24h (R10(2))**; decide within 15 days (R10(3)(a)); escalation to the SRB, then appeal to MIB | Not stayed |
| 11(2) | (a) Grievance Officer "based in India"; (b) display the mechanism, officer's name and contact "at an appropriate place on its website"; (c) decide in 15 days; **(d) "be a member of a self-regulating body"** | Not stayed (but see below) |
| 12 | SRB: headed by a retired SC/HC judge or "independent eminent person", registered with MIB; can warn, require an apology or disclaimer, refer to MIB | Not stayed |
| 13–14 | MIB oversight; Inter-Departmental Committee | Not stayed (Bombay HC declined to stay R14 as the committee did not yet exist) |
| 15–16 | Blocking and emergency blocking directions (can be addressed to "the publisher … or any intermediary") | Not stayed |
| 18 | Furnish entity details to MIB within 30 days of starting operations (forms in MIB's notice of 26.05.2021, re-issued 30.05.2025); **R18(3) "publish periodic compliance report every month"** | Not stayed |
| 19 | Public disclosure of grievances and orders, "updated monthly"; **R19(3) "preserve records of content transmitted by it for a minimum period of sixty days"** | Not stayed |

Part III has **no monetary penalty** [V]. The levers are MIB advisories, the committee and blocking.

**Current status of the court challenges**

- **Bombay HC, 14 Aug 2021** (Agij Promotion of Nineteenonea Media v UoI; Nikhil Wagle v UoI) [V]:
  - Para 37: "we direct stay of operation of sub-rules (1) and (3) of Rule 9". Rule 9 is prima facie beyond the IT Act's rule-making power and chills Art. 19(1)(a).
  - A stay of R16 was refused because it tracks s.69A.
  - The order does not itself say "pan-India".
- **Madras HC, 16 Sep 2021** (Digital News Publishers Association; T.M. Krishna) [V]: records that the Additional Solicitor-General "accepts that the order passed by the High Court of Judicature at Bombay would have pan-India effect".
- **Supreme Court** [S]:
  - 9 May 2022: High Court proceedings stayed, interim orders continue.
  - **22 Mar 2024: all challenges transferred to the Delhi High Court.** The Union may seek to vacate the interim orders there.
  - Arguments were listed from Nov 2024. **No judgment found; treated as pending (UNVERIFIED for 2025–26 hearings).**
- **MIB's practice** [V]:
  - It lists 11 registered SRBs. The 9 for news: NBF-PNBSA, WJAI, IDPCGC, MDMF, DIGIPUB, Working Journalist Media Council, Digital Media Publishers & News Portal Grievance Council, PADMA, JMAGC.
  - It re-issued the R18 forms (30.05.2025).
  - It still cites the Code of Ethics in advisories to OTT platforms (Feb and Apr 2025).
  - About 3,101 digital news publishers had filed R18 details by May 2023 [S]. MIB told an RTI appeal the filings were "voluntary" [S].
- **Enforcement against aggregators:** none found against Dailyhunt, Inshorts, Google News or Way2News [UNVERIFIED — absence of evidence only].

**Amendments, and whether they touch us**

| Amendment | What it does | Touches Prism? |
|---|---|---|
| Oct 2022 (G.S.R. 794(E)) | Grievance Appellate Committee for intermediaries | No [V] |
| Apr 2023 (G.S.R. 275(E)) | Fact-check unit, R3(1)(b)(v). Struck down by Bombay HC (Kunal Kamra, 20/26 Sep 2024). SC issued notice 10 Mar 2026 and **declined a stay** [S] | No |
| Oct 2025 (G.S.R. 775(E), in force 15.11.2025) | Takedown notices to intermediaries need a court order or a senior officer's reasoned intimation | No (intermediaries) |
| **Feb 2026 (G.S.R. 120(E), in force 20.02.2026)** | "Synthetically generated information" = audio/visual only. Labels + metadata for intermediaries whose tools create it. Intermediary timelines: 3h takedown, 7-day grievance resolution | **No.** MeitY FAQ: a "chatbot-generated article … is not SGI" [V]. Part III unchanged |
| Draft Second Amendment 2026 (Mar/Apr 2026; comments to 7 May) | Makes MeitY advisories binding on intermediaries; extends R14–16 (committee and blocking) to intermediaries and to news shared "by users who are not publishers" | Not final [UNVERIFIED as of Sep 2026]. Does **not** add grievance officers for creators, despite some reports [V] |
| Broadcasting Services (Regulation) Bill | 2024 draft covering digital creators withdrawn Aug 2024; "under consultation" Dec 2025 [S] | Not law |

**Is Prism an intermediary as well?** [I]

- The IT Act's intermediary definition and the s.79 safe harbour cover "third party information". The safe harbour is lost if the platform selects or modifies what is transmitted.
- Our clustered records, machine headlines, briefs and Ask answers are generated and selected by us. **We are their publisher**, with no safe harbour.
- The user's Ask question is not passed on to anyone, so an intermediary reading is marginal.
- The MeitY AI advisory (1 Mar 2024, revised 15 Mar 2024) asks platforms to label fallible AI output. It is not law; our "software-written" label already meets its spirit.

**How it applies to Prism** [I]

- We aggregate ~33–42 outlets, choose what goes together, and write our own headline. That is "a significant role in determining the news … content … aggregated, curated and presented". We are a Bengaluru LLP, so R8(2) is met.
- We are very likely a "publisher of news and current affairs content" (as a news aggregator, and arguably as a news portal for our own machine-written text).

**Options**

| Option | What it means | Pros | Cons |
|---|---|---|---|
| A. Do nothing until challenged | Rely on the stay | Zero cost | Rules 10–19 are not stayed; low-cost duties ignored; poor look with MIB and readers |
| **B. Comply with the cheap, unstayed parts; leave SRB membership and R18 filing to counsel** | N1–N4 now; C1–C2 after advice | Covers the duties counsel will almost certainly say apply; reversible | Small ongoing effort |
| C. Full compliance incl. SRB + MIB filing now | Everything | Maximum safety | Joins a regime under constitutional challenge; SRB decisions bind us; fees unknown |

**Recommended: B.**

### 3.2 DPDP Act 2023 + DPDP Rules 2025

**Commencement** [V: G.S.R. 843(E)–846(E), dated 13 Nov 2025, Gazette digitally signed 14 Nov 2025]

| Stage | What commences | Date |
|---|---|---|
| On publication | Definitions; Board (ss.18–26); ss.35, 38–43; s.44(1),(3) (the RTI amendment). Rules 1, 2, 17–21 | 13/14 Nov 2025 |
| +12 months | s.6(9) and s.27(1)(d) (Consent Managers). Rule 4 | **13/14 Nov 2026**. Nothing for us to do |
| +18 months | **ss.3–5, 6(1)–(8),(10), 7–17, 27 (except (1)(d)), 28–34, 36, 37, 44(2)**. Rules 3, 5–16, 22, 23 | **13/14 May 2027** |

Notes:

- A proposal to cut 18 months to 12 was floated in Jan 2026. On 31 Aug 2026 the MeitY Secretary said deadlines "would remain unchanged" [S]. No amending notification was found.
- The Board is established in law. As of 1 Aug 2026 no Chairperson or members were appointed [S].
- Some secondary sources say the Board can penalise generally from Nov 2026. **That is wrong per G.S.R. 843(E)** [V].
- **s.44(2), which deletes IT Act s.43A, commences only in May 2027** [V]. So s.43A and the **SPDI Rules 2011 stay in force until then**. SPDI r.5(9): "designate a Grievance Officer and publish his name and contact details on its website", redress "within one month" [S]. Whether r.5 applies depends on collecting *sensitive* data (passwords, financial data). We store no passwords and Razorpay holds card/UPI data, so it is arguable. Naming the officer (N1) closes it.

**What a data fiduciary must do from 13 May 2027** [V unless marked]

| Duty | Source | What it means for Prism |
|---|---|---|
| Standalone, itemised, plain-language notice: each data item, each purpose, how to withdraw (as easy as giving consent), how to exercise rights, how to complain to the Board | s.5, R3 | Rewrite /privacy in itemised form; our current page is close |
| Free, specific, informed, unambiguous consent; withdrawable | s.6 | Sign-up consent screen; no pre-ticked boxes |
| Accuracy where data is used for decisions | s.8(3) | Low relevance |
| Processors only under a valid contract with security terms | s.8(2), R6(1)(f) | N10 |
| Security minimum: encryption/masking, access control, "appropriate logs, monitoring and review", backups, keep logs and personal data one year | s.8(5), R6 | Log drain (N5) serves both CERT-In and this |
| Breach: tell each affected person "without delay"; tell the Board "without delay", detailed report "within seventy-two hours" | s.8(6), R7 | N12 |
| **Keep "personal data, associated traffic data and other logs of the processing for a minimum period of one year"** for Seventh Schedule purposes, then erase | **R8(3)** | **Conflicts with instant deletion and short logs.** Need a "deleted but retained for 1 year, restricted" state. Scope is for counsel (C6) |
| 3-year inactivity erasure | R8(1), Third Schedule | **Not us**: only e-commerce ≥2 crore users, gaming ≥50 lakh, social media ≥2 crore |
| Publish business contact of a person who can answer questions, "prominently" and in every rights response | s.8(9), R9 | Grievance Officer page (N1) |
| Answer grievances within a period "not exceeding ninety days" | s.13, R14(3) | Our 15-day SLA (N2) is well inside |
| Children (under 18): verifiable parental consent; no tracking, behavioural monitoring or targeted ads | s.9, R10 | Our Terms already require 18+. Add an affirmative "I am 18 or older" at sign-up. Watchlists and stored questions could count as behavioural monitoring if a child got in |
| Cross-border transfer allowed unless a country is blacklisted (none notified) | s.16, R15 | Vercel, Railway, OpenRouter abroad are fine today [V/S] |
| Significant Data Fiduciary duties | s.10, R13 | Only if designated; unlikely |
| **No journalism exemption.** The startup exemption (s.17(3)) needs a notification, and none exists | s.17 | We are fully in scope |

**Penalties** (Schedule) [V]:

| Breach | Maximum penalty |
|---|---|
| Security safeguards | ₹250 crore |
| Breach notification | ₹200 crore |
| Children | ₹200 crore |
| Significant Data Fiduciary duties | ₹150 crore |
| Anything else | ₹50 crore |

**Fiduciary vs processor** [I]:

- The LLP decides purposes and means, so it is the fiduciary.
- Matryx is a processor under contract. If it ever uses the data for its own purposes (e.g. training its own models), it becomes a joint fiduciary.
- Labellers who see personal data are processors or agents and need contracts.

**Options and recommendation**

- **Now:** N10, N11, N12, the age declaration, and the log drain.
- **By Q1 2027:** the itemised notice, consent screen, withdrawal path and the R8(3) retention design, after counsel on C6.
- **Before 13 May 2027:** go live with all of it. Starting now spreads the work and costs little.

### 3.3 CERT-In Directions, 28 Apr 2022 (No. 20(3)/2022-CERT-In)

**Applicability** [V]:

- They apply to "service providers, intermediaries, data centres, body corporate and Government organisations".
- FAQ Q25 uses the IT Act s.43A definition: "any company and includes a firm, sole proprietorship or other association of individuals engaged in commercial or professional activities". An LLP is a body corporate under LLP Act s.3 [S]. **Both the LLP and Matryx are covered.**
- In force since 27/28 Jun 2022; for MSMEs since **25 Sep 2022** [V].

**Requirements** [V]

1. **Clocks:** "connect to the Network Time Protocol (NTP) Server of National Informatics Centre (NIC) or National Physical Laboratory (NPL) or with NTP servers traceable to these".
   - FAQ Q41: cloud customers "relying on the native time services offered as part of Cloud may continue to use the same".
   - IST is not required; record the time zone.
2. **Report incidents within 6 hours** of noticing, as listed in Annexure I. The 20 types include unauthorised access, website defacement, malicious code, attacks on servers and applications, phishing, DoS/DDoS, **data breach, data leak**, cloud and AI/ML attacks.
   - Channels: incident@cert-in.org.in, 1800-11-4949.
   - A partial first report is fine (Q30).
   - The duty "is neither transferrable nor indemnified" (Q13): whoever notices must report.
3. **Point of Contact:** send details in Annexure II to info@cert-in.org.in and keep them updated.
4. **Logs:** "enable logs of all their ICT systems and maintain them securely for a rolling period of 180 days and the same shall be maintained within the Indian jurisdiction".
   - Q37 examples: firewall, web/database/mail server, application logs, SSH, VPN.
   - Record both successful and unsuccessful events.

**What the FAQs relax, and what they don't** [V]

- **Q35:** "The logs may be stored outside India also as long as the obligation to produce logs to CERT-In is adhered to by the entities in a reasonable time." Our earlier finding is confirmed.
- **Q36:** "Any service provider offering services to the users in the country needs to enable and maintain logs **and** records of financial transactions in Indian jurisdiction."
  - This sits awkwardly with Q35. The safe course is to keep a copy of logs in India.
  - Our "financial transactions" live primarily at Razorpay (in India; RBI requires payment-system operators to store payment data only in India [S]). Our Postgres on Railway (no India region [V]) holds plan, status and amount.
- **Q23:** penalties to be used "reasonably and on occasions when the non-compliance is deliberate".

**Penalty** [V]: s.70B(7) — up to 1 year's imprisonment and/or a fine **up to ₹1 crore** (Jan Vishwas Act 2023, in force 30 Nov 2023). No reported enforcement 2022–26 [S].

**Later developments:**

- The CERT-In Comprehensive Cyber Security Audit Policy Guidelines (25 Jul 2025) expect an annual audit from organisations "required to or … seeking to" evaluate posture. **This is guidance, not a direct duty on us** [V].
- No amendment to the 2022 Directions found [S].

**Practical position with our hosts** [V: vendor docs]

- **Vercel** runtime logs: Pro keeps **1 day**. Log drains are available on Pro ($0.50/GB).
- **Railway**: Pro keeps **30 days**, Enterprise up to 90. No native drain; forward with Vector/Fluent Bit/OpenTelemetry.
- Neither reaches 180 days, so we need our own log store.
- India-region object storage exists (AWS ap-south-1 Mumbai / ap-south-2 Hyderabad; GCP asia-south1/2; Azure Central India). Use lifecycle expiry and write-once locking.

**Options**

| Option | Pros | Cons |
|---|---|---|
| A. Logs abroad, rely on FAQ Q35 | Simplest | Q36 ambiguity; must be able to produce logs "in a reasonable time" |
| **B. Drain logs to India-region storage, 180 days now → 1 year from May 2027** | Removes the ambiguity; serves DPDP R6/R8(3) | Small build + storage bill |
| C. Also move billing tables to an India-region database | Answers Q36 fully | Splits the database; real work. Only if counsel says Razorpay-as-record is insufficient |

**Recommended: B now (N5); C only if counsel requires it (C3).**

### 3.4 Consumer Protection (E-Commerce) Rules 2020 and Dark Patterns Guidelines 2023

**Do they apply?** [V text; I application]

- The CP Act s.2(16) defines "e-commerce" as "buying or selling of goods or services including digital products over digital or electronic network".
- R2 applies the Rules to "all models of e-commerce, including marketplace and inventory models".
- An "inventory e-commerce entity … owns the inventory of goods or services and sells such goods or services directly to the consumers" (R3(1)(f)).
- **Selling Plus on our own site makes the LLP an inventory e-commerce entity** [I].
- The resident **nodal officer** (R4(1), as amended May 2021) applies only where the entity "is a company incorporated under the Companies Act…" [V]. **On the literal text an LLP is outside it, but Matryx (a company) would be inside it if it is treated as the seller.**
- The June 2021 draft (Chief Compliance Officer, flash sales) was never notified [V].

**Duties once selling** [V]

- **R4(2):** legal name, "principal geographic address of its headquarters and all branches", website details, customer-care and grievance officer contacts.
- **R4(4)–(5):** appoint a grievance officer, display "name, contact details, and designation"; acknowledge "within forty-eight hours", redress "within one month". No residency requirement stated.
- **R4(9):** consent by "explicit and affirmative action … no … pre-ticked checkboxes".
- **R4(10):** refunds "within a reasonable period".
- **R7(1)(c):** show "the procedure to cancel regular payments".
- **R7(1)(e):** "total price in single figure … along with the breakup price … and the applicable tax".
- CP Act s.2(47)(vii)–(viii): not issuing a bill, or refusing to refund for deficient service within the stated period (or 30 days), is an unfair trade practice.

**New: E-Commerce (Amendment) Rules 2026** [V: Gazette CG-DL-E-10092026-276125; in force **1 January 2027**. The year digit did not extract from the PDF; secondary sources agree on 2027]

- The grievance officer must also give the complainant "a copy of the complaint as recorded by the grievance officer".
- "Every e-commerce entity shall become a partner in the convergence process of the National Consumer Helpline."
- Prior-price rule: a price cut must show "the lowest price … thirty days prior". Relevant if the ₹999 founding price is advertised against ₹1,199.
- "Comply with the Guidelines for Prevention and Regulation of Dark Patterns, 2023 and also conduct **yearly self-audit** … and a **certificate** to this effect shall be displayed prominently."

**Dark Patterns Guidelines 2023** [V]

- They apply to "all platforms, systematically offering goods or services in India". 13 patterns are listed. The ones that matter for a subscription:
- **Subscription trap:**
  - "(i) making cancellation of a paid subscription impossible or a complex and lengthy process";
  - "(ii) hiding the cancellation option";
  - "(iii) forcing a user to provide payment details or authorization for auto debits for availing a free subscription";
  - "(iv) making the instructions related to cancellation … ambiguous, latent, confusing, cumbersome".
- **SaaS billing:** includes "no notification is given to the user when free trial is converted to paid" and "silent recurring transactions … auto-renewing monthly subscriptions without telling users".
- **Drip pricing:** price elements "not revealed upfront", or charging "higher than the amount disclosed at the time of checkout".
- **Bait and switch**, **confirm shaming** (guilt copy on decline or cancel), **nagging**, and **disguised advertisement** (ads posing as news; relevant if we ever run sponsored content).
- **Enforcement** [S]:
  - A CCPA self-audit advisory was issued 5 Jun 2025.
  - About ₹20 lakh in penalties across 9 platforms had been imposed by Aug 2026. Examples: FirstCry ₹2 lakh (GST added at checkout = drip pricing); McAfee ₹1 lakh (prominent "Renew Now" beside a greyed-out decline).

**How it applies to our undecided renewal terms** [I]

- **Current design:**
  - One-click cancel keeping access to period end, and a 7-day full refund on yearly charges (`web/src/lib/legal.ts`). **Good.**
  - The Terms say prices include GST and that we tell users before a changed price applies. **Good**, if true on the day.
- **Must decide before sale:**
  - (a) What the **₹999 founding** plan renews at. If ₹1,199, say so at checkout, beside the price.
  - (b) Any free trial: if one requires a mandate, say so prominently and notify before conversion.
  - (c) Whether we send our own reminder before yearly renewals. The bank sends only a 24h notice, and a 7-day advance email is cheap goodwill [I].
  - (d) No "are you sure you want to lose…" copy in the cancel sheet.

**Recommended:** N7 + N8 + N9 before sale; the yearly self-audit (a one-page checklist signed by a partner) and the National Consumer Helpline partnership by 1 Jan 2027.

### 3.5 Payments: RBI e-mandate, the merchant-of-record problem, GST

**RBI e-mandate** [V: "Digital Payments – E-mandate Framework, 2026", RBI/DPSS/2026-27/396, 21 Apr 2026, effective immediately; repeals the 2019–2024 circulars]

- Registration only after additional-factor authentication (AFA).
- The **issuer** sends a pre-debit notice "at least 24 hours prior", giving the merchant's name, amount, date and reason. It lets the customer opt out of a debit or withdraw the mandate.
- Recurring debits need no AFA "up to ₹15,000/- per transaction", which covers all our prices.
- "An acquirer shall ensure compliance with these directions by merchants on-boarded by them."
- The Authentication Directions 2025 (effective 1 Apr 2026) exempt recurring e-mandate debits other than the first [V].
- **Razorpay and the bank handle the mechanics.**
- **We handle** the disclosures: plan terms, price, frequency, cancellation route and policy pages. Razorpay's terms also require keeping "a log of all instances of obtaining customer consent" [V].
- Known Razorpay constraints are already in our design: UPI/e-mandate subscriptions cannot be patched; pause needs Razorpay support to enable it.

**Merchant of record: Matryx collecting for the LLP** [V text; I application]

- **Razorpay terms:** "You shall not resell or assign the Services … or otherwise allow the use of the Services by any third parties, including Your affiliates." Collecting on behalf of sub-merchants requires being onboarded as a master merchant with licences "to operate as a payment aggregator/e-commerce marketplace".
- **RBI Payment Aggregator Master Direction (15 Sep 2025):**
  - A PA is "an entity that facilitates aggregation of payments made by customers to the merchants … and subsequently settles the collected funds to such merchants".
  - Non-banks "shall seek authorisation".
  - Operating a payment system without authorisation is barred by the PSS Act s.4 [S].
- **GST:** the tax invoice is issued by the supplier (CGST s.31). A person supplying "on behalf of other taxable persons whether as an agent or otherwise" must register (s.24(vii)) [S].
- **Our Terms already disclose the arrangement** ("collected by Matryx … on behalf of" the LLP). That is honest, but it documents exactly the third-party use Razorpay's terms prohibit.
- **Recommended (N6):** stay in test mode until the LLP's own Razorpay account is live. If the business insists on selling earlier, counsel and a CA must design it (C4). One option to test: Matryx as the actual seller under a licence from the LLP. That changes who the consumer-law seller and GST supplier are, and possibly who the "publisher" is.

**GST** [V rate; S registration]

- **Rate:** Notification 11/2017-CT(Rate), heading 9984, "information supply services" at 9% CGST + 9% SGST = **18%**. SAC 998431 is "On-line text based information such as online books, newspapers, periodicals…".
  - The 5% rate is only for e-books.
  - The "news" exemption covers only independent journalists, PTI and UNI.
  - GST 2.0 (Notification 15/2025, effective 22 Sep 2025) did not change heading 9984.
- **Registration:**
  - Compulsory above ₹20 lakh aggregate turnover (Karnataka is not a special-category state).
  - Inter-state B2C services below the threshold are exempt from compulsory registration (Notification 10/2017-IT).
  - Selling on our own site means no e-commerce-operator trigger.
- **Consequence** [I]: an unregistered LLP cannot charge GST. Then "the price you see … includes GST" (Terms) would be wrong. Either register voluntarily before sale, or change the copy.
  - If registered, imported services (Vercel, Railway, OpenRouter) attract reverse-charge IGST, generally creditable [S].
- **Decision C9, with a CA.**

### 3.6 Copyright Act 1957 and publisher terms

**What the law says** [V: copyright.gov.in consolidated Act]

- **s.52(1)(a):** "a fair dealing with any work, not being a computer programme, for the purposes of— (i) private or personal use, including research; (ii) criticism or review…; (iii) **the reporting of current events and current affairs**, including the reporting of a lecture delivered in public."
  - **Explanation:** "The storing of any work in any electronic medium for the purposes mentioned in this clause … shall not constitute infringement of copyright."
- **s.52(1)(b):** transient or incidental storage "purely in the technical process of electronic transmission".
- **s.52(1)(c):** transient or incidental storage for "providing electronic links, access or integration, where such links … has not been expressly prohibited by the right holder". There is a 21-day takedown on a written complaint.
- **s.14(a):** exclusive rights include reproduction "including the storing of it in any medium by electronic means" and **translation** (v) and adaptation (vi).

**Indian cases** [S]

- **Fair dealing is fact-specific.** Civic Chandran (Ker 1996) weighs how much was taken, the purpose, and competition. Super Cassettes v Hamar TV (Del 2010) holds that commercial use is not unfair in itself.
- **ESPN Star v Global Broadcast News** (Del DB 2008): use beyond ~30s per bulletin / 2 min a day "may negate" fair dealing for news. Quantity matters.
- **Akuate Internet v Star India** (Del DB 2013): no US-style "hot news" right; facts are free.
- **Krishika Lulla** (SC 2015): no copyright in a title. By analogy, low risk for showing headlines.
- **Associated Broadcasting (TV9) v Google** (Del, 28 Feb 2026): 4–5-second clips for news context were fair dealing for reporting current events.
- **No Indian case against a news aggregator found** (UNVERIFIED).
- **ANI Media v OpenAI** (CS(COMM) 1028/2024) [V via LiveLaw; S detail]:
  - **24 Jul 2026**, Amit Bansal J refused the interim injunction.
  - Storage in a "closed space" for training is reproduction, but prima facie fair dealing as **private use / research** (not "reporting current events").
  - Outputs were "not a substantial reproduction".
  - The court noted quoted material came from third-party speakers (s.17(cc): the speaker owns a public speech).
  - Appeal: notice issued 15 Sep 2026, **next date 8 Dec 2026** [S]. Sources conflict on the bench.
- **DPIIT Working Paper on Generative AI and Copyright, Part I (8 Dec 2025)** [V]: proposes a mandatory blanket licence with statutory remuneration for AI training. It is a proposal, with no bill found [UNVERIFIED].

**Publisher terms and robots.txt** [V, fetched 2026-09-24]

- **Times of India RSS:** "permission to only access and make personal use of its RSS feeds … forbids … displaying, hosting, aggregating, reselling or putting to commercial use … must not retain any copies".
- **Hindustan Times RSS:** "solely for … individuals to view headlines … for their personal and non-commercial use."
- **Indian Express RSS:** "strictly for personal and non-commercial use."
- **The Hindu terms:** no scraping or data-mining scripts, no caching or archiving, no use "for … training a machine learning or artificial intelligence (AI) system" without written consent. Its robots.txt blocks GPTBot, ClaudeBot, CCBot, PerplexityBot and others. Indian Express blocks ClaudeBot, PerplexityBot and Bytespider. TOI has no AI block.
- robots.txt has no statutory force in India. It is still evidence of "express prohibition" under s.52(1)(c) and of knowledge [I].

**How it applies to Prism** [I]

| Activity | Risk | Why |
|---|---|---|
| Headline + outlet + time + link out | Low (copyright); **contract risk under RSS terms** | Titles are weakly protected; link-outs send readers to the outlet |
| Verbatim quotes with attribution | Low–medium | Reporting current events; speakers often own public speeches (s.17(cc)); keep quotes short |
| Our machine headline + brief | Low–medium | Facts are free; risk only if it closely paraphrases one outlet's expression |
| **Storing full article text** internally | **Medium** | Reproduction. Best defence is s.52(1)(a)(iii) + the Explanation (storage for the reporting purpose), and ANI's "closed space" reasoning by analogy. s.52(1)(b)/(c) fit poorly because the copy is kept |
| Sending text to overseas LLMs | Medium | Each transfer is a further copy; zero-retention settings help |
| Translating quotes (planned) | Medium–low | Translation is an exclusive right; fair dealing arguably still covers reporting; no case |
| Paid subscription on top | Raises the stakes | Commercial use is not fatal to fair dealing, but it is exactly what the RSS terms forbid |

**Options:**

- **A. Status quo.**
- **B. Minimise:** N14, plus a per-source review of terms, dropping or seeking permission from sources whose terms expressly bar our use. **Recommended now.**
- **C. Licence key outlets or wires:** cost unknown; best long-term.

Recommended **B now, with counsel on C5 before the paywall goes live.**

### 3.7 Other things that matter

**Press and Registration of Periodicals Act 2023 — does not apply** [V]

- s.2(g): a "periodical" is a publication "published **and printed** at regular intervals containing public news". "Printing" means mass reproduction of copies.
- A digital-only site is not a periodical. The earlier drafts' "news on digital media" did not survive into the Act [S].

**Foreign investment — material before any fundraise** [S]

- Digital news is capped at **26% FDI, government route** (Press Note 4, 2019).
- The DPIIT clarification of 16 Oct 2020 applies it expressly to "news aggregators", defined as "an entity which, using software o[r] web application, aggregates news content from various sources".
- Conditions: majority of the board and the CEO must be Indian citizens; security clearance for foreign staff deployed >60 days a year.
- **Foreign investment in an LLP is allowed only in sectors with 100% automatic-route FDI and no FDI-linked conditions** (NDI Rules). So **a digital-news LLP cannot take foreign investment** [S; counsel to confirm, C8].

**SEBI Research Analyst rules — Markets lens** [S]

- A "research report" is a communication with "research analysis or research recommendation or an opinion concerning securities … providing a basis for investment decision". It does not include "comments on general trends in the securities market", commentaries on economic, political or market conditions, or broad-based indices.
- SEBI FAQs (Jul 2025): journalists "on the payrolls of media agencies" need not register, but any recommendations they make must follow SEBI's rules.
- **Our position** [I]: a news re-read tagged to a ticker is probably general news. A paid lens that says a stock will rise or fall probably is not. Keep N16; ask counsel (C7) before charging for Markets.

**Defamation — our machine text is our publication** [S/I]

- Criminal defamation is BNS s.356 (was IPC 499/500), with up to 2 years' simple imprisonment. There is civil liability too.
- A wrong machine headline or brief about a named person is our statement; the "software-written" label is not a defence.
- Mitigations: grounding (already our design), a corrections policy with visible notes (N13), fast action on complaints (N2), and keeping versions (N4).

**Karnataka bills — watch, nothing to do** [S]

- The Misinformation and Fake News (Prohibition) Bill 2025 was a draft, with 2–7 years' jail proposed.
- The "Karnataka Responsible Social Media & Digital Safety Bill, 2026" was submitted to the CM in Apr 2026. It proposes AI labels, 24–48h takedowns and a state regulator. Introduction was targeted for the 2026 monsoon session; whether it was introduced is UNVERIFIED.
- The Hate Speech and Hate Crimes (Prevention) Bill 2025 was reserved by the Governor for the President.
- None is law as of this research.

**Karnataka establishment basics** [S]: Shops & Commercial Establishments registration within 30 days of opening an office; professional tax enrolment for the LLP (about ₹2,500 a year). Ask the CA.

**Labellers**: currently unpaid (v1).

- If paid later, a CA handles tax withholding.
- Now: a short contributor agreement covering confidentiality, handling of personal data they may see, and our ownership of labels. Add applicant data to the privacy notice (N10, N11).

---

## 4. The Grievance Officer

**What the role is.** One named person readers can complain to about content, privacy or billing. The officer logs each complaint, acknowledges it, decides it within the deadline, and reports the monthly numbers publicly. Under the IT Rules the officer is also the "nodal point for interaction with the complainant, the self-regulating body and the Ministry" (R11(3)) [V].

**Who can hold it**

| Regime | Must be… | Employee? | Deadlines | What to publish | In force |
|---|---|---|---|---|---|
| IT Rules Part III, R10–11 | "based in India" [V] | No requirement found [V] | Acknowledge 24h (R10(2)); decide 15 days | Name, contact details, the mechanism (R11(2)(b)) | Now |
| E-Commerce Rules R4(4)–(5) | No residency stated [V] (resident *nodal officer* only for companies) | No | Acknowledge 48h, redress 1 month; from 1 Jan 2027 also a copy of the complaint as recorded | Name, contact details, **designation** | Once selling |
| SPDI Rules r.5(9) | Not stated | No | Redress within one month [S] | Name + contact | Now → May 2027 |
| DPDP s.8(9), s.13, R9, R14(3) | No residency for the contact person. A DPO must be in India, but only Significant Data Fiduciaries need one (s.10) [V] | No | ≤90 days | Business contact info, prominently, and in every rights response | 13 May 2027 |
| SSMI Resident Grievance Officer (R4) | Resident employee | **Yes**, but only for significant social media intermediaries | — | — | **Not us** [V] |
| CERT-In Point of Contact | — | — | Incident reports within 6h | Filed with CERT-In, not published | Now |

- **Can a founder hold it?** Nothing in these texts bars a partner of the LLP [V as to the texts; UNVERIFIED as to other law]. Small Indian publishers name a senior person: Newslaundry names its Grievance Officer with grievance@ and monthly reports; The News Minute (Bengaluru) names the officer, a postal address and a form [V].
- **Can one person cover IT Rules + Consumer + SPDI + DPDP?** No text prohibits it, and it is common practice [V/S]. Use the strictest deadlines (24h / 15 days) for everything.
- **Practical recommendation** [I]: one India-resident partner as Grievance Officer, a named backup for leave, and a dedicated mailbox, not hello@. The CERT-In Point of Contact can be the engineer on call (likely the CTO), since incident reporting is a technical 6-hour clock.

**Day to day** (a few minutes a day at our volume)

1. Check the grievance queue daily (the 24h clock).
2. Acknowledge with a reference number and a copy of the complaint as recorded.
3. Triage by kind:
   - **Content:** accuracy, a wrong quote, a machine headline, ethics.
   - **Privacy / data rights.**
   - **Billing / subscription.**
   - **Copyright** (an outlet objecting).
   - **Legal order** (MIB, court, police): escalate same day.
4. Decide within 15 days, with written reasons. Correct, update, remove or decline.
5. For content fixes, add a visible correction note on the record.
6. At month end, publish the report: counts by kind, resolved, median time, outcomes, orders received.
7. Keep complaint records and published-content versions (≥60 days; we suggest 1 year).

**Sample /grievance page (outline)**

1. **Title:** "Grievances and corrections".
2. **Who publishes Prism:** Prism Media Intelligence LLP, registered address [to fill], Bengaluru, Karnataka; LLPIN [optional].
3. **Grievance Officer:** [Name], [Designation, e.g. Designated Partner], [postal address], grievance@readprism.news, [phone optional].
4. **What you can raise here:**
   - something wrong in a record, quote, machine-written headline or brief;
   - your personal data (access, correction, erasure, withdrawing consent);
   - a subscription or payment;
   - a copyright concern (rights holders);
   - anything else about how Prism is run.
5. **How:** a short form (kind, link to the record if any, what is wrong, what you want us to do, your email; name optional). Or email.
6. **What happens next:** acknowledged within 24 hours with a copy of your complaint as recorded; a written decision within 15 days; corrections shown on the record.
7. **If you're not satisfied:**
   - content: [the self-regulating body, if we join one] / MIB;
   - consumer matters: National Consumer Helpline (1915 / consumerhelpline.gov.in) or the consumer commission via e-Daakhil;
   - personal data: the Data Protection Board of India (from May 2027).
8. **Monthly reports:** link to /grievance/reports.
9. **Corrections log:** link.
10. **From 1 Jan 2027:** the dark-pattern self-audit certificate (could live here or in the footer).
11. **Last updated:** date.

---

## 5. Questions for Indian counsel, and what counsel to hire

**Numbered questions** (each maps to a decision in §6)

1. Are we a "news aggregator" and so a "publisher of news and current affairs content" under R2(1)(o)/(t)? Does our own machine-written headline also make us a "news portal"? Does Ask change anything?
2. With R9(1) and R9(3) stayed (Bombay HC 14 Aug 2021; now pending before the Delhi HC after the SC transfer of 22 Mar 2024), which of Rules 10–19 are operative for us in practice?
3. Must we file the R18 information with MIB? We have been publicly live since [date]; is it "overdue"? What are the consequences of filing (entering the MIB regime) vs not filing?
4. R11(2)(d): must we join an SRB? If so, which of the 9 MIB-registered news SRBs suits a small aggregator? What do they cost, and what does being bound by their decisions mean?
5. R19(3): what counts as "records of content transmitted" for us — records, machine headlines and briefs, Ask answers? For how long do you advise keeping them?
6. Can one designated partner be Grievance Officer under the IT Rules, E-Commerce Rules, SPDI Rules and DPDP at once? Any conflict?
7. Do SPDI Rules r.5 duties (named Grievance Officer, one-month redress) apply to us now, given we hold no passwords or payment data?
8. Please confirm the roles: LLP as data fiduciary, Matryx as processor. What must the LLP–Matryx contract say? Does admin or labeller work make Matryx a joint fiduciary?
9. DPDP R8(3) (keep personal data, traffic data and processing logs for one year): what exactly must we keep after a user deletes their account? How do we square this with erasure requests?
10. DPDP children: is an 18+ affirmative declaration at sign-up plus blocking enough, or must we verify age?
11. CERT-In: may our logs stay abroad under FAQ Q35 despite Q36's wording? Are our Postgres rows (plan, status, amount) "records of financial transactions" that must be in India, when Razorpay holds the payment records in India?
12. CERT-In: the LLP and Matryx are both body corporates and the duty is "neither transferrable nor indemnified". One Point of Contact or two? How do we avoid duplicate or missing reports?
13. Payments: is Matryx collecting for the LLP permissible under Razorpay's terms, RBI's PA directions and GST? If we must sell before the LLP account is live, what structure works, and what does it do to consumer-law and publisher status?
14. E-Commerce Rules: is the LLP an "e-commerce entity" when selling its own subscription? Does the resident nodal officer rule (companies only) bite on Matryx in the interim?
15. Dark patterns: please review our checkout, renewal, cancel and founding-price flows. What renewal disclosures are enough? Who can sign the yearly self-audit certificate required from 1 Jan 2027?
16. Copyright: is internal full-text storage for extraction and Ask defensible under s.52(1)(a)(iii) + the Explanation? How long may we keep it? What does the ANI v OpenAI interim order (24 Jul 2026; appeal next 8 Dec 2026) change for us?
17. RSS and site terms: TOI, HT and IE limit feeds to personal non-commercial use; The Hindu bars scraping, caching and AI use. Is breach of these terms actionable against us? Should we license, drop, or rely on fair dealing? Does fetching the article page, not just the feed, change the analysis?
18. Is translating verbatim quotes into other Indian languages fair dealing for reporting?
19. Sending article text and user questions to overseas LLM providers: any copyright or contractual issues? What processor terms should we insist on?
20. Defamation: what exposure do machine-written headlines create, and what minimum editorial controls and corrections process do you advise?
21. SEBI: at what point would a paid Markets lens become a "research report" or investment advice? What guardrails?
22. FDI: please confirm a digital-news LLP cannot take foreign investment. What entity structure should we use before fundraising? Does Matryx's own shareholding matter while it only builds the tech?
23. Labellers: contributor agreement terms (IP in labels, confidentiality, personal data); employment-status risk if we pay them later.
24. Karnataka: anything in the 2026 digital-safety draft we should prepare for?

**What kind of counsel**

- **Primary: a technology, media and telecom (TMT) / digital-media practice** that has advised digital news publishers on Part III, including the R18 filing and SRB questions. Most such teams also cover DPDP and CERT-In (Q1–Q15, Q19–Q21, Q24).
- **Copyright / IP counsel** with news or aggregation experience (Q16–Q18). This may be the same firm.
- **A Chartered Accountant** for GST registration, invoicing, reverse charge, the merchant-of-record structure (with counsel), LLP filings and Karnataka registrations (Q13, C9).
- **Names found in research** (not endorsements; not vetted): Trilegal, Khaitan, Cyril Amarchand, AZB, IndusLaw, Nishith Desai, Ikigai Law, Saraf, SNG, and Bengaluru firms such as Spice Route Legal and Samvad Partners; Anand and Anand for IP.

**Cost** (only credible published figures; everything else UNKNOWN)

- A fixed-fee privacy policy from one online legal-services firm: "₹15,000" [V, ipandlegalfilings.com].
- A vendor blog estimates year-one DPDP compliance for a startup at "₹40,000 to ₹2 lakh" (Consently, Apr 2026). This is **low credibility**; the vendor sells compliance tooling.
- **Tier-1 hourly rates, TMT opinion fees and SRB membership fees: UNKNOWN.** No reliable public source was found.
- Suggest asking two firms for a **fixed-fee scoped review** of Q1–Q15 plus a separate short copyright opinion (Q16–Q18), and comparing the quotes.

---

## 6. Decision log (for the team to fill)

| # | Decision | Options | Research recommends | Owner | Due |
|---|---|---|---|---|---|
| D1 | Who is Grievance Officer (and backup) | CEO / CTO / other India-resident partner | An India-resident partner + named backup; dedicated mailbox | | This week |
| D2 | Build /grievance, tracker, monthly report, content-version retention | Now / after counsel | Now (N1–N4) | | 2 weeks |
| D3 | Engage counsel and CA | Firm A / B; fixed-fee scope | Two quotes on §5 Q1–Q15 + a copyright opinion | | 2 weeks |
| D4 | File R18 information with MIB | File / don't / after counsel | After counsel (C1) | | After counsel |
| D5 | Join a self-regulating body | Join X / don't / defer | After counsel (C2) | | After counsel |
| D6 | CERT-In Point of Contact + incident runbook | Who | CTO as Point of Contact; runbook covers the LLP and Matryx | | This week |
| D7 | Log retention and location | Abroad (FAQ Q35) / India-region drain / also billing DB in India | India-region drain; 180 days → 1 year by May 2027 | | 1 month |
| D8 | When to go on sale | Now via Matryx / wait for LLP account | Wait for the LLP's own Razorpay account (N6) | | Before sale |
| D9 | Renewal terms | Founding ₹999 renews at ₹999 or ₹1,199; trial or not; pre-renewal reminder | Decide, then print at checkout (N7) | | Before sale |
| D10 | GST registration | Voluntary now / at ₹20 lakh | Ask CA; fix Terms copy either way (N8) | | Before sale |
| D11 | Full-text retention and source policy | Keep all / delete after N days / per-source licences | Delete after a set window + opt-out list (N14); licences later | | 1 month |
| D12 | DPDP programme | Start now / start Q1 2027 | Start now; complete by 13 May 2027 | | 13 May 2027 |
| D13 | R8(3) one-year retention design | After counsel | After counsel (C6) | | Q1 2027 |
| D14 | Dark-pattern self-audit owner | Who signs | A partner signs a yearly checklist | | 1 Jan 2027 |
| D15 | Markets lens guardrails | Copy rules / counsel | N16 now; counsel before charging (C7) | | Before paid Markets |
| D16 | Entity for fundraising | Stay LLP / company | Counsel before any outside money (C8) | | Before fundraise |
| D17 | Labeller contributor agreement | Now / when paid | Now | | Before next round |

---

## 7. Sources

**IT Rules 2021 / MIB / courts**

- MeitY consolidated IT Rules (updated 10.02.2026): https://www.meity.gov.in/static/uploads/2026/02/550681ab908f8afb135b0ad42816a1c9.pdf
- MeitY consolidated IT Rules (updated 06.04.2023): https://www.meity.gov.in/static/uploads/2024/02/Information-Technology-Intermediary-Guidelines-and-Digital-Media-Ethics-Code-Rules-2021-updated-06.04.2023-.pdf
- MIB copy of IT Rules (May 2026): https://mib.gov.in/sites/default/files/2026-05/it-rules-2021-2.pdf
- MIB Digital Media page (SRB list): https://mib.gov.in/en/ministry/our-wings/digital-media
- MIB R18 forms corrigendum 30.05.2025: https://mib.gov.in/sites/default/files/2025-06/furnishing-of-informaiton-30.05.2025_0.pdf
- MIB registration letter for an SRB (MDMF), 03.01.2022: https://mib.gov.in/sites/default/files/2025-01/registration-of-media9-digital-media-fedration-dated-03.01.2022.pdf
- MIB advisories 19.02.2025 / 22.04.2025: https://mib.gov.in/sites/default/files/2025-02/advisory-dated-19.02.2025_0.pdf ; https://mib.gov.in/sites/default/files/2025-04/advisory-dated-22.04.2025-1.pdf
- MeitY SGI FAQ: https://www.meity.gov.in/static/uploads/2025/10/065b6deb585441b5ccdf8be42502a49c.pdf
- MeitY draft Second Amendment 2026: https://www.meity.gov.in/static/uploads/2026/03/30591fc6e322dcbcc9dae84a0f02e9e7.pdf ; https://www.meity.gov.in/static/uploads/2026/04/c6a19720a5818c853e526a082e7f8f9a.pdf
- Bombay HC order 14.08.2021 (via IFF): https://drive.google.com/file/d/10Ng6Ve2pXTf2G78UHBfGntwMndKpQLqj/view ; summary https://internetfreedom.in/bombay-high-court-stays-the-operation-of-rule-9-1-and-rule-9-3-of-it-rules-2021/
- Madras HC order 16.09.2021: https://www.medianama.com/wp-content/uploads/2021/09/IT-Rules-Madras-High-Court-Order-September-17-2021.pdf
- SC transfer to Delhi HC (22.03.2024): https://www.livelaw.in/top-stories/supreme-court-petitions-against-it-rules-2021-transferred-delhi-hc-253147 ; https://www.scobserver.in/cases/transfer-of-it-rules-challenges/
- SC stay of HC proceedings (09.05.2022): https://internetfreedom.in/supreme-court-stays-proceedings-before-high-courts-challenging-it-rules-2021-interim-orders-to-continue/
- Delhi HC hearing notice: https://internetfreedom.in/dhc-it-rules-2021-hearing/
- Kunal Kamra SC appeal: https://www.newsonair.gov.in/sc-agrees-to-examine-centres-plea-against-striking-down-of-it-rules-amendments
- IFF on draft Second Amendment: https://internetfreedom.in/sound-the-alarm-iffs-first-read-on-meitys-draft-it-rules-second-amendment-2026/
- IFF on R18 filings / RTI: https://internetfreedom.in/revealed-two-thousand-news-publishers-furnished-details-to-mib/ ; https://internetfreedom.in/rule-18-it-rules-rti-appeal/ ; https://internetfreedom.in/mib-cic-order-itrules-2021/
- Broadcasting Bill status: https://internetfreedom.in/a-broadcasting-summary/ ; https://www.etvbharat.com/en/bharat/government-has-examined-suggestions-on-broadcasting-services-bill-minister-murugan-tells-rajya-sabha-enn25120505833
- MeitY AI advisory 1 Mar 2024 (copy): https://regmedia.co.uk/2024/03/04/meity_ai_advisory_1_march.pdf ; revised: https://www.azbpartners.com/bank/meity-liberalizes-ai-advisory-dated-march-1-2024-following-industry-concerns-and-issues-revised-advisory-on-march-15-2024/
- IT Amendment Rules 2026 notes: https://www.khaitanco.com/thought-leadership/MeitY-notifies-the-IT-Amendment-Rules-2026

**DPDP / SPDI**

- G.S.R. 843(E) commencement: https://egazette.gov.in/WriteReadData/2025/267647.pdf
- G.S.R. 844(E) Board: https://egazette.gov.in/WriteReadData/2025/267648.pdf ; G.S.R. 845(E): https://egazette.gov.in/WriteReadData/2025/267649.pdf
- G.S.R. 846(E) DPDP Rules 2025: https://egazette.gov.in/WriteReadData/2025/267650.pdf ; https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf
- DPDP Act 2023: https://www.meity.gov.in/static/uploads/2024/06/2bf1f0e9f04e6fb4f8fef35e82c42aa5.pdf
- Rule 8 text: https://www.dpdpa.com/dpdparules/rule8.html ; Rule 9: https://www.dpdpa.com/dpdparules/rule9.html
- PIB backgrounder 17 Nov 2025: https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf
- MeitY Board appointments circular 06.05.2026: https://www.meity.gov.in/static/uploads/2026/05/cd481c027470b420b4cb85fb40a91c53.pdf
- Board status (LiveLaw, 1 Aug 2026): https://www.livelaw.in/articles/india-data-protection-board-established-law-543751
- Timeline unchanged (31 Aug 2026): https://varindia.com/news/dpdp-deadline-stays-meity-issues-major-update ; 12-month proposal: https://www.business-standard.com/technology/tech-news/meity-may-cut-compliance-timeline-for-key-dpdp-rules-to-12-months-126012201293_1.html
- SPDI Rules r.5: https://indiankanoon.org/doc/70568009/
- LLP Act s.3: https://indiankanoon.org/doc/113974804/

**CERT-In**

- Directions 28.04.2022: https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf
- FAQs May 2022: https://www.cert-in.org.in/PDF/FAQs_on_CyberSecurityDirections_May2022.pdf
- MSME extension 27.06.2022: https://www.cert-in.org.in/PDF/CERT-In_directions_extension_MSMEs_and_validation_27.06.2022.pdf
- Audit Policy Guidelines 2025: https://www.cert-in.org.in/PDF/Comprehensive_Cyber_Security_Audit_Policy_Guidelines.pdf
- Jan Vishwas Act 2023 (s.70B(7) fine): https://egazette.gov.in/WriteReadData/2023/248047.pdf ; https://www.meity.gov.in/static/uploads/2024/03/MeitY-JVA-1.pdf
- Vercel logs / drains: https://vercel.com/docs/observability/runtime-logs ; https://vercel.com/docs/drains
- Railway logs / regions: https://docs.railway.com/guides/logs ; https://docs.railway.com/reference/deployment-regions
- RBI storage of payment system data FAQ: https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=2995

**Consumer protection / dark patterns**

- E-Commerce Rules 2020: https://consumeraffairs.gov.in/public/upload/files/E%20commerce%20rules_1732703966.pdf
- E-Commerce Amendment Rules 2021: https://consumeraffairs.gov.in/public/upload/files/Consumer%20Protection%20(E-Commerce)%20(Amendment)%20Rules,%202021_1732704241.pdf
- E-Commerce Amendment Rules 2026: https://consumeraffairs.gov.in/public/upload/admin/cmsfiles/whatsnews/E_Commerce_Amendment_Rules_2026_2026-09-11_18-12-39.pdf ; https://egazette.gov.in/WriteReadData/2026/276125.pdf
- Dark Patterns Guidelines 2023: https://consumeraffairs.gov.in/public/upload/files/The%20Guidelines%20for%20Prevention%20and%20Regulation%20of%20Dark%20Patterns,%202023_1732707717.pdf
- CP Act 2019: https://consumeraffairs.gov.in/public/upload/files/CP%20Act%202019_1732700731.pdf
- June 2021 draft (never notified): https://prsindia.org/billtrack/draft-amendments-to-the-consumer-protection-e-commerce-rules-2020
- CCPA penalties: https://www.business-standard.com/industry/news/ccpa-fines-indigo-zepto-bookmyshow-dark-patterns-quick-commerce-penalty-126080600580_1.html ; https://www.barandbench.com/law-firms/view-point/from-nudge-to-notice-what-indias-dark-pattern-orders-mean-for-digital-business
- CCPA self-audit advisory: https://chambers.com/articles/central-consumer-protection-authority-advisory-on-self-audit

**Payments / GST**

- RBI E-mandate Framework 2026: https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=13374
- RBI Authentication Directions 2025: https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12896
- RBI PA directions: https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12898&Mode=0
- Razorpay terms: https://razorpay.com/terms/ ; website requirements: https://razorpay.com/docs/payments/dashboard/account-settings/business-website-details/
- GST rate notification 11/2017-CT(Rate) (consolidated copy): https://www.tgct.gov.in/tgportal/Docs/Notifications/TGST/Updated%20TGST%20Rates,%202017%2011-2017-CT(R).pdf
- Exemption notification 12/2017-CT(Rate): https://www.tgct.gov.in/tgportal/Docs/Notifications/TGST/Updated%20TGST%20Rates,%202017%2012-2017-CT(R).pdf
- GST 2.0 notification 15/2025-CT(Rate): https://accounts.iith.ac.in/pdf/GST/15-2025-CTR-eng1758171762.pdf
- Compulsory registration s.24: https://taxguru.in/goods-and-service-tax/compulsory-gst-registration-section-24-cgst-act-2017.html
- AAR on online subscriptions: https://www.taxscan.in/subscription-charge-providing-access-online-content-18-gst-aar/38889
- Reverse charge on imported cloud services: https://taxguru.in/goods-and-service-tax/gst-hosting-services-oidar-classification-rcm-liability-latest-judgments.html

**Copyright / publisher terms**

- Copyright Act (consolidated): https://copyright.gov.in/Documents/CopyrightRules1957.pdf
- ANI v OpenAI interim order (LiveLaw): https://www.livelaw.in/amp/high-court/delhi-high-court/delhi-high-court-openai-ani-copyright-infringement-interim-relief-chatgpt-542746
- ANI appeal: https://www.livelawbiz.com/copyright/delhi-high-court-issues-notice-on-ani-appeal-against-dismissal-of-interim-injunction-plea-in-copyright-suit-against-openai-550080 ; https://www.storyboard18.com/digital/ani-appeals-delhi-hcs-openai-copyright-ruling-ws-l-110016.htm
- DPIIT Working Paper on GenAI and Copyright (Dec 2025): https://www.dpiit.gov.in/static/uploads/2025/12/ff266bbeed10c48e3479c941484f3525.pdf
- ESPN Star v Global Broadcast News: https://spicyip.com/2008/10/for-love-of-cricket-delhi-high-courts.html
- Akuate v Star India: https://indiankanoon.org/doc/160841206/
- TV9 v Google (2026): https://spicyip.com/2026/03/a-new-shield-for-the-strike-era-analysing-the-delhi-high-courts-reasoning-in-associated-broadcasting-v-google.html
- CCI order on DNPA complaint: https://www.cci.gov.in/images/antitrustorder/en/4120211665141327.pdf ; 2026 complaint: https://www.medianama.com/2026/05/223-dainik-bhaskar-publishers-file-cci-case-google-revenue-sharing/
- RSS / terms / robots: https://timesofindia.indiatimes.com/rss.cms ; https://www.hindustantimes.com/rss ; https://indianexpress.com/rss/ ; https://www.thehindu.com/termsofuse/ ; https://www.thehindu.com/robots.txt ; https://indianexpress.com/robots.txt

**Grievance page examples**

- https://www.newslaundry.com/grievance-redressal ; https://www.thenewsminute.com/grievance-redressal ; https://www.boomlive.in/grievance-redressal

**Other**

- PRP Act 2023: https://prgi.gov.in/sites/default/files/2025-04/act_2023.pdf
- FDI in digital media (DPIIT clarification 16.10.2020): https://www.khaitanco.com/thought-leaderships/Clarification-on-the-FDI-Policy-for-uploading-streaming-of-news-and-current-affairs-through-digital-media ; https://www.business-standard.com/article/economy-policy/digital-media-news-agencies-need-to-comply-with-26-fdi-cap-govt-120101601220_1.html
- FDI in LLPs: https://www.lexology.com/library/detail.aspx?g=3c153318-4032-4de6-bac2-7a2b139f28ab
- SEBI RA FAQs (Jul 2025): https://www.sebi.gov.in/legal/circulars/jul-2025/frequently-asked-questions-faqs-related-to-regulatory-provisions-for-research-analysts_95549.html ; https://www.lkslaw.com/insights/articles/key-clarifications-under-the-sebi-issued-faqs-2025
- BNS s.356: https://testbook.com/judiciary-notes/section-356-bns
- Karnataka drafts: https://thesouthfirst.com/karnataka/karnataka-proposes-bill-to-tackle-misinformation-deepfakes-online-harassment/ ; https://sflc.in/sflcins-statement-on-the-karnataka-misinformation-and-fake-news-prohibition-bill-2025/ ; https://www.thenewsminute.com/karnataka/karnataka-governor-withholds-assent-on-hate-speech-bill-sends-for-presidential-assent
- Karnataka establishment / professional tax: https://www.indiafilings.com/learn/shops-establishments-registration-in-karnataka ; https://cleartax.in/s/professional-tax-karnataka
- Counsel cost data points: https://www.ipandlegalfilings.com/services/privacy-policy/ ; https://www.consently.in/blog/dpdp-act-compliance-cost-india-2026
