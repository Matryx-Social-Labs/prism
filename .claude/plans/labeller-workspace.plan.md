# Plan: a labeller workspace — sign up, learn, qualify, then label

**Source**: founder request 2026-09-23 — "a dashboard where labellers can sign up,
view all the available tasks, submit, see examples and an explanation per task,
and pass a practice test before they start"
**Complexity**: Large (5 phases, each shippable on its own)
**Status**: RATIFIED 2026-09-23 — building in order 1 → 5

## Founder decisions (2026-09-23)

1. **Open application + admin approval.** Anyone can apply; nobody labels a work
   batch until an admin approves them AND they pass that kind's test.
2. **No payment in v1.** Razorpay is live for subscriptions; paying labellers is
   a payout, not a charge (RazorpayX), and is deferred. `ms_spent` is already
   recorded per response, so hours can be computed when it lands.
3. **Language gating on.** A labeller sees only tasks in languages they read.
4. **Pass mark 90%** on every qualification test.
5. **Order 1 → 2 → 3 → 4 → 5**, each phase shipped on its own.

## Why now

Every quality gate on the roadmap is waiting on labels, not code:

| gate | what it unlocks | labels needed |
|---|---|---|
| `tools/gold_renderings --score` ≥ 0.95 | "translation" labels + one-statement grouping on quote cards | 240-row sheet (today a CSV) |
| gold_crosslingual batch `tKECdZfjiL0n` | the cross-language headline tier — ~5.6% of events have an unmerged twin | 150 tasks |
| gold_xposts ≥ 0.9 | the X signal tier | not yet built |
| gold_clips | podcast clip precision (live at ~0.8) | re-labels |

And the last round showed why a practice gate matters. From the comment on
`EventPrimer` in `web/src/app/label/[key]/page.tsx`:

> 123 tasks came back with the two labellers disagreeing — not randomly, but with
> opposite systematic biases. One ticked on any shared word; the other missed the
> same cricket ban reported in English and in Kannada. **Neither had read the
> guidance, because nothing made them.**

## What already exists (reuse, do not rebuild)

| piece | where | state |
|---|---|---|
| batches, tasks, responses, invites | migrations `d9e4c1a70f38`, `e2b6f014c9a7`, `c5f9a71e3b48`, `a1c4e8b90d23` | live; 4 kinds: `story_boundary`, `event_identity`, `topic_relation`, `claim_attribution` |
| serve one task at a time, record answers, admin export | `api/routes/label.py` (380 lines) | join / header / next / answer / export |
| anti-anchoring | same file | a labeller never sees another's answer — keep |
| `unsure` vs `skipped` ("I can't read this language") | same file | keep; skipped routes the task to someone else |
| per-kind primers with worked examples | `web/src/app/label/[key]/page.tsx` — `Guide`, `TopicGuide`, `ClaimGuide`, `EventPrimer` | shown once per batch, dismissable, **not tested** |
| invite, revoke, status, agreement (kappa), compile | `tools/gold_candidates.py` | CLI only |
| accounts: magic link + Google sign-in, Bearer sessions | `api/routes/auth.py`, `api/deps.get_current_user` | live for readers |

**The one decision this plan reverses.** `label.py`'s docstring says *"No account,
still … a signup wall would cost more labels than it protects."* That was right
for two founders labelling for a minute. It is wrong once there is a practice
test to pass and a per-person accuracy record to keep: both need an identity
that outlives one batch. Google sign-in makes the cost one tap.

## Architecture

```
Prism account (users)  ──1:1──  labellers            (profile: languages READ, status)
                                   │
                                   ├── labeller_qualifications  (per kind: passed_at, score, attempts)
                                   │
label_batches (+ purpose: work|practice|qualify, + listed)
   └── label_tasks (+ expected, + explanation)      ← practice/qualify items carry the answer
         └── label_responses ── label_invites (+ user_id)   ← UNCHANGED path; an invite is
                                                               minted for a signed-in labeller
```

The key move: **a signed-in labeller still answers through an invite.** When a
qualified labeller opens a batch from the dashboard, the API mints (or reuses)
an invite bound to their `user_id`. Every response, `--status`, `--agreement`
and `--compile` path in `tools/gold_candidates` keeps working untouched, and the
legacy `/label/<key>#token` links keep working for anyone already holding one.

Practice and qualification are **batches too** (`purpose`), so `next` / `answer`
serve them with no new task machinery — the only additions are the expected
answer and its explanation on each task, and feedback on answer.

## Phases

### Phase 1 — sign in, a profile, a dashboard

- `labellers` table: `user_id` PK → users, `languages_read text[]`,
  `status` (`applied | active | paused`), `created_at`, `approved_by`.
- `label_invites.user_id` (nullable), `label_batches.listed bool default false`.
- `GET /api/v1/labeller/me`, `POST /api/v1/labeller/apply` (languages read).
- `GET /api/v1/labeller/batches` — listed, open batches the labeller is
  qualified for AND can read, with *their* progress (answered / total) and a
  count of labellers on it — never anyone's answers.
