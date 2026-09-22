# Plan: Jev live + whole-product audit and hardening + SEO/GEO ranking programme

**Source**: conversational (`/ecc:plan`, 2026-09-22)
**Complexity**: Large — a multi-session programme, one PR per tier into `dev`
**Builds on**: `.claude/plans/jev-decisions.plan.md` (landed on `feat/jev-decisions`, uncommitted)

## What "from scratch" covers (census 2026-09-22)

| Surface | Size | Notes |
|---|---|---|
| Backend | 21.6k lines / 150 files (+11.7k in `tools/`) | `correlation/partition.py` 1,243 and `correlation/consumer.py` 835 over the 800 ceiling |
| API | 41 endpoints in 11 route files | `api/schemas.py`, `serialization.py` shared |
| Web (Next.js) | 15.1k lines, 22 pages, 61 test files | `lib/api.ts` 840, `label/[key]/page.tsx` 1,018, `StoryView.tsx` 775 |
| Tests | 105 backend files (724 pass, 1 pre-existing fail), web suite green | |
| Model calls | 14 trace names | gate, classifier, gate-classify (Jev), extract-shared, event-analysis, lens-brief, market-digest, thread-link, story-veto, clip-judge, clip-tiebreak, xpost-judge, ask-guard, Ask (plain_chat) |
| SEO | `docs/SEO.md` — code side done 2026-09-21 | SSR lists, JSON-LD, sitemaps, news sitemap, llms.txt, IndexNow; owner checklist (Search Console, Publisher Center, Bing) status unknown |
| Coupling | god nodes: `session_scope` 274, `get_settings` 206, `structured_chat` 62, `fetch_prompt` 39, `decide` 28 | |

## Tier 0 — ship what exists and go live (½ session)

1. Commit `feat/jev-decisions`, PR → `dev`, CI green, `make promote`.
2. Railway worker: `PRISM_DECISIONS_MODE=live`, `PRISM_DECISIONS_MIN_CONFIDENCE=<decision Q1>`,
   `PRISM_JUDGE_BACKEND=<decision Q2>`. Verify via Railway logs (`decision` lines, cost) and
   the daily rejected ratio + sector mix against the prior week (SQL over the proxy, read-only).
3. Start `docs/OPTIMIZATION-LEDGER.md`: one row per change — what, before (measured), after
   (measured), how measured, date. Seeded with the Jev + Phase 0 numbers already in hand.

## Tier 1 — the audit, from scratch (1 session, read-only, parallel ecc agents)

Output: `docs/AUDIT-2026-09.md`, one ranked ledger (CRITICAL/HIGH/MEDIUM/LOW × effort S/M/L),
every finding with `file:line`, verified by me before it is listed. You approve which tiers to fix.

| Lens | Agent(s) | Scope |
|---|---|---|
| Architecture | `ecc:architect`, `ecc:code-explorer` | pipeline stages, stream contracts, module boundaries, the two >800-line files, god-node coupling, import cycles |
| API design | `ecc:fastapi-reviewer` + `ecc:api-design` skill | 41 endpoints: envelope consistency, pagination/limits, error shapes, versioning, auth per route, OpenAPI quality |
| Security | `ecc:security-reviewer` (backend), `ecc:typescript-reviewer` (web) | the four known items (RAG system-role injection `agent/rag.py:141`, `X-Forwarded-For` first hop `api/routes/events.py:663`, admin token `!=` + `"change-me"` default, guard fail-open without a metric) plus a full OWASP pass: auth flows, billing webhook, session cookies, CORS, headers, secrets |
| Performance | `ecc:performance-optimizer`, `ecc:database-reviewer` | the known items (retries ×9, global cooldown pausing Ask, 15 sequential INSERTs in `threads.py`, Source per item, DF-CTE recompute in `_story_component`, duplicate-URL re-embed) plus query plans on the hot reads (feed, trending, story), indexes, N+1 in serializers, web bundle + Core Web Vitals (Lighthouse on prod) |
| Code quality | `ecc:python-reviewer`, `ecc:react-reviewer` | DRY (the 9 `structured_chat` boilerplate sites), >50-line functions, mutation, dead code (`prism_gate_mode=enforce`), silent failures |
| Design | `ecc:a11y-architect` + `/design-review` (gstack, live browser) | conformance to DESIGN.md (monochrome chrome, three voices, hairlines, lens flip motion), WCAG 2.2, the two open contrast fails + header gradient + mono eyebrows from the Lovable landing |
| SEO / GEO | `ecc:seo-specialist` + curl checks against prod | what `docs/SEO.md` claims vs what a crawler gets today; structured-data validation; the ranking programme below |

## Tier 2 — fix CRITICAL + HIGH (1–2 sessions)

