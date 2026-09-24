# Plan: Trust, India compliance and Indic output (response to the ReadPrism strategy report)

**Source**: `.context/attachments/DmzjSc/ReadPrism_ Product, Trust, India and Indic-Language Strategy.pdf` (24 pp., audited the live site ~Sept 2026)
**Verified against**: dev `5ef9e44` (= main, 0.0.94.0), live `www.readprism.news` + `api.readprism.news`, 2026-09-24
**Complexity**: Large. Seven phases; Phase 0 fits in one PR, Phases 2 and 4 are several each.

## Summary
The report's main point holds: Prism promises more than its trust tooling can show yet. Every finding below was
checked against code or the live API. Two findings are worse than the report says: all 76 source rows in the
live sample have a stance label, and 79 of the top 100 stories come from a single source. Three findings need
correcting: the Plus price exists but only renders in the browser, part of the IT Rules is stayed by a court,
and CERT-In allows logs to be kept outside India. Order of work: first fix copy that says something untrue
(days), then India compliance, then evidence for each generated sentence, then corrections/registry/denominator,
then Indic output, then paid launch.

## Verification ledger

| # | Report claim | Verdict | Evidence |
|---|---|---|---|
| V1 | "Nothing unsourced", yet briefs make inferences | **CONFIRMED** | Absolute copy at `StoryView.tsx:428`, `HowItWorks.tsx:46,195`. The extraction prompt asks for inference by design: "the last [sentence] why it matters" (`enrichment/schemas.py:120-127`). Brief points are plain strings with no link to a source (`correlation/schemas.py:32` `points: list[str]`). |
| V2 | Stance words ("neutral", "supportive") on source rows | **CONFIRMED, worse** | 76 of 76 source rows across 30 live stories carry one (neutral 39, critical 32, defensive 3, supportive 2). Rendered raw at `SourceList.tsx:59`. LLM-extracted (`enrichment/schemas.py:84-86`) with no definition, method or appeal. |
| V3 | No "2 of N monitored outlets" denominator; thin coverage | **CONFIRMED, worse** | No "of N" anywhere in web. Live: 79/100 feed stories single-source, 23 distinct outlets in top 100. `ingestion/seed.py` lists 33 sources: 21 English, 12 Indic across 10 languages, **zero Malayalam**, which is one of the report's five launch languages. (Memory says 42 in the prod DB, so confirm against the `outlets` table.) |
| V4 | Plus price blank | **PARTLY WRONG** | API serves ₹149 / ₹1,199 / ₹999 (`/api/v1/billing/plans`). `PlusPage.tsx` fetches prices in `useEffect`, so server HTML (crawlers, the auditor) has none. Checkout runs on an `rzp_test_` key in prod, so plans are not really on sale, which matches the refund page. |
| V5 | "Nothing renews" (Plus) vs "renews until cancelled" (Terms) | **CONFIRMED, three-way** | FAQ `PlusPage.tsx:31` says the offer completes after twelve months. True only for the monthly offer (`razorpay.TOTAL_COUNT` 12). Yearly offer = 10 charges (renews). Founding = 3 yearly charges, labelled "price locked 3 years" (`billing.py:40`). Terms `legal.ts:149,193` say every plan renews. |
| V6 | Matryx collects on behalf of the LLP | CONFIRMED, disclosed consistently | `legal.ts:194`, Plus FAQ. Keep it; also state it at checkout. |
| V7 | "we know nothing about you" vs server logs | **CONFIRMED** | `legal.ts:39` vs `legal.ts:55`. |
| V8 | Model-provider disclosure thin | **CONFIRMED, plus a real gap** | One line (`legal.ts:87`). No OpenRouter `provider.data_collection` setting anywhere in `common/llm.py`, so routed providers **may retain or train on Ask text**. We cannot promise "no training" until that flag is set. |
| V9 | DPDP main obligations start ~May 2027 | Plausible; wording fix | Privacy says it is "written to" the Act. Change to "written ahead of its phased commencement". |
| V10 | No named Grievance Officer / compliance hub | **CONFIRMED**, and more in force than first thought | `legal.ts:136` says only "the same address reaches our grievance officer". No name, SLA, form or monthly report. Bombay HC (Aug 2021, now pending in Delhi HC) stayed **only Rules 9(1) and 9(3)**, the ethics code and the three-tier structure. **Rules 10–19 are not stayed** (grievance officer, 24h/15d, MIB filing within 30 days of starting (possibly overdue), monthly report, 60-day records). Full analysis: `docs/COMPLIANCE-INDIA.md`. |
| V11 | CERT-In: 6h incident reporting, 180-day logs in India | Partly right | CERT-In's FAQ allows logs outside India if they can be produced promptly on demand. **Financial-transaction records must stay in India.** An LLP is a body corporate. Railway log retention is well short of 180 days, so we need a log drain. |
| V12 | No corrections/version log | **CONFIRMED** | Listed as "Next" in `StatusGrid.tsx:17`. No revisions table. |
| V13 | No claim types (reported/attributed/inference/context/unknown) | **CONFIRMED** | None exist. |
| V14 | No public source registry | **CONFIRMED** | No `/sources` route. |
| V15 | No Indic output layer | **CONFIRMED** | All Prism-written text is generated "In English" (`schemas.py:113,121`). `headline_lang` is null on 100/100 feed items. No i18n library. What exists: quote-language labels and outlet-translation detection; renderings are judged in shadow mode. |
| V16 | Account privacy controls | PARTIAL | Logout exists (`DELETE /auth/session`). Deletion and export are by email only (`legal.ts:115`). |
| V17 | Security baseline | PARTIAL | Web: HSTS, XFO, nosniff, Referrer-Policy, Permissions-Policy present; **no CSP**. API responses carry none. `/api/docs` open in prod. **C5 is now unblocked:** `api.readprism.news` is live, so the bearer token can move from `localStorage` to an HttpOnly cookie. |
| V18 | Plus sells "the stronger model" | CONFIRMED | `PlusPage.tsx:128,164`. The report advises selling workflow (follow, alerts, whole-story Ask) instead. |
| — | Internal drift found on the way | — | `PRODUCT.md` says Ask is 30/day signed in; code says 10 (`common/quota.py:162`). |

