"""The verbatim gate — the one check standing between the model and a libel.

A wrong story boundary shows a reader an unrelated card. A wrong attribution puts
words in a named person's mouth, and the reader has no way to tell: a fabricated
quote renders exactly like a real one. These tests pin the cases where a failure
still LOOKS like a working claim.
"""

from enrichment.claims import MIN_QUOTE_CHARS, verify_claims
from enrichment.schemas import Claim

ARTICLE = (
    "Speaking in Bengaluru on Tuesday, the minister said the state would "
    "double its outlay on rural roads before the monsoon.\n\n"
    "Opposition leaders disputed the figure, calling it optimistic."
)


def claim(**kw) -> Claim:
    base = dict(speaker="The minister",
                quote_text="double its outlay on rural roads before the monsoon")
    return Claim(**{**base, **kw})


def test_a_quote_the_article_never_contained_is_rejected():
    """The failure this module exists for. Nothing about a fabricated quote looks
    wrong downstream — it renders identically to a real one."""
    kept, why = verify_claims([claim(quote_text="triple its outlay on rural roads")], ARTICLE)
    assert kept == [] and why["not_verbatim"] == 1


def test_a_real_quote_survives_and_its_span_points_at_the_words():
    kept, _ = verify_claims([claim()], ARTICLE)
    assert len(kept) == 1
    c = kept[0]
    flat = " ".join(ARTICLE.split())
    assert flat[c.quote_start:c.quote_end] == c.quote_text


def test_wrong_offsets_do_not_lose_a_correct_quote():
    """Models copy sentences reliably and count characters badly. Rejecting a real
    quote over arithmetic would discard good evidence for a bad reason, so the
    quote is the claim and the span is recomputed from it."""
    kept, _ = verify_claims([claim(quote_start=9999, quote_end=10042)], ARTICLE)
    assert len(kept) == 1
    flat = " ".join(ARTICLE.split())
    assert flat[kept[0].quote_start:kept[0].quote_end] == kept[0].quote_text


def test_a_newline_inside_the_quote_still_matches():
    """Extraction collapses newlines inside quotations constantly. That is an
    artefact of the surrounding markup, not a change to what was said."""
    kept, _ = verify_claims(
        [claim(quote_text="double its outlay on rural\n   roads before the monsoon")], ARTICLE)
    assert len(kept) == 1


def test_case_is_NOT_normalised_away():
    """Whitespace is a transcription artefact; capitalisation is a word. Folding
    case would let a near-quote pass as a quote, which is the whole thing being
    guarded against."""
    kept, why = verify_claims(
        [claim(quote_text="DOUBLE ITS OUTLAY ON RURAL ROADS BEFORE THE MONSOON")], ARTICLE)
    assert kept == [] and why["not_verbatim"] == 1


def test_a_claim_with_no_speaker_is_not_a_claim():
    """Unattributed text is what the perspectives layer cannot use: "what has this
    person said across this story" needs a person."""
    kept, why = verify_claims([claim(speaker="  ")], ARTICLE)
    assert kept == [] and why["no_speaker"] == 1


def test_a_fragment_too_short_to_be_evidence_is_rejected():
    """"Yes" or a bare name matches almost any article by accident, so a span for
    it proves nothing about who said what."""
    short = "double its outlay"
    assert len(short) < MIN_QUOTE_CHARS
    kept, why = verify_claims([claim(quote_text=short)], ARTICLE)
    assert kept == [] and why["short_quote"] == 1


def test_an_empty_article_keeps_nothing_rather_than_everything():
    """A fulltext fetch can fail. With no text there is nothing to verify against,
    and admitting the claims would mean trusting the model exactly where the
    evidence is missing — the absence-of-evidence trap this repo keeps hitting."""
    assert verify_claims([claim()], "")[0] == []


def test_the_rejection_reasons_are_counted_not_swallowed():
    """Extraction quality has to be measurable without re-reading articles."""
    kept, why = verify_claims(
        [claim(), claim(quote_text="a quote that is nowhere in this article at all"),
         claim(speaker="")], ARTICLE)
    assert len(kept) == 1
    assert why == {"no_speaker": 1, "short_quote": 0, "not_verbatim": 1}


def test_a_role_the_article_never_stated_is_dropped_not_printed():
    """Asked for the role EXACTLY as the article gives it, the model still adds
    what it knows ('Agriculture Minister (Andhra Pradesh)', 'Vice President of
    the United States' on an article that says neither). Unverifiable → null:
    no role is better than a plausible one."""
    kept, _ = verify_claims([claim(speaker_role="Karnataka Minister for Rural Development")], ARTICLE)
    assert kept[0].speaker_role is None


def test_a_role_in_the_articles_own_words_survives():
    kept, _ = verify_claims([claim(speaker_role="the minister")], ARTICLE)
    assert kept[0].speaker_role == "minister"


def test_a_composed_or_essay_role_is_dropped_even_if_every_word_appears():
    kept, _ = verify_claims([claim(speaker_role="minister (state)")], ARTICLE)
    assert kept[0].speaker_role is None
    long = "the minister who said the state would double its outlay on rural roads before the monsoon"
    kept, _ = verify_claims([claim(speaker_role=long)], ARTICLE)
    assert kept[0].speaker_role is None


def test_a_trailing_acronym_is_the_articles_shorthand_not_a_composition():
    kept, _ = verify_claims([claim(speaker_role="minister (MIN)")], ARTICLE)
    assert kept[0].speaker_role == "minister"