Security first, then performance, then architecture — each its own PR:
- **Security**: RAG sources out of the system role (numbered, delimited user-role block + citation-set check on output); trust only the proxy's forwarded hop; `hmac.compare_digest` + startup assertion on `prism_admin_token`; a counter/alert on `ask_guard_failed`; whatever Tier 1 adds.
- **Performance**: SDK `max_retries=0` so `structured_chat` owns retries (worst case 3 attempts, not 9); cooldown scoped per model for 429 and global only for 402; `executemany` in `threads.py`; a Source cache; DF-CTE precompute or recursive CTE; skip re-embed on duplicate URL.
- **Architecture**: split `partition.py` (veto → `correlation/story_veto.py`, persistence → `partition_persist.py`) and `correlation/consumer.py`; one `run_prompt()` helper for the 9 boilerplate sites; `prism_gate_mode` validated at load.

## Tier 3 — the rest of the LLM decisions on Jev (½–1 session)

| Stage | Shape | Decision needed |
|---|---|---|
| thread-link | Jev nouls/choices for `related` + `direction` per candidate; **rationale is user-facing** (`StoryTimeline.tsx`) | Q3: hybrid (LLM writes rationale only for accepted links, ~600/day) or drop the "why" note |
| ask-guard | Jev `allowed`/category first; LLM guard only when Jev < 0.9 or says refuse | Q4: hybrid as the security verdict requires, or leave on the LLM |
| clip-tiebreak | one noul per story on the short menu | measure against the podcast gold; flip with the judge backend |
| event-analysis impacts `direction`/`horizon`, extraction `stance` | enums inside prose calls — **not separable** without a second call | leave |

Each measured before flip, numbers into the ledger.

## Tier 4 — web and design (1 session)

DESIGN.md conformance fixes from Tier 1, a11y fixes, `lib/api.ts` split by domain, `label/[key]/page.tsx`
and `StoryView.tsx` decomposition, Lighthouse ≥ 90 on performance/SEO/a11y for `/feed`, `/story/<id>`,
`/trending/<slug>`, `/`. `/qa` pass on the critical flows (landing → feed → story → Ask → sign-in → Plus).

## Tier 5 — SEO + GEO ranking programme (½ session code + owner actions)

The code side is largely in place; ranking sooner is now authority, coverage and freshness:
- **Verify live**: the three curl checks in `docs/SEO.md`, Rich Results on a record, news sitemap
  count, IndexNow acceptance in Bing.
- **Owner actions (only you can)**: Search Console (domain property), Google Publisher Center
  (news inclusion — the single biggest lever for a news product), Bing Webmaster import,
  `hello@` inbound mail. Decision Q5: robots policy for training crawlers.
- **Code levers to add**: entity hub pages (`/entity/<slug>` — the cast is already extracted;
  hubs are how news sites earn long-tail queries), state pages (`/state/IN-KA`) since 31% of the
  corpus is Kannada/Karnataka, `BreadcrumbList` + `hasPart` on sector pages, `dateModified` on
  records that re-project, an author/methodology page for E-E-A-T ("Headline by Prism" needs a
  page that says who Prism is and how a record is written), hreflang for the Indic surfaces,
  `speakable` on the reader brief (GEO), a `/api/records.json` feed for answer engines, and the
  sitemap paging past 100 records.
- **Measure**: Search Console impressions/clicks weekly; the ledger records the baseline.

## Tier 6 — close out

Ledger complete; `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/SEO.md` updated; CHANGELOG + VERSION
per tier; `make check` green; memory updated.

## Patterns to mirror
| Category | Source | Pattern |
|---|---|---|
| Measured change | `common/config.py:26-82` | the decision and its numbers in the comment beside the setting |
| Fail-open + log | `common/moderation.py:64`, `common/pair_judge.py:121` | broad except, structured warning with `error_type` |
| Batched writes | `correlation/partition.py:1001` | `executemany` |
| Tests | `tests/test_classification_consumer.py` | stub the model call, assert the DB row, mutation-verify |
| Docs | `docs/SEO.md` | "in the code" table + "owner's checklist" + "how to check" |

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| Scope creep — "everything" never lands | High | Tiers are separate PRs; you approve each from the audit ledger |
| Cost — this session is already ~$60; the programme is several hundred | Certain | Audit agents run once, findings verified by me; fixes are targeted |
| Going live without the shadow days | Medium | Bake-off + gold already measured; `off` is a one-env rollback; watch the rejected ratio daily |
| Refactors of `partition.py`/`consumer.py` regress clustering | Medium | Behaviour-preserving splits only; `tools/score_stories` before/after |
| SEO gains depend on owner accounts | Certain | Checklist with exact steps; code levers land regardless |

## Acceptance
- [ ] Tier 0 live on prod, ledger seeded
- [ ] `docs/AUDIT-2026-09.md` delivered and triaged with you
- [ ] Every CRITICAL/HIGH fixed or explicitly deferred, with a ledger row each
- [ ] Remaining Jev stages measured, flipped or declined with numbers
- [ ] Lighthouse ≥ 90 ×4 on the four surfaces; DESIGN.md conformance clean
- [ ] SEO/GEO code levers shipped; owner checklist handed over with status
