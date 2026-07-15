"""Sector → sub-domain taxonomy (single source of truth).

Drives the classifier prompt menu, subsector validation, the
/api/v1/taxonomy endpoint, and (through it) the onboarding interest
picker. Add a sector or subsector here and every consumer follows —
never hardcode this list anywhere else.
"""

TAXONOMY: dict[str, list[str]] = {
    "politics": ["elections", "governance_policy", "diplomacy", "conflict_defense", "courts_law"],
    "business": ["economy", "corporate", "startups", "trade"],
    "finance": ["markets", "banking", "crypto", "personal_finance", "commodities"],
    "technology": ["ai", "mobile", "software_internet", "hardware_chips", "telecom"],
    "cybersecurity": ["vulnerabilities", "breaches_incidents", "malware_threats", "policy_compliance"],
    "sports": [
        "cricket",
        "football",
        "basketball",
        "tennis",
        "hockey",
        "motorsport",
        "olympics_athletics",
        "other_sports",
    ],
    "health": ["public_health", "medicine_research", "diseases_outbreaks", "fitness_wellness"],
    "entertainment": ["movies", "music", "tv_streaming", "celebrity"],
    "science": ["space", "climate_environment", "research"],
    "other": [],
}

SECTORS = list(TAXONOMY)


def display_name(slug: str) -> str:
    return slug.replace("_", " ").title().replace("Tv ", "TV ").replace("Ai", "AI")


def valid_subsector(sector: str, subsector: str | None) -> str | None:
    """Return subsector if it belongs to the sector, else None."""
    if subsector and subsector in TAXONOMY.get(sector, []):
        return subsector
    return None


def prompt_menu() -> str:
    """sector: sub1 | sub2 lines for the classifier prompt."""
    return "\n".join(
        f"- {sector}: {' | '.join(subs) if subs else '(no subsectors)'}"
        for sector, subs in TAXONOMY.items()
    )
