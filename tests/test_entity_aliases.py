"""Romanisation variants of one entity must resolve to one slug — and nothing else may.

Devanagari romanisation is not standardised, so जनता arrives as both "Janta" and
"Janata" and भारतीय as both "Bharatiya" and "Bhartiya". Both are correct, both
appear in Indian mastheads, and on production 2026-07-28 they were splitting the
cast of live trending stories into near-duplicate actors.

The risk in fixing it is over-merging, which this codebase has already paid for
once (fuzzy matching collapsed 1638 CVEs into 7). So the guard tests matter more
than the folding tests.
"""

import pytest

from common.entity_aliases import ENTITY_ALIASES, resolve_alias
from common.text import entity_slug


@pytest.mark.parametrize(
    "a,b",
    [
        ("Cockroach Janta Party", "Cockroach Janata Party"),
        ("Bharatiya Janta Party", "Bharatiya Janata Party"),
        ("Bhartiya Janata Party", "Bharatiya Janata Party"),
        ("E-20 Janta Party", "E20 Janta Party"),
        ("I20 Janta Party", "E20 Janata Party"),
        # the folding survives the punctuation rules it composes with
        ("Cockroach Janta Party (CJP)", "Cockroach Janata Party"),
    ],
)
def test_variants_resolve_to_one_entity(a, b):
    assert entity_slug(a) == entity_slug(b)


@pytest.mark.parametrize(
    "a,b",
    [
        ("Janta", "Janata"),                    # bare word: no rule, no fold
        ("NDTV", "NDRF"),
        ("CPI(M)", "CPI"),
        ("Hindu Mahasabha", "Hindustan Times"),
        ("Rahul Gandhi", "Rajiv Gandhi"),
        ("CVE-2026-11090", "CVE-2026-11109"),   # the 1638->7 shape
    ],
)
def test_distinct_entities_never_fold(a, b):
    assert entity_slug(a) != entity_slug(b)


def test_the_table_is_a_flat_map_not_a_chain():
    """A value that is itself a key would make resolution order-dependent, so one
    pass would leave some names on an intermediate spelling."""
    for canonical in set(ENTITY_ALIASES.values()):
        assert canonical not in ENTITY_ALIASES, f"{canonical} is both a variant and a target"


def test_every_canonical_target_is_stable_under_slugging():
    """A target that isn't already a valid slug would never be produced by
    entity_slug, so the alias would silently point at nothing."""
    for canonical in set(ENTITY_ALIASES.values()):
        assert resolve_alias(canonical) == canonical
        assert canonical == canonical.lower().strip("-")
        assert " " not in canonical
