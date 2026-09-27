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

from api.routes.events import _speaker_key, dedupe_sources, group_claims, quote_id

T0 = datetime(2026, 7, 27, 10, 0, tzinfo=UTC)
T1 = datetime(2026, 7, 28, 10, 0, tzinfo=UTC)


def _src(article_id, claims, published_at=T0, name="The Hindu", url="https://h.example/a",
         canonical=None, lang="en", clean_text=None):
    """An article row as the route reads it. Unless a test brings its own text,
    the article prints each claim's words inside quotation marks — the shape a
    direct quote has in a real report, and the only shape the card now shows."""
    if clean_text is None and isinstance(claims, list):
        clean_text = " ".join(
            f"The reporter wrote this line. “{c['quote_text']}”"
            for c in claims if isinstance(c, dict) and isinstance(c.get("quote_text"), str)
        )
    return {"article_id": article_id, "source_name": name, "url": url,
            "url_canonical": canonical, "published_at": published_at, "claims": claims,
            "lang": lang, "clean_text": clean_text}


def _c(speaker, quote, start=None):
    return {"speaker": speaker, "quote_text": quote, "quote_start": start,
            "stance": "critical", "said_at": "2026-07-27"}


def test_groups_by_speaker_most_quoted_first_then_first_seen():
    out = group_claims([
        _src("a1", [_c("Alice", "one thing I said today"), _c("Bob", "another thing entirely here")]),
        _src("a2", [_c("Alice", "a second thing I said"), _c("Carol", "the third thing said here")]),
    ])
    assert [g.speaker for g in out] == ["Alice", "Bob", "Carol"]
    assert len(out[0].claims) == 2


def test_only_verified_fields_leave_the_server():
    """`stance` and `said_at` are model opinions verify_claims never checks."""
    text = "Asked about the fee, the minister said: “We will not roll back the fee.”"
    out = group_claims([_src("a1", [_c("Alice", "We will not roll back the fee.", start=40)], clean_text=text)])
    cl = out[0].claims[0]
    assert cl.model_dump().keys() == {
        "quote_text", "quote_start", "quote_end", "context_before", "context_after",
        "article_id", "source_name", "url", "published_at",
        # `lang` is verified in the same sense the rest are: it is the article's
        # own language from raw_items, not something the extractor asserted.
        "lang",
        # Present but inert unless PRISM_QUOTE_VERDICTS and a judged card.
        "utterance", "translated",
        # The quote's address (its words, not its position) and the other
        # outlets that printed the same words.
        "id", "also_in",
    }
    # A stale stored offset is repaired from the words, as at write time.
    assert cl.quote_start == text.index("We will")
    assert cl.published_at == T0.isoformat()


def test_within_one_article_quotes_keep_article_order():
    """Two quotes by one speaker from one article come out as the article said them."""
    text = "“The earlier thing she said.” Later on: “The later thing she said.”"
    out = group_claims([_src("a1", [_c("Alice", "The later thing she said."), _c("Alice", "The earlier thing she said.")],
                             clean_text=text)])
    assert [c.quote_text for c in out[0].claims] == ["The earlier thing she said.", "The later thing she said."]


def test_newer_article_comes_first_across_articles():
    out = group_claims([
        _src("old", [_c("Alice", "the old quote from Monday", start=0)], published_at=T0),
        _src("new", [_c("Alice", "the new quote from Tuesday", start=0)], published_at=T1),
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
        _src("a1", [_c("D.K. Shivakumar", "the first thing he said")]),
        _src("a2", [_c("D K Shivakumar", "the second thing he said")]),
    ])
    assert len(out) == 1
    assert out[0].speaker == "D.K. Shivakumar"
    assert len(out[0].claims) == 2


def test_drops_empty_speaker_or_quote():
    out = group_claims([_src("a1", [_c("", "a quote with no speaker"), _c("Alice", "  "), _c("Bob", "this one is fine")])])
    assert [g.speaker for g in out] == ["Bob"]


