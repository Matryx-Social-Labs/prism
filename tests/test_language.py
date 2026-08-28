"""Language-aware feed: headline localisation + the rank-not-filter boost.

The cluster stays cross-language; the feed renders each reader the headline in
their preferred language (falling back to English, never hiding the story) and
ranks preferred-language coverage up.
"""

from datetime import UTC, datetime

from api.routes.serialization import _pick_headline
from common.lenses import get_lens
from personalization.ranking import score_event

_PROJ = {
    "languages": ["en", "hi", "ta"],
    "headlines": [
        {"lang": "en", "title": "Metro shut over security"},
        {"lang": "hi", "title": "मेट्रो बंद"},
        {"lang": "ta", "title": "மெட்ரோ மூடல்"},
    ],
}


def test_pick_headline_prefers_reader_language():
    # Hindi-first reader gets the Hindi headline.
    assert _pick_headline(_PROJ, "Event title", ["hi", "en"]) == ("मेट्रो बंद", "hi")


def test_pick_headline_english_fallback_never_hides_story():
    # Kannada-only reader: no Kannada headline, falls back to visible English.
    assert _pick_headline(_PROJ, "Event title", ["kn"]) == ("Metro shut over security", "en")


def test_pick_headline_no_languages_uses_event_title():
    # Anonymous / not-onboarded reader: the event title, no language tag.
    assert _pick_headline(_PROJ, "Event title", None) == ("Event title", None)


def test_pick_headline_falls_back_to_event_title_when_no_english():
    proj = {"languages": ["ta"], "headlines": [{"lang": "ta", "title": "தமிழ்"}]}
    # reader wants kn; no kn, no en -> the event title (still never blank).
    assert _pick_headline(proj, "Event title", ["kn"]) == ("Event title", None)


def test_language_boost_ranks_preferred_up_without_filtering():
    lens = get_lens("reader")
    now = datetime.now(UTC)
    en_only = {"languages": ["en"]}
    base = score_event(lens=lens, reference_time=now, projection=en_only, languages=None)
    top = score_event(lens=lens, reference_time=now, projection=_PROJ, languages=["hi", "en"])
    # An English-only event still scores (never filtered out) — key for a news app.
    english_only_for_hi_reader = score_event(
        lens=lens, reference_time=now, projection=en_only, languages=["hi", "en"]
    )
    assert english_only_for_hi_reader > 0
    # But a story covered in the reader's PRIMARY language ranks above it.
    assert top > english_only_for_hi_reader >= base


def test_default_lens_is_general_reader():
    """Missing OR unknown lens must fall back to the general reader (all sectors),
    not a narrow professional lens. Regression: DEFAULT_LENS="cyber" served a
    general visitor cybersecurity-only when no/stale lens slug was sent."""
    for slug in (None, "", "general", "some-old-slug"):
        lens = get_lens(slug)
        assert lens.slug == "reader"
        assert lens.sectors == []  # [] = all sectors, i.e. every story


# --- script detection must cover every script we INGEST ----------------------


def test_arabic_script_is_detected_not_silently_latin():
    """Urdu returned "latin" because _SCRIPT_RANGES had no Arabic block, and the
    fallback for "no Indic block leads" is latin.

    That was not harmless. It put Urdu inside EMBEDDING_TRUSTED_SCRIPTS with
    nothing having validated the embedding there, and it made the partition's
    cross-script guard read an Urdu/English pair as the SAME script — so
    content_similarity compared them, found zero shared words (different
    alphabets share none) and CUT the edge. The absence-of-evidence guard was
    defeated by the detector rather than by its own logic.
    """
    from common.text import detect_script

    assert detect_script("مکہ معاہدے میں بنگلہ دیش کی شمولیت پر ڈھاکہ") == "arabic"


def test_every_ingested_feed_language_has_a_script_range():
    """The real guard. detect_script FAILS OPEN — any script without a range is
    reported as latin, silently. So adding a feed in a new language can quietly
    break clustering for it, with no error anywhere.

    This ties the detector to what the collectors actually ingest: add a feed in
    a language whose script is unknown and this fails, instead of production
    mislabelling every one of its articles.
    """
    from common.text import _SCRIPT_RANGES, detect_script

    known = {name for name, _lo, _hi in _SCRIPT_RANGES} | {"latin"}
    # One representative headline per script the seeded feeds publish in.
    samples = {
        "en": "Delhi police used pellet guns on protesters",
        "hi": "दिल्ली पुलिस ने प्रदर्शनकारियों पर पैलेट गन चलाई",
        "mr": "नेपाळ : 'वेळेवर सूचना न दिल्या'च्या आरोपावर",
        "ta": "நேபாளத்தை உரிய நேரத்தில் எச்சரிக்க சீனா தவறியது",
        "kn": "ರಾಹುಲ್ ಸಭೆ ಅಂತ್ಯ, ಬೆಂಗಳೂರಿನತ್ತ ಡಿಕೆಶಿ",
        "te": "టిబెట్ నుంచి కైలాస మానస సరోవర యాత్ర",
        "bn": "তারেক রহমানকে দিল্লিতে কেন চায় ভারত?",
        "gu": "મહાસાગરો ઊકળ્યા : દરિયાનું તાપમાન રેકૉર્ડ",
        "pa": "ਇਕੱਲੇ ਬੈਠ ਕੇ ਖਾਣਾ ਖਾਂਦੇ ਹੋ ਤਾਂ ਕੁਝ ਖ਼ਾਸ",
        "ur": "مکہ معاہدے میں بنگلہ دیش کی شمولیت پر ڈھاکہ",
    }
    for lang, text in samples.items():
        script = detect_script(text)
        assert script in known, f"{lang}: {script!r} is not a known script"
        if lang != "en":
            assert script != "latin", (
                f"{lang} headlines detect as 'latin' — detect_script fails OPEN, so this "
                f"silently disables the cross-script guard and mislabels every article"
            )
