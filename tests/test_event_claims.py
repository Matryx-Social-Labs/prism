"""Claims on the event payload — the perspectives layer's first read surface.

1,285 verbatim-verified claims sat in enrichments.shared_fields with nothing
reading them. These tests pin the two things that make the surface trustworthy:
only VERIFIED fields leave the server (quote, repaired offsets, source, date —
never the model's `stance` or `said_at`), and the grouping cannot 500 the most-
viewed route on a drifted row.
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from api.routes.events import _speaker_key, dedupe_sources, group_claims

T0 = datetime(2026, 7, 27, 10, 0, tzinfo=UTC)
T1 = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)


def _src(article_id, claims, published_at=T0, name="The Hindu", url="https://h.example/a",
         canonical=None, lang="en"):
    return {"article_id": article_id, "source_name": name, "url": url,
            "url_canonical": canonical, "published_at": published_at, "claims": claims,
            "lang": lang}


def _c(speaker, quote, start=None):
    return {"speaker": speaker, "quote_text": quote, "quote_start": start,
            "stance": "critical", "said_at": "2026-07-27"}


def test_groups_by_speaker_most_quoted_first_then_first_seen():
    out = group_claims([
        _src("a1", [_c("Alice", "one thing"), _c("Bob", "another")]),
        _src("a2", [_c("Alice", "a second thing"), _c("Carol", "third")]),
    ])
    assert [g.speaker for g in out] == ["Alice", "Bob", "Carol"]
    assert len(out[0].claims) == 2


def test_only_verified_fields_leave_the_server():
    """`stance` and `said_at` are model opinions verify_claims never checks."""
    out = group_claims([_src("a1", [_c("Alice", "q", start=40)])])
    cl = out[0].claims[0]
    assert cl.model_dump().keys() == {
        "quote_text", "quote_start", "quote_end", "context_before", "context_after",
        "article_id", "source_name", "url", "published_at",
        # `lang` is verified in the same sense the rest are: it is the article's
        # own language from raw_items, not something the extractor asserted.
        "lang",
    }
    assert cl.quote_start == 40
    assert cl.published_at == T0.isoformat()


def test_within_one_article_quotes_keep_article_order():
    """Two quotes by one speaker from one article come out as the article said them."""
    out = group_claims([_src("a1", [_c("Alice", "later", start=900), _c("Alice", "earlier", start=100)])])
    assert [c.quote_text for c in out[0].claims] == ["earlier", "later"]


def test_newer_article_comes_first_across_articles():
    out = group_claims([
        _src("old", [_c("Alice", "old quote", start=0)], published_at=T0),
        _src("new", [_c("Alice", "new quote", start=0)], published_at=T1),
    ])
    assert [c.article_id for c in out[0].claims] == ["new", "old"]


def test_speaker_key_folds_punctuation_and_case_only():
    assert _speaker_key("D.K. Shivakumar") == _speaker_key("D K Shivakumar") == _speaker_key("d k shivakumar")
    assert _speaker_key("IndiGo") == _speaker_key("Indigo")
    # different people who share a surname must NOT fold — tokens are kept
    assert _speaker_key("Chinna Reddy") != _speaker_key("Komatireddy Rajagopal Reddy")
    assert _speaker_key("Jaishankar") != _speaker_key("S Jaishankar")


def test_folded_speakers_show_under_the_first_surface_form_seen():
    out = group_claims([
        _src("a1", [_c("D.K. Shivakumar", "first")]),
        _src("a2", [_c("D K Shivakumar", "second")]),
    ])
    assert len(out) == 1
    assert out[0].speaker == "D.K. Shivakumar"
    assert len(out[0].claims) == 2


def test_drops_empty_speaker_or_quote():
    out = group_claims([_src("a1", [_c("", "q"), _c("Alice", "  "), _c("Bob", "ok")])])
    assert [g.speaker for g in out] == ["Bob"]


@pytest.mark.parametrize("bad", [None, {"speaker": "x"}, "oops", 7])
def test_a_drifted_claims_column_cannot_500_the_story_page(bad):
    """LEFT JOIN gives NULL for un-enriched articles; an older extractor could
    have left a dict or string. Neither may raise on the most-viewed route."""
    assert group_claims([_src("a1", bad)]) == []


@pytest.mark.parametrize("claim", [
    {"speaker": 7, "quote_text": "a real quote here"},          # non-string speaker → .strip() raises
    {"speaker": "Alice", "quote_text": ["list"]},                # non-string quote
    {"speaker": "Alice", "quote_text": "q", "quote_start": {"weird": 1}},  # offset fails ClaimOut
    {"speaker": "Alice", "quote_text": "q", "quote_end": "12"},  # stringly offset
])
def test_a_malformed_leaf_inside_a_well_shaped_claim_cannot_500_either(claim):
    """The container guards are not enough; a drifted row can be a dict with the
    wrong leaf types, and that must also cost one quote, never the page."""
    out = group_claims([_src("a1", [claim, _c("Bob", "survives")])])
    assert [g.speaker for g in out] == ["Bob"] or (
        # the offset cases keep the claim and null the bad offset
        [g.speaker for g in out] == ["Alice", "Bob"]
        and out[0].claims[0].quote_start is None and out[0].claims[0].quote_end is None
    )


def test_a_non_dict_claim_entry_is_skipped():
    out = group_claims([_src("a1", ["not a claim", _c("Alice", "real")])])
    assert [g.speaker for g in out] == ["Alice"]


def test_published_at_none_is_tolerated():
    out = group_claims([_src("a1", [_c("Alice", "q")], published_at=None)])
    assert out[0].claims[0].published_at is None


def test_one_document_observed_three_times_is_one_source_and_one_quote():
    """Production regression: BBC emitted one page as #0, #2 and #5.

    The fragment lived in external_id while every row carried the same article
    URL. Stored observations may remain separate, but the reader must see one
    document and one copy of its claims.
    """
    url = "https://www.bbc.com/hindi/articles/example?at_medium=RSS&at_campaign=rss"
    canonical = "https://www.bbc.com/hindi/articles/example"
    rows = [
        _src(f"a{i}", [_c("Alice", "एक ही बयान")], published_at=T0, name="BBC News Hindi",
             url=url, canonical=canonical)
        for i in range(3)
    ]
    unique = dedupe_sources(rows)
    assert [s["article_id"] for s in unique] == ["a0"]
    claims = group_claims(unique)
    assert len(claims) == 1
    assert [c.quote_text for c in claims[0].claims] == ["एक ही बयान"]


def test_rows_without_a_url_are_distinct_documents():
    rows = [_src("a1", [], url=None), _src("a2", [], url=None)]
    assert [s["article_id"] for s in dedupe_sources(rows)] == ["a1", "a2"]


@pytest.mark.asyncio(loop_scope="session")
async def test_THE_ROUTE_returns_claims_to_an_anonymous_reader_and_keeps_sources():
    """The wiring, and the paywall decision made explicit.

    Every unit test above passes with the route never calling group_claims. And
    claims are READER-TIER: evidence, not lens depth — so no Authorization header
    is sent here. The sources query was MODIFIED (one added column), so this also
    asserts `sources` still arrives in the same response.
    """
    import api.routes.events as events
    from api.main import app

    eid = uuid.uuid4()
    aid = uuid.uuid4()
    duplicate_aid = uuid.uuid4()

    class _R:
        def __init__(self, sql):
            self.sql = sql

        def mappings(self):
            return self

        def scalars(self):  # the placeholder-photo hashes: none in this corpus
            return self

        def first(self):
            if "FROM events WHERE id" in self.sql:
                return {"id": eid, "title": "t", "headline_by": None, "summary": "s", "sector": None, "subsector": None,
                        "image_url": None, "regions": [], "occurred_at": None,
                        "last_updated_at": T0, "projection": {}}
            return None
        def all(self):
            if "FROM event_memberships em" in self.sql:
                article = {"source_name": "Mint", "source_slug": "mint", "funding": None,
                           "url": "https://m.example/x?utm_source=rss",
                           "url_canonical": "https://m.example/x", "title": "T",
                           "published_at": T0, "stance": None, "lang": "en",
                           "claims": [_c("Anita Dipke", "We were receiving proposals", start=12)]}
                # The same publisher document was observed under two unstable
                # feed ids. The route, not only the helper, must collapse it.
                return [{"article_id": aid, **article}, {"article_id": duplicate_aid, **article}]
            return []

    class _S:
        async def execute(self, stmt, *a, **kw):
            return _R(str(stmt))

    async def fake_db():
        yield _S()

    app.dependency_overrides[events.get_db] = fake_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get(f"/api/v1/events/{eid}")
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["claims"] == [{
                "speaker": "Anita Dipke",
                "role": None,  # the article named no office; the field is present, never invented
                "claims": [{"quote_text": "We were receiving proposals", "quote_start": 12,
                            "quote_end": None, "context_before": "", "context_after": "",
                            "article_id": str(aid), "source_name": "Mint",
                            "url": "https://m.example/x?utm_source=rss",
                            "published_at": T0.isoformat(), "lang": "en"}],
                "languages": ["en"],
            }], "the route did not pass claims through, or leaked an unverified field"
            assert body["sources"] and body["sources"][0]["article_id"] == str(aid), (
                "the sources query was changed and sources stopped arriving"
            )
            assert len(body["sources"]) == 1, "one document leaked through as two source rows"
    finally:
        app.dependency_overrides.pop(events.get_db, None)


def test_a_speakers_role_is_the_one_the_articles_repeat_most():
    """Particle prints who a speaker is under the name; the extractor now carries
    speaker_role as the article states it, and the record shows the most-repeated
    one across the speaker's quotes — never a role we made up."""
    a = _src("a1", [_c("J. D. Vance", "We can't predict the future, but the president is right on this one")])
    a["claims"][0]["speaker_role"] = "Vice President of the United States"
    b = _src("a2", [_c("J.D. Vance", "This thing will enter a much different phase in a couple of months")])
    b["claims"][0]["speaker_role"] = "Vice President of the United States"
    c = _src("a3", [_c("J.D. Vance", "The second phase is to ensure they are not able to rebuild")])
    c["claims"][0]["speaker_role"] = "US Vice President"
    grouped = group_claims([a, b, c])
    assert len(grouped) == 1 and grouped[0].role == "Vice President of the United States"
    # no role anywhere → None, not ""
    assert group_claims([_src("a9", [_c("Someone", "A perfectly long enough quotation here")])])[0].role is None