@pytest.mark.parametrize("bad", [None, {"speaker": "x"}, "oops", 7])
def test_a_drifted_claims_column_cannot_500_the_story_page(bad):
    """LEFT JOIN gives NULL for un-enriched articles; an older extractor could
    have left a dict or string. Neither may raise on the most-viewed route."""
    assert group_claims([_src("a1", bad)]) == []


@pytest.mark.parametrize("claim", [
    {"speaker": 7, "quote_text": "a real quote here"},          # non-string speaker → .strip() raises
    {"speaker": "Alice", "quote_text": ["list"]},                # non-string quote
    {"speaker": "Alice", "quote_text": "a real quote here", "quote_start": {"weird": 1}},  # offset fails ClaimOut
    {"speaker": "Alice", "quote_text": "a real quote here", "quote_end": "12"},  # stringly offset
])
def test_a_malformed_leaf_inside_a_well_shaped_claim_cannot_500_either(claim):
    """The container guards are not enough; a drifted row can be a dict with the
    wrong leaf types, and that must also cost one quote, never the page."""
    rows = [_src("a1", [claim, _c("Bob", "this one survives intact")])]
    out = group_claims(rows)
    assert [g.speaker for g in out] == ["Bob"] or (
        # the offset cases keep the claim, its span repaired from the words
        [g.speaker for g in out] == ["Alice", "Bob"]
        and rows[0]["clean_text"][out[0].claims[0].quote_start:out[0].claims[0].quote_end] == "a real quote here"
    )
    # The unchecked card (share-link addresses only) must not 500 either.
    legacy = group_claims(rows, checked=False)
    assert [g.speaker for g in legacy] == ["Bob"] or (
        [g.speaker for g in legacy] == ["Alice", "Bob"]
        and legacy[0].claims[0].quote_start is None and legacy[0].claims[0].quote_end is None
    )


def test_a_non_dict_claim_entry_is_skipped():
    out = group_claims([_src("a1", ["not a claim", _c("Alice", "a real quote from Alice")])])
    assert [g.speaker for g in out] == ["Alice"]


def test_published_at_none_is_tolerated():
    out = group_claims([_src("a1", [_c("Alice", "a quote with no date")], published_at=None)])
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
        _src(f"a{i}", [_c("Alice", "एक ही बयान दिया गया")], published_at=T0, name="BBC News Hindi",
             url=url, canonical=canonical)
        for i in range(3)
    ]
    unique = dedupe_sources(rows)
    assert [s["article_id"] for s in unique] == ["a0"]
    claims = group_claims(unique)
    assert len(claims) == 1
    assert [c.quote_text for c in claims[0].claims] == ["एक ही बयान दिया गया"]


def test_rows_without_a_url_are_distinct_documents():
    rows = [_src("a1", [], url=None), _src("a2", [], url=None)]
    assert [s["article_id"] for s in dedupe_sources(rows)] == ["a1", "a2"]


