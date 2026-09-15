# Plan: Claims on the story page — "What was said"

## Summary
The perspectives layer exists on the write side only: 1,285 verbatim-verified claims sit in
`enrichments.shared_fields->'claims'`, 45% of live events carry at least one (median 2, max 23),
and nothing reads them. The step-5b gate passed at 0.983 attribution precision. This exposes
claims on `GET /api/v1/events/{id}` grouped by speaker and renders them on the story page as a
rules-and-type evidence section, per DESIGN.md.

## User Story
As a reader on a story page, I want to see who said what — the exact words, attributed, with the
outlet and date — so that "every perspective" is something I can check rather than a summary I
have to trust.

## Problem → Solution
Claims are extracted, verified verbatim, stored, and invisible → a "What was said" section on
every story that has any, grouped by speaker, each quote carrying a mono citation to the source
list.

## Metadata
- **Complexity**: Medium
- **Source PRD**: N/A (rebuild plan step 5b, first read surface)
- **Estimated Files**: 12 after review (3 backend, 2 test, 6 web + 3 fixture touches)

---

## UX Design

### Before
```
Story page
  ├─ headline · N sources · time
  ├─ [nav] Lens brief · Perspectives · What to expect · Sources
  ├─ LENS BLOCK (the flip)
  ├─ Perspectives          (≤4 LLM-labelled narrative cards)
  ├─ What to expect
  └─ Sources               [1] Outlet  title
```

### After
```
Story page
  ├─ headline · N sources · time
  ├─ [nav] Lens brief · Said 5 · Perspectives · What to expect · Sources
  ├─ LENS BLOCK (unchanged)
  ├─ What was said         ← NEW, rules and type, neutral ink
  │    Devdatt Kamat                                   3 quotes
  │    "There are large-scale reports that ultimately the money has
  │     not reached the Trust…"
  │    [4] The Hindu · 27 Jul                          ← mono provenance
  │    ────────────────────────────────────────────── hairline
  │    Delhi Government                                1 quote
  │    "No adverse legal action will be taken…"
  │    [2] Hindustan Times · 22 Jul
  ├─ Perspectives
  ├─ What to expect
  └─ Sources               [1] Outlet  title   ← [n] here matches [n] above
```

### Interaction Changes
| Touchpoint | Before | After | Notes |
|---|---|---|---|
| Section nav (mobile chips + desktop rail) | 4 items | 5 items: "Said" with count, after Lens brief | count = total quotes; hidden when 0? NO — chip shows `0` like Perspectives does, section shows quiet empty state |
| `[n]` citation | only in Sources list | also under each quote | same index as Sources — reader can cross-reference |
| Lens flip | — | unchanged | section sits below the lens block; layout never moves |
| Paywall | — | claims are READER-TIER (free) | evidence, not lens depth; sources are already free |

---

## Mandatory Reading

| Priority | File | Lines | Why |
|---|---|---|---|
| P0 | `DESIGN.md` | 42-60, 81-88, 102-109, 139 | colour rule, three voices, no cards on desktop, width rule |
| P0 | `api/routes/events.py` | 55-95, 175-215 | get_event's sources query (already joins enrichments) + serialisation |
| P0 | `api/schemas.py` | 76-133 | SourceRef / PerspectiveOut / EventDetail shapes |
| P0 | `web/src/components/StoryView.tsx` | 207-220, 774-800, 895-935 | navItems, the shared evidence layer, the Sources list (rules-and-type exemplar) |
| P1 | `enrichment/schemas.py` | 34-60 | Claim fields as stored |
| P1 | `web/src/lib/api.ts` | 44-53, 67-73, 116-140 | SourceRef / PerspectiveOut / EventDetail TS types |
| P1 | `tests/test_ask_attribution.py` | 103-170 | fake_db + dependency_overrides route-test pattern |
| P2 | `web/src/components/StoryView.lens.test.tsx` | 1-60 | EVENT fixture + api mock pattern |

## External Documentation
None needed — established internal patterns only.

---

## Patterns to Mirror

### RESPONSE_MODEL
// SOURCE: api/schemas.py:76-92
```python
class SourceRef(BaseModel):
    article_id: str
    source_name: str
    source_slug: str
    url: str | None
    title: str
    published_at: str | None
    stance: str | None
    funding: str | None = None  # "state" | "public" | None — outlet transparency chip
```

