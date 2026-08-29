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
    # Spelling variants are still NOT fuzzed by any RULE — which is what this
    # assertion has always been guarding. It used to demonstrate that with
    # "Cockroach Janta/Janata Party"; that pair has since been listed in
    # common/entity_aliases, because the same comment's own standard — judgement,
    # not a rule — is exactly what a curated table is. The mechanism is unchanged,
    # so the example moves to a pair nobody has ruled on.
    assert entity_slug("Janta") != entity_slug("Janata")
    assert entity_slug("Samyukta Morcha") != entity_slug("Samyukt Morcha")
    # distinct acronyms/orgs stay distinct
    assert entity_slug("NDRF") != entity_slug("NDMA")
    assert entity_slug("Delhi Police") != entity_slug("Delhi Metro")


def test_a_listed_variant_folds_only_because_it_is_listed():
    """The counterpart to the above: the table is the ONLY thing that folds a
    spelling variant, so removing an entry must un-fold that pair."""
    from common.entity_aliases import ENTITY_ALIASES

    assert entity_slug("Cockroach Janta Party") == entity_slug("Cockroach Janata Party")
    assert "cockroach-janta-party" in ENTITY_ALIASES


def test_dominant_acronyms_fold_into_their_expansion():
    """Outlets mix "BJP" and "Bharatiya Janata Party" freely, often inside one
    article. Left unfolded they are two entities each carrying half the document
    frequency, so the matcher's 1/df weighting scores a national fixture as twice
    as distinctive as it really is."""
    assert entity_slug("BJP") == entity_slug("Bharatiya Janata Party")
    assert entity_slug("CJP") == entity_slug("Cockroach Janata Party")
    assert entity_slug("DMK") == entity_slug("Dravida Munnetra Kazhagam")


def test_ambiguous_acronyms_are_not_folded():
    """The counterpart, and the whole reason this stays a hand-curated table rather
    than an initialism rule. In this corpus "BRS" initialises both Bharat Rashtra
    Samithi and the Boston Red Sox; deriving the fold would merge a Telangana party
    into a baseball team, and nothing downstream could recover from that."""
    from common.entity_aliases import ENTITY_ALIASES

    assert "brs" not in ENTITY_ALIASES
    assert entity_slug("BRS") != entity_slug("Boston Red Sox")
    assert entity_slug("BRS") != entity_slug("Bharat Rashtra Samithi")


def test_singular_plural_org_variants_fold():
    assert entity_slug("All India Student Federation") == entity_slug("All India Students Federation")
    assert entity_slug("Student Federation of India") == entity_slug("Students Federation of India")


def test_canonical_is_idempotent():
    for name in ("D.K. Shivakumar", "Cockroach Janta Party (CJP)", "CPI(M)", "Plain Name"):
        assert canonical_entity_name(canonical_entity_name(name)) == canonical_entity_name(name)


# --- non-Latin names must stay DISTINCT ---------------------------------------
# slugify was `[^a-z0-9]+`, which deleted every non-ASCII character instead of
# transliterating it. Every Indic or Urdu name therefore slugged to the empty
# string and fell through to the SAME fallback, silently merging unrelated people
# into one entity with an enormous document frequency. Nine Indian-language feeds
# now ingest, so this is armed the moment extraction emits a native-script name.

NATIVE = {
    "hindi": "भारतीय जनता पार्टी",
    "kannada": "ನರೇಂದ್ರ ಮೋದಿ",
    "bengali": "নরেন্দ্র মোদী",
    "urdu": "نریندر مودی",
    "tamil": "நரேந்திர மோடி",
    "telugu": "నరేంద్ర మోదీ",
    "gujarati": "નરેન્દ્ર મોદી",
    "punjabi": "ਨਰਿੰਦਰ ਮੋਦੀ",
}


def test_native_script_names_do_not_collapse_to_one_slug():
    slugs = {lang: entity_slug(name) for lang, name in NATIVE.items()}
    assert len(set(slugs.values())) == len(NATIVE), f"names collided: {slugs}"
    assert "unknown" not in slugs.values(), f"a real name slugged to the fallback: {slugs}"


def test_a_native_script_name_survives_slugging():
    """Not merely 'not unknown' — the characters must actually be there. An empty
    result would also pass a distinctness check if the fallback were per-input."""
    assert entity_slug("ನರೇಂದ್ರ ಮೋದಿ") == "ನರೇಂದ್ರ-ಮೋದಿ"


def test_indic_vowel_signs_are_kept_not_stripped_as_accents():
    """A Devanagari matra is a letter, not a diacritic. Folding combining marks
    the way we fold Latin accents would rewrite the name into a different one."""
    assert entity_slug("मोदी") != entity_slug("मद")
    assert "ी" in entity_slug("मोदी")


def test_latin_diacritics_fold_rather_than_vanish():
    """The old rule DELETED the accented letter, so 'Ávila' became 'vila' — a
    wrong slug rather than a visibly broken one."""
    assert entity_slug("Ávila") == entity_slug("Avila") == "avila"
    assert entity_slug("Beyoncé") == entity_slug("Beyonce")


def test_story_slugs_stay_ascii_while_entity_slugs_do_not():
    """Same normaliser, two jobs. An entity slug is an IDENTITY and must keep its
    script; a story slug is a shareable URL and must not become percent-encoded
    line noise. A fully non-Latin label degrades to the `story-<id>` fallback."""
    import uuid

    from correlation.trending import story_slug

    sid = uuid.UUID(int=0)
    assert story_slug("दिल्ली में प्रदर्शन", sid) == "story-000000"
    assert story_slug("Delhi protest", sid) == "delhi-protest-000000"
    assert story_slug("Ávila verdict", sid) == "avila-verdict-000000"
    # The entity path keeps what the URL path drops — that contrast is the point.
    assert entity_slug("दिल्ली") == "दिल्ली"