QUOTE = "We were receiving proposals for him"
NARRATION = "Anita Dipke said the family was proud of him."
TEXT = f"Her mother Anita Dipke spoke to reporters. \"{QUOTE},\" she said. {NARRATION}"


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
                           "clean_text": TEXT,
                           # The reporter's sentence was stored as her quote
                           # before the direct-speech rule; it must not be served.
                           "claims": [_c("Anita Dipke", NARRATION, start=TEXT.index(NARRATION)),
                                      _c("Anita Dipke", QUOTE, start=12)]}
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
            at = TEXT.index(QUOTE)
            assert body["claims"] == [{
                "speaker": "Anita Dipke",
                "role": None,  # the article named no office; the field is present, never invented
                "claims": [{"id": quote_id(QUOTE), "quote_text": QUOTE, "quote_start": at,
                            "quote_end": at + len(QUOTE),
                            "context_before": "Her mother Anita Dipke spoke to reporters. \"",
                            "context_after": ",\" she said. " + NARRATION,
                            "article_id": str(aid), "source_name": "Mint",
                            "url": "https://m.example/x?utm_source=rss",
                            "published_at": T0.isoformat(), "lang": "en",
                            "utterance": None, "translated": False, "also_in": []}],
                "languages": ["en"],
            }], "the route did not pass claims through, or leaked an unverified field"
            # The address shared before the rule (the quote was 0-0 then, the
            # narration 0-1) still resolves; the withdrawn narration's does not.
            assert body["quote_aliases"] == {"0-0": quote_id(QUOTE)}
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
    text = "Intro words here. \u201cThe quote is itself here.\u201d Trailing words here."
    q = "The quote is itself here."
    src = _src("a1", [_c("Alice", q, start=text.index(q))], clean_text=text)
    src["claims"][0]["quote_end"] = text.index(q) + len(q)
    cl = group_claims([src])[0].claims[0]
    assert cl.context_before == "Intro words here. \u201c" and cl.context_after == "\u201d Trailing words here."


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
        _src("kn1", [_c("X", "the first kannada line"), _c("X", "the second kannada line")], published_at=T1, lang="kn"),
        _src("en1", [_c("X", "the one english line")], published_at=T0, lang="en"),
    ])
    assert out[0].claims[0].lang == "en"
    assert out[0].languages == ["en", "kn"]


def test_one_language_is_left_exactly_as_it_was():
    """Round-robin over a single bucket is the identity: 43% of stored quotes are
    non-English originals and nothing about them should move."""
    out = group_claims([
        _src("a2", [_c("X", "the newer line said here")], published_at=T1, lang="kn"),
        _src("a1", [_c("X", "the older line said here")], published_at=T0, lang="kn"),
    ])
    assert [c.quote_text for c in out[0].claims] == ["the newer line said here", "the older line said here"]
    assert out[0].languages == ["kn"]


def test_an_untagged_article_is_not_reported_as_a_language():
    """A source with no `language` still yields quotes; it must not print as one
    more language on a card that counts them."""
    out = group_claims([_src("a1", [_c("X", "no language on this row")], lang=None)])
    assert out[0].claims[0].lang is None
    assert out[0].languages == []


def test_a_speaker_quoted_identically_by_two_outlets_still_orders_deterministically():
    """Two ClaimOut rows with equal fields compare equal under Pydantic, so the
    language order must come from where each was bucketed, not from list.index.
    (Identical words from two outlets are one row now; the order still holds.)"""
    out = group_claims([
        _src("a1", [_c("X", "the very same sentence here")], published_at=T1, name="Hindu", lang="hi"),
        _src("a2", [_c("X", "the very same sentence here")], published_at=T0, name="Mint", lang="hi"),
        _src("a3", [_c("X", "a third sentence said here")], published_at=T0, name="TV9", lang="kn"),
    ])
    assert out[0].languages == ["hi", "kn"]


# ── Verdicts: one statement printed twice, and an outlet's translation ───────
#
# enrichment/renderings.py judges each speaker card; these pin what the route
# does with the answer. Keyed by the quote's identity (article + words), never
# its position, and inert for any quote the verdicts do not mention.

from enrichment.renderings import claim_key  # noqa: E402


def _meloni():
    return [
        _src("kn1", [_c("Giorgia Meloni", "ಶಾಲೆಗೆ ಮುಖ ಮುಚ್ಚದೆ ಬರಬೇಕು")], published_at=T1, name="Prajavani", lang="kn"),
        _src("en1", [_c("Giorgia Meloni", "You must go to school with your face uncovered"),
                     _c("Giorgia Meloni", "A measure will soon be presented to Cabinet")],
             published_at=T0, name="Mint", lang="en"),
    ]


