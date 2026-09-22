"""The subject tree: what a story is about, one path deep enough to be useful.

`common/taxonomy.py` is two flat levels — ten sectors, thirty-six sub-sectors —
and production shows what that costs: 22 % of stories land in `other`, and
`business/corporate` holds a dairy building, an MBA admission and a deepwater
drilling programme. A reader cannot follow cricket, only sports; an analysis
cannot ask what moved banking, only read 139 undifferentiated rows.

THE SPINE IS AUTHORED, THE DEPTH IS DERIVED. Levels 1 and 2 are editorial
judgement: they are the navigation, the URLs and the reader's mental model, and
no clustering can tell you how someone thinks about a beat. Level 3 exists only
where the corpus put it there — every node below was proposed by clustering 30
days of production events and then read by hand.

What the clustering got WRONG is why the spine is not derived. On sports it
returned `Asian Games 2026` as the largest cluster (~378 of 865 events): a
tournament, not a category, and an empty node by March. On politics it split by
STATE — Karnataka, Telangana, Uttar Pradesh — because the embedding keys on
place names. Geography is already a facet (`common/regions.py`) and a tournament
is already an entity; neither is a branch of a tree.

THREE RULES, and they are load-bearing:

1. A node is decidable by its siblings alone. Classification asks one question
   per level with the parent fixed, which is the shape Jev's `choice` answers
   best. A flat 200-way question is worse at every level.
2. A node earns its existence at ~30 stories a month. An empty section is a
   promise the product breaks, so `other_sports` stays (258/month) while twelve
   imagined sports do not.
3. A node is a URL and a feed. If `/subject/sports/cricket` cannot fill a page,
   the node should not exist.

WHAT THIS IS NOT. It is not multi-label: a story takes ONE path, because a path
is navigation and breadcrumbs and "what is in this section". Everything else a
story is — who is in it, where it happened, which security it names, what kind
of event it is — is a facet, carried by the entities, regions and securities
that already exist. That is the join that makes analysis possible; the tree is
what makes it browsable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Subject:
    """One node. `criterion` is what the classifier is told this node means, so
    the vocabulary the model sees and the vocabulary the product ships are the
    same string — a taxonomy that drifts from its own prompt is how
    `business/corporate` became a dumping ground."""

    path: str
    label: str
    criterion: str
    # What this node writes into the legacy `events.sector` / `events.subsector`
    # columns, so every existing reader keeps working while the tree lands.
    legacy: tuple[str, str | None] | None = None


# ── The tree ────────────────────────────────────────────────────────────────
# Parents before children. Level 1 is the reader's nav: D3's six, plus civic &
# safety and education, both of which the corpus demanded (founder, 2026-09-22). Level 2 is authored. Level 3 appears only where 30 days
# of production events showed a real, recurring cluster.
#
# CIVIC & SAFETY IS NEW, and it is the largest single win here. Today's `other`
# is 22 % of the corpus and, clustered, it is not miscellaneous at all: ~53 %
# crime (violent, property, sexual offences, custody and investigation), ~23 %
# accidents and disasters, ~20 % festivals, ceremonies and community honours,
# and a weather-and-farmers cluster. Ganesh immersions and taluk award
# ceremonies are a genuine Indian local beat with nowhere to live. "Other" is
# never shown as a heading (D3), so a fifth of the product is unreachable.

SUBJECTS: tuple[Subject, ...] = (
    # ── politics ────────────────────────────────────────────────────────────
    Subject("politics", "Politics", "government, parties, elections, courts, policy and diplomacy", ("politics", None)),
    Subject("politics.elections", "Elections", "campaigns, candidates, voting, results and electoral rolls", ("politics", "elections")),
    Subject("politics.governance", "Governance & policy", "a government acting: schemes, budgets, appointments, legislation, administration", ("politics", "governance_policy")),
    Subject("politics.courts", "Courts & law", "judgments, hearings, petitions, tribunals, investigations by agencies", ("politics", "courts_law")),
    Subject("politics.protest", "Protests & demands",
            "an organised demand on government: a protest, a strike, a memorandum, a bandh. The clustering "
            "found this is one of the largest things in Indian politics coverage and it had no node",
            ("politics", "governance_policy")),
    Subject("politics.diplomacy", "Diplomacy & foreign affairs", "relations between countries: visits, treaties, tariffs, sanctions, summits", ("politics", "diplomacy")),
    Subject("politics.conflict", "Conflict & defence", "armed conflict, military action, defence procurement, security operations", ("politics", "conflict_defense")),

    # ── business & markets ──────────────────────────────────────────────────
    Subject("business", "Business & Markets", "companies, markets, the economy and the industries that make them up", ("business", None)),
    Subject("business.companies", "Companies", "one company's own news: results, deals, leadership, products, disputes", ("business", "corporate")),
    Subject("business.markets", "Markets", "traded instruments: equities, indices, IPOs, commodities, currency, crypto", ("finance", "markets")),
    Subject("business.economy", "Economy", "the economy as a whole: inflation, growth, jobs, the budget, rates", ("business", "economy")),
    Subject("business.trade", "Trade", "imports, exports, tariffs, trade agreements and disputes between countries", ("business", "trade")),
    Subject("business.banking", "Banking & finance", "banks, lending, insurance, regulators of finance, payments", ("finance", "banking")),
    Subject("business.energy", "Energy & resources", "oil, gas, power, renewables, mining and exploration", ("business", "corporate")),
    Subject("business.startups", "Startups & funding", "a startup raising, launching, shutting or being acquired", ("business", "startups")),

    # ── sports ──────────────────────────────────────────────────────────────
    Subject("sports", "Sports", "matches, results, players, selections and the bodies that run a sport", ("sports", None)),
    Subject("sports.cricket", "Cricket", "any cricket: internationals, franchise leagues, domestic and age-group", ("sports", "cricket")),
    Subject("sports.football", "Football", "football at any level, in India or abroad", ("sports", "football")),
    Subject("sports.multisport", "Multi-sport events",
            "a games rather than a sport: Asian Games, Olympics, Commonwealth Games, national games. "
            "A node because the coverage is continuous and cross-sport, not because any one games is",
            ("sports", "olympics_athletics")),
    Subject("sports.school", "School & amateur sport",
            "taluk, district and school-level meets, inter-collegiate tournaments, local championships. "
            "The clustering found ~100 of these a month; they are the local paper's sport",
            ("sports", "other_sports")),
    Subject("sports.other", "Other sports", "any sport without its own node: kabaddi, hockey, tennis, shooting, chess, motorsport", ("sports", "other_sports")),

    # ── tech & cyber ────────────────────────────────────────────────────────
    Subject("tech", "Tech & Cyber", "technology, the companies building it, and the security of computers and data", ("technology", None)),
    Subject("tech.ai", "AI", "artificial intelligence: models, products, research, the companies and the policy", ("technology", "ai")),
    Subject("tech.products", "Software & products", "consumer and business technology products, platforms and launches", ("technology", "software_internet")),
    Subject("tech.infrastructure", "Infrastructure & chips", "data centres, semiconductors, cloud, networks and the capital behind them", ("technology", "hardware_chips")),
    Subject("tech.telecom", "Telecom", "operators, spectrum, tariffs and the telecom regulator", ("technology", "telecom")),
    Subject("tech.security", "Cybersecurity", "attacks on or defence of computers, networks and data", ("cybersecurity", None)),
    Subject("tech.security.vulnerabilities", "Vulnerabilities", "a disclosed or exploited flaw in software or hardware, a CVE, a patch", ("cybersecurity", "vulnerabilities")),
    Subject("tech.security.breaches", "Breaches & incidents", "an organisation breached, data exposed, a service disrupted by attack", ("cybersecurity", "breaches_incidents")),
    Subject("tech.security.malware", "Malware & threats", "ransomware, malware families, threat actors and their campaigns", ("cybersecurity", "malware_threats")),
    Subject("tech.security.policy", "Security policy", "rules, standards, compliance and enforcement about security", ("cybersecurity", "policy_compliance")),

    # ── health & science ────────────────────────────────────────────────────
    Subject("health", "Health & Science", "health, medicine, and scientific research about the world", ("health", None)),
    Subject("health.public", "Public health", "health of a population: services, hospitals, campaigns, food and drug safety", ("health", "public_health")),
    Subject("health.outbreaks", "Outbreaks & disease", "an outbreak, an epidemic, a disease spreading or being contained", ("health", "diseases_outbreaks")),
    Subject("health.medicine", "Medicine & research", "clinical research, treatments, trials, pharmaceuticals and medical findings", ("health", "medicine_research")),
    Subject("health.climate", "Climate & environment", "climate, pollution, conservation, rivers, forests and wildlife", ("science", "climate_environment")),
    Subject("health.space", "Space", "launches, missions, observations and the agencies and companies behind them", ("science", "space")),
    Subject("health.research", "Science & research", "scientific research outside medicine, climate and space", ("science", "research")),

    # ── entertainment ───────────────────────────────────────────────────────
    Subject("entertainment", "Entertainment", "film, music, television and the people who make them", ("entertainment", None)),
    Subject("entertainment.film", "Film", "films: releases, box office, casting, production, awards", ("entertainment", "movies")),
    Subject("entertainment.music", "Music", "music releases, artists, concerts and the industry", ("entertainment", "music")),
    Subject("entertainment.television", "Television & streaming", "television and streaming shows, platforms and their business", ("entertainment", "tv_streaming")),
    Subject("entertainment.people", "People & celebrity", "a public figure in entertainment as the story: their life, statements, disputes", ("entertainment", "celebrity")),

    # ── education (NEW) ─────────────────────────────────────────────────────
    # Surfaced in three separate derivations and had nowhere to go each time:
    # IIM admissions sat in `business/corporate`, an IB schools conference and a
    # NEET answer key both landed in `other` at low confidence. Exams and
    # admissions are a staple of Indian news and a beat a reader follows.
    Subject("education", "Education", "schools, colleges, universities, exams and the people in them", ("other", None)),
    Subject("education.exams", "Exams & results",
            "an exam, its results, answer keys, admit cards, toppers, or a recruitment test",
            ("other", None)),
    Subject("education.admissions", "Admissions & fees", "admissions, counselling, seats, quotas and fees", ("other", None)),
    Subject("education.institutions", "Schools & universities",
            "an institution as the story: its administration, appointments, buildings, conferences, disputes",
            ("other", None)),
    Subject("education.policy", "Education policy", "government decisions about education: curriculum, rules, funding, language of instruction", ("other", None)),

    # ── civic & safety (NEW — today's "other") ──────────────────────────────
    Subject("civic", "Civic & Safety", "crime, accidents, community life and local conditions where people live", ("other", None)),
    Subject("civic.crime", "Crime",
            "an offence and what follows it: the act, the arrest, the investigation, the charge",
            ("other", None)),
    Subject("civic.crime.violent", "Violent crime", "murder, assault, kidnapping, a death being investigated as a crime", ("other", None)),
    Subject("civic.crime.property", "Theft & fraud", "theft, robbery, burglary, cheating, financial fraud and scams", ("other", None)),
    Subject("civic.crime.sexual", "Sexual offences", "rape, sexual assault, harassment and offences against children", ("other", None)),
    Subject("civic.crime.policing", "Policing & investigations",
            "the police as the story: an arrest, a racket busted, a custodial death, an investigation's progress",
            ("other", None)),
    Subject("civic.accidents", "Accidents & disasters", "road and rail accidents, fires, drownings, industrial accidents, building collapse", ("other", None)),
    Subject("civic.disasters", "Natural disasters", "floods, landslides, earthquakes, cyclones and the rescue that follows", ("other", None)),
    Subject("civic.community", "Community & culture",
            "festivals, religious observances, ceremonies, inaugurations, awards and honours in a community. "
            "~20 % of what used to be `other`: Ganesh immersions, Onam, taluk award ceremonies",
            ("other", None)),
    Subject("civic.local", "Local government & works", "civic works, municipal decisions, local infrastructure, water and power supply", ("other", None)),
    Subject("civic.weather", "Weather & its impact", "rainfall, heat, cold and what they do to farming, traffic and daily life", ("other", None)),
)

# Nodes at level 1, in nav order. Seven: D3's six plus civic & safety.
ROOTS: tuple[str, ...] = ("politics", "business", "sports", "tech", "health", "education", "entertainment", "civic")

_BY_PATH: dict[str, Subject] = {s.path: s for s in SUBJECTS}


def get(path: str) -> Subject | None:
    return _BY_PATH.get(path)


def depth(path: str) -> int:
    return path.count(".") + 1


def parent_of(path: str) -> str | None:
    return path.rsplit(".", 1)[0] if "." in path else None


def children(path: str | None) -> tuple[Subject, ...]:
    """Direct children of a node, or the roots when path is None."""
    if path is None:
        return tuple(_BY_PATH[p] for p in ROOTS)
    prefix = f"{path}."
    want = depth(path) + 1
    return tuple(s for s in SUBJECTS if s.path.startswith(prefix) and depth(s.path) == want)


def descendants(path: str) -> tuple[Subject, ...]:
    """Every node under this one, at any depth (not including itself)."""
    prefix = f"{path}."
    return tuple(s for s in SUBJECTS if s.path.startswith(prefix))


def is_valid(path: str) -> bool:
    return path in _BY_PATH


def legacy_for(path: str) -> tuple[str, str | None]:
    """The old (sector, subsector) for a path, so `events.sector` keeps its
    meaning for every reader that has not moved to paths yet. Walks up until a
    node declares one: `civic.crime.violent` has no sector of its own and
    inherits `other` from `civic`."""
    node = _BY_PATH.get(path)
    while node is not None:
        if node.legacy is not None:
            sector, sub = node.legacy
            return sector, sub
        parent = parent_of(node.path)
        node = _BY_PATH.get(parent) if parent else None
    return "other", None


def choices(parent: str | None) -> dict[str, str]:
    """The classifier's menu at one level: {slug: criterion} for the children of
    `parent`, keyed on the LAST segment so the model chooses among siblings and
    never re-reads the whole tree."""
    return {s.path.rsplit(".", 1)[-1]: s.criterion for s in children(parent)}


def demo() -> None:
    """Self-check: the tree is well formed and the legacy bridge is total."""
    from common.taxonomy import TAXONOMY

    for s in SUBJECTS:
        parent = parent_of(s.path)
        assert parent is None or parent in _BY_PATH, f"{s.path} has no parent node"
        assert s.criterion and s.label, s.path
        sector, sub = legacy_for(s.path)
        assert sector in TAXONOMY, f"{s.path} maps to unknown sector {sector}"
        assert sub is None or sub in TAXONOMY[sector], f"{s.path} maps to unknown subsector {sector}/{sub}"
    assert set(ROOTS) <= set(_BY_PATH), "a root is missing from the tree"
    assert all(depth(p) == 1 for p in ROOTS)
    assert len(children(None)) == len(ROOTS)
    assert {c.path for c in children("tech.security")} == {
        "tech.security.vulnerabilities", "tech.security.breaches",
        "tech.security.malware", "tech.security.policy",
    }
    assert legacy_for("civic.crime.violent") == ("other", None), "inherited from civic"
    assert legacy_for("sports.cricket") == ("sports", "cricket")
    assert set(choices(None)) == set(ROOTS)
    assert "cricket" in choices("sports")
    print(f"ok: {len(SUBJECTS)} nodes, {len(ROOTS)} roots, max depth {max(depth(s.path) for s in SUBJECTS)}")


if __name__ == "__main__":
    demo()