### QUERY_SHAPE (the sources query — claims ride on this exact join, zero extra round trips)
// SOURCE: api/routes/events.py:70-90
```python
    sources = (
        await db.execute(
            text(
                """
                SELECT a.id AS article_id, s.name AS source_name, s.slug AS source_slug,
                       s.reliability ->> 'funding' AS funding,
                       ri.url, ri.title, ri.published_at,
                       e.shared_fields -> 'stance' ->> 'label' AS stance
                FROM event_memberships em
                JOIN articles a ON a.id = em.article_id
                JOIN raw_items ri ON ri.id = a.raw_item_id
                JOIN sources s ON s.id = ri.source_id
                LEFT JOIN enrichments e ON e.article_id = a.id
                WHERE em.event_id = :eid
                ORDER BY ri.published_at DESC NULLS LAST
                """
            ),
            {"eid": str(event_id)},
        )
    ).mappings().all()
```

### SERIALISATION
// SOURCE: api/routes/events.py:184-196
```python
        sources=[
            SourceRef(
                article_id=str(s["article_id"]),
                source_name=s["source_name"],
                ...
                published_at=s["published_at"].isoformat() if s["published_at"] else None,
```

### ROUTE_TEST (fake_db + auth override; the wiring, not the parts)
// SOURCE: tests/test_ask_attribution.py:136-170
```python
    async def fake_db():
        class _R:
            def mappings(self): return self
            def first(self): return {...}
            def all(self): return [...]
        class _S:
            async def execute(self, *a, **kw): return _R()
        yield _S()
    app.dependency_overrides[events.get_db] = fake_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get(...)
    finally:
        app.dependency_overrides.pop(events.get_db, None)
```
GOTCHA: get_event runs 5 queries; the fake must DISPATCH on SQL text, not return one shape.

### WEB_SECTION (rules and type — the Sources list, NOT the Perspectives cards)
// SOURCE: web/src/components/StoryView.tsx:896-935
```tsx
      <section id="sources" className="mt-11 scroll-mt-24">
        <h2 className="mb-4 text-[23px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
          Sources{" "}
          <span className="text-[15px] font-normal" style={{ color: "var(--ink-faint)" }}>({event.sources.length})</span>
        </h2>
        <ul className="flex flex-col gap-[9px]">
          {event.sources.map((s, i) => (
            <li key={s.article_id} className="flex items-baseline gap-2.5 text-[13.5px]">
              <span className="shrink-0 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>[{i + 1}]</span>
```

### WEB_EMPTY_STATE
// SOURCE: web/src/components/StoryView.tsx:802-806
```tsx
          <p className="text-[13.5px]" style={{ color: "var(--ink-faint)" }}>
            Perspective analysis pending — it generates as coverage from more origins arrives.
          </p>
```

### WEB_TEST (mock api, render, assert on text)
// SOURCE: web/src/components/StoryView.lens.test.tsx:7-11, 36-60, 84-95
```tsx
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief: vi.fn(async () => null), fetchQuestions: vi.fn(async () => []) };
});
const EVENT = { id: "e1", ..., sources: [], perspectives: [], impacts: [] } as unknown as EventDetail;
    render(<StoryView event={EVENT} />);
    expect(await mobile().findByText(READER_BRIEF)).toBeInTheDocument();
```
GOTCHA: jsdom renders BOTH the mobile and desktop trees, so use `getAllByText` / scope with `within`.

---

## Files to Change

| File | Action | Justification |
|---|---|---|
| `api/schemas.py` | UPDATE | `ClaimOut`, `SpeakerClaims`; `EventDetail.claims: list[SpeakerClaims]` |
| `api/routes/events.py` | UPDATE | add `e.shared_fields -> 'claims' AS claims` to the sources query; `group_claims()` pure fn; serialise |
| `tests/test_event_claims.py` | CREATE | unit tests for `group_claims` + route wiring test with SQL-dispatching fake_db |
| `web/src/lib/api.ts` | UPDATE | `ClaimOut`, `SpeakerClaims` types; `claims` on `EventDetail` |
| `web/src/components/StoryView.tsx` | UPDATE | "What was said" section + nav item + `sourceIndex` map |
| `web/src/components/StoryView.claims.test.tsx` | CREATE | renders speakers/quotes/citations, empty state, nav count |
| `web/src/components/StoryView.{controls,lens,desktop}.test.tsx` | UPDATE | add `claims: []` to EVENT fixtures (they cast `as unknown as`, so a missing key is a runtime crash not a type error) |
| `web/src/lib/dateline.ts` + `dateline.test.ts` | UPDATE | `shortDate(iso)` pinned to IST (D6) |
| `web/src/components/StoryTimeline.tsx` | UPDATE | use `shortDate` instead of its inline formatter (D6) |
| `web/src/components/StoryDesktop.tsx` | UPDATE | `railFacts` carries the quote count (D13) |
| `tests/test_extract_prune.py` | UPDATE | docstring no longer claims nothing reads claims |

