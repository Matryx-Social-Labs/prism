"""Candidate retrieval + match scoring for event canonicalization.

Match cascade (strongest first), all persisted in the match trail:
  1. cve_id     — shared CVE identifier (the canonical key for the cyber beachhead)
  2. url_exact  — an article for the same URL already belongs to an event
  3. title_time — trigram title similarity within a time window (pg_trgm)
  4. embedding  — cosine similarity to the event embedding (pgvector)

Identity is never merged: matching links the article to the event; it never
rewrites entities or inflates impact (EduThreat canonicalization rules).
"""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.text import detect_script

logger = logging.getLogger(__name__)

TITLE_SIMILARITY_THRESHOLD = 0.6
EMBEDDING_DISTANCE_THRESHOLD = 0.12  # cosine distance (1 - similarity); near-duplicates only
TIME_WINDOW_DAYS = 4

# Scripts where cosine distance actually carries same-story signal.
#
# Measured against production, 2026-07-28. The embedding model
# (paraphrase-multilingual-mpnet-base-v2) has a COLLAPSED subspace for some
# scripts: unrelated articles land as close as genuine duplicates, so a
# nearest-neighbour query returns an arbitrary neighbour rather than the same
# story.
#
#   script      unrelated-pair floor   median NN dist   unrelated neighbours <=0.12
#   latin       0.2606                 0.2911           1.50
#   devanagari  0.1510                 0.1985           0.54
#   kannada     0.0065                 0.0338           228.4
#   tamil       0.0148                 0.0284           21.2 (of 36 peers)
#
# For Kannada the ROC against distance is the diagonal (AUC ~0.5): excluding 90%
# of unrelated pairs costs ~91% of true duplicates. There is no threshold that
# works, at 0.12 or anywhere — one event absorbed 139 unrelated articles this way.
# So this is NOT a number to tune; the embedding path is simply unusable there and
# those articles must match on shared actors instead.
#
# It is emphatically not "non-Latin is bad" — Devanagari is healthy (69% recall at
# ZERO false positives), and gating on "not English" would needlessly cripple it.
# Allow-list, not deny-list: a script nobody has measured gets the safe path.
# Measure the two columns above before adding one.
EMBEDDING_TRUSTED_SCRIPTS = frozenset({"latin", "devanagari"})
# Cross-language / same-story: shared canonical entities + a looser embedding band.
# A translated retelling scores ~0.42 distance (vs <0.12 for a near-dup) but shares
# the key actors — so require >=2 shared entities AND moderate similarity.
ENTITY_MATCH_MIN_SHARED = 2
ENTITY_MATCH_LOOSE_DISTANCE = 0.45  # was 0.55; retellings sit ~0.42, trim the loose tail
# IDF-weight shared actors (1/df) rather than a df CUTOFF. A magnet (Modi, a major
# party, Cockroach Janta Party df82) contributes almost nothing; a specific actor
# carries the match. A cutoff deleted a trending story's OWN core (CJP/Pradhan/Wangchuk
# at df50-82), so its same-development articles — sharing only those — never merged and
# the story shattered into dozens of single-source events. Down-weight instead: require
# >= ENTITY_MATCH_MIN_SHARED actors AND IDF weight >= ENTITY_MATCH_MIN_IDF, so two
# unrelated events sharing only national magnets (low IDF) still don't merge while a
# same-development cross-language retelling that shares a specific actor (Delhi Metro
# df6 -> 0.167) does. The 0.45 embedding band is the outer guard against topic drift;
# df is window-scoped (recently ubiquitous). Weak types (place/government) still excluded.
ENTITY_MATCH_MIN_IDF = 0.15
# Near-dup band: within this distance ONE IDF-strong actor is enough (two Hindi
# retellings of "16 metro stations shut" sit at ~0.20 and share only "Delhi Metro");
# in the looser 0.25-0.45 band require >=2, since a single shared actor there is more
# likely coincidental.
ENTITY_MATCH_NEAR_DISTANCE = 0.25
# At least ONE shared actor must be specific on its own, not merely specific in
# aggregate. sum(1/df) can clear MIN_IDF from a pile of half-magnets, which is how
# two unrelated blobs that both mention several national figures reach each other.
# 0.1 means df <= 10 events in the window — appearing in ten stories in four days
# is still a particular actor, not a fixture.
#
# This hardens the gate; it does not close the feedback loop the 139-article event
# exposed. That event accumulated 978 entities, and _match_by_entities compares
# against an event's WHOLE accumulated set, so each bad merge widens the opening
# for the next. Bounding it properly means knowing which entities are core to the
# event rather than inherited from something it wrongly absorbed — and
# event_entities has no per-article link, so that is a schema change, not a
# tweak. Left explicit rather than half-solved.
ENTITY_MATCH_MIN_TOP_IDF = 0.1
ENTITY_MATCH_TYPES = ("person", "company", "organization")


