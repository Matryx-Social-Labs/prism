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
}


def resolve_alias(slug: str) -> str:
    """The canonical slug for `slug`, or `slug` itself."""
    return ENTITY_ALIASES.get(slug, slug)
