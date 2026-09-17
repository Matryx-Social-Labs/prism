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

from api.routes.events import _speaker_key, group_claims

T0 = datetime(2026, 7, 27, 10, 0, tzinfo=UTC)
T1 = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)


def _src(article_id, claims, published_at=T0, name="The Hindu", url="https://h.example/a"):
    return {"article_id": article_id, "source_name": name, "url": url,
            "published_at": published_at, "claims": claims}


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

    class _R:
        def __init__(self, sql):
            self.sql = sql

        def mappings(self):
            return self

        def first(self):
            if "FROM events WHERE id" in self.sql:
                return {"id": eid, "title": "t", "headline_by": None, "summary": "s", "sector": None, "subsector": None,
                        "image_url": None, "regions": [], "occurred_at": None,
                        "last_updated_at": T0, "projection": {}}
            return None
        def all(self):
            if "FROM event_memberships em" in self.sql:
                return [{"article_id": aid, "source_name": "Mint", "source_slug": "mint",
                         "funding": None, "url": "https://m.example/x", "title": "T",
                         "published_at": T0, "stance": None,
                         "claims": [_c("Anita Dipke", "We were receiving proposals", start=12)]}]
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
                "claims": [{"quote_text": "We were receiving proposals", "quote_start": 12,
                            "quote_end": None, "context_before": "", "context_after": "",
                            "article_id": str(aid), "source_name": "Mint",
                            "url": "https://m.example/x", "published_at": T0.isoformat()}],
            }], "the route did not pass claims through, or leaked an unverified field"
            assert body["sources"] and body["sources"][0]["article_id"] == str(aid), (
                "the sources query was changed and sources stopped arriving"
            )
    finally:
        app.dependency_overrides.pop(events.get_db, None)


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


def test_context_rides_the_claim_when_the_row_carries_the_article_text():
    text = "Intro words here. The quote itself. Trailing words here."
    q = "The quote itself."
    src = _src("a1", [_c("Alice", q, start=text.index(q))])
    src["claims"][0]["quote_end"] = text.index(q) + len(q)
    src["clean_text"] = text
    cl = group_claims([src])[0].claims[0]
    assert cl.context_before == "Intro words here." and cl.context_after == "Trailing words here."
