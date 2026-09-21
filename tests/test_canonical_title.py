"""The canonical title is Prism's headline when there is one, labelled as ours."""

from correlation.consumer import canonical_title


def test_prism_headline_becomes_the_title_and_is_marked():
    assert canonical_title({"headline": "  Cabinet expansion delayed again  "}, "outlet words") == ("Cabinet expansion delayed again", "prism")


def test_without_a_headline_the_outlet_words_stay_unmarked():
    assert canonical_title({}, "outlet words") == ("outlet words", None)
    assert canonical_title({"headline": "   "}, "outlet words") == ("outlet words", None)


def test_a_headline_the_extractor_echoed_in_another_script_is_not_prisms():
    """The prompt asks for English; the model sometimes copies the Hindi source
    title into the field (BBC Hindi, 2026-09-21). That title is the outlet's,
    unmarked — never labelled 'Headline by Prism', never the cross-language
    tier's query."""
    from correlation.consumer import english_headline

    hindi = "जिन्होंने एआई बनाया क्या अब वो उनके क़ाबू से भी बाहर हो जाएगा?"
    assert canonical_title({"headline": hindi}, hindi) == (hindi, None)
    assert english_headline({"headline": hindi}) is None
    assert english_headline({"headline": "AI pioneers warn the systems may escape their makers’ control"}) == "AI pioneers warn the systems may escape their makers’ control"
    # A Latin headline quoting one Indic word is still English.
    assert english_headline({"headline": "Court reads ‘न्याय’ into the order"}) is not None


def test_the_backfill_refuses_a_non_english_answer_and_repairs_the_written_ones():
    from tools.backfill_headlines import acceptable, needs_headline

    assert acceptable("Cabinet expansion delayed again")
    assert not acceptable("ईरान पर हमले की अमेरिका ने अब तक क्या कीमत चुकाई है")
    assert needs_headline("ईरान पर हमले की अमेरिका ने अब तक क्या कीमत चुकाई है", "prism")
    assert not needs_headline("Cabinet expansion delayed again", "prism")
    assert needs_headline("Cabinet expansion delayed again", None)