def test_a_confident_same_statement_verdict_groups_the_two_renderings():
    kn = claim_key("kn1", "ಶಾಲೆಗೆ ಮುಖ ಮುಚ್ಚದೆ ಬರಬೇಕು")
    en = claim_key("en1", "You must go to school with your face uncovered")
    card = {"spoken": {}, "same": [[en, kn, 0.95]]}
    out = group_claims(_meloni(), {"giorgia meloni": card})[0]
    by_text = {c.quote_text: c for c in out.claims}
    assert by_text["ಶಾಲೆಗೆ ಮುಖ ಮುಚ್ಚದೆ ಬರಬೇಕು"].utterance is not None
    assert by_text["ಶಾಲೆಗೆ ಮುಖ ಮುಚ್ಚದೆ ಬರಬೇಕು"].utterance == by_text["You must go to school with your face uncovered"].utterance
    assert by_text["A measure will soon be presented to Cabinet"].utterance is None


def test_only_a_confident_no_marks_a_translation():
    """D-quote-4: a model may downgrade a claim, never assert one. Unsure (0.5)
    must leave the quote as a verbatim quote."""
    kn = claim_key("kn1", "ಶಾಲೆಗೆ ಮುಖ ಮುಚ್ಚದೆ ಬರಬೇಕು")
    en = claim_key("en1", "You must go to school with your face uncovered")
    card = {"spoken": {kn: 0.03, en: 0.5}, "same": []}
    out = group_claims(_meloni(), {"giorgia meloni": card})[0]
    translated = {c.quote_text for c in out.claims if c.translated}
    assert translated == {"ಶಾಲೆಗೆ ಮುಖ ಮುಚ್ಚದೆ ಬರಬೇಕು"}


def test_no_verdicts_is_exactly_todays_card():
    plain = group_claims(_meloni())
    judged_elsewhere = group_claims(_meloni(), {"someone else": {"spoken": {}, "same": []}})
    assert [c.model_dump() for c in plain[0].claims] == [c.model_dump() for c in judged_elsewhere[0].claims]
    assert not any(c.translated or c.utterance for c in plain[0].claims)


def test_a_verdict_about_a_quote_no_longer_on_the_card_changes_nothing():
    """The report it named left the event (a re-cluster, a dedupe): a stale
    verdict must not group or label anything that remains."""
    gone = claim_key("gone", "words from a report that moved away")
    en = claim_key("en1", "You must go to school with your face uncovered")
    card = {"spoken": {gone: 0.01}, "same": [[en, gone, 0.99]]}
    out = group_claims(_meloni(), {"giorgia meloni": card})[0]
    assert not any(c.translated or c.utterance for c in out.claims)


# ── Direct speech only, one speaker per quote, one row per thing said ────────
#
# Founder decision, 27 Sep 2026: quotes are direct speech only. The rules run
# where the card is built, so what was stored before them is served under them
# without a backfill. Fixtures are the live records the audit found.

MAJITHIA = "The accused should face the strictest punishment under law. But police inaction fuelled the situation."
TOORA = "When we reached here, we came to know that there were rumours. Because of the rumours, students gathered here"


def test_the_reporters_sentence_stored_as_a_quote_is_not_served():
    """Live, event 8db8e742: Scroll's "Saheb said he pointed out sections…" and
    ToI's "workers accompanying Jarnail Singh abused his family…" were served as
    quotes. They were stored before the rule; the card no longer shows them."""
    scroll = ("The video shows police were present. Saheb said he pointed out sections where the road "
              "surface was breaking apart, after which Verma slapped him. Kejriwal shared the video.")
    real = "When his worker abused my family, I did what any person would do after getting angry."
    toi = ("He alleged that workers accompanying Jarnail Singh abused his family and said he reacted after that. "
           f"Verma said, “{real}”")
    out = group_claims([
        _src("s", [_c("Saheb", "Saheb said he pointed out sections where the road surface was breaking apart, "
                               "after which Verma slapped him.")], clean_text=scroll),
        _src("t", [_c("Parvesh Verma", "workers accompanying Jarnail Singh abused his family and said he reacted after that."),
                   _c("Parvesh Verma", real)], clean_text=toi),
    ])
    assert [(g.speaker, [c.quote_text for c in g.claims]) for g in out] == [("Parvesh Verma", [real])]