## NOT Building
- Claim dedup / clusters (5c — measured 1.7% cross-outlet recurrence)
- Per-entity STORY ledger across events (needs QIDs; step 5 at 22%)
- Position-change detection (5d — gated on evaluation)
- Speaker → entity page links (speakers are strings)
- Any change to the lens block, the flip, Perspectives, or the paywall
- A `claims` table (JSONB is the store; a table is a later normalisation)
- Showing `claim_text` (the neutral one-liner) — the verbatim quote IS the claim; a paraphrase beside it invites the reader to trust the paraphrase
- Showing `stance` or `said_at` — model opinions never verified (D1)
- An empty state — the section renders only when there is something to show (D12)
- The desktop-rail paid-lens leak found during review — separate concern, TODOS.md (D14)

---

## Step-by-Step Tasks

### Task 1: Response schema
- **ACTION**: add to `api/schemas.py` before `EventDetail`
- **IMPLEMENT**:
```python
class ClaimOut(BaseModel):
    # VERIFIED FIELDS ONLY. quote_text is verbatim-checked against the article at
    # write time; the offsets are repaired from it, not trusted from the model;
    # source/published_at come from raw_items. `stance` and `said_at` are model
    # opinions verify_claims never checks — showing them beside a verified quote
    # would lend a guess the quote's credibility, so they are not exposed.
    quote_text: str
    quote_start: int | None
    quote_end: int | None
    article_id: str
    source_name: str
    url: str | None
    published_at: str | None


class SpeakerClaims(BaseModel):
    speaker: str
    claims: list[ClaimOut]
```
  and `claims: list[SpeakerClaims]` on `EventDetail` after `perspectives`, with a comment: reader-tier — evidence, not lens depth; grouped by speaker STRING because within one article the name is consistent and QIDs (step 5) are not yet wired.
- **MIRROR**: RESPONSE_MODEL
- **VALIDATE**: `uv run python -c "from api.schemas import SpeakerClaims"`

### Task 2: Query + grouping + serialisation
- **ACTION**: in `api/routes/events.py`
- **IMPLEMENT**:
  1. Add `e.shared_fields -> 'claims' AS claims` to the sources SELECT (one line; same join).
  2. Module-level pure functions (D2 within-article order, D3 conservative key, D4 non-list guard):
```python
def _speaker_key(name: str) -> str:
    """Fold punctuation and case ONLY: "D.K. Shivakumar" == "D K Shivakumar" == "d k shivakumar".

    Measured on the live window: 3% of events carry one person under two strings,
    and every real duplicate was a punctuation/case variant. A surname key would
    also have merged Chinna Reddy with Komatireddy Rajagopal Reddy — different
    people — so tokens are kept. "Jaishankar" vs "S Jaishankar" stays two rows;
    that fold is the QID ledger's job, not this one's.
    """
    return " ".join(name.replace(".", " ").split()).casefold()


def group_claims(sources: list[dict]) -> list[SpeakerClaims]:
    """Speaker-grouped, most-quoted first; newest article first, article order within it.

    Grouped by a punctuation-insensitive speaker key and shown under the first
    surface form seen. Folding "Pradhan" and "the Education Minister" ACROSS a story
    is the ledger, and that waits on QIDs.
    """
    by: dict[str, list[tuple[tuple, ClaimOut]]] = {}
    label: dict[str, str] = {}
    first_seen: dict[str, int] = {}
    for s in sources:                                  # already newest-first
        claims = s["claims"]
        if not isinstance(claims, list):               # NULL for un-enriched; a dict/str on a
            continue                                   # drifted row must not 500 the story page
        pub = s["published_at"]
        for c in claims:
            if not isinstance(c, dict):
                continue
            sp = (c.get("speaker") or "").strip()
            q = (c.get("quote_text") or "").strip()
            if not sp or not q:
                continue                               # verified at write time; belt and braces
            k = _speaker_key(sp)
            if k not in by:
                by[k] = []; label[k] = sp; first_seen[k] = len(first_seen)
            # sort key: newest article first, then the order the article said them
            sk = (-(pub.timestamp() if pub else 0.0), c.get("quote_start") or 0)
            by[k].append((sk, ClaimOut(
                quote_text=q, quote_start=c.get("quote_start"), quote_end=c.get("quote_end"),
                article_id=str(s["article_id"]), source_name=s["source_name"], url=s["url"],
                published_at=pub.isoformat() if pub else None)))
    return [
        SpeakerClaims(speaker=label[k], claims=[cl for _, cl in sorted(by[k], key=lambda x: x[0])])
        for k in sorted(by, key=lambda k: (-len(by[k]), first_seen[k]))
    ]
```
  3. `claims=group_claims(sources)` in the `EventDetail(...)` call.
