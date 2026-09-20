"""Where an event is placed. State codes used to come only from a state-edition
feed, so a national outlet's report on Bengaluru carried `IN` alone and
"Karnataka" on Today was really "Karnataka outlets". The classifier now places
the event from the article; these pin that the codes it writes are real."""

from classification.schemas import ClassificationResult


def test_a_real_state_code_from_the_article_survives():
    r = ClassificationResult(sector="politics", regions=["IN", "in-ka"])
    assert r.regions == ["IN", "IN-KA"]


def test_an_invented_state_code_is_dropped_not_stored():
    # The model writes city or old-style codes; none of these is a state we can tier on.
    r = ClassificationResult(sector="politics", regions=["IN", "IN-BLR", "IN-BOM", "IN-KAR", "IN_KA"])
    assert r.regions == ["IN", "IN-KA"]


def test_duplicates_collapse():
    r = ClassificationResult(sector="politics", regions=["IN", "IN", "IN-KA", "IN-KA"])
    assert r.regions == ["IN", "IN-KA"]


def test_a_feeds_state_stamp_yields_to_the_article():
    """Prajavani (whole-site, IN-KA) printed the US Russia-sanctions bill; the
    stamp filed it under Karnataka. The stamp holds only for an article about
    India with no state of its own."""
    from classification.consumer import feed_state_applies

    assert feed_state_applies([]) is True
    assert feed_state_applies(["IN"]) is True
    assert feed_state_applies(["US", "RU", "IN", "CN"]) is False, "a foreign story is not local to the feed's state"
    assert feed_state_applies(["IN", "IN-MH"]) is False, "the classifier already placed it"
