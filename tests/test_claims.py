"""The verbatim gate — the one check standing between the model and a libel.

A wrong story boundary shows a reader an unrelated card. A wrong attribution puts
words in a named person's mouth, and the reader has no way to tell: a fabricated
quote renders exactly like a real one. These tests pin the cases where a failure
still LOOKS like a working claim.
"""

from enrichment.claims import MIN_QUOTE_CHARS, check_quote, named_in, verify_claims
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
                   "not_quoted": 0, "not_named": 0, "narration": 0, "fragment": 0}


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
        why, quote, at, speech = check_quote(text, "We spoke to the students who had some issues.", "Gaurav Toora")
        assert why is None and speech == "direct", (opener, closer)
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
    why, quote, _, _ = check_quote(text, "“When one of his workers started shouting abuses at my family, I reacted.”", "Parvesh Verma")
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


# ── Reported speech, Indian-language articles only (founder decision, 28 Sep) ─
#
# Direct-only cost 55% of Indian-language claims against 16% of English ones:
# Hindi, Kannada, Malayalam and Odia outlets mostly print speech without
# quotation marks ("…ने कहा कि", "…ಎಂದು ಹೇಳಿದರು"). Such words are kept when the
# article attributes them with a speech verb in the language's own pattern and
# names the speaker, and they are served as "reported", never as a quote.
# Fixtures are shaped on live articles.

SAPKALE = "26 सितंबर तक इस वर्ष गणेशोत्सव के दौरान कुल 199185 गणेश प्रतिमाओं का विसर्जन हुआ है।"


def test_a_hindi_statement_after_x_ne_kaha_ki_is_reported_speech():
    text = f"मुंबई में 278 स्थानों पर तालाब बनाए गए थे। BMC के उपायुक्त प्रशांत सपकाले ने बताया कि {SAPKALE} उन्होंने बताया कि भक्तों ने इको-फ्रेंडली मूर्तियों को प्राथमिकता दी।"
    why, quote, at, speech = check_quote(text, SAPKALE, "Prashant Sapkale", lang="hi")
    assert (why, speech) == (None, "reported")
    assert " ".join(text.split())[at:at + len(quote)] == quote


def test_english_articles_stay_direct_speech_only():
    text = "Education minister Nityananda Gond said that schools in the flooded districts will stay shut for two more days."
    quote = "schools in the flooded districts will stay shut for two more days."
    assert check_quote(text, quote, "Nityananda Gond", lang="en")[0] == "not_quoted"
    assert check_quote(text, quote, "Nityananda Gond")[0] == "not_quoted"  # no language: no exception


def test_verb_final_languages_report_with_a_quotative_after_the_words():
    cases = [
        ("kn", "Sangappa", "ನಗರವನ್ನು ಸ್ವಚ್ಛ ಹಾಗೂ ವಾಸಯೋಗ್ಯವಾಗಿಡುವಲ್ಲಿ ಪೌರಕಾರ್ಮಿಕ ಪಾತ್ರ ಅತ್ಯಂತ ಮಹತ್ವದ್ದಾಗಿದೆ",
         "ಬಾಗಲಕೋಟೆ: {q} ಎಂದು ಜಿಲ್ಲಾಧಿಕಾರಿ ಸಂಗಪ್ಪ ಹೇಳಿದರು. ನಗರಸಭೆ ಸಭಾಭವನದಲ್ಲಿ ಕಾರ್ಯಕ್ರಮ ನಡೆಯಿತು."),
        ("ml", "A.V. Anandraj", "ശ്രീനാരായണഗുരുദേവനെ ആക്ഷേപിച്ചവർക്കെതിരേ ശക്തമായ നിയമനടപടികൾ സ്വീകരിക്കണമെന്ന്",
         "പ്രകടനം നടത്തി. {q} യൂണിയൻ ചെയർമാൻ ഡോ. എ.വി. ആനന്ദരാജ് ആവശ്യപ്പെട്ടു. യൂണിയൻ വൈസ് ചെയർമാൻ സംസാരിച്ചു."),
        ("ta", "Rohit Sharma", "என்னுடைய வேலை முடிந்துவிட்டது என்ற எண்ணம் ஒருபோதும் என்னுடைய மனதில் வரவில்லை",
         "உலகக் கோப்பையில் விளையாடுவது குறித்து ரோஹித் சர்மா பேசியதாவது: {q} என்றார். தொடர் அடுத்தாண்டு நடைபெறும்."),
        ("or", "Nityananda Gond", "ବର୍ଷାକୁ ଦୃଷ୍ଟିରେ ରଖି ଜିଲ୍ଲାପାଳମାନେ ଦୁଇ କିମ୍ବା ତିନି ଦିନ ସ୍କୁଲ ଛୁଟି କରିଥିଲେ।",
         "ଗଣଶିକ୍ଷା ମନ୍ତ୍ରୀ ନିତ୍ୟାନନ୍ଦ ଗଣ୍ଡ କହିଛନ୍ତି ଯେ {q} ମନ୍ତ୍ରୀ ସୁରେଶ ପୂଜାରୀ ସ୍ଥିତି ସମୀକ୍ଷା କରିଛନ୍ତି।"),
        ("ur", "Seema Malhotra", "فصلیں اگانے میں جراثیم کش ادویات کا استعمال کافی زیادہ ہو رہا ہے۔",
         "پروفیسر سیما ملہوترا کا کہنا ہے کہ {q} نوزائیدہ بچے کے لیے ماں کا دودھ محفوظ ہے۔"),
    ]
    for lang, speaker, q, shape in cases:
        why, _, _, speech = check_quote(shape.format(q=q), q, speaker, lang=lang)
        assert (why, speech) == (None, "reported"), lang