- **MIRROR**: QUERY_SHAPE, SERIALISATION
- **GOTCHA**: `shared_fields -> 'claims'` comes back as a Python list via asyncpg/SQLAlchemy JSONB — NOT a string. Do not `json.loads` it. `LEFT JOIN enrichments` means `claims` is `None` for un-enriched articles: handle `or []`.
- **GOTCHA**: `s["published_at"]` is a datetime or None — same handling as SourceRef.
- **VALIDATE**: `uv run pytest tests/test_event_claims.py -q`

### Task 3: Backend tests (write FIRST)
- **ACTION**: create `tests/test_event_claims.py`
- **IMPLEMENT**:
  - `test_group_claims_groups_by_speaker_and_orders_most_quoted_first` — 3 sources, speakers A,B,A,C → [A(2), B, C]
  - `test_group_claims_drops_empty_speaker_or_quote` — belt-and-braces guard
  - `test_group_claims_tolerates_unenriched_articles` — `claims: None`
  - `test_group_claims_orders_within_an_article_by_quote_start` (D2)
  - `test_group_claims_folds_punctuation_and_case_but_not_different_people` (D3): "D.K. Shivakumar"+"D K Shivakumar" → 1 row labelled by first-seen; "Chinna Reddy"+"Komatireddy Rajagopal Reddy" → 2 rows
  - `test_group_claims_ignores_a_non_list_claims_column` (D4): `claims: {"speaker": "x"}` and `claims: "oops"` → no crash, no claims
  - `test_THE_ROUTE_returns_claims_to_an_anonymous_reader` — the wiring AND the paywall decision. Also asserts `sources` is still populated in the same response (the sources query was MODIFIED — regression rule). fake_db dispatches on SQL text: `"FROM events WHERE id"` → event row with `projection: {}`; `"FROM event_memberships em"` → one source row with two claims; everything else → `[]`. Assert `r.json()["claims"][0]["speaker"]` and that NO Authorization header was needed.
- **MIRROR**: ROUTE_TEST
- **GOTCHA**: get_event also calls `unlocked_lenses` only when `user_id is not None` — anonymous path skips it, so the fake needn't handle `lens_unlocks`. `available_lenses(projection, sector)` is pure. `event["last_updated_at"].isoformat()` — fake must return a datetime, not a string.
- **VALIDATE**: mutation — (a) remove `claims=group_claims(sources)` from the route → wiring test fails; (b) replace `sorted(...)` with `order` → ordering test fails.

### Task 4: Web types
- **ACTION**: `web/src/lib/api.ts`
- **IMPLEMENT**: `export interface ClaimOut { quote_text; quote_start; quote_end; article_id; source_name; url; published_at }`, `export interface SpeakerClaims { speaker: string; claims: ClaimOut[] }`, `claims: SpeakerClaims[]` on `EventDetail` after `perspectives`.
- **VALIDATE**: `cd web && npx tsc --noEmit`

