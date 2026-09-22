"""The relevance gate and the classifier as one typed call on Jev.

The LLM pair asks two chat models to write JSON about an item; this asks one
decision model ten typed questions about the same title and body, in one
pass, and folds the answers into the very same GateResult and
ClassificationResult, so nothing downstream knows which answered.

What the questions are built from is the code's own vocabulary — the sector
taxonomy, the state table, the languages the feeds carry — never a second
copy. What Jev cannot give is a free list: the classifier's `regions` are
therefore a chosen country plus a chosen state, which is all the pipeline ever
took from them (correlation prefers the extraction's countries and merges only
the state codes from here).

Jev reads instructions literally, so every noul is a positive statement and
the gate is two of them: the item IS an event, and the item IS a form that is
not news (column, listicle, promotion). Relevant is the first without the
second.

The specs live here, not in Langfuse: they are typed criteria, not prose
prompts, and the endpoint has no prompt object to version. QUESTIONS_VERSION
rides on every trace instead.
"""

from __future__ import annotations

import hashlib
import json

from classification import subject
from classification.schemas import ClassificationResult, GateResult
from common import subjects
from common.decisions import Choice, ChoiceAnswer, Decisions, Noul, NoulAnswer, Question
from common.regions import IN_STATES, is_state_code
from common.taxonomy import TAXONOMY, display_name, valid_subsector

MAX_GATE_CHARS = 4000

# Where each noul crosses. Not 0.5 across the board: Jev's probabilities are
# calibrated to the statement, not to our labels, and on 450 prod items the LLM
# pair had labelled (tools/bakeoff_decide, 2026-09-22) the `event` noul for
# items the LLM kept sat at 0.52-0.86 and for items it rejected at 0.09-0.77,
# so the gate leans on `not_news` (0.07 vs 0.42 medians); `fast_lane` was
# 0.79+ on every LLM fast-lane item and under 0.63 on 90% of the rest, so 0.7
# keeps all of them at a 4% false-positive rate where 0.5 gave 23%; `cyber`
# likewise. `markets` stays at 0.5 because where the two disagreed Jev was
# right — the LLM had tagged a school shooting and a co-op's ₹51-lakh profit
# as market-moving; Jev's 0.88+ were a stock down 11%, a ₹4,433-crore fine and
# a BoJ rate hike.
EVENT_MIN = 0.3
NOT_NEWS_MAX = 0.4
FAST_LANE_MIN = 0.7
LENS_MIN = {"cyber": 0.7, "markets": 0.5}

# Countries that carried 96% of the classifier's country mentions in the 30 days to
# 2026-09-22 (prod), most frequent first. Anything else is "other" and the regions
# fall back to the source's country, as they did when the LLM named nothing.
COUNTRIES: dict[str, str] = {
    "IN": "India", "US": "United States", "PK": "Pakistan", "CN": "China", "JP": "Japan",
    "IR": "Iran", "RU": "Russia", "SA": "Saudi Arabia", "GB": "United Kingdom",
    "BD": "Bangladesh", "YE": "Yemen", "UA": "Ukraine", "AF": "Afghanistan",
    "AU": "Australia", "LK": "Sri Lanka", "NP": "Nepal", "AE": "United Arab Emirates",
    "IL": "Israel", "DE": "Germany", "FR": "France", "CA": "Canada", "QA": "Qatar",
    "other": "a country not listed",
}

# The languages the feeds carry (prod, 30 days to 2026-09-22), BCP-47.
LANGUAGES: dict[str, str] = {
    "en": "English", "hi": "Hindi", "kn": "Kannada", "ta": "Tamil", "te": "Telugu",
    "ur": "Urdu", "gu": "Gujarati", "bn": "Bengali", "mr": "Marathi", "pa": "Punjabi",
    "ml": "Malayalam",
}

_SECTOR_NOTES: dict[str, str] = {
    "cybersecurity": (
        "attacks on or defense of computers, networks or data — breaches, ransomware, CVEs and "
        "vulnerabilities, malware, exploitation, security policy or compliance. A crime, scandal or "
        "accident that merely involved a phone, app, website or chatbot is not this"
    ),
    "technology": "AI products, models and companies; mobile; software and internet; hardware and chips; telecom",
    "other": "crime, accidents, disasters, civic life, and anything no listed sector genuinely fits",
}


def _sector_criteria() -> dict[str, str]:
    return {
        sector: _SECTOR_NOTES.get(sector, ", ".join(display_name(s).lower() for s in subs))
        for sector, subs in TAXONOMY.items()
    }


def _subsector_criteria() -> dict[str, str]:
    out = {f"{sector}/{sub}": f"{display_name(sector)}: {display_name(sub).lower()}" for sector, subs in TAXONOMY.items() for sub in subs}
    out["none"] = "no listed sub-domain fits"
    return out