@dataclass
class Match:
    event_id: uuid.UUID
    match_type: str
    match_score: float


async def find_event(
    session: AsyncSession,
    *,
    cve_ids: list[str],
    url: str | None,
    title: str,
    published_at,
    embedding: list[float] | None,
    entity_slugs: list[str] | None = None,
    cve_record: bool = False,
) -> Match | None:
    if cve_ids:
        match = await _match_by_cve(session, cve_ids)
        if match:
            return match

    # Authoritative CVE records (NVD/KEV) are one-event-per-CVE by
    # construction: distinct CVEs must never merge, and their boilerplate
    # descriptions ("vulnerability in X allows...") make title/embedding
    # similarity meaningless. Identity match or a new event — nothing fuzzy.
    if cve_record:
        return None

    if url:
        match = await _match_by_url(session, url)
        if match:
            return match

    match = await _match_by_title(session, title, published_at)
    if match:
        return match

    # Distance alone is only evidence where the model's subspace for this script
    # isn't collapsed (see EMBEDDING_TRUSTED_SCRIPTS). Where it is, skipping
    # straight to the actor path is the whole fix: of the 139 articles that piled
    # into one Kannada event, 120 arrived here, and not one of them shared two
    # actors with the founding article.
    trusted = detect_script(title) in EMBEDDING_TRUSTED_SCRIPTS

    if embedding is not None and trusted:
        match = await _match_by_embedding(session, embedding, published_at)
        if match:
            return match

    # Cross-language / same-story: same key actors + a looser embedding band.
    if entity_slugs and embedding is not None:
        match = await _match_by_entities(
            session,
            entity_slugs,
            embedding,
            published_at,
            # The one-strong-actor shortcut leans on the near-dup band being
            # meaningful. For a collapsed script it isn't: 0.25 spans 54% of all
            # unrelated Kannada pairs, which is how 18 more articles reached that
            # same event down this path. Two actors, always.
            allow_single_actor=trusted,
        )
        if match:
            return match

    return None


async def _match_by_cve(session: AsyncSession, cve_ids: list[str]) -> Match | None:
    result = await session.execute(
        text(
            """
            SELECT e.id
            FROM events e
            WHERE jsonb_exists_any(e.projection -> 'cyber' -> 'cve_ids',
                                   CAST(:cve_ids AS text[]))
            ORDER BY e.last_updated_at DESC
            LIMIT 1
            """
        ),
        {"cve_ids": cve_ids},
    )
    event_id = result.scalar_one_or_none()
    if event_id:
        return Match(event_id=event_id, match_type="cve_id", match_score=1.0)
    return None


async def _match_by_url(session: AsyncSession, url: str) -> Match | None:
    result = await session.execute(
        text(
            """
            SELECT em.event_id
            FROM event_memberships em
            JOIN articles a ON a.id = em.article_id
            JOIN raw_items ri ON ri.id = a.raw_item_id
            WHERE ri.url = :url
            LIMIT 1
            """
        ),
        {"url": url},
    )
    event_id = result.scalar_one_or_none()
    if event_id:
        return Match(event_id=event_id, match_type="url_exact", match_score=1.0)
    return None


async def _match_by_title(session: AsyncSession, title: str, published_at) -> Match | None:
    result = await session.execute(
        text(
            f"""
            SELECT e.id, similarity(e.title, :title) AS sim
            FROM events e
            WHERE similarity(e.title, :title) >= :threshold
              AND (CAST(:published_at AS timestamptz) IS NULL
                   OR e.last_updated_at >= CAST(:published_at AS timestamptz) - interval '{TIME_WINDOW_DAYS} days')
            ORDER BY sim DESC
            LIMIT 1
            """
        ),
        {"title": title, "threshold": TITLE_SIMILARITY_THRESHOLD, "published_at": published_at},
    )
    row = result.first()
    if row:
        return Match(event_id=row.id, match_type="title_time", match_score=float(row.sim))
    return None


