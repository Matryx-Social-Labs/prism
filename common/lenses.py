"""Declarative role-lens registry (docs/PERSONAS.md).

A lens = which extra fields are extracted, how the feed is ranked, and
which questions the agent seeds. New roles are added here (and, for new
extraction fields, in enrichment/schemas.py) — never by branching the
pipeline. This is the in-code stand-in for the deferred `role_lenses`
table; moving it to the DB later is a data migration, not a rewrite.

Slugs are single words so the same key refers to a lens on both the API and
the frontend (reader / cyber / markets). `upcoming=True` lenses are drafted
for future work: they're in the registry but excluded from /api/v1/lenses and
never activate extraction, so the live picker only offers the shipped set.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RankingWeights:
    recency: float = 1.0
    severity: float = 0.0  # CVSS-derived (cyber)
    exploited: float = 0.0  # KEV boost (cyber)
    price_impact: float = 0.0  # finance catalyst boost
    corroboration: float = 0.05  # per extra source, capped in scorer


@dataclass(frozen=True)
class Lens:
    slug: str
    name: str
    tagline: str
    # which classifier role_interest activates this lens's extraction fields
    role_interest: str | None
    # feed defaults
    sectors: list[str] = field(default_factory=list)  # empty = all sectors
    ranking: RankingWeights = field(default_factory=RankingWeights)
    suggested_questions: list[str] = field(default_factory=list)
    # Raw CVE-database records (NVD/KEV entries with no news coverage) are
    # signal for defenders but noise for everyone else.
    include_cve_records: bool = False
    # Drafted for future work: kept in the registry, but not served by
    # /api/v1/lenses and never activates extraction/gating.
    upcoming: bool = False


LENSES: dict[str, Lens] = {
    "cyber": Lens(
        slug="cyber",
        name="Cybersecurity / GRC",
        tagline="CVEs, incidents, and what they mean for your controls",
        role_interest="cyber",
        sectors=["cybersecurity"],
        ranking=RankingWeights(recency=1.0, severity=0.8, exploited=0.5),
        include_cve_records=True,
        suggested_questions=[
            "Does this affect my stack?",
            "Is it being actively exploited?",
            "What should I patch or mitigate?",
            "Which of my controls does this touch?",
        ],
    ),
    "markets": Lens(
        slug="markets",
        name="Finance / Trader",
        tagline="Market-moving news with tickers, catalysts, and price-impact reads",
        role_interest="markets",
        sectors=["finance", "business"],
        ranking=RankingWeights(recency=1.4, price_impact=0.6),
        suggested_questions=[
            "Which tickers does this move?",
            "What is the catalyst here?",
            "What's the likely price impact?",
            "What are the second-order effects?",
        ],
    ),
    "reader": Lens(
        slug="reader",
        name="General reader",
        tagline="Every story with both sides, consequences, and answers",
        role_interest=None,
        sectors=[],
        ranking=RankingWeights(recency=1.2, corroboration=0.1),
        suggested_questions=[
            "What led to this?",
            "Who is affected?",
            "What are the likely outcomes?",
            "How is each side framing it?",
        ],
    ),
    # ── Upcoming (drafted, not yet shipped) ──────────────────────────────
    "health": Lens(
        slug="health",
        name="Health",
        tagline="Clinical and public-health read: who's affected, access, and delivery",
        role_interest="health",
        sectors=["health"],
        ranking=RankingWeights(recency=1.2, corroboration=0.1),
        suggested_questions=[
            "Who does this affect clinically?",
            "How does access or supply change?",
            "What are the delivery and safety questions?",
            "What should patients or providers do?",
        ],
        upcoming=True,
    ),
    "policy": Lens(
        slug="policy",
        name="Policy",
        tagline="Regulatory and policy read: precedent, rule-making, and second-order effects",
        role_interest="policy",
        sectors=["politics"],
        ranking=RankingWeights(recency=1.2, corroboration=0.1),
        suggested_questions=[
            "What precedent does this set?",
            "Who does the rule-making affect?",
            "What are the second-order effects?",
            "How will each side litigate or lobby it?",
        ],
        upcoming=True,
    ),
}

DEFAULT_LENS = "cyber"


def get_lens(slug: str | None) -> Lens:
    return LENSES.get(slug or DEFAULT_LENS, LENSES[DEFAULT_LENS])


def active_lenses() -> list[Lens]:
    """Shipped lenses only — what /api/v1/lenses serves and the picker renders."""
    return [lens for lens in LENSES.values() if not lens.upcoming]