def test_a_quote_given_to_two_speakers_stays_with_the_one_named_beside_it():
    """Live, the LPU record: Majithia's post on X stored under both Majithia and
    SSP Gaurav Toora — and the landing page showcased it as Toora's."""
    text = ("SSP Gaurav Toora said the situation was under control. Akali leader Bikram Singh Majithia blamed "
            f"the AAP leadership. “{MAJITHIA}” Majithia wrote on X.")
    out = group_claims([_src("tt", [_c("Gaurav Toora", MAJITHIA), _c("Bikram Singh Majithia", MAJITHIA)], clean_text=text)])
    assert [(g.speaker, len(g.claims)) for g in out] == [("Bikram Singh Majithia", 1)]


def test_a_quote_given_to_two_speakers_neither_named_near_it_is_shown_for_neither():
    text = ("Protests continued on the campus through the night. " * 6 + f"“{MAJITHIA}” "
            + "Traffic resumed later. " * 12 + "SSP Gaurav Toora and Bikram Singh Majithia visited the site.")
    out = group_claims([_src("tt", [_c("Gaurav Toora", MAJITHIA), _c("Bikram Singh Majithia", MAJITHIA)], clean_text=text)])
    assert out == []


def test_the_same_words_from_four_outlets_are_one_quote_listing_the_others():
    """Live: the SSP's "When we reached here…" printed four times on his card."""
    [card] = group_claims([
        _src("toi", [_c("Gaurav Toora", TOORA)], published_at=T1, name="The Times of India"),
        _src("hindu", [_c("Gaurav Toora", TOORA)], published_at=T0, name="The Hindu"),
        _src("et", [_c("Gaurav Toora", TOORA)], published_at=T1, name="The Economic Times"),
        _src("dh", [_c("Gaurav Toora", TOORA + ".")], published_at=T1, name="Deccan Herald"),
    ])
    [row] = card.claims
    assert row.article_id == "hindu"  # the earliest report is the citation
    assert [a.source_name for a in row.also_in] == ["The Times of India", "The Economic Times", "Deccan Herald"]


def test_near_identical_words_are_one_quote_and_different_words_are_two():
    a = "We spoke to students who had some issues with the LPU administration. We heard them and are trying to get them resolved"
    b = "We spoke to the students who had some issues with the LPU administration. We heard them and are trying to get them resolved"
    c = "An assessment of the property damage is being done and necessary legal action will be taken"
    [card] = group_claims([
        _src("toi", [_c("Gaurav Toora", a), _c("Gaurav Toora", c)], name="The Times of India"),
        _src("dc", [_c("Gaurav Toora", b)], name="Deccan Chronicle", published_at=T1),
    ])
    assert sorted(len(r.also_in) for r in card.claims) == [0, 1]


def test_a_first_name_speaker_is_folded_into_the_full_name_on_the_same_record():
    """Live, event 8db8e742: "Saheb Singh" and "Saheb" were two speakers."""
    out = group_claims([
        _src("mint", [_c("Saheb Singh", "I was recording a video when he snatched my phone and raised his hand at me")]),
        _src("toi", [_c("Saheb", "The police were present right there, and all of this happened in their presence")]),
    ])
    assert [(g.speaker, len(g.claims)) for g in out] == [("Saheb Singh", 2)]


def test_a_name_two_speakers_could_share_folds_into_neither():
    out = group_claims([
        _src("a", [_c("Saheb Singh", "I was recording a video when he snatched my phone")]),
        _src("b", [_c("Jarnail Singh", "I peeled the road off like a carpet and showed it to him")]),
        _src("c", [_c("Singh", "We have lodged an FIR and action must be taken")]),
    ])
    assert sorted(g.speaker for g in out) == ["Jarnail Singh", "Saheb Singh", "Singh"]