- `POST /api/v1/label/{key}/start` — mint-or-reuse the invite for this user;
  the task page then runs exactly as today.
- Web `/label` — the dashboard: sign-in (existing Google / magic link),
  a two-question profile (languages you can READ well, name shown to admins),
  then three lists: **Ready to label**, **Learn and qualify**, **Done**.
- New file `api/routes/labeller.py` — `label.py` is the anonymous task
  protocol; the signed-in surface is a different job.

### Phase 2 — learn: one page per task kind

- `/label/learn/[kind]`: what the task is, why it matters to readers, DO / DO
  NOT, and worked examples — the four primers that already exist, **moved out of
  the 1,018-line task page** into `web/src/components/label/guides/` (the page is
  past the 800-line ceiling and the split is overdue).
- Examples stay invented or drawn from real disagreements, as today — never from
  the batch being labelled (that would hand out answers).

### Phase 3 — practice, then a qualification test

- `label_batches.purpose` (`work | practice | qualify`),
  `label_tasks.expected jsonb`, `label_tasks.explanation text`.
- **Practice** (per kind, ~8 items): answer → immediate feedback — right/wrong,
  the expected answer, and *why*. Unlimited retries. The point is to teach.
- **Qualification** (per kind, ~15 items drawn at random from a pool of ~40):
  no feedback until the end, then score + the explanations for the ones missed.
  Pass mark: see Q4. Fail → retake after a cooldown (24 h), new random draw.
- `labeller_qualifications(user_id, kind, passed_at, score, attempts, last_attempt_at)`.
- Items come from the **adjudicated** gold sets that already exist
  (`tools/gold_story_pairs`, `tools/gold_claims` — founder-ratified 2026-09-14),
  agreed items only; disputes are exactly the wrong thing to test on.
- **Explanations need authors.** I draft one per item from the adjudication
  provenance; a founder approves each before it goes live (`tools/label_qualify.py
  --draft / --publish`).
- Never send `expected` to the client before the answer (practice) or before the
  test ends (qualify). Scoring is server-side.

### Phase 4 — the quote-rendering task kind

- New kind `quote_rendering`: two question shapes the founders already know from
  the sheet — *same statement?* and *spoken in the language printed?*
- A primer + practice set written for it (the Telugu/Tamil case is the one to
  teach: an outlet translating a national figure vs quoting a local one).
- `tools/gold_renderings --push` replaces `--export` (the CSV and its formula
  risk go away); `--score` reads responses from the batch.
- The existing cross-language batch `tKECdZfjiL0n` gets `listed = true`.

### Phase 5 — quality in production (after the first real batch)

- ~1 in 10 tasks in a work batch is a hidden gold item; each labeller's live
  accuracy is kept per kind.
- Below the pass mark over the last 20 gold items → paused for that kind, re-test.
- Admin view `/label/admin` (behind `require_admin`): labellers, status, per-kind
  accuracy, agreement between pairs (the `--agreement` kappa, on a page), approve
  / pause. The CLI stays.

## Patterns to mirror

| category | source | pattern |
|---|---|---|
| credential | `api/routes/label.py` docstring | write credential never in a URL; token in body / fragment |
| anti-anchoring | `api/routes/label.py` | never return another labeller's answer |
| auth | `api/deps.get_current_user` | Bearer session → user id, one 401 message |
| admin | `api/deps.require_admin` | constant-time token compare |
| migrations | `db/versions/e2b6f014c9a7_label_invites.py` | additive columns, server defaults |
| primers | `EventPrimer` in the task page | DO / DO NOT, real disagreements as examples |
| tests | `tests/test_label.py`, `page.test.tsx` | route-level + jsdom; mutation-verified |

## Risks

| risk | likelihood | mitigation |
|---|---|---|
| a labeller memorises the qualification pool | medium | random draw from ~40, explanations for missed items only, cooldown between attempts |
| practice/qualify answers leak through the API | medium | `expected` never serialised before answer/test end; scored server-side; a test pins it |
| the signup wall costs labels | low | Google sign-in is one tap; the legacy invite links keep working |
| open signup lets anyone write into a gold set | high if open | admin approval (Q1) + qualification + hidden gold |
| PII: labellers are accounts with emails | certain | only admins see emails; responses keep `labeller` display names, as today |
| a lone labeller's bias becomes the gold | medium | gold still compiles from ≥ 2 agreeing labellers (`merge_votes`), disputes excluded |

## Validation

```bash
make check                       # backend + web + migration round-trip
uv run pytest -q tests/test_label.py tests/test_labeller.py
cd web && npx vitest run src/app/label
```

## Acceptance

- [ ] A new person can sign in, say what they read, learn a kind, pass its test, and label — with no CLI step but an admin approval
- [ ] A labeller who has not passed a kind cannot open a work batch of that kind
- [ ] No API response carries an expected answer before it should
- [ ] Existing `/label/<key>#token` links keep working; `tools/gold_candidates` unchanged
- [ ] The quote-rendering sheet is a batch, not a CSV