async def _match_by_entities(
    session: AsyncSession,
    entity_slugs: list[str],
    embedding: list[float],
    published_at,
    allow_single_actor: bool = True,
) -> Match | None:
    """Recent event within the looser embedding band that shares enough IDF-weighted
    canonical actors with this article — merges cross-language / translated retellings
    the near-dup threshold misses. Actors are weighted 1/df, so a shared national magnet
    counts for almost nothing (two unrelated events sharing only Modi/Congress won't
    merge) while a specific actor carries a same-development retelling. Requires >=2
    shared actors in the loose band, but only 1 when the embedding is itself near-dup
    (<=0.25) — two Hindi retellings of the same event that share only "Delhi Metro".
    Weak types (place/government) don't count."""
    vector_literal = "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"
    result = await session.execute(
        text(
            f"""
            WITH ent_df AS (
                SELECT ent.id, count(DISTINCT ee.event_id)::float AS df
                FROM entities ent
                JOIN event_entities ee ON ee.entity_id = ent.id
                JOIN events ev ON ev.id = ee.event_id
                WHERE ent.slug = ANY(:slugs)
                  AND ent.entity_type = ANY(:types)
                  AND (CAST(:published_at AS timestamptz) IS NULL
                       OR ev.last_updated_at >= CAST(:published_at AS timestamptz) - interval '{TIME_WINDOW_DAYS} days')
                GROUP BY ent.id
            )
            SELECT e.id,
                   sum(1.0 / d.df) AS idf,
                   (e.embedding <=> CAST(:vec AS vector)) AS dist
            FROM ent_df d
            JOIN event_entities ee ON ee.entity_id = d.id
            JOIN events e ON e.id = ee.event_id
            WHERE e.embedding IS NOT NULL
              AND (e.embedding <=> CAST(:vec AS vector)) <= :dist_threshold
              AND (CAST(:published_at AS timestamptz) IS NULL
                   OR e.last_updated_at >= CAST(:published_at AS timestamptz) - interval '{TIME_WINDOW_DAYS} days')
            GROUP BY e.id, e.embedding
            HAVING (
                       count(DISTINCT d.id) >= :min_shared
                       OR (count(DISTINCT d.id) >= 1
                           AND min(e.embedding <=> CAST(:vec AS vector)) <= :near_dist)
                   )
                   AND sum(1.0 / d.df) >= :min_idf
                   AND max(1.0 / d.df) >= :min_top_idf
            ORDER BY idf DESC, dist ASC
            LIMIT 1
            """
        ),
        {
            "vec": vector_literal,
            "slugs": entity_slugs,
            "types": list(ENTITY_MATCH_TYPES),
            "min_idf": ENTITY_MATCH_MIN_IDF,
            "min_top_idf": ENTITY_MATCH_MIN_TOP_IDF,
            "dist_threshold": ENTITY_MATCH_LOOSE_DISTANCE,
            "min_shared": ENTITY_MATCH_MIN_SHARED,
            # -1 is unreachable for a cosine distance, so the single-actor
            # branch of the HAVING can never fire — >=2 shared actors becomes
            # the only way in.
            "near_dist": ENTITY_MATCH_NEAR_DISTANCE if allow_single_actor else -1.0,
            "published_at": published_at,
        },
    )
    row = result.first()
    if row:
        return Match(event_id=row.id, match_type="entity_overlap", match_score=1.0 - float(row.dist))
    return None


async def _match_by_embedding(
    session: AsyncSession, embedding: list[float], published_at
) -> Match | None:
    vector_literal = "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"
    result = await session.execute(
        text(
            f"""
            SELECT e.id, (e.embedding <=> CAST(:vec AS vector)) AS dist
            FROM events e
            WHERE e.embedding IS NOT NULL
              AND (e.embedding <=> CAST(:vec AS vector)) <= :threshold
              AND (CAST(:published_at AS timestamptz) IS NULL
                   OR e.last_updated_at >= CAST(:published_at AS timestamptz) - interval '{TIME_WINDOW_DAYS} days')
            ORDER BY dist ASC
            LIMIT 1
            """
        ),
        {"vec": vector_literal, "threshold": EMBEDDING_DISTANCE_THRESHOLD, "published_at": published_at},
    )
    row = result.first()
    if row:
        return Match(
            event_id=row.id, match_type="embedding", match_score=1.0 - float(row.dist)
        )
    return None