def test_the_context_is_the_articles_own_words_around_a_re_verified_span():
    """A reader can see the quote in place: the words either side, cut at word
    boundaries, and only when the span still points at the quote."""
    from api.routes.events import quote_context

    text = "Earlier in the day the minister met the delegation. " + "We will not roll back the fee, he said. " + "The traders left without a meeting."
    q = "We will not roll back the fee"
    start = text.index(q)
    before, after = quote_context(text, q, start, start + len(q))
    assert before.endswith("met the delegation.") and not before.startswith(" ")
    assert after.startswith(", he said.")
    # a stale offset shows nothing rather than the wrong sentence
    assert quote_context(text, q, start + 3, start + 3 + len(q)) == ("", "")
    assert quote_context(None, q, start, start + len(q)) == ("", "")


def test_context_survives_the_newlines_the_verifier_collapsed():
    """verify_claims computes the span on whitespace-flattened text, so an article
    with a paragraph break before the quote has offsets that do not index the
    raw text. Prod 2026-09-18: 534 of 4,444 claims (12%) lost their context this
    way. The context must be cut from the same flattened text the span was
    measured on."""
    from api.routes.events import quote_context
    from enrichment.claims import flat_ws

    raw = "First paragraph ends here.\n\n  Second one:  We will not roll back the fee, he said. Then more."
    q = "We will not roll back the fee"
    start = flat_ws(raw).index(q)
    assert raw[start:start + len(q)] != q  # the raw slice is off by the collapsed whitespace
    before, after = quote_context(raw, q, start, start + len(q))
    assert before.endswith("Second one:") and after.startswith(", he said.")


