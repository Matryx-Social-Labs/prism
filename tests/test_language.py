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
