# Plan: a quote carries the language it was spoken in

**Source**: founder report — "a Kannada report arriving later replaces the English quotes"
**Complexity**: Medium (Phase 0 small, Phases 1–2 measured and gated)
**Status**: Phase 0 SHIPPED (v0.0.90.0). Phases 1+2 SHIPPED IN SHADOW and Phase 3 SHIPPED (v0.0.91.0). Open: founders label `tools/gold_renderings --export`; turn PRISM_QUOTE_VERDICTS on for the API only if `--score` passes.

## What is actually happening (measured on production, read-only, 2026-09-22)

Nothing is overwritten. Claims are stored per article in `enrichments.shared_fields`
and never merged; `group_claims` (`api/routes/events.py:206`) accumulates them across
the event's articles. Four facts compose into the reported bug:

1. **Speaker names are canonicalised to English.** `extract-shared` requires entities
   in "CANONICAL ENGLISH/ROMANIZED form — never the native script", and `speaker` is
   "the personal name, as in entities". Measured: 10,763 of 10,766 stored speaker
   strings are Latin. So a Kannada article's quote lands on the **same speaker card**
   as the English one.
2. **The card is ordered newest-article-first** (`ORDER BY ri.published_at DESC`, then
   `sort_key = -published_at` in `group_claims`).
3. **The card shows two quotes** (`QUOTES_FOLD = 2`, `web/src/components/Said.tsx:29`).
   A later Kannada report therefore pushes the English rendering behind "N more quotes".
   Measured: 93 speaker cards currently mix scripts; on 3 of them an English rendering
   is already out of the visible fold.
4. **Verbatim is enforced against the article, not against the speaker.**
   `enrichment/claims.py` checks the quote appears in that article's `clean_text`.
   An outlet's own translation passes that check perfectly.

So the founder saw a display displacement — but it exposed the real defect, which is (4).

### The case that settles the design

Event `11974a44`, speaker **Giorgia Meloni**. She spoke **Italian**. Times of India
printed an English translation; Prajavani printed a Kannada one. Prism shows both
inside quotation marks, attributed to her, and the quote share card's honesty line
(`DESIGN.md:287`) reads `VERBATIM`. **Neither is what she said.**

"Prefer English" is therefore the wrong fix twice over: it would enshrine one
translation as the original here, and it would empty the Indic corpus — 2,445 events
carry claims only from non-English sources (4,618 quotes, 43% of all stored quotes),
where the Indic quote **is** the original.

### Corpus shape

| | events | claims |
|---|---|---|
| claims from English sources only | 2,389 | 5,916 |
| claims from non-English sources only | 2,445 | 4,618 |
| mixed-language | 41 | 232 |

Quote scripts: latin 6,085 · kannada 2,653 · devanagari 1,359 · tamil 169 · arabic 140
· gujarati 108 · bengali 90 · telugu 83 · gurmukhi 79.

Claim yield per enriched article: kn 37.7%, en 27.3%, hi 25.2%, ta 45.7% — Indic
articles are **not** silently losing quotes, so there is no second hidden bug. But the
prompt does hold a live contradiction ("ALWAYS write every output value in ENGLISH"
vs `quote_text` "VERBATIM"); it currently resolves toward verbatim by luck and would
flip on any model change.

## The rule to adopt

> **A quote carries the language it was spoken in, or it is labelled as a rendering.**
> Prism prints a quote as someone's words only when the article printed them in the
> language they were spoken in. Every other rendering is printed as what it is —
> "Prajavani's Kannada rendering" — and the original leads. When Prism holds no
> rendering in the original language, it says so.

