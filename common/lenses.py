"""Declarative role-lens registry (docs/PERSONAS.md).

A lens = which extra fields are extracted, how the feed is ranked, and
which questions the agent seeds. New roles are added here (and, for new
extraction fields, in enrichment/schemas.py) — never by branching the
pipeline. This is the in-code stand-in for the deferred `role_lenses`
table; moving it to the DB later is a data migration, not a rewrite.
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


LENSES: dict[str, Lens] = {
    "cyber_grc": Lens(
        slug="cyber_grc",
        name="Cybersecurity / GRC",
        tagline="CVEs, incidents, and what they mean for your controls",
        role_interest="cyber_grc",
        sectors=["cybersecurity"],
        ranking=RankingWeights(recency=1.0, severity=0.8, exploited=0.5),
        suggested_questions=[
            "Does this affect my stack?",
            "Is it being actively exploited?",
            "What should I patch or mitigate?",
            "Which of my controls does this touch?",
        ],
    ),
    "finance_trader": Lens(
        slug="finance_trader",
        name="Finance / Trader",
        tagline="Market-moving news with tickers, catalysts, and price-impact reads",
        role_interest="finance_trader",
        sectors=["finance", "business"],
        ranking=RankingWeights(recency=1.4, price_impact=0.6),
        suggested_questions=[
            "Which tickers does this move?",
            "What is the catalyst here?",
            "What's the likely price impact?",
            "What are the second-order effects?",
        ],
    ),
    "general": Lens(
        slug="general",
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
}

DEFAULT_LENS = "cyber_grc"


def get_lens(slug: str | None) -> Lens:
    return LENSES.get(slug or DEFAULT_LENS, LENSES[DEFAULT_LENS])
