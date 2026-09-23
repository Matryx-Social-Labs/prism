"""Which quotes on a speaker card are one statement, and which are a translation.

VERBATIM IS CHECKED AGAINST THE ARTICLE, NOT THE SPEAKER (enrichment/claims.py).
An outlet writing in its own language prints its own translation, and that
translation passes the verbatim check perfectly. The extractor canonicalises
speaker names to English, which puts that translation on the same card as the
original. Two consequences, and this module answers both:

1. ONE STATEMENT PRINTED TWICE. Times of India and Prajavani both quote Giorgia
   Meloni on the same sentence; the card shows it as two quotes and spends its
   two-quote fold on one thing she said. When the same statement appears in two
   languages, at most one of them can be the words as spoken — that is
   arithmetic, not judgement, and it is what lets the card say so honestly.

2. A LONE TRANSLATION. TV9 Kannada quotes Donald Trump in Kannada and nothing
   else on the story quotes him. There is no second language on the card to
   compare against, so the card prints the Kannada as his words.

FOUNDER DECISION D-quote-4 (2026-09-23) fixes what a model may do here: it may
DOWNGRADE a claim Prism is making, never assert one. So the only question about
a single quote is one-sided — "were these words spoken in the language this
article printed them in?" — and only a confident NO changes anything: the quote
is then labelled as the outlet's translation. Prism never asks which language
the words WERE spoken in, because printing that would put a model's guess on
the same line as verbatim evidence, which is what D4 removed.

ONE CALL PER SPEAKER CARD. Jev answers every question in one parallel pass, so
the "spoken here?" question for each quote and the "same statement?" question
for each cross-language pair ride together. Verdicts are stored per card with a
hash of the claims they were asked about; the sweep re-asks when a new report
changes the card, and the read path applies any verdict whose quotes are still
on it.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.decisions import Decisions, Noul, Question, decide
from common.languages import display_name
from common.logging import get_logger
from enrichment.claims import dedupe_sources, speaker_key

logger = get_logger(__name__)

# PROVISIONAL crossing points. Neither has been measured against labels yet; the
# verdicts are recorded as raw probabilities precisely so these can be set from
# tools/gold_renderings without asking the model again. Nothing is served until
# they are (PRISM_QUOTE_VERDICTS, off by default).
SAME_MIN = 0.8
# "Spoken in the language printed?" under this is a confident NO. Deliberately
# low: an unsure answer leaves the quote exactly as it is today.
SPOKEN_MAX = 0.2

# A card with twenty quotes in three languages is 130 pairs; the fold shows two.
# Past this many pairs the rest stay unjudged, which is today's behaviour.
MAX_PAIRS = 40
MAX_CLAIMS = 24

QUESTIONS_VERSION = "renderings-v1"
JUDGE_CONCURRENCY = 8


@dataclass(frozen=True)
class CardClaim:
    key: str
    lang: str | None
    source: str
    quote: str
    claim_text: str


def claim_key(article_id: str, quote: str) -> str:
    """A quote's identity: the article and the words. Not its position — a
    re-extraction or a role backfill can reorder the claims array, and a
    verdict pinned to an index would then describe a different sentence."""
    return f"{article_id}:{hashlib.md5(quote.encode()).hexdigest()[:12]}"


def card_hash(claims: list[CardClaim]) -> str:
    """What the verdicts were asked about. A changed card is re-asked."""
    body = "|".join(sorted(c.key for c in claims)) + "|" + QUESTIONS_VERSION
    return hashlib.sha1(body.encode()).hexdigest()[:16]


def cross_language_pairs(claims: list[CardClaim]) -> list[tuple[int, int]]:
    """Pairs worth asking "same statement?" about: different printed languages.

    Two quotes in ONE language are either different sentences or the same
    sentence copied, and the card already handles copies (dedupe_sources); the
    question only earns its cost where a translation could be hiding."""
    out = [
        (i, j)
        for i in range(len(claims))
        for j in range(i + 1, len(claims))
        if claims[i].lang and claims[j].lang and claims[i].lang != claims[j].lang
    ]
    return out[:MAX_PAIRS]


def questions_for(speaker: str, event_title: str, claims: list[CardClaim]) -> tuple[dict[str, Any], dict[str, Question]]:
    """The state and questions for one card: every quote once, every
    cross-language pair once. Keys index into `claims`."""
    claims = claims[:MAX_CLAIMS]
    state = {
        "speaker": speaker,
        "story": event_title,
        "quotes": [
            {
                "n": i,
                "printed_in": display_name(c.lang) or "unknown",
                "outlet": c.source,
                "words": c.quote,
                "meaning_in_english": c.claim_text,
            }
            for i, c in enumerate(claims)
        ],
    }
    questions: dict[str, Question] = {}
    for i, c in enumerate(claims):
        if not c.lang:
            continue
        questions[f"spoken_{i}"] = Noul(
            instructions=(
                f"Did {speaker} most likely say quote {i} themselves in "
                f"{display_name(c.lang)} — the language {c.source} printed it in — rather "
                f"than saying it in another language that {c.source} then translated?"
            )
        )
    for i, j in cross_language_pairs(claims):
        questions[f"same_{i}_{j}"] = Noul(
            instructions=(
                f"Are quote {i} and quote {j} the same statement by {speaker}, reported "
                "in two languages, rather than two different things they said?"
            )
        )
    return state, questions


def verdicts_from(answers: Decisions, claims: list[CardClaim]) -> dict[str, Any]:
    """Raw probabilities keyed by claim identity, never by position, so they
    survive the card being re-ordered or partly deduped at read time."""
    claims = claims[:MAX_CLAIMS]
    spoken: dict[str, float] = {}
    same: list[list[Any]] = []
    for name, ans in answers.answers.items():
        p = getattr(ans, "noul", None)
        if p is None:
            continue
        parts = name.split("_")
        if parts[0] == "spoken":
            spoken[claims[int(parts[1])].key] = round(float(p), 4)
        elif parts[0] == "same":
            a, b = claims[int(parts[1])].key, claims[int(parts[2])].key
            same.append([a, b, round(float(p), 4)])
    return {"version": QUESTIONS_VERSION, "spoken": spoken, "same": same}


def apply(
    keys: list[str],
    verdicts: list[dict[str, Any]],
    *,
    same_min: float = SAME_MIN,
    spoken_max: float = SPOKEN_MAX,
) -> tuple[dict[str, str], set[str]]:
    """(utterance id per quote key, the keys that are translations).

    Only verdicts whose quotes are ALL still on the card count. An utterance id
    is the smallest key in its group, so the same group gets the same id on
    every read. A quote with no verdict is left exactly as it is today — no
    group, not a translation — which is what makes an unjudged card safe."""
    present = set(keys)
    parent = {k: k for k in keys}

    def find(k: str) -> str:
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    translated: set[str] = set()
    for v in verdicts:
        for k, p in (v.get("spoken") or {}).items():
            if k in present and float(p) < spoken_max:
                translated.add(k)
        for a, b, p in v.get("same") or []:
            if a in present and b in present and float(p) >= same_min:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[max(ra, rb)] = min(ra, rb)
    groups: dict[str, list[str]] = {}
    for k in keys:
        groups.setdefault(find(k), []).append(k)
    utterance = {k: root for root, members in groups.items() if len(members) > 1 for k in members}
    return utterance, translated


# ── The sweep: judge the cards that changed ─────────────────────────────────

# The rows a speaker card is built from — the story page's, minus what it
# does not need. Read by the sweep and by tools/gold_renderings.
CARD_SOURCES = text(
    """
    SELECT a.id AS article_id, s.name AS source_name, ri.url, ri.url_canonical,
           ri.published_at, ri.language AS lang, en.shared_fields -> 'claims' AS claims
    FROM event_memberships em
    JOIN articles a ON a.id = em.article_id
    JOIN raw_items ri ON ri.id = a.raw_item_id
    JOIN sources s ON s.id = ri.source_id
    JOIN enrichments en ON en.article_id = a.id
    WHERE em.event_id = :eid
    ORDER BY ri.published_at DESC NULLS LAST
    """
)


def cards_from(sources: list[dict[str, Any]]) -> dict[str, tuple[str, list[CardClaim]]]:
    """speaker key -> (the name as first printed, that speaker's quotes).

    Built from the SAME rows, in the same order and with the same document
    dedupe, as the story page's card (api/routes/events.group_claims), so a
    verdict is asked about the card a reader actually sees."""
    cards: dict[str, tuple[str, list[CardClaim]]] = {}
    for src in dedupe_sources(sources):
        claims = src.get("claims")
        if isinstance(claims, str):
            claims = json.loads(claims)
        if not isinstance(claims, list):
            continue
        for c in claims:
            if not isinstance(c, dict):
                continue
            speaker, quote = c.get("speaker"), c.get("quote_text")
            if not isinstance(speaker, str) or not isinstance(quote, str) or not speaker.strip() or not quote.strip():
                continue
            key = speaker_key(speaker)
            name, bucket = cards.setdefault(key, (speaker.strip(), []))
            bucket.append(CardClaim(
                key=claim_key(str(src["article_id"]), quote.strip()),
                lang=src.get("lang"),
                source=src["source_name"],
                quote=quote.strip(),
                claim_text=str(c.get("claim_text") or ""),
            ))
    return cards


async def judge_event(session: AsyncSession, event_id: Any, title: str, *, write: bool = True) -> dict[str, Any]:
    """Ask about every card on one event whose quotes changed since it was last
    asked. Returns what was asked and what it cost; writes only when `write`."""
    rows = [dict(r) for r in (await session.execute(CARD_SOURCES, {"eid": str(event_id)})).mappings().all()]
    cards = cards_from(rows)
    known = {
        r.speaker_key: r.card_hash
        for r in (await session.execute(
            text("SELECT speaker_key, card_hash FROM claim_verdicts WHERE event_id = :eid"), {"eid": str(event_id)}
        )).all()
    }
    todo = [(k, name, claims) for k, (name, claims) in cards.items()
            if any(c.lang for c in claims) and known.get(k) != card_hash(claims)]
    sem = asyncio.Semaphore(JUDGE_CONCURRENCY)

    async def one(key: str, name: str, claims: list[CardClaim]) -> tuple[str, str, dict[str, Any], Decisions] | None:
        state, questions = questions_for(name, title, claims)
        if not questions:
            return None
        async with sem:
            try:
                answers = await decide(state, questions, trace_name="quote-renderings",
                                       metadata={"event_id": str(event_id), "speaker": name})
            except Exception as exc:  # noqa: BLE001 — an unjudged card is today's card; the next sweep retries
                logger.warning("renderings_judge_failed", event_id=str(event_id), speaker=name, error=str(exc)[:160])
                return None
        return key, card_hash(claims), verdicts_from(answers, claims), answers

    judged = [r for r in await asyncio.gather(*(one(*t) for t in todo)) if r]
    if write and judged:
        await session.execute(
            text(
                """
                INSERT INTO claim_verdicts (event_id, speaker_key, card_hash, verdicts, model, cost)
                VALUES (:e, :k, :h, CAST(:v AS jsonb), :m, :c)
                ON CONFLICT (event_id, speaker_key) DO UPDATE
                SET card_hash = EXCLUDED.card_hash, verdicts = EXCLUDED.verdicts,
                    model = EXCLUDED.model, cost = EXCLUDED.cost, created_at = now()
                """
            ),
            [{"e": str(event_id), "k": k, "h": h, "v": json.dumps(v), "m": a.model, "c": a.usage.cost}
             for k, h, v, a in judged],
        )
    return {
        "cards": len(cards),
        "judged": len(judged),
        "cost": sum(a.usage.cost for *_, a in judged),
        "verdicts": {k: v for k, _, v, _ in judged},
    }


async def recent_events(session: AsyncSession, *, days: int, limit: int, offset: int = 0) -> list[tuple[Any, str]]:
    """Events updated in the window that hold at least one quote, newest first."""
    rows = (await session.execute(
        text(
            """
            SELECT e.id, e.title FROM events e
            WHERE e.last_updated_at > now() - make_interval(days => :d)
              AND EXISTS (
                SELECT 1 FROM event_memberships m JOIN enrichments en ON en.article_id = m.article_id
                WHERE m.event_id = e.id AND jsonb_typeof(en.shared_fields -> 'claims') = 'array'
                  AND jsonb_array_length(en.shared_fields -> 'claims') > 0)
            ORDER BY e.last_updated_at DESC, e.id
            LIMIT :n OFFSET :o
            """
        ),
        {"d": days, "n": limit, "o": offset},
    )).all()
    return [(r.id, r.title or "") for r in rows]


async def sweep(session: AsyncSession, *, days: int = 2, limit: int = 200) -> dict[str, float]:
    """The worker's pass: recently touched events, only the cards that changed.
    A card nobody touched costs one indexed read and nothing else."""
    judged, cost = 0, 0.0
    for event_id, title in await recent_events(session, days=days, limit=limit):
        out = await judge_event(session, event_id, title)
        judged += out["judged"]
        cost += out["cost"]
    if judged:
        logger.info("renderings_sweep", judged=judged, cost=round(cost, 5))
    return {"judged": judged, "cost": cost}


def demo() -> None:
    """Self-check of the pure parts: pairs cross languages only, verdicts key by
    identity, stale verdicts are ignored, unsure never downgrades."""
    en = CardClaim(claim_key("a1", "we will act"), "en", "Mint", "we will act", "They will act.")
    kn = CardClaim(claim_key("a2", "ನಾವು ಕ್ರಮ"), "kn", "Prajavani", "ನಾವು ಕ್ರಮ", "They will act.")
    en2 = CardClaim(claim_key("a3", "another thing"), "en", "Hindu", "another thing", "Something else.")
    assert cross_language_pairs([en, kn, en2]) == [(0, 1), (1, 2)]
    state, qs = questions_for("Giorgia Meloni", "Italy schools", [en, kn, en2])
    assert set(qs) == {"spoken_0", "spoken_1", "spoken_2", "same_0_1", "same_1_2"}, qs.keys()
    assert state["quotes"][1]["printed_in"] == "Kannada"
    v = {"spoken": {en.key: 0.9, kn.key: 0.05, en2.key: 0.5}, "same": [[en.key, kn.key, 0.93], [kn.key, en2.key, 0.1]]}
    utt, tr = apply([en.key, kn.key, en2.key], [v])
    assert utt[en.key] == utt[kn.key] and en2.key not in utt
    assert tr == {kn.key}, tr  # 0.5 is unsure: unsure never downgrades
    utt, tr = apply([en.key, en2.key], [v])  # the Kannada report left the event
    assert utt == {} and tr == set()
    assert card_hash([en, kn]) == card_hash([kn, en]) != card_hash([en])
    print("ok: pairs, identity keys, stale verdicts, one-sided downgrade")


if __name__ == "__main__":
    demo()