## Report recommendations I would not do now
- **Self-hosted IndicTrans2**: GPU operations for about 60 stories/day is premature. Start with a route we can call today, cache everything, and self-host only when measured volume justifies it.
- **All 22 languages on demand**: after five languages work end to end.
- **Native app, WhatsApp distribution, ISO 27001/SOC 2**: later. VAPT before the first B2B deal.
- **A/B programme**: traffic is too thin for significance. Make the calls as design decisions and re-test at scale.
- **Publisher partnerships, universities, fact-checker ties**: founder/GTM track, no engineering blocked on them.

## Patterns to mirror
| Category | Source | Pattern |
|---|---|---|
| Legal copy | `web/src/lib/legal.ts` | One source for Privacy, Terms and Refunds. Constants for entity, partner, email. Bump `LEGAL_UPDATED`. |
| Routes | `api/routes/billing.py:101` | `@router.<verb>("/api/v1/...")`, `HTTPException(status_code, detail="plain words")` |
| Data access | `common/billing.py:88-99` | Raw `sqlalchemy.text` on `AsyncSession`; alembic in `db/versions/` |
| Logging | `common/logging.get_logger(__name__)` | structlog. **Never pass an `event=` kwarg** (TypeError, see memory). |
| Verification of model output | `enrichment/claims.py` (`verify_claims`) | The model's offsets are repaired from text, never trusted. Reuse this for citation spans. |
| Citations in UI | `web/src/lib/sources.ts:11` `indexSources` | One `[n]` index shared by quotes and report cards. Brief cites must use the same index. |
| Risky features | quote verdicts, xposts, podcasts | `PRISM_*` flag default off → shadow mode → gold gate → serve |
| Human QA | `/label` labeller workspace | Language-gated reviewers, hidden checks. Reuse for translation QA instead of building a queue. |
| Figures | `/admin` ledger | Every figure sourced, n<30 shown as counts. The Reliability Report reads from here. |
| Tests | `tests/test_*.py`, `web/src/**/*.test.tsx` | pytest + vitest; mutation-verify every regression test. |

## Phase 0: Stop the contradictions (one PR, ~1–2 days, no founder input except D-a/D-b)
| Task | File | Change | Validate |
|---|---|---|---|
| 0.1 | `StoryView.tsx:428`, `HowItWorks.tsx:46,195` | Drop "Nothing here is unsourced" and "No unsourced lines". Say: "Written by software from the N reports below." Until Phase 2, label the last point "Prism's reading" when the brief has ≥3 points. | vitest: copy absent; label on last point |
| 0.2 | `SourceList.tsx:59` | Stop rendering `s.stance` (keep the data). **D-a** | vitest; live 0/76 |
| 0.3 | `common/razorpay.py`, `billing.py`, `PlusPage.tsx`, `legal.ts` | Derive one per-plan term (`charges`, `renews`) from `TOTAL_COUNT`, serve it in `/billing/plans`, and render the same sentence in the Plus FAQ and Terms. **D-b** | pytest on plans payload; vitest FAQ = Terms |
| 0.4 | `app/plus/page.tsx` | Fetch plans on the server so prices are in the HTML | `curl /plus \| grep ₹149` |
| 0.5 | `legal.ts:39`, DPDP line | "We do not build an account-linked history of what anonymous readers read." / "written ahead of the Act's phased commencement" | vitest on legal copy |
| 0.6 | `common/llm.py` | Send `provider: {data_collection: "deny"}` on OpenRouter calls, then disclose it. **Measure first:** it can remove cheap providers from routing (check the Ask cost/latency ledger before and after). | pytest on request body; 50-question Ask sample |
| 0.7 | `PlusPage.tsx:128,164` | Replace "stronger model" with whole-story Ask + allowance (follow/alerts come later) | vitest |
| 0.8 | `PRODUCT.md` | 30/day → 10/day | — |