def test_a_pronoun_is_not_a_name():
    """"उन्होंने कहा कि" (he said that) with nobody named near it: the words may
    be anyone's, so they are not shown."""
    text = "छात्रों ने प्रदर्शन किया। उन्होंने कहा कि किताबों में इतनी बड़ी संख्या में गलतियां सामने आने के बाद जिम्मेदारी तय होनी चाहिए।"
    quote = "किताबों में इतनी बड़ी संख्या में गलतियां सामने आने के बाद जिम्मेदारी तय होनी चाहिए।"
    assert check_quote(text, quote, "Saurav Das", lang="hi")[0] == "not_named"


def test_the_speakers_own_name_inside_reported_words_is_narration():
    text = "डीआईजी नवीन सिंगला ने कहा कि छात्रा तीन दिन पहले अपने घर चली गई थी, डीआईजी नवीन सिंगला ने बताया।"
    quote = "छात्रा तीन दिन पहले अपने घर चली गई थी, डीआईजी नवीन सिंगला ने बताया।"
    assert check_quote(text, quote, "Naveen Singla", lang="hi")[0] == "narration"


def test_the_reporters_own_framing_inside_reported_words_is_narration():
    """Hand check of recovered claims, 28 Sep: the span ran past what was reported
    into the reporter's next sentence ("उन्होंने इसे … बताया है" — "he called it…")."""
    text = ("यूक्रेन के विदेश मंत्री एंड्री सिबिहा ने इन हमलों की निंदा की. उन्होंने X पर पोस्ट करते हुए कहा कि "
            "यह 'कोलेटरल डैमेज' यानी अनजाने में हुआ नुकसान नहीं है. उन्होंने इसे लोगों को निशाना बनाने की सुनियोजित कोशिश बताया है.")
    span = "यह 'कोलेटरल डैमेज' यानी अनजाने में हुआ नुकसान नहीं है. उन्होंने इसे लोगों को निशाना बनाने की सुनियोजित कोशिश बताया है."
    assert check_quote(text, span, "Andrii Sybiha", lang="hi")[0] == "narration"
    # The same report, stopped where the reporter's voice begins, is kept.
    why, _, _, speech = check_quote(text, "यह 'कोलेटरल डैमेज' यानी अनजाने में हुआ नुकसान नहीं है.", "Andrii Sybiha", lang="hi")
    assert (why, speech) == (None, "reported")
    # "…ಎಂದು ಆರೋಪಿಸಿದರು." copied into the words is the attribution, not the report.
    kn = "ರೈತ ಮುಖಂಡ ಬೊಕ್ಕಹಳ್ಳಿ ನಂಜುಂಡಸ್ವಾಮಿ ಮಾತನಾಡಿ, ಕಾರ್ಖಾನೆ ಲಿಖಿತ ಭರವಸೆ ಕೊಟ್ಟಿತ್ತು. ಆದರೆ ಈಡೇರಿಸದೇ ನಿರ್ಲಕ್ಷ್ಯ ವಹಿಸಿದೆ ಎಂದು ಆರೋಪಿಸಿದರು. ಸಂಧಾನ ನಡೆಯಿತು."
    kspan = "ಕಾರ್ಖಾನೆ ಲಿಖಿತ ಭರವಸೆ ಕೊಟ್ಟಿತ್ತು. ಆದರೆ ಈಡೇರಿಸದೇ ನಿರ್ಲಕ್ಷ್ಯ ವಹಿಸಿದೆ ಎಂದು ಆರೋಪಿಸಿದರು."
    assert check_quote(kn, kspan, "Bokkahalli Nanjundaswamy", lang="kn")[0] == "narration"