### Task 5: The section
- **ACTION**: `web/src/components/StoryView.tsx`
- **IMPLEMENT**:
  1. Next to `sourceById`: `const claims = event.claims ?? [];` (D9 — Vercel and Railway deploy from two pipelines and get_event is cached 60s; a new page can meet an old payload), `const sourceIndex = new Map(event.sources.map((s, i) => [s.article_id, i + 1]));` (D5 — the Sources list reads `sourceIndex.get(s.article_id)` too, one source of truth for `[n]`), `const quoteCount = claims.reduce((n, s) => n + s.claims.length, 0);`
  2. navItems: insert `{ id: "said", label: "Said", count: quoteCount }` after `lens-brief` **only when `quoteCount > 0`** (D12).
  3. New `<section id="said" className="mt-11 scroll-mt-24">` rendered **only when `claims.length > 0`** (D12 — no empty state; the section appearing is the signal), as the FIRST child inside `<div className="lg:ml-[136px] lg:max-w-[604px]">`, before Perspectives:
```tsx
        <SectionTitle
          title="What was said"
          hint="Attributed, verbatim. Every quote is checked against the article it came from — a quote that does not match is not shown."
        />
        {(
          <div className="flex flex-col">
            {claims.map((sp, i) => (
              <div key={sp.speaker} className={i === 0 ? "" : "mt-5 border-t pt-5"} style={i === 0 ? undefined : { borderColor: "var(--line)" }}>
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="text-[14.5px] font-semibold">{sp.speaker}</h3>
                  <span className="shrink-0 font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
                    {sp.claims.length} {sp.claims.length === 1 ? "quote" : "quotes"}
                  </span>
                </div>
                <ul className="mt-2 flex flex-col gap-3.5">
                  {sp.claims.map((c, j) => (
                    <li key={`${c.article_id}-${j}`}>
                      <blockquote className="text-[14.5px] leading-[1.6]" style={{ color: "var(--ink)" }}>
                        “{c.quote_text}”
                      </blockquote>
                      <div className="mt-1 flex items-baseline gap-2 font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
                        {/* D11: the citation is the link. One tap to check us, same target/rel as Sources. */}
                        {sourceIndex.has(c.article_id) && (c.url ? (
                          <a href={c.url} target="_blank" rel="noopener noreferrer" className="underline-offset-2 hover:underline">[{sourceIndex.get(c.article_id)}]</a>
                        ) : <span>[{sourceIndex.get(c.article_id)}]</span>)}
                        <span>{c.source_name}</span>
                        {c.published_at && <span>· {shortDate(c.published_at)}</span>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
```
     `shortDate(iso)` lives in `web/src/lib/dateline.ts` (D6): `new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: "Asia/Kolkata" })` — pinned to IST like `istDate`, and `StoryTimeline.tsx:18` switches to it so there is one formatter and one timezone.
  4. `StoryDesktop.railFacts` (D13): push `["", \`${quoteCount} quote${quoteCount === 1 ? "" : "s"}\`]` when `quoteCount > 0` — the Stone ledger carries evidence, and `navItems` never reach desktop.
  5. `tests/test_extract_prune.py` docstring: it still says "nothing reads claims" — now false twice over. Fix the comment.
- **MIRROR**: WEB_SECTION (rules and type — hairline `border-t`, NO `rounded` card, NO colour), WEB_EMPTY_STATE
- **GOTCHA**: DESIGN.md — mono is for provenance ONLY (the `[n] Source · date` line and the count), never the quote or the speaker. No lens hue anywhere. Do not touch `#lens-brief`.
- **GOTCHA**: `railFacts` is lens-conditional; add the quote count to the DEFAULT branch and also alongside cyber/markets facts, since a quote count is not lens-specific.
- **GOTCHA**: `ml-auto` on stance keeps it right-aligned like the Sources list does.
- **VALIDATE**: `npx vitest run src/components/StoryView` and `tsc --noEmit`

### Task 6: Web tests (write FIRST)
- **ACTION**: create `web/src/components/StoryView.claims.test.tsx`; add `claims: []` to the three existing EVENT fixtures.
- **IMPLEMENT**:
  - renders speaker, verbatim quote, `[n]` matching the source's index in the Sources list, source name
  - groups: one speaker with two quotes shows the name once and "2 quotes"
  - empty: "No attributed quotes" and nav chip shows `0`
  - the quote is NOT in mono and NOT lens-coloured (assert `blockquote` has no `font-mono` class) — the DESIGN.md discipline, asserted
  - `[n]` is an anchor to the article URL when present, plain text when not (D11)
  - zero claims → NO section and NO "Said" chip (D12); `event.claims` undefined → same, no crash (D9)
  - the `[n]` under a quote equals the `[n]` beside the same article in Sources (D5 — one map)
  - `shortDate` unit test in `dateline.test.ts`: a 23:30 UTC timestamp renders the NEXT day in IST (D6 timezone)
  - `StoryDesktop` rail shows "N quotes" when N > 0 and nothing when 0 (D13)