This is not new doctrine: `faithful_role` already applies exactly this to titles
(`DESIGN.md:245` — "an English role on a Hindi article is unverifiable… No role is
better than a plausible one — same rule as the quotes: verbatim or absent"). The
codebase solved this for the *role* and not for the *words*.

## Three languages, currently conflated into one field

| | what it is | where it comes from | cost |
|---|---|---|---|
| `quote_lang` | the language the article printed | `raw_items.language` — populated, already in the join | free |
| `spoken_lang` | the language the speaker used | unknown today | Phase 2 |
| reader's language | `accounts.languages`, ordered by preference | already collected | free |

## Founder decisions (2026-09-23)

**D-quote-1 — the reader's language leads, labelled as what it is.** A signed-in
reader of language L is shown the rendering in L when Prism holds one, explicitly
labelled a rendering; otherwise the default (the original, else English). Serving
Indian readers their own language across the whole product is a separate, later
piece of work — this decision is only about not hiding the rendering they can read.

**D-quote-2 — original *with* the translation.** When the reader's language differs
from the original's, both are on the card: the original leads, the reader's-language
rendering sits beside it, labelled. Never the rendering alone.

**D-quote-3 — a rendering is printed even when Prism holds no original.** It is
still evidence of what an outlet reported. It is never printed unlabelled: this is
the first time Prism puts quotation marks around something it knows is not the
speaker's words, and the label is what makes that honest rather than a regression.

**D-quote-4 — the model may DOWNGRADE a claim, never assert one.** Decided rather
than deferred, and the shape matters more than the answer:

- Prism **never** asks a model "what language was this spoken in?" — that is an
  assertion the reader cannot check, printed beside verbatim material, which is
  exactly what D4 removed when it retired the Perspectives cards, and exactly why
  `ClaimOut` already drops `stance` and `said_at` (`api/schemas.py:236`).
- Prism **may** ask the one-sided question it already asks of every quote:
  *do this article's own words support that the speaker said this, in this language?*
  A "no" removes a claim Prism is currently making. It can never add one.
- **The primary mechanism needs no model at all.** If one utterance appears in two
  languages, then at most one of them is the original — that is arithmetic, not
  judgement, and it is what makes the Meloni card honest with zero model calls.
- When nothing is established, the default is today's behaviour: the quote prints as
  verbatim with its language named. Unsure never downgrades 43% of the corpus.

So the ordering is: **evidence first (free), model second (one-sided, gated), and no
assertion of an original language ever.**

## Phases

### Phase 0 — stop the displacement, name the language (no model call, no migration)

| File | Action | Why |
|---|---|---|
| `api/routes/events.py` | UPDATE | add `ri.language` to the source SELECT; carry it onto `ClaimOut` |
| `api/schemas.py` | UPDATE | `ClaimOut.lang`, `SpeakerClaims.languages` |
| `api/routes/events.py::group_claims` | UPDATE | one quote per language before any language's second quote, so no language can push another out of the fold; reader's primary first when signed in, else English-first (`PRODUCT.md:118`) |
| `common/languages.py` | UPDATE | display names for every **ingested** language (ur, gu, mr, pa, bn, te), kept separate from `LAUNCH_LANGUAGES` which is the onboarding picker |
| `web/src/components/Said.tsx` | UPDATE | language beside the outlet in the mono provenance voice (`ಕನ್ನಡ · Prajavani`) when the card holds >1 language; sub-line counts languages the way the coverage bar already does (`DESIGN.md:204`) |
| `web/src/app/story/[id]/quote/[n]` (OG card) | UPDATE | honesty line becomes `VERBATIM · <language> · outlet · date` — it must never assert VERBATIM over a translation without naming the language |

Mirrors: `dedupe_sources` for the defensive-shape style; `faithful_role` for the
"absent beats plausible" rule; `projection.languages` (already carried, read by
`personalization/ranking.py:52`) for the language-set idiom.

### Phase 1 — recognise one utterance seen twice (cheap, gated)

- Candidate pairs: same event, same speaker key, **different** `quote_lang`.
- Key: `claim_text` — the neutral English sentence the extractor already writes,
  populated on 10,752 of 10,766 claims (99.9%). Embed with fastembed (in the stack),
  take pairs above a measured cosine floor.
- Confirm with a Jev `noul` through **`common/pair_judge.py`** — the module already
  built for this exact shape (pairwise judge, cache table, `JUDGE_CONCURRENCY`).
  41 mixed events in the whole corpus, so the backfill is cents.
- Store `utterance_id` on the claim. One utterance renders once; the other renderings
  collapse beneath it ("Also reported in Kannada by Prajavani").
- **Gate on a gold set** before it serves, like `gold_claims` / `gold_clips` /
  `gold_xposts`. Target precision ≥0.95: a wrong merge asserts that two different
  statements are the same statement, which is its own misattribution.

### Phase 2 — which rendering is the original

Evidence in order, stopping at the first that holds:

1. **The article says so** — "speaking in Kannada", "ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಮಾತನಾಡಿ". One
   optional `Claim` field filled only from the article's own words, same discipline as
   `speaker_role_native`.
2. **One Jev `choice` per utterance cluster** over {languages present} ∪ {other},
   given speaker, event and occasion. This is world knowledge and it is a JUDGEMENT,
   so it is printed as one: "Prism reads this as originally Italian." Never as a fact.
3. **No confident answer → designate nothing.** Print every rendering with its language
   and outlet. The reader sees the truth; we have not invented one.

The payoff is the Meloni case: when the original language is established and Prism
holds no rendering in it, the card says *"Meloni said this in Italian; Prism has no
Italian source — both readings below are translations."* No aggregator says that, and
it is the verbatim-or-nothing promise applied one level deeper.

### Phase 3 — close the prompt contradiction, backfill

- `common/prompts/fallbacks/extract-shared.json`: carve `quote_text` (and only
  `quote_text`) out of the ALWAYS-ENGLISH rule explicitly, so a model swap cannot flip
  43% of the corpus to translations overnight.
- Backfilling `lang` is a join, not a model call — free.
- Backfill utterance clusters for the 41 mixed-language events only.

## Validation

```bash
uv run ruff check . && uv run pytest -q tests/test_event_claims.py tests/test_fulltext_markup.py
cd web && npm test
uv run python -m tools.backfill_quote_lang            # dry run, prod read-only
```

New tests: a speaker card holding en+kn shows one of each inside the fold; a
translation never renders with an unqualified VERBATIM line; `group_claims` is stable
when `raw_items.language` is NULL. Each mutation-verified (`CLAUDE.md`).

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Phase 1 merges two different statements by one speaker | Medium | gold set + ≥0.95 precision gate before it serves; unmerged is the safe default |
| `raw_items.language` is source-level, so a Kannada outlet's English piece is mislabelled | Low | script check on the quote overrides the column when they disagree |
| Reader-language ordering makes the event response vary per reader | Certain | the route already varies by user (unlocked lenses); no new cache class |
| Phase 2's judgement is an LLM opinion on the page — the boundary D4 drew | — | **founder question Q4** |

## Acceptance

- [ ] No quote renders without its language when its card holds more than one
- [ ] No language can displace another out of the 2-quote fold
- [ ] `VERBATIM` never appears unqualified over a rendering
- [ ] The Meloni card reads truthfully

## Outcome (2026-09-23)

- **Phase 1 + 2 merged into one mechanism.** One Jev call per speaker card asks
  "spoken in the language printed?" for every quote and "same statement?" for
  every cross-language pair. Evidence first holds by construction: a
  cross-language group is shown as one statement with "at most one is the words
  as spoken" without any model assertion about which; the "spoken here?" answer
  can only DOWNGRADE (below 0.2) — D-quote-4. "The article says so" (a new
  extraction field) was dropped: forward-only, and the one-sided question
  already covers what it would.
- **Phase 3** shipped after a prompt bake-off (claims kept 0.82 -> 0.90 on kn+hi,
  everything else unchanged).
- **Gate**: `tools/gold_renderings --judge --apply` (shadow backfill) ->
  `--export` -> founders label -> `--score`. Crossing points SAME_MIN 0.8 and
  SPOKEN_MAX 0.2 are provisional and settable from labels without re-asking.
