"""Profession taxonomy — a controlled vocabulary collected at sign-up.

Structured (not free-text) so we can match a reader to lenses + interest sectors
and curate professional news lists later. Each profession maps to a default lens
and a set of interest sectors (keys of common.taxonomy.TAXONOMY). Grouped by
domain for the sign-up dropdown; served via /api/v1/professions.
"""

# group -> list of (slug, label, lens, interest sectors)
PROFESSION_GROUPS: dict[str, list[tuple[str, str, str, list[str]]]] = {
    "Finance & Markets": [
        ("trader", "Trader", "markets", ["finance"]),
        ("investor", "Investor / PE / VC", "markets", ["finance", "business"]),
        ("financial_analyst", "Financial analyst", "markets", ["finance", "business"]),
        ("banker", "Banker", "markets", ["finance"]),
        ("wealth_advisor", "Wealth / financial advisor", "markets", ["finance"]),
        ("accountant", "Accountant / auditor", "markets", ["finance", "business"]),
    ],
    "Cybersecurity & IT": [
        ("security_analyst", "Security analyst / SOC", "cyber", ["cybersecurity"]),
        ("ciso", "CISO / security leader", "cyber", ["cybersecurity"]),
        ("grc", "GRC / risk / compliance", "cyber", ["cybersecurity"]),
        ("it_admin", "IT / infrastructure", "cyber", ["cybersecurity", "technology"]),
        ("pentester", "Pentester / red team", "cyber", ["cybersecurity"]),
        ("devsecops", "DevSecOps engineer", "cyber", ["cybersecurity", "technology"]),
    ],
    "Technology & Product": [
        ("software_engineer", "Software engineer", "reader", ["technology"]),
        ("product_manager", "Product manager", "reader", ["technology", "business"]),
        ("data_scientist", "Data / ML scientist", "reader", ["technology"]),
        ("designer", "Designer", "reader", ["technology"]),
        ("tech_founder", "Founder / startup", "reader", ["technology", "business", "finance"]),
    ],
    "Policy, Law & Government": [
        ("policy_analyst", "Policy analyst", "reader", ["politics"]),
        ("civil_servant", "Government / civil servant", "reader", ["politics"]),
        ("lawyer", "Lawyer / legal", "reader", ["politics", "business"]),
        ("journalist", "Journalist / media", "reader", ["politics", "business"]),
        ("diplomat", "Diplomacy / intl. relations", "reader", ["politics"]),
    ],
    "Business & Management": [
        ("executive", "Executive / management", "markets", ["business", "finance"]),
        ("consultant", "Consultant", "reader", ["business", "finance"]),
        ("entrepreneur", "Entrepreneur / SMB owner", "reader", ["business", "finance"]),
        ("marketer", "Marketing / communications", "reader", ["business"]),
        ("operations", "Operations / supply chain", "reader", ["business"]),
    ],
    "Health & Science": [
        ("healthcare", "Healthcare / medicine", "reader", ["health"]),
        ("researcher", "Researcher / academic", "reader", ["science"]),
        ("pharma_biotech", "Pharma / biotech", "reader", ["health", "science", "business"]),
    ],
    "General": [
        ("student", "Student", "reader", []),
        ("educator", "Educator / teacher", "reader", []),
        ("other", "Other / general reader", "reader", []),
    ],
}

# slug -> (label, lens, interests) for validation + later curation.
PROFESSIONS: dict[str, dict] = {
    slug: {"label": label, "group": group, "lens": lens, "interests": interests}
    for group, rows in PROFESSION_GROUPS.items()
    for slug, label, lens, interests in rows
}


def is_valid_profession(slug: str) -> bool:
    return slug in PROFESSIONS


def grouped() -> list[dict]:
    """Sign-up dropdown payload: [{group, options: [{slug, label}]}]."""
    return [
        {"group": group, "options": [{"slug": s, "label": lbl} for s, lbl, _, _ in rows]}
        for group, rows in PROFESSION_GROUPS.items()
    ]


if __name__ == "__main__":  # tiny self-check: slugs unique, lenses valid
    slugs = [s for rows in PROFESSION_GROUPS.values() for s, *_ in rows]
    assert len(slugs) == len(set(slugs)), "duplicate profession slug"
    assert all(p["lens"] in {"reader", "cyber", "markets"} for p in PROFESSIONS.values())
    print(f"professions OK — {len(PROFESSIONS)} across {len(PROFESSION_GROUPS)} groups")
