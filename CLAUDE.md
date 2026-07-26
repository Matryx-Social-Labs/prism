# Parse — agent instructions

## Design System
Always read DESIGN.md before making any visual or UI decisions.
All font choices, colors, spacing, and aesthetic direction are defined there.
Do not deviate without explicit user approval.
In QA mode, flag any code that doesn't match DESIGN.md.

Core rules worth restating:
- Tagline is "One story. Every perspective." Never enumerate lens names in generic/marketing copy — the lens set grows (pickers render whatever /api/v1/lenses returns).
- Chrome is monochrome; color only ever means a lens is speaking (lens hues: general amber, cyber cyan, markets violet — discrete, never gradients).
- Three type voices: Fraunces (display), General Sans (UI), IBM Plex Mono (provenance only: timestamps, sources, citations, funding labels, chain dates).
- The signature motion is the re-typeset lens flip (scan line + re-ink, 500ms, reduced-motion collapses to instant swap). Never a crossfade.

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
