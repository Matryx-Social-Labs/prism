"""Curated spelling variants that resolve to one entity.

`canonical_entity_name` folds punctuation and nothing else, on purpose: fuzzy
edit-distance once merged 1638 CVEs into 7, and CVE-2026-11090 and -11109 differ
by one character while being entirely different vulnerabilities. So variants that
need JUDGEMENT get listed here by hand rather than inferred.

What lives here is a real, systematic class rather than typos: Devanagari
romanisation is not standardised, so जनता reaches us as both "Janta" and
"Janata", and भारतीय as "Bharatiya" and "Bhartiya". Both spellings are correct
and both appear in Indian mastheads, which is why an outlet-agnostic feed sees
both for the same party. Measured on production 2026-07-28, these variants were
splitting the cast of live trending stories.

Deliberately NOT a transliteration rule. Schwa deletion is regular enough to
tempt one, but "Janta"->"Janata" generalises to collapsing any optional interior
'a', which would merge distinct names. A list is auditable; a rule is a future
incident.

Keys and values are SLUGS (post-slugify), so matching is already
punctuation-folded. Add a pair only when you have seen both forms refer to the
same entity in real coverage.
"""

# variant slug -> canonical slug
ENTITY_ALIASES: dict[str, str] = {
    # जनता — the single most common romanisation split in Indian party names.
    "cockroach-janta-party": "cockroach-janata-party",
    "bharatiya-janta-party": "bharatiya-janata-party",
    "bhartiya-janata-party": "bharatiya-janata-party",
    "bhartiya-janta-party": "bharatiya-janata-party",
    # The same party with a model-number prefix, hyphenated or not. E20 and I20
    # are both attested; the leading letter is not reliably extracted.
    "e-20-janta-party": "e20-janata-party",
    "e20-janta-party": "e20-janata-party",
    "e-20-janata-party": "e20-janata-party",
    "i20-janta-party": "e20-janata-party",
    "i-20-janta-party": "e20-janata-party",
    # Acronyms outlets use interchangeably with the full name, often inside one
    # article ("the BJP said" after naming Bharatiya Janata Party once). Measured
    # on production 2026-07-30, these were splitting a single party across two
    # entities: bjp 176 articles vs bharatiya-janata-party 234, cjp 54 vs
    # cockroach-janata-party 430. Each half then carries half the document
    # frequency, so the matcher's 1/df weighting treats a national fixture as
    # twice as distinctive as it is.
    #
    # Listed by hand and NOT derived by initialism, because the initialism is
    # ambiguous and a wrong fold is unrecoverable. In THIS corpus "brs"
    # initialises both Bharat Rashtra Samithi and boston-red-sox; "cjp" also
    # initialises civil-jurisprudence-party, chhatra-jawan-party,
    # crocodile-janata-party and charama-janpad-panchayat; "bjp" also matches
    # bhanupratappur-janpad-panchayat. Every pair below was checked against its
    # article count and folded only where one expansion is unambiguously
    # dominant. Deliberately absent for that reason: brs, ani.
    "bjp": "bharatiya-janata-party",
    "cjp": "cockroach-janata-party",
    "dmk": "dravida-munnetra-kazhagam",
    "nda": "national-democratic-alliance",
    "tvk": "tamilaga-vettri-kazhagam",
    # Spelling and singular/plural forms of one organisation.
    "tamilaga-vetri-kazhagam": "tamilaga-vettri-kazhagam",
    "all-india-student-federation": "all-india-students-federation",
    "student-federation-of-india": "students-federation-of-india",
    "left-wing-student-unions": "left-wing-students-unions",
}


def resolve_alias(slug: str) -> str:
    """The canonical slug for `slug`, or `slug` itself."""
    return ENTITY_ALIASES.get(slug, slug)