def test_context_rides_the_claim_when_the_row_carries_the_article_text():
    text = "Intro words here. The quote itself. Trailing words here."
    q = "The quote itself."
    src = _src("a1", [_c("Alice", q, start=text.index(q))])
    src["claims"][0]["quote_end"] = text.index(q) + len(q)
    src["clean_text"] = text
    cl = group_claims([src])[0].claims[0]
    assert cl.context_before == "Intro words here." and cl.context_after == "Trailing words here."


# ── The language a quote was printed in ──────────────────────────────────────
#
# A quote is verified VERBATIM AGAINST ITS ARTICLE (enrichment/claims.py), which
# is not the same as verbatim against the speaker: an outlet's own translation
# passes that check perfectly. Speaker names are canonicalised to English by the
# extractor, so a Kannada retelling lands on the SAME speaker card as the English
# one — measured on production, 10,763 of 10,766 speaker strings are Latin. The
# card shows two quotes; ordering by recency alone therefore let a later
# rendering hide an earlier one with nothing saying a language was missing.


def test_a_later_language_cannot_push_an_earlier_one_out_of_the_fold():
    """The founder-reported bug: TV9 Kannada files later, the English rendering
    disappears behind "2 more quotes" with nothing marking it missing."""
    out = group_claims([
        _src("kn2", [_c("Donald Trump", "a later kannada line")], published_at=T1, lang="kn"),
        _src("kn1", [_c("Donald Trump", "an earlier kannada line")], published_at=T1, lang="kn"),
        _src("en1", [_c("Donald Trump", "what he actually said")], published_at=T0, lang="en"),
    ])
    fold = [c.quote_text for c in out[0].claims[:2]]
    assert "what he actually said" in fold
    assert {c.lang for c in out[0].claims[:2]} == {"en", "kn"}


