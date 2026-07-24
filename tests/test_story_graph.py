"""Story-graph safeguards: the generic-entity stoplist.

Generic responders (NDRF, the Army, Fire & Emergency) appear across unrelated
disasters, so two events sharing ONLY these are not one story — a flood must not
link a tunnel collapse. IDF suppresses them at scale, but a small corpus gives
them a high 1/df, so the stoplist makes the rule explicit. It must stay NARROW:
specific bodies (Delhi Police) and investigative bodies (the ED) DO identify a
story and must not be stoplisted, or real stories (the CJP protest) fragment."""

from correlation.threads import STORY_STOP_ENTITIES


def test_generic_responders_are_stoplisted():
    # These linked the Assam flood to the Sikkim tunnel collapse on live data.
    for name in (
        "NDRF", "National Disaster Response Force",
        "SDRF", "State Disaster Response Force",
        "Army", "Indian Army", "Fire and Emergency Services",
    ):
        assert name in STORY_STOP_ENTITIES, f"{name} should be a story-graph stopword"


def test_discriminative_actors_are_not_stoplisted():
    # "Delhi Police" carries the CJP protest edge (df6); the ED is central to its own
    # cases; "Supreme Court" is a 'government' entity already excluded by type. Adding
    # any of these to the stoplist would fragment real stories.
    for name in ("Delhi Police", "Cockroach Janta Party", "Enforcement Directorate", "Supreme Court"):
        assert name not in STORY_STOP_ENTITIES, f"{name} must NOT be stoplisted (it identifies a story)"