def test_a_quotative_without_a_speech_verb_is_not_speech():
    """"…ಎಂದು ಶಂಕಿಸಲಾಗಿದೆ" — "it is suspected that…" — names nobody's words."""
    text = "ಎಸ್‌ಪಿ ಅನಿತಾ ಹದ್ದಣ್ಣವರ ಸ್ಥಳಕ್ಕೆ ಭೇಟಿ ನೀಡಿದರು. ಅಪಘಾತಕ್ಕೆ ಲಾರಿ ಚಾಲಕನ ಅತಿವೇಗವೇ ಕಾರಣ ಎಂದು ಶಂಕಿಸಲಾಗಿದೆ."
    assert check_quote(text, "ಅಪಘಾತಕ್ಕೆ ಲಾರಿ ಚಾಲಕನ ಅತಿವೇಗವೇ ಕಾರಣ", "Anita Haddannavar", lang="kn")[0] == "not_quoted"


def test_a_speech_verb_in_the_next_sentence_does_not_attribute_the_words():
    text = "ಬೆಳೆ ಹಾನಿ ಪರಿಹಾರ ಇನ್ನೂ ರೈತರಿಗೆ ತಲುಪಿಲ್ಲ ಎಂದು ವರದಿಯಾಗಿದೆ. ಶಾಸಕ ಕೆ. ವೆಂಕಟೇಶ್ ಸಭೆಯಲ್ಲಿ ಹೇಳಿದರು."
    assert check_quote(text, "ಬೆಳೆ ಹಾನಿ ಪರಿಹಾರ ಇನ್ನೂ ರೈತರಿಗೆ ತಲುಪಿಲ್ಲ", "K. Venkatesh", lang="kn")[0] == "not_quoted"


def test_quoted_words_in_an_indian_language_article_stay_direct():
    text = 'पत्रकारों से बात करते हुए उन्होंने कहा, "यह फैसला गलत है और हम इसका विरोध करेंगे।" इसके बाद वे चले गए।'
    why, _, _, speech = check_quote(text, "यह फैसला गलत है और हम इसका विरोध करेंगे।", "Akhilesh Yadav", lang="hi")
    assert (why, speech) == (None, "direct")


def test_reported_words_keep_the_fragment_floor():
    text = "BMC के उपायुक्त प्रशांत सपकाले ने बताया कि विसर्जन पूरा हुआ। उन्होंने बताया कि भक्त खुश थे।"
    assert check_quote(text, "विसर्जन पूरा हुआ।", "Prashant Sapkale", lang="hi")[0] == "fragment"


def test_the_write_time_gate_keeps_reported_speech_only_for_an_indian_language():
    text = f"BMC के उपायुक्त प्रशांत सपकाले ने बताया कि {SAPKALE} उन्होंने बताया कि भक्त खुश थे।"
    kept, _ = verify_claims([claim(speaker="Prashant Sapkale", quote_text=SAPKALE)], text, lang="hi")
    assert [c.quote_text for c in kept] == [SAPKALE]
    kept, why = verify_claims([claim(speaker="Prashant Sapkale", quote_text=SAPKALE)], text)
    assert kept == [] and why["not_quoted"] == 1


def test_an_english_name_is_found_in_the_articles_own_script():
    """Speaker names are canonicalised to English by the extractor; the article
    prints them in its script. Consonant skeletons compare the two."""
    assert named_in("Naveen Singla", "डीआईजी नवीन सिंगला ने कहा")
    assert named_in("H.C. Balakrishna", "ಎಂದು ಶಾಸಕ ಎಚ್.ಸಿ. ಬಾಲಕೃಷ್ಣ ಹೇಳಿದರು")
    assert named_in("M.K. Stalin", "முதல்வர் மு.க.ஸ்டாலின் தெரிவித்தார்")
    assert named_in("Pinarayi Vijayan", "മുഖ്യമന്ത്രി പിണറായി വിജയൻ പറഞ്ഞു")
    assert named_in("Imran Khan", "عمران خان نے کہا")
    assert named_in("Siddaramaiah", "ಮುಖ್ಯಮಂತ್ರಿ ಸಿದ್ದರಾಮಯ್ಯನವರು ಹೇಳಿದರು")  # a case suffix on the name
    assert not named_in("Naveen Singla", "एसएसपी गौरव तूरा ने बताया")
    assert not named_in("Rao", "राव ने कहा")  # one consonant proves nothing
