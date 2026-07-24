"""Entity identity folding: punctuation variants merge, distinct entities don't.

The story cast/graph is only as good as entity identity — 'Cockroach Janta Party (CJP)',
'Cockroach Janta Party' and the DK/D.K. pair were three rows each, splitting the signal.
entity_slug folds the safe punctuation variants WITHOUT fuzzy edit-distance (which once
over-merged 1638 CVEs into 7 — CVE-2026-11090 and -11109 differ by one char but are
distinct vulnerabilities)."""

from common.text import canonical_entity_name, entity_slug


def test_punctuation_and_acronym_variants_fold():
    assert entity_slug("D.K. Shivakumar") == entity_slug("DK Shivakumar")
    assert entity_slug("J.P. Nadda") == entity_slug("JP Nadda")
    assert entity_slug("U.S. Treasury") == entity_slug("US Treasury")
    # trailing "(ACRONYM)" that is the initials of the preceding words is dropped
    assert entity_slug("Cockroach Janta Party (CJP)") == entity_slug("Cockroach Janta Party")
    assert entity_slug("Enforcement Directorate (ED)") == entity_slug("Enforcement Directorate")


def test_distinct_entities_do_not_merge():
    # meaningful parenthetical (not an acronym of the head) is kept
    assert entity_slug("CPI(M)") != entity_slug("CPI")
    # spelling variants are NOT fuzzed together (needs judgement, not a rule)
    assert entity_slug("Cockroach Janta Party") != entity_slug("Cockroach Janata Party")
    # distinct acronyms/orgs stay distinct
    assert entity_slug("NDRF") != entity_slug("NDMA")
    assert entity_slug("Delhi Police") != entity_slug("Delhi Metro")


def test_canonical_is_idempotent():
    for name in ("D.K. Shivakumar", "Cockroach Janta Party (CJP)", "CPI(M)", "Plain Name"):
        assert canonical_entity_name(canonical_entity_name(name)) == canonical_entity_name(name)
