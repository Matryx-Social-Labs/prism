"""Profession taxonomy — a controlled vocabulary collected at sign-up.

Structured (not free-text) so we can match a reader to lenses + interest sectors
and curate professional news lists later. Each profession maps to a default lens
and a set of interest sectors (keys of common.taxonomy.TAXONOMY). Grouped by
domain for the sign-up dropdown; served via /api/v1/professions.
"""

# group -> list of (slug, label, lens, interest sectors)
PROFESSION_GROUPS: dict[str, list[tuple[str, str, str, list[str]]]] = {
    "Finance & Markets": [
        ("trader", "Trader", "finance_trader", ["finance"]),
        ("investor", "Investor / PE / VC", "finance_trader", ["finance", "business"]),
        ("financial_analyst", "Financial analyst", "finance_trader", ["finance", "business"]),
        ("banker", "Banker", "finance_trader", ["finance"]),
        ("wealth_advisor", "Wealth / financial advisor", "finance_trader", ["finance"]),
        ("accountant", "Accountant / auditor", "finance_trader", ["finance", "business"]),
    ],
    "Cybersecurity & IT": [
        ("security_analyst", "Security analyst / SOC", "cyber_grc", ["cybersecurity"]),
        ("ciso", "CISO / security leader", "cyber_grc", ["cybersecurity"]),
        ("grc", "GRC / risk / compliance", "cyber_grc", ["cybersecurity"]),
        ("it_admin", "IT / infrastructure", "cyber_grc", ["cybersecurity", "technology"]),
        ("pentester", "Pentester / red team", "cyber_grc", ["cybersecurity"]),
        ("devsecops", "DevSecOps engineer", "cyber_grc", ["cybersecurity", "technology"]),
    ],
    "Technology & Product": [
        ("software_engineer", "Software engineer", "general", ["technology"]),
        ("product_manager", "Product manager", "general", ["technology", "business"]),
        ("data_scientist", "Data / ML scientist", "general", ["technology"]),
        ("designer", "Designer", "general", ["technology"]),
        ("tech_founder", "Founder / startup", "general", ["technology", "business", "finance"]),
    ],
    "Policy, Law & Government": [
        ("policy_analyst", "Policy analyst", "general", ["politics"]),
        ("civil_servant", "Government / civil servant", "general", ["politics"]),
        ("lawyer", "Lawyer / legal", "general", ["politics", "business"]),
        ("journalist", "Journalist / media", "general", ["politics", "business"]),
        ("diplomat", "Diplomacy / intl. relations", "general", ["politics"]),
    ],
    "Business & Management": [
        ("executive", "Executive / management", "finance_trader", ["business", "finance"]),
        ("consultant", "Consultant", "general", ["business", "finance"]),
        ("entrepreneur", "Entrepreneur / SMB owner", "general", ["business", "finance"]),
        ("marketer", "Marketing / communications", "general", ["business"]),
        ("operations", "Operations / supply chain", "general", ["business"]),
    ],
    "Health & Science": [
        ("healthcare", "Healthcare / medicine", "general", ["health"]),
        ("researcher", "Researcher / academic", "general", ["science"]),
        ("pharma_biotech", "Pharma / biotech", "general", ["health", "science", "business"]),
    ],
    "General": [
        ("student", "Student", "general", []),
        ("educator", "Educator / teacher", "general", []),
        ("other", "Other / general reader", "general", []),
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
    assert all(p["lens"] in {"general", "cyber_grc", "finance_trader"} for p in PROFESSIONS.values())
    print(f"professions OK — {len(PROFESSIONS)} across {len(PROFESSION_GROUPS)} groups")
