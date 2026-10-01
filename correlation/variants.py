"""One name, one entity: spellings of a person's or organisation's name, folded on Jev's word.

Entity identity is a slug. Punctuation folds by rule (common/text.py) and other
spellings only through the hand-kept common/entity_aliases.py, so every
transliteration an Indian-language article makes is a new entity. Measured in
production 2026-10-01: the Flydubai pilot was fifteen entities (smit-machchhar 78
articles, smit-machhar 29, smith-machar 19, smith-machhar 6, ...), and in 30 days
713 groups of spellings sharing a consonant skeleton sat in one record together
(trinamool/trinamul congress 431/7, zelenskyy/zelensky/zelenskiy 88/22/6, ...).
Each split halves an actor's document frequency, and the matching tier and the
story graph join records on shared entity ids, so one story split by language.

THE KEY is the consonant skeleton (`skeleton`): the aspirate and sibilant
spellings folded, doubled letters collapsed, vowels dropped. Multi-word names only,
five consonants or more; a respaced name ("fly-dubai", "flydubai") is its own key.
A leading-vowel variant of it was tried and kept out: on the 902 skeleton pairs in
one record (30 days) it separated 2 different (Eastern/Southern Railway) but lost
14 real ones (an initial "A.", "U.", "O." dropped by one outlet).

A KEY NEVER FOLDS ALONE. Skeletons collide across different people that never
meet — sahil-goyal/sahil-gill, sunil-kumar/sanal-kumar, divya-shinde/dave-sunday —
so a pair is a candidate only with evidence that both name one thing (the same
record, records joined by a verified follow-up link, or one current story), and
folds only when Jev reads both names in context and calls them one entity. A pair
one article names together is two entities, not asked: 6 of the 7 such pairs in 30
days were different (Rehan/Rehana Shaikh, Akash/Akshay Singh, Eastern/Southern
Railway), the seventh Bangalore/Bengaluru Speciality Pharma.

STAR, NEVER CHAIN. Every variant is judged against the survivor itself — the
spelling with the most mentions, so the fewest rows move — never through a third
spelling; union-find over pairwise "same" answers is how one wrong answer merges
two groups.

Each answer is kept in entity_variant_verdicts (decision record, replay cache, and
the fold's journal); the fold is correlation/entity_fold.py, the mechanics
tools/link_entities.py introduced. `reconcile_on_attach` is the ingest half (an
article joining a record), tools/entity_variants.py the backlog half.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from common.decisions import Noul, NoulAnswer, decide
from common.logging import get_logger
from correlation import entity_fold

logger = get_logger(__name__)

VARIANT_TYPES = ("person", "organization", "company", "government")
MIN_SKELETON = 5
# Pairs per Jev call. verify.py measured batched and pairwise judging equal.
BATCH = 8
# Asked after the attach has committed, off the match lock, but inside the
# handling of one message: a hard ceiling, and a timeout folds nothing.
VARIANT_TIMEOUT_S = 6.0
# The lock correlation/consumer._attach holds: a fold must not interleave with an
# attach writing a mention onto the row being folded.
_LOCK = "SELECT pg_advisory_xact_lock(hashtext('correlation.match_or_create'))"

# Longest first: "chh" before "ch", "ch" before "ck" can see it.
_FOLDS = (("chh", "c"), ("ch", "c"), ("th", "t"), ("dh", "d"), ("bh", "b"), ("kh", "k"), ("gh", "g"),
          ("ph", "f"), ("sh", "s"), ("w", "v"), ("z", "j"), ("q", "k"), ("ck", "k"))

SAME_ENTITY = (
    "{a} and {b} name the same real person or organisation: one name written two ways, transliterated, spelled, "
    "spaced or abbreviated differently (a doubled or dropped letter, an aspirated or unaspirated consonant, a "
    "different vowel, an initial written or left out). They do NOT if the names differ in a way spelling does not "
    "explain: a different first name or surname that only looks alike, two members of one family, or two different "
    "zones, branches or units of an organisation"
)


def skeleton(slug: str) -> str:
    """The consonant skeleton of a slug, word by word: 'smith-machar' -> 'smt mcr'."""
    s = slug.replace("-", " ")
    for a, b in _FOLDS:
        s = s.replace(a, b)
    s = re.sub(r"([a-z])\1+", r"\1", s)
    s = re.sub(r"[aeiouy]", "", s)
    return " ".join(w for w in s.split() if w)


def keys(slug: str) -> set[str]:
    """What two spellings of one name share: the skeleton, when the name is long
    and multi-word enough to key safely, and the slug respaced."""
    out = {"r:" + slug.replace("-", "")}
    sk = skeleton(slug)
    if " " in sk and len(sk.replace(" ", "")) >= MIN_SKELETON:
        out.add("s:" + sk)
    return out


def same_name(a: str, b: str) -> bool:
    return a != b and bool(keys(a) & keys(b))


@dataclass(frozen=True)
class Name:
    id: uuid.UUID
    slug: str
    name: str
    kind: str
    mentions: int


@dataclass(frozen=True)
class Pair:
    variant: Name
    survivor: Name
    evidence: str  # record | verified_link | story
    variant_seen: str  # a record headline the variant is named in
    survivor_seen: str

    @property
    def key(self) -> frozenset:
        return frozenset((self.variant.id, self.survivor.id))


def rank(n: Name) -> tuple:
    """Survivor first: the spelling with the most mentions, so the fewest rows
    move; ties break on id so a rerun picks the same one."""
    return (-n.mentions, str(n.id))


def ordered(a: Name, b: Name) -> tuple[Name, Name]:
    """(variant, survivor)."""
    survivor, variant = sorted((a, b), key=rank)
    return variant, survivor


def _line(n: Name, seen: str) -> str:
    return f'{n.name}, a {n.kind} named in the report "{seen}"'


async def judge(pairs: list[Pair], *, metadata: dict | None = None) -> tuple[list[float], str, float]:
    """Jev's probability, per pair, that both spellings name one entity, the model
    that answered, and the cost (USD). One call; network only, so a failure or a
    timeout raises and the caller folds nothing."""
    state, questions = {}, {}
    for k, p in enumerate(pairs, 1):
        state[f"A_{k}"] = _line(p.variant, p.variant_seen)
        state[f"B_{k}"] = _line(p.survivor, p.survivor_seen)
        questions[f"same_{k}"] = Noul(instructions=SAME_ENTITY.format(a=f"A_{k}", b=f"B_{k}"))
    d = await asyncio.wait_for(
        decide(state, questions, trace_name="entity-variant", metadata={"stage": "correlation", **(metadata or {})}),
        VARIANT_TIMEOUT_S,
    )
    nouls = []
    for k in range(1, len(pairs) + 1):
        answer = d.answers[f"same_{k}"]
        assert isinstance(answer, NoulAnswer)
        nouls.append(answer.noul)
    return nouls, d.model or get_settings().prism_model_decide, d.usage.cost


async def recorded(c, pairs: list[Pair]) -> dict[frozenset, dict]:
    """The verdicts already given for these pairs, either way round."""
    ids = sorted({i for p in pairs for i in p.key}, key=str)
    if not ids:
        return {}
    rows = await c.fetch(
        "SELECT variant_id, survivor_id, noul, journal IS NOT NULL AS folded, reverted_at "
        "FROM entity_variant_verdicts WHERE variant_id = ANY($1::uuid[]) AND survivor_id = ANY($1::uuid[])",
        ids,
    )
    return {frozenset((r["variant_id"], r["survivor_id"])): dict(r) for r in rows}


async def settle(c, pairs: list[Pair], answers: dict[frozenset, tuple[float, str]], *, via: str,
                 fold: bool) -> list[Pair]:
    """Record the new answers ((noul, model) per pair key), and when `fold`, fold
    every pair whose recorded answer is "same" and which has been neither folded
    nor undone. One transaction under the attach lock. Returns the pairs folded."""
    floor = get_settings().prism_entity_variant_min
    folded: list[Pair] = []
    async with c.transaction():
        await c.execute(_LOCK)
        for p in pairs:
            if p.key in answers:
                noul, model = answers[p.key]
                await c.execute(
                    "INSERT INTO entity_variant_verdicts (variant_id, survivor_id, noul, model, via, evidence) "
                    "VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT DO NOTHING",
                    p.variant.id, p.survivor.id, noul, model, via, p.evidence,
                )
        if not fold:
            return folded
        verdicts = await recorded(c, pairs)
        for p in pairs:
            v = verdicts.get(p.key)
            if v is None or v["noul"] < floor or v["folded"] or v["reverted_at"] is not None:
                continue
            if await _fold(c, p, v):
                folded.append(p)
    return folded


async def _fold(c, p: Pair, verdict: dict) -> bool:
    # Either side folded since it was judged (another pair, another run): the next
    # run judges against whatever survived rather than building a chain here.
    live = await c.fetchval(
        "SELECT count(*) FROM entities WHERE id = ANY($1::uuid[]) AND merged_into IS NULL",
        [p.variant.id, p.survivor.id],
    )
    if live < 2:
        return False
    entries = await entity_fold.journal(c, p.variant.id, p.survivor.id)
    await entity_fold.fold_into(c, p.variant.id, p.survivor.id)
    doc = {"format": entity_fold.JOURNAL_FORMAT, "variant": str(p.variant.id), "survivor": str(p.survivor.id),
           "entries": entries}
    await c.execute(
        "UPDATE entity_variant_verdicts SET journal = $3::jsonb WHERE variant_id = $1 AND survivor_id = $2",
        verdict["variant_id"], verdict["survivor_id"], json.dumps(doc),
    )
    return True


async def connect():
    """A connection of its own for the write: the folds are a handful a day, and
    the fold mechanics speak asyncpg, like the tools that share them."""
    import asyncpg

    url = re.sub(r"^postgres(ql)?(\+asyncpg)?://", "postgresql://", get_settings().database_url)
    return await asyncpg.connect(url, timeout=10)


# The record's live cast of the types that fold, and which of it this article named.
_CAST_SQL = text(
    """
    SELECT en.id, en.slug, en.name, en.entity_type, (ae.article_id IS NOT NULL) AS own
    FROM event_entities ee
    JOIN entities en ON en.id = ee.entity_id AND en.merged_into IS NULL AND en.entity_type = ANY(:types)
    LEFT JOIN article_entities ae ON ae.entity_id = en.id AND ae.article_id = :a
    WHERE ee.event_id = :e
    """
)


async def reconcile_on_attach(event_id: uuid.UUID, article_id: uuid.UUID) -> int:
    """The ingest half: the article has joined a record whose cast may already hold
    another spelling of one of its names. Run after the attach commits, so Jev is
    never asked under the match lock; any failure leaves both spellings as they
    are. Returns the number of folds.

    Measured on production 2026-10-01 (14 days): about 14% of articles joining a
    record clash on some skeleton, but most clashes repeat a pair already asked,
    so with the verdict cache it is about 2.5% of articles — 100 to 130 Jev calls
    on a 4,100-article day, under a cent. In a random 50 of those in-record pairs,
    49 were one entity; the 50th (Eastern/Southern Railway) was named by one
    article, which the guard below refuses before Jev is asked.
    """
    settings = get_settings()
    if settings.prism_entity_variants not in ("shadow", "live"):
        return 0
    async with session_scope() as s:
        cast = (await s.execute(_CAST_SQL, {"types": list(VARIANT_TYPES), "a": str(article_id),
                                            "e": str(event_id)})).mappings().all()
        own = [r for r in cast if r["own"]]
        others = [r for r in cast if not r["own"]]
        clashes = [(x, y) for x in own for y in others
                   if x["entity_type"] == y["entity_type"] and same_name(x["slug"], y["slug"])]
        if not clashes:
            return 0
        ids = sorted({str(r["id"]) for pair in clashes for r in pair})
        mentions = dict((await s.execute(text(
            "SELECT entity_id, count(*) FROM article_entities WHERE entity_id = ANY(CAST(:ids AS uuid[])) "
            "GROUP BY entity_id"), {"ids": ids})).all())
        together = {frozenset(r) for r in (await s.execute(text(
            "SELECT a1.entity_id, a2.entity_id FROM article_entities a1 "
            "JOIN article_entities a2 ON a2.article_id = a1.article_id AND a2.entity_id = ANY(CAST(:ids AS uuid[])) "
            "WHERE a1.entity_id = ANY(CAST(:ids AS uuid[])) AND a1.entity_id <> a2.entity_id"), {"ids": ids})).all()}
        title = (await s.execute(text("SELECT title FROM events WHERE id = :e"), {"e": str(event_id)})).scalar() or ""

    def name(r) -> Name:
        return Name(r["id"], r["slug"], r["name"], r["entity_type"], int(mentions.get(r["id"], 0)))

    pairs = [Pair(*ordered(name(x), name(y)), "record", title, title)
             for x, y in clashes if frozenset((x["id"], y["id"])) not in together][:BATCH]
    if not pairs:
        return 0
    c = await connect()
    try:
        known = await recorded(c, pairs)
        ask = [p for p in pairs if p.key not in known]
        answers: dict[frozenset, tuple[float, str]] = {}
        if ask:
            try:
                nouls, model, _ = await judge(ask, metadata={"article_id": str(article_id), "event_id": str(event_id)})
            except Exception as exc:  # noqa: BLE001 — no answer folds nothing; the backlog tool asks again
                logger.warning("entity_variant_judge_failed article=%s error=%s", article_id, str(exc)[:160])
                pairs = [p for p in pairs if p.key in known]
            else:
                answers = {p.key: (n, model) for p, n in zip(ask, nouls, strict=True)}
        if not pairs:
            return 0
        folded = await settle(c, pairs, answers, via="attach", fold=settings.prism_entity_variants == "live")
    finally:
        await c.close()
    for p in folded:
        logger.info("entity_variant_folded variant=%s survivor=%s event=%s", p.variant.name, p.survivor.name, event_id)
    return len(folded)