QUESTIONS: dict[str, Question] = {
    "event": Noul(
        instructions=(
            "The item reports a real, specific public event or development: something that happened, was "
            "decided, announced, disclosed, demanded, ruled or resolved — including a public statement, demand, "
            "resignation, appointment, court ruling, government or party action, protest call, breach or "
            "vulnerability, market-moving event, safety advisory, or a match result, by a newsworthy person or "
            "institution"
        )
    ),
    "not_news": Noul(
        instructions=(
            "The item is a form other than reported news: an opinion column or editorial essay, a product "
            "promotion or vendor marketing, a listicle, a how-to guide or tutorial, career advice, a horoscope, "
            "a piece on a celebrity's or businessperson's personal wealth, lifestyle or ventures, sports gossip "
            "or a player spat, or a fixture list or schedule with no result"
        )
    ),
    "sector": Choice(
        instructions="The sector the story's substance belongs to — not the tools or platforms it happens to name",
        criteria=_sector_criteria(),
    ),
    "subsector": Choice(
        instructions="The sub-domain within the story's sector",
        criteria=_subsector_criteria(),
    ),
    "indian_state": Choice(
        instructions=(
            "The Indian state or union territory the event is LOCAL to as the article itself places it — a state "
            "government, a city, a district, a state election. 'national' for an event of national scope "
            "(Parliament, the Union government, the Supreme Court, RBI, a national policy) even when datelined "
            "New Delhi. 'none' when the event is not in India"
        ),
        criteria={**dict(IN_STATES), "national": "national scope, no single state", "none": "not an Indian event"},
    ),
    "country": Choice(
        instructions="The country the event is primarily located in or about — not the outlet's country",
        criteria=COUNTRIES,
    ),
    "language": Choice(instructions="The language the title and content are written in", criteria=LANGUAGES),
    "cyber": Noul(
        instructions="The item matters to a security professional: a security incident, CVE, exploit, breach, malware, or security advisory"
    ),
    "markets": Noul(
        instructions=(
            "The item is market-moving news: earnings, guidance, a rate decision, M&A, a regulatory action, or a "
            "major corporate event with market impact"
        )
    ),
    "fast_lane": Noul(
        instructions="The item is time-critical: an actively exploited vulnerability, an ongoing incident, or breaking market-moving news"
    ),
}

# The subject tree's questions ride in the SAME call: Jev answers every question
# in one parallel pass, so a root choice plus one menu per root costs a little
# input and no extra round trip (classification/subject.py).
QUESTIONS.update({"subject": subject.root_question(), **subject.level_two_questions()})

QUESTIONS_VERSION = hashlib.sha256(
    json.dumps({k: q.model_dump() for k, q in QUESTIONS.items()}, sort_keys=True).encode()
).hexdigest()[:12]


def body_for_prompt(body: str | None) -> str:
    return (body or "(no content — title only)")[:MAX_GATE_CHARS]


def state_for(title: str, body: str | None) -> dict[str, str]:
    return {"title": title, "content": body_for_prompt(body)}


def _noul(d: Decisions, key: str) -> float:
    a = d.answers[key]
    assert isinstance(a, NoulAnswer), key
    return a.noul


def _choice(d: Decisions, key: str) -> ChoiceAnswer:
    a = d.answers[key]
    assert isinstance(a, ChoiceAnswer), key
    return a


def to_results(d: Decisions, *, source_country: str | None) -> tuple[GateResult, ClassificationResult | None]:
    """The answers as the gate and classifier records the LLM pair would have written."""
    event, not_news = _noul(d, "event"), _noul(d, "not_news")
    gate = GateResult(
        is_relevant=event >= EVENT_MIN and not_news < NOT_NEWS_MAX,
        reason=f"jev event={event:.2f} not_news={not_news:.2f}",
    )
    if not gate.is_relevant:
        return gate, None
    path, path_confidence = subject.path_from(d)
    sector = _choice(d, "sector")
    # The old columns are DERIVED from the path when there is one, not elicited
    # separately. Two independent judgements in the same call can disagree, and
    # for the two new roots there is no old sector to elicit at all — `civic`
    # and `education` have no entry in the flat taxonomy, so the old question
    # could only guess. One placement, one answer, and the migration's promise
    # that `sector` still means something is actually kept. The separate
    # question stays as the fallback for a story the tree could not place.
    if path is not None:
        legacy_sector, legacy_sub = subjects.legacy_for(path)
    else:
        sub_key = _choice(d, "subsector").choice
        legacy_sector = sector.choice
        legacy_sub = valid_subsector(
            sector.choice, sub_key.split("/", 1)[1] if sub_key.startswith(f"{sector.choice}/") else None
        )
    country = _choice(d, "country").choice
    state = _choice(d, "indian_state").choice
    country_code = country if country != "other" else source_country
    regions = [c for c in (country_code, state) if c and (c == country_code or is_state_code(c))]
    return gate, ClassificationResult(
        sector=legacy_sector,
        subsector=legacy_sub,
        regions=regions,
        language=_choice(d, "language").choice,
        role_interests=[lens for lens, floor in LENS_MIN.items() if _noul(d, lens) >= floor],
        route="fast_lane" if _noul(d, "fast_lane") >= FAST_LANE_MIN else "standard",
        confidence=sector.confidence,
        subject_path=path,
        subject_confidence=round(path_confidence, 3),
    )


def decided_confidence(d: Decisions) -> float:
    """How sure the decision is: the sector's confidence for an item that
    passed the gate (0.98 median where Jev and the LLM agreed on the sector,
    0.71 where they did not), how surely it is not news for one that did not.
    Under prism_decisions_min_confidence the item goes to the LLM pair."""
    event, not_news = _noul(d, "event"), _noul(d, "not_news")
    if event >= EVENT_MIN and not_news < NOT_NEWS_MAX:
        return _choice(d, "sector").confidence
    return max(not_news, 1.0 - event)