## Phase 1: India compliance hub (counsel-gated; build ~3–4 days)
1. **Founder + Indian media counsel (blocking):** does "news aggregator" apply to us, and what is operative given the 9(1)/9(3) stay? Is membership of a self-regulating body required? CERT-In applicability to the LLP? Where does our Postgres live (Railway region), since subscription/payment records must be in India? **D-c**: named India-based Grievance Officer.
2. `/grievance`: name, contact, minimal structured form (kind, story URL, text, email). Add a `grievances` table with received/acknowledged/decided timestamps, enforce the 24h ack / 15d decision clocks, and give it an admin view (reuse `admin_audit` and `/admin` shell). Minimise fields and set a retention period.
3. `/compliance/<yyyy-mm>`: monthly report generated from the table (received, resolved, median time, outcomes).
4. A log drain to storage with 180-day retention, plus a one-page incident runbook with the 6h CERT-In clock.
5. The factual-error / mistranslation / missing-source / "source says something different" reports feed the same table through a `kind` column (Phase 3 corrections reads it).

## Phase 2: Evidence for every sentence (the moat; ~2–3 weeks)
Prerequisite: audit rows **H11** (projection single writer) and **H12** (`EventProjection` model). Both are open, and Phase 3's revision log needs one writer.
1. **Schema:** a brief point becomes `{text, kind: reported|attributed|inference|context, article_ids[], span?}` in `SharedExtraction.reader_brief` and `LensRead.points`, with the prompt updated to match. Single-article extractions cite that article implicitly.
2. **Deterministic check (no LLM):** cited ids must be event members. A `reported` point must have its digits, dates and currency present in a cited article, located with the `verify_claims` repair approach. If the check fails, downgrade the point to `inference` or drop it. Log the support rate.
3. **Gold set:** 200 points labelled in `/label`, giving the unsupported-claim rate per language. Gate: evidence attached for ≥99.5% of `reported` points before the UI ships (the report's target).
4. **UI:** `[n]` markers from `indexSources`, and a line-form "Prism's reading" marker for inference (DESIGN: line form, never hue). A popover shows outlet, paragraph and last checked.
5. Flag `PRISM_CLAIM_CITES`: shadow first. Old events carry string briefs and regenerate when membership changes.
6. Deferred until 2.1 ships: conflicting-number detection ("12 vs 14 injured → unresolved").

## Phase 3: Corrections, source registry, denominator, coverage (~1–2 weeks, parallel with Phase 4)
1. `event_revisions`, append-only: field, old, new, reason (`new_reporting|source_correction|prism_error|translation_error`), at. Written only by the single projection writer. Stories show "Updated" / "Corrected", and a public `/corrections` feed lists them.
2. `/sources` registry: name, language, type, origin, included since, last successful ingest. No endpoints or credentials.
3. Story denominator: "2 of N monitored outlets · checked 4 min ago", where N = active outlets and the time is the last ingest run.
4. **Coverage is the real product problem** (79% single-source). Add sources in the launch languages, starting with **Malayalam, which has none**, then Tamil, Telugu, Kannada, Hindi, business. **D-e.** Also close the cross-language merge hole (5.6% unmerged twins, see `crosslingual-merge.plan.md`), because it inflates the single-source share. KPI: single-source share, reported weekly.

## Phase 4: Indic output (~3 weeks; after Phase 2 so translated blocks carry citations)
1. **Engine (D-d):** benchmark the OpenRouter models we already pay for against Google NMT on 100 blocks × 5 languages. Reviewers come from `/label` with the language gate. Pick on critical-error rate, then cost. IndicTrans2 comes later, when volume justifies it.
2. `translations` table keyed `(block_hash, target_lang, engine_version, glossary_version)`. Translate on first request per (event, lang) and cache indefinitely. Only a changed block is retranslated.
3. Only Prism-written blocks get translated: headline, brief points, watch points, lens reads. Quotes stay original, with a labelled machine translation beside them (the existing quote-language layer).
4. Guard: digits, dates, currency and entity count must survive translation. If they don't, try the fallback engine, then English with a notice. High-risk classes (elections, communal, crime accusations, health) are not translated without review.
5. UI: a language switch driven by the profile's reading languages (already stored), and "Machine translated · show original". Chrome stays English in v1. **D-f.**
6. Launch hi/ta/te/kn. Add ml once it has sources. Report QA metrics per language on `/admin`, never one blended accuracy figure.

## Phase 5: Paid launch (after Phase 0.3 and Phase 1)
Razorpay live keys on the LLP's own merchant account, the contracting entity named at checkout, and Terms/FAQ reading from the one plan-term source. Price from measured COGS per paid user (Ask spend ledger) using `price ≥ COGS / (1 − target margin)`.

## Phase 6: Trust Centre + monthly Reliability Report
`/trust`: model classes, grounding and refusal rules, provider retention/training (true only after 0.6), and eval results per language. `/reliability/<yyyy-mm>` reads from the admin ledger: stories, % with 2+ sources, % single-source, quote-check failures, corrections and median time, Ask refusals, incidents. Publish the bad numbers too.

## Phase 7: Security (runs alongside)
C5: HttpOnly `Secure` `SameSite=Lax` cookie on `.readprism.news`, now possible. CSP report-only, then enforce. Close `/api/docs` in prod. Security headers on the API. A second factor for `/admin`. External VAPT before B2B.

## Founder rulings (2026-09-24) and status
| # | Ruling | Status |
|---|---|---|
| D-a | Remove stance labels | **DONE** 0821781 — gone from the payload and the cards |
| D-b | Plan renewal terms undecided; settle at launch | On the launch checklist (memory `prism-launch-checklist`); the undecided renewal FAQ removed from /plus |
| D-c | Team has no view on compliance | Decision doc `docs/COMPLIANCE-INDIA.md` for the team; Phase 1 build waits on it |
| D-d | Hold translation until the product is complete and data quality is good | Phase 4 **HELD**; no copy promises translation |
| D-e | As much Indian news as possible, top languages first | **DONE** 4cc56db — 19 outlets, Malayalam/Odia/Assamese new; bn/gu/pa blocked from a datacenter IP, retry from Railway egress |
| D-f | UI-chrome translation deferred | Deferred; recommendation on record: record content before chrome, on an adoption signal |

**Shipped on `feat/trust-alignment` (0821781):** Phase 0 (0.1, 0.2, 0.5, 0.7, 0.8; 0.3 and 0.4 deferred to launch per D-b),
Phase 3.2 + 3.3 (public `/sources` registry, "k of N monitored outlets · checked" on the record and landing),
structured report-a-problem links (mailto; becomes a form once D-c decides the queue), the /about glossary, evidence-first landing.
**Still open, in order:** 0.6 OpenRouter `data_collection: deny` (measure Ask cost first) → H11/H12 → Phase 2 (claim-level
citations) → Phase 3.1 corrections log → Phase 1 build once D-c lands → Phase 5 launch (checklist) → Phase 6 → Phase 7 (C5 is unblocked).
Data-quality gate for lifting D-d: single-source share falling week on week after the expansion, cross-language merge hole
closed (`crosslingual-merge.plan.md`), Phase 2 support rate ≥ 99.5% on the gold set.

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| `data_collection: deny` removes cheap providers, so Ask cost/latency rises | Medium | Measure a 50-question sample before/after; adjust model list |
| Citation check drops too many points, so briefs get thin | Medium | Downgrade to `inference` rather than drop; gold set tunes it |
| IT Rules scope misread either way | Medium | Counsel before Phase 1 ships; cheap parts don't depend on the ruling |
| Translation critical errors on low-resource languages | High | Guard + per-language gate from `/label`; English fallback with notice |
| Phase 2 blocked behind H11/H12 refactor | Medium | Do H11/H12 first as their own PRs (already scoped in AUDIT-2026-09) |
| Shared local Postgres/Redis across worktrees skews tests | Known | Per-worktree `DATABASE_URL` (memory: prism-worktree-make-check) |

## Acceptance (programme level)
- [ ] 0/N live source rows show a stance label; no absolute "unsourced" claims remain
- [ ] Plus FAQ and Terms render the same per-plan term from one source; prices in server HTML
- [ ] Named Grievance Officer live; monthly compliance report generated
- [ ] ≥99.5% of `reported` brief points carry a valid citation (gold-measured)
- [ ] Every story shows "k of N monitored outlets"; `/sources` and `/corrections` public
- [ ] Single-source share tracked weekly and falling; Malayalam has sources
- [ ] hi/ta/te/kn records served from cache with per-language QA on `/admin`
