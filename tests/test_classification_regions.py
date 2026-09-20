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
