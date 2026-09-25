# Prism — agent instructions

## Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.

Core rules worth restating (the system is Design System v2, 2026-09-24, from the Claude Design project
"Prism Design System"; PRODUCT.md holds the product truth and the founder decisions D1–D6):
- Product promise is "Follow the story, not the headlines." Never enumerate lens names in generic/marketing copy — the lens set grows (pickers render whatever /api/v1/lenses returns).
- Chrome is neutral warm paper and carbon ink with ONE interactive accent (cobalt). Other colour appears only where the prism splits light: the coverage bar (navy · blue-green · orange · hatched grey, fixed slot order, always with its count) and a lens (one discrete hue each; Reader has none). The mark's band is the only gradient.
- Three type voices: Newsreader + per-script Noto Serif (the record: headlines, titles, quotes, hero figures), Anek (everything read or tapped, eyebrows included), Geist Mono (provenance only: counts, times, codes, [n], tickers, CVE ids — never prose, a heading or a label). 11px floor for mono; 4.5:1 on both grounds.
- Records are cut square (2px), controls pressed (8px), sheets held (16px); sections sit under a 3px ink rule. State is line form — solid verified, dashed provisional/one source, faded stale, hatched not counted — never hue alone. Icons from `web/src/components/icons.tsx`, never text glyphs.
- Counted structure is printed as counts ("k of n" below 30); quotes are verbatim or absent; no invented numbers or examples anywhere — the design mocks' ILLUSTRATION banners and sample data never ship.
- The signature motion is the lens flip (scan line + re-ink, paced by block height, reduced-motion = instant swap). Never a crossfade. Rows print in; publisher photos fade in (320ms); the story's photo deck advances with a 5° tilt.
- Routing: `/` is the landing for a first visitor and redirects returning readers (cookie `prism.returning`) to `/feed`, which is always the chart; `/about` is the landing's permanent address.

## Web tests
The Next.js app has a test suite as of v0.0.70.0: `cd web && npm test` (vitest + jsdom +
Testing Library; `npm run test:watch` while iterating). Tests live beside the code as
`web/src/**/*.test.ts(x)`, config in `web/vitest.config.ts`, jsdom shims in
`web/vitest.setup.ts`. CI runs it in the `web` job, so a failing test blocks the PR.
Backend tests: `uv run pytest -q`. As of v0.0.72.0 the suite hard-exits (code 2, not a skip)
if `DATABASE_URL` points anywhere but `localhost`/`127.0.0.1`/`db`/`postgres` or a `*_test`
database — the DB tests insert events and supersede partition runs, and this repo reaches prod
over the Railway proxy for admin queries, so a leftover exported URL was a live path to
corrupting production. Guard is `tests/conftest.py`.

Two jsdom traps that make a test pass without testing anything — both cost real debugging
time here, so check for them when writing or reviewing web tests:
- `vi.spyOn(Storage.prototype, ...)` does **not** intercept `sessionStorage` in jsdom
  (it doesn't route through the prototype), so the spy never fires. Stub the global:
  `vi.stubGlobal("sessionStorage", { getItem, setItem, clear })`. `vi.restoreAllMocks()`
  does not undo a stub — `vi.unstubAllGlobals()` in `afterEach` does.
- `renderHook` swallows errors thrown inside effects, so `expect(...).not.toThrow()` on a
  hook is vacuous. Render a real component that uses the hook and assert the tree survived
  (`expect(screen.getByText(...)).toBeInTheDocument()`).

Every regression test should be mutation-verified: put the bug back, confirm the test fails.

## Branches: dev is where work lands, main is prod

`dev` is the default branch and the only one to commit to. `main` is production —
Railway and Vercel both deploy from it.

**Promote with `make promote`, never by merging a dev→main PR.** A PR merge writes
a merge commit onto `main` that `dev` does not have, so `main` ends up AHEAD of
`dev` by one commit per release while the two trees stay byte-identical. Sixteen of
those accumulated before anyone noticed. It is only bookkeeping, but it makes "is
prod behind?" unanswerable at a glance, which is the single question `main` exists
to answer.

`make promote` fast-forwards instead, so `main` is always a PREFIX of `dev`'s
history — behind or equal, never ahead. It refuses to run on uncommitted changes,
refuses if `main` is not an ancestor of `dev` (someone committed to `main`
directly), and refuses unless CI is green for that exact `dev` commit, so prod
ships what CI vouched for rather than what happens to be on disk.

**GitHub enforces the same thing (ruleset on `main`, 2026-09-20):** no deletion, no
force-push, linear history (a merge commit is refused), and the two CI checks
(`backend · …`, `web · …`) must be green **on the commit being pushed**. Because
those checks ran on `dev` for the same SHA, a fast-forward promote is accepted; an
untested commit, a squash, a rebase or a PR merge is refused with `GH013`. CI does
NOT re-run the tests on `main`: the `main` workflow only re-reads those checks
(`vouched`) and deploys the web. Railway deploys the API and worker from `main` on
its own, so this ruleset is what guarantees prod never receives an untested commit.
No PR ever targets `main`; feature branches PR into `dev`.

Delete every branch after merge except `main`, `dev` and `stage`. The repo has
`delete_branch_on_merge` enabled, so this is automatic for PR merges.

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
- Author a backlog-ready spec/issue → invoke /spec