def test_a_body_is_never_folded_into_a_longer_body():
    """Live window: the name rule alone put "Bank of India" under State Bank of
    India and "IIT-Bombay" under its Faculty Forum."""
    out = group_claims([
        _src("a", [_c("State Bank of India", "We have raised the lending rate by ten basis points")]),
        _src("b", [_c("Bank of India", "Our deposit rates will stay where they are for now")]),
        _src("c", [_c("IIT-Bombay Faculty Forum", "The faculty stands with the students on this matter")]),
        _src("d", [_c("IIT-Bombay", "We apologise for the statements in our earlier communication")]),
    ])
    assert sorted(g.speaker for g in out) == ["Bank of India", "IIT-Bombay", "IIT-Bombay Faculty Forum", "State Bank of India"]


def test_a_name_in_the_next_sentence_does_not_take_the_quote():
    """Live: "“The BJP wants to kill me. I may die anyday.” Union minister
    Sukanta Majumdar, however, attributed…" — Majumdar is named nearest, but in
    the reporter's next sentence; the words are Kunal Ghosh's."""
    quote = "The BJP wants to kill me. I may die anyday."
    text = (f"Kunal Ghosh later lodged a complaint at the police station and blamed the BJP. He argued, “{quote}” "
            "Union minister Sukanta Majumdar, however, attributed the incident to a factional feud.")
    out = group_claims([_src("dc", [_c("Kunal Ghosh", quote), _c("Sukanta Majumdar", quote)], clean_text=text)])
    assert [(g.speaker, len(g.claims)) for g in out] == [("Kunal Ghosh", 1)]


def test_a_quotes_address_is_its_words_not_its_position():
    """Share links were `<speaker>-<quote>` positions, so a newer report
    renumbered every link on the card. The address is now the words."""
    first = group_claims([_src("a1", [_c("Alice", "the words she said on Monday")])])
    later = group_claims([
        _src("a2", [_c("Alice", "a newer quote that now leads the card")], published_at=T1),
        _src("a1", [_c("Alice", "the words she said on Monday")]),
    ])
    old = first[0].claims[0].id
    assert later[0].claims[0].id != old  # the position now names another quote…
    assert [c.quote_text for c in later[0].claims if c.id == old] == ["the words she said on Monday"]  # …the id does not


def test_the_addresses_shared_before_the_rule_resolve_to_the_same_words():
    """/story/<id>/quote/<n> links already shared must not break: each old
    position maps to the row now holding its words, and a withdrawn quote maps
    to nothing (its page sends the reader to the story)."""
    from api.routes.events import quote_aliases

    text = (f"“We spoke to the students who had some issues.” DIG Naveen Singla said the girl had left "
            f"the hostel. “The matter will be investigated with forensic analysis.” Majithia wrote: “{MAJITHIA}”")
    rows = [_src("a1", [_c("Naveen Singla", "DIG Naveen Singla said the girl had left the hostel."),
                        _c("Naveen Singla", "The matter will be investigated with forensic analysis."),
                        _c("Gaurav Toora", "We spoke to the students who had some issues."),
                        _c("Gaurav Toora", MAJITHIA),
                        _c("Bikram Singh Majithia", MAJITHIA)], clean_text=text)]
    groups = group_claims(rows)
    by_text = {c.quote_text: c.id for g in groups for c in g.claims}
    # Unchecked, the card was: 0 Singla [narration, investigated], 1 Toora [spoke, Majithia's], 2 Majithia [his].
    assert quote_aliases(rows, groups) == {
        "0-1": by_text["The matter will be investigated with forensic analysis."],
        "1-0": by_text["We spoke to the students who had some issues."],
        # The link that printed Majithia's words under Toora now shows them under Majithia.
        "1-1": by_text[MAJITHIA],
        "2-0": by_text[MAJITHIA],
    }