- **MIRROR**: WEB_TEST
- **GOTCHA**: both trees render in jsdom; `getAllByText(...)[0]` or scope.
- **VALIDATE**: mutation — delete the `<section id="said">` → 3 tests fail; put `font-mono` on the blockquote → the discipline test fails.

---

## Testing Strategy

| Test | Input | Expected | Edge |
|---|---|---|---|
| group by speaker | speakers A,B,A,C | [A×2, B, C] | ordering by count then first-seen |
| empty speaker/quote dropped | `{"speaker": "", ...}` | excluded | belt-and-braces |
| un-enriched article | `claims: None` | no crash, no claims | LEFT JOIN null |
| route wiring, anonymous | no auth header | 200 + claims present | paywall decision made explicit |
| web: renders + citation | 1 speaker, `[2]` source | text present | index matches Sources |
| web: empty | `claims: []` | quiet line, chip `0` | 55% of events |
| web: typography discipline | any | blockquote lacks `font-mono` | DESIGN.md |

### Edge Cases
- [x] no claims (55% of live events) — quiet empty state
- [x] 23 claims on one event — list scrolls, no truncation (verbatim-or-nothing applies to the quote, not the list)
- [x] article without enrichment — `None` claims
- [x] same speaker string, different casing — NOT folded (deliberate; folding is the ledger's job)
- [x] claim whose `article_id` is not in `event.sources` — no `[n]`, still shown

## Validation Commands
```bash
uv run ruff check api/ tests/                       # EXPECT: clean
uv run pytest tests/test_event_claims.py -q         # EXPECT: pass
cd web && npx tsc --noEmit && npx vitest run src/components/StoryView   # EXPECT: pass
make check                                          # EXPECT: check: PASS
```

## Acceptance Criteria
- [ ] GET /api/v1/events/{id} returns `claims: [{speaker, claims:[{quote_text, stance, said_at, article_id, source_name, published_at}]}]`, anonymous
- [ ] Story page shows "What was said" with speaker → verbatim quotes → `[n] Source · date` in mono
- [ ] nav item "Said N"
- [ ] no card, no colour, no mono on prose; lens block untouched
- [ ] all tests mutation-verified; `make check` green

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The sources query now returns JSONB per row — payload grows on 23-claim events | low | low | claims are short; cap not needed; measured max 23 |
| A speaker string like "he" or "the official" reads badly as a heading | medium | low | extractor names as the article names; "senior forest official" is honest; NOT building name resolution here |
| Existing StoryView tests crash on missing `claims` | certain | low | Task 6 adds `claims: []` to the three fixtures |
| get_event is cached 60s for anonymous — claims appear late | n/a | none | claims are not user-specific; cache is correct |

## Notes
- Claims are reader-tier by decision: they are evidence, and the paid tier is lens DEPTH. Making the
  verbatim record free is the trust argument; making the reading of it paid is the business.
- Perspectives (LLM narrative cards) stays. The plan calls it the thing claims REPLACE, but removal is
  a separate decision once the founder has seen both side by side.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 1 | issues_found | 12 raised: 3 verified true, 1 dismissed by data (max quote 567 chars), 3 already covered, 5 became D9–D13 |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 14 issues, 0 critical gaps open; all 14 accepted as recommended |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **CODEX:** outside voice ran on the plan (2026-09-15). Its strongest catch was the deploy-window crash (`event.claims.reduce` on an old payload) — two independent deploy pipelines plus a 60 s cache make the defensive default mandatory; the plan had rejected it on principle and the principle was wrong here.
- **CROSS-MODEL:** two tensions, both resolved toward the outside voice with the founder's approval: D9 (defensive default) and D10 (keep the repaired offsets — they are verified, so D1's rule admits them).
- **VERDICT:** ENG CLEARED — ready to implement. Design review recommended next since this is a visual surface (D12/D13 change what appears on the page).

NO UNRESOLVED DECISIONS
