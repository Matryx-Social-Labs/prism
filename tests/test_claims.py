"""The verbatim gate — the one check standing between the model and a libel.

A wrong story boundary shows a reader an unrelated card. A wrong attribution puts
words in a named person's mouth, and the reader has no way to tell: a fabricated
quote renders exactly like a real one. These tests pin the cases where a failure
still LOOKS like a working claim.
"""

from enrichment.claims import MIN_QUOTE_CHARS, check_quote, verify_claims
from enrichment.schemas import Claim

ARTICLE = (
    "Speaking in Bengaluru on Tuesday, the minister said the state would "
    "\u201cdouble its outlay on rural roads before the monsoon\u201d.\n\n"
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
    assert why == {"no_speaker": 1, "short_quote": 0, "not_verbatim": 1,
                   "not_quoted": 0, "narration": 0, "fragment": 0}


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


def test_a_bracketed_role_is_dropped_and_an_essay_is_cut_to_its_title():
    kept, _ = verify_claims([claim(speaker_role="minister (state)")], ARTICLE)
    assert kept[0].speaker_role is None
    long = "the minister who said the state would double its outlay on rural roads before the monsoon"
    kept, _ = verify_claims([claim(speaker_role=long)], ARTICLE)
    assert kept[0].speaker_role == "minister"
    # An essay with no clause to cut at is dropped whole.
    kept, _ = verify_claims([claim(speaker_role="minister of the state's outlay on rural roads before the monsoon season began")], ARTICLE)
    assert kept[0].speaker_role is None


def test_a_trailing_acronym_is_the_articles_shorthand_not_a_composition():
    kept, _ = verify_claims([claim(speaker_role="minister (MIN)")], ARTICLE)
    assert kept[0].speaker_role == "minister"


def test_an_office_spelled_out_holds_against_an_article_that_abbreviated_it():
    """The press writes "Karnataka CM"; the role is asked for in full so the
    card can say whose Chief Minister. Expansion on both sides keeps the
    verbatim rule honest without rejecting every spelled-out office."""
    article = "Bengaluru: Karnataka CM Siddaramaiah said the state would \"double its outlay on rural roads before the monsoon\"."
    kept, _ = verify_claims([claim(speaker="Siddaramaiah", speaker_role="Karnataka Chief Minister")], article)
    assert kept[0].speaker_role == "Karnataka Chief Minister"
    # …but the state still has to be the article's, not the model's.
    kept, _ = verify_claims([claim(speaker="Siddaramaiah", speaker_role="Kerala Chief Minister")], article)
    assert kept[0].speaker_role is None


def test_a_paraphrased_tail_is_cut_and_the_true_head_kept():
    kept, _ = verify_claims([claim(speaker_role="minister belonging to the coalition's rural wing")], ARTICLE)
    assert kept[0].speaker_role == "minister"


def test_a_role_on_a_kannada_report_stands_when_its_own_script_is_in_the_article():
    article = "ಬೆಂಗಳೂರು: ಗೃಹ ಸಚಿವ ಪ್ರಿಯಾಂಕ್ ಖರ್ಗೆ ಅವರು ಹೇಳಿದರು, \u2018ರಾಜ್ಯವು ಗ್ರಾಮೀಣ ರಸ್ತೆಗಳ ವೆಚ್ಚವನ್ನು ದ್ವಿಗುಣಗೊಳಿಸಲಿದೆ\u2019 ಎಂದು."
    quote = "ರಾಜ್ಯವು ಗ್ರಾಮೀಣ ರಸ್ತೆಗಳ ವೆಚ್ಚವನ್ನು ದ್ವಿಗುಣಗೊಳಿಸಲಿದೆ"
    kept, _ = verify_claims([claim(speaker="Priyank Kharge", quote_text=quote, speaker_role="Home Minister", speaker_role_native="ಗೃಹ ಸಚಿವ")], article)
    assert kept[0].speaker_role == "Home Minister"
    # A native copy the article does not contain proves nothing.
    kept, _ = verify_claims([claim(speaker="Priyank Kharge", quote_text=quote, speaker_role="Home Minister", speaker_role_native="ಮುಖ್ಯಮಂತ್ರಿ")], article)
    assert kept[0].speaker_role is None


# ── Direct speech only (founder decision, 27 Sep 2026) ───────────────────────
#
# The verbatim check proves the words are in the ARTICLE, not that the speaker
# said them: live records showed a reporter's sentence ("…, DIG Jalandhar Range
# Naveen Singla said on…") printed as Singla's quote. A quote is now shown only
# if the article itself prints those words inside quotation marks.

def test_reported_speech_is_not_a_quote():
    """The live LPU record: narration naming the speaker, no quotation marks."""
    text = ("Punjab news. A girl student staying at LPU's G-3 hostel was allegedly raped three days ago, "
            "DIG Jalandhar Range Naveen Singla said on Saturday.")
    quote = "A girl student staying at LPU's G-3 hostel was allegedly raped three days ago, DIG Jalandhar Range Naveen Singla said on"
    assert check_quote(text, quote, "Naveen Singla")[0] == "not_quoted"
    # …and the write-time gate refuses it for the same reason.
    kept, why = verify_claims([claim(speaker="Naveen Singla", quote_text=quote)], text)
    assert kept == [] and why["not_quoted"] == 1


def test_words_inside_quotation_marks_are_a_quote_in_every_style_outlets_use():
    for opener, closer in [("“", "”"), ('"', '"'), ("‘", "’"), ("'", "'"),
                           ("‘‘", "’’"), ("«", "»")]:
        text = f"Earlier, SSP Gaurav Toora said: {opener}We spoke to the students who had some issues.{closer} Traffic resumed."
        why, quote, at = check_quote(text, "We spoke to the students who had some issues.", "Gaurav Toora")
        assert why is None, (opener, closer)
        assert " ".join(text.split())[at:at + len(quote)] == quote


def test_a_contiguous_part_of_a_longer_quotation_is_still_a_quote():
    text = "He said, “The situation is under control. We spoke to students who had some issues. Action will follow.”"
    assert check_quote(text, "We spoke to students who had some issues.", "Toora")[0] is None


def test_a_span_that_leaves_the_quotation_is_not_a_quote():
    """Two quoted halves stitched across the reporter's own words."""
    text = "“We will act,” he said on Sunday, “and we will act within the week.”"
    assert check_quote(text, "We will act,” he said on Sunday, “and we will act", "Toora")[0] == "not_quoted"


def test_the_reporters_sentence_between_two_quotes_is_not_a_quote():
    text = ("“We spoke to the students,” the SSP said. The police then cleared the national highway "
            "by noon. “The situation is under control,” he added.")
    assert check_quote(text, "The police then cleared the national highway by noon.", "Toora")[0] == "not_quoted"


def test_a_list_of_quoted_words_is_a_fragment_not_a_statement():
    """Live: `"false", "baseless" and "fabricated` shown as the registrar's quote."""
    text = 'with Registrar Monica Gulati saying elements were spreading "false", "baseless" and "fabricated" allegations.'
    assert check_quote(text, 'false", "baseless" and "fabricated', "Monica Gulati")[0] == "not_quoted"
    # The same list inside one pair of marks is still only a list.
    text = 'The registrar called the reports "false, baseless and fabricated" on Sunday.'
    assert check_quote(text, "false, baseless and fabricated", "Monica Gulati")[0] == "fragment"


def test_three_words_are_too_few_to_be_a_statement():
    text = "The minister said, “Unconstitutional, arbitrary, unacceptable.”"
    assert check_quote(text, "Unconstitutional, arbitrary, unacceptable.", "The minister")[0] == "fragment"


def test_the_reporters_attribution_inside_the_marks_is_narration():
    """A quoted press note that narrates the speaker is not the speaker's words."""
    text = "The release read: “The matter is under investigation, Naveen Singla said on Saturday.”"
    assert check_quote(text, "The matter is under investigation, Naveen Singla said on Saturday.", "Naveen Singla")[0] == "narration"


def test_a_speaker_quoting_someone_else_is_still_their_quote():
    """Measured on the live window: "He had told us…", "according to the 2022
    census…" are real words inside real quotes (14 of 15 pronoun or "according
    to" hits); only the speaker's own name beside a speech verb marks the
    reporter's voice."""
    text = "His father said, “He had told us that he repeatedly faced caste discrimination at the institute.”"
    assert check_quote(text, "He had told us that he repeatedly faced caste discrimination at the institute.", "Ravindra Wakode")[0] is None


def test_the_models_own_copy_of_the_quotation_marks_is_trimmed():
    text = "On the other hand, Verma said: “When one of his workers started shouting abuses at my family, I reacted.”"
    why, quote, _ = check_quote(text, "“When one of his workers started shouting abuses at my family, I reacted.”", "Parvesh Verma")
    assert why is None
    assert quote == "When one of his workers started shouting abuses at my family, I reacted."


def test_a_title_quoted_inside_the_quote_does_not_end_it():
    text = "उन्होंने कहा, 'मुझे 'रामायणम्' में कास्ट नहीं किया गया और मैं खुश हूं।' अभिषेक"
    assert check_quote(text, "मुझे 'रामायणम्' में कास्ट नहीं किया गया और मैं खुश हूं।", "Dev Sharma")[0] is None


def test_an_apostrophe_is_not_a_quotation_mark():
    text = "The VC said, ‘The university doesn’t know about any such incident at LPU’s hostel.’"
    assert check_quote(text, "The university doesn’t know about any such incident at LPU’s hostel.", "Jaspal Singh")[0] is None


def test_an_unclosed_quote_does_not_run_into_the_next_paragraph():
    """Scraped text loses closing marks. A paragraph break ends the damage, so
    the reporter's next paragraph is not read as the speaker's words."""
    text = "He said, “We will look into it.\n\nThe district collector later visited the relief camps in the area."
    assert check_quote(text, "The district collector later visited the relief camps in the area.", "Collector")[0] == "not_quoted"


def test_a_quote_the_article_no_longer_contains_is_not_shown():
    assert check_quote("Nothing here matches at all.", "We will reopen the bridge on Monday.", "X")[0] == "not_verbatim"