def test_english_leads_for_a_reader_who_has_expressed_no_preference():
    out = group_claims([
        _src("kn1", [_c("X", "kannada one"), _c("X", "kannada two")], published_at=T1, lang="kn"),
        _src("en1", [_c("X", "english one")], published_at=T0, lang="en"),
    ])
    assert out[0].claims[0].lang == "en"
    assert out[0].languages == ["en", "kn"]


def test_one_language_is_left_exactly_as_it_was():
    """Round-robin over a single bucket is the identity: 43% of stored quotes are
    non-English originals and nothing about them should move."""
    out = group_claims([
        _src("a2", [_c("X", "newer")], published_at=T1, lang="kn"),
        _src("a1", [_c("X", "older")], published_at=T0, lang="kn"),
    ])
    assert [c.quote_text for c in out[0].claims] == ["newer", "older"]
    assert out[0].languages == ["kn"]


def test_an_untagged_article_is_not_reported_as_a_language():
    """A source with no `language` still yields quotes; it must not print as one
    more language on a card that counts them."""
    out = group_claims([_src("a1", [_c("X", "no language on this row")], lang=None)])
    assert out[0].claims[0].lang is None
    assert out[0].languages == []


def test_a_speaker_quoted_identically_by_two_outlets_still_orders_deterministically():
    """Two ClaimOut rows with equal fields compare equal under Pydantic, so the
    language order must come from where each was bucketed, not from list.index."""
    out = group_claims([
        _src("a1", [_c("X", "the same sentence")], published_at=T1, name="Hindu", lang="hi"),
        _src("a2", [_c("X", "the same sentence")], published_at=T0, name="Mint", lang="hi"),
        _src("a3", [_c("X", "a third")], published_at=T0, name="TV9", lang="kn"),
    ])
    assert out[0].languages == ["hi", "kn"]
