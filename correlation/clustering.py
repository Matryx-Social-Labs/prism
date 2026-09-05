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

from common.config import get_settings
from common.text import detect_script

logger = logging.getLogger(__name__)

TITLE_SIMILARITY_THRESHOLD = 0.6
TIME_WINDOW_DAYS = 4

# ── Distance scale: these MOVE WITH THE MODEL ────────────────────────────────
# Cosine distances are not comparable across embedding models, and the failure
# mode is silent in both directions. Swapping the model while keeping these
# numbers was measured through the full cascade against gold_pairs:
#
#   mpnet, its own thresholds     tp 28  fp  3  P 0.9032  R 0.4590  Cdet 0.5766
#   mE5,   MPNET's thresholds     tp 47  fp 76  P 0.3821  R 0.7705  Cdet 1.1316  <-- 25x the false merges
#   mE5,   its own thresholds     tp 31  fp  8  P 0.7949  R 0.5082  Cdet 0.5868
#
# E5 compresses the space: its same-event median distance is 0.063 and its
# different-event median 0.145, so mpnet's 0.12 sits BETWEEN them and sweeps in
# roughly a third of unrelated pairs. Nothing errors; the feed just starts fusing
# unrelated stories.
#
# Keyed by model so the two can never drift apart. Derived by matching PERCENTILES
# of the pairwise distance distribution (tools/tune_embed_threshold), not by a
# constant ratio — the distributions differ in shape as well as width.
# EVERY cosine distance in the correlation layer lives here. Three of them did;
# four did not, and stayed raw mpnet numbers through a model swap:
# threads.EMBED_NEAR / EMBED_FAR / STORY_MAX_EMBED_DIST and
# partition.STORY_EMBED_EDGE_MAX_DIST. The last was added with the v2 story layer
# after tools/tune_embed_threshold was written, so it was not even on that tool's
# list of what a swap invalidates.
#
# The failure would have been silent and severe: mE5's same-event median distance
# is 0.063 against mpnet's 0.195, so a 0.50 edge cutoff admits nearly every pair,
# the kNN graph goes dense, and the story layer over-merges. No error, no log.
#
# mE5 values are PERCENTILE-matched against mpnet's distribution by
# tools/tune_embed_threshold, not rescaled by a constant ratio — the two
# distributions differ in shape as well as width.
_SCALE = {
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": {
        "embedding": 0.12, "entity_near": 0.25, "entity_loose": 0.45,
        "embed_far": 0.45, "story_max": 0.55, "story_edge_max": 0.50,
    },
    "intfloat/multilingual-e5-base": {
        "embedding": 0.050, "entity_near": 0.079, "entity_loose": 0.106,
        "embed_far": 0.106, "story_max": 0.127, "story_edge_max": 0.115,
    },
}


def _scale() -> dict:
    """Thresholds for the CONFIGURED model.

    An unknown model falls back to the incumbent's numbers and says so loudly —
    silently guessing a scale for an unmeasured model is how a swap turns into a
    quiet 25x increase in false merges.
    """
    name = get_settings().prism_embed_model
    if name not in _SCALE:
        logger.warning(
            "embedding_model_uncalibrated model=%s — using incumbent thresholds; "
            "run tools/tune_embed_threshold before trusting match quality", name
        )
        return _SCALE["sentence-transformers/paraphrase-multilingual-mpnet-base-v2"]
    return _SCALE[name]


EMBEDDING_DISTANCE_THRESHOLD = _scale()["embedding"]  # cosine distance; near-duplicates only

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
ENTITY_MATCH_LOOSE_DISTANCE = _scale()["entity_loose"]  # outer guard against topic drift
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
ENTITY_MATCH_NEAR_DISTANCE = _scale()["entity_near"]
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
# ...unless the cast overlap is broad. Requiring an individually-specific actor
# turned out to reject real stories: an article sharing EIGHT actors with its
# event (Amit Shah, Rahul Gandhi, the CJP, the presiding judge) was refused
# because its most specific shared actor sat at df 12, just past the df<=10 the
# threshold implies. Eight shared actors is not a coincidence, and demanding a
# rare one on top of that is a second tax on the same evidence. Either a
# genuinely specific actor, OR a cast overlap wide enough to stand on its own.
ENTITY_MATCH_BROAD_SHARED = 4
# How many of an event's OWN articles must name an actor for it to count as that
# event's actor. event_entities is cumulative — an actor arrives when an article
# is absorbed and stays forever, even after the article is moved away — so a
# single mistaken merge permanently widens what the event can match. One event
# reached 978 actors that way, at which point the gate is open.
#
# Requiring two of the event's articles to name it means an actor inherited from
# one absorbed article contributes nothing, which is exactly the feedback loop.
# Single-article events are exempt: they have nothing to corroborate with, and
# the >=2-shared-actor rule already guards them.
ENTITY_MATCH_MIN_ARTICLES = 2
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
            title=title,
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


# Which similarity the title tier uses. pg_trgm compares CHARACTER trigrams, so
# it scores shared boilerplate and a shared rare name the same way; the cosine
# variant weights words by IDF, so a distinctive name carries the match. Measured
# on gold_pairs BATCH 2 (held out) as a standalone signal:
#
#     production cascade            P 0.629  R 0.667  F1 0.647  Cdet 0.260
#     title IDF cosine >= 0.39      P 0.944  R 0.515  F1 0.667  Cdet 0.083
#
# That is a pairwise number, and pairwise numbers have over-promised three times
# in this file (see TITLE_COSINE_GATE below, which looked excellent and lost).
# So this is a switch scored through the real cascade by tools/score_cascade,
# not a default flipped on the table above.
#
# MEASURED 2026-09-04, and the answer is DO NOT SHIP — but not for the usual
# reason. Full cascade replay, 328 events, both tiers, gold_pairs split into the
# fold its threshold was fitted on and the fold held out:
#
#                     all 398        batch1 (fitted)   batch2 (HELD OUT)
#     trigram >=0.6   Cdet 0.5930    Cdet 0.5268       Cdet 0.6555
#     cosine  >=0.39  Cdet 0.5658    Cdet 0.7143       Cdet 0.4737
#
# On the combined set cosine wins by 0.027 and looks shippable. Split, the two
# folds disagree violently AND IN THE WRONG DIRECTION: cosine is far WORSE on the
# fold its threshold was fitted to and far better on the held-out one. Overfitting
# produces the opposite shape, so this is not a tuned-threshold story — the two
# "independent samples of the same distribution" are not behaving like one
# distribution.
#
# The mechanism is 7 events. Cosine makes 9 false merges in total, 8 of them in
# batch 1 (8/128 negatives) against 1 in batch 2 (1/209). Cdet weights a false
# alarm 4x, so that single cluster of 8 swings batch 1 by 0.25 on its own. With 28
# and 33 positive pairs per fold, a seven-event difference is not a finding.
#
# So the honest reading is that GOLD_PAIRS IS TOO SMALL TO DECIDE THIS, and the
# combined number hides that rather than resolving it. The fix is a bigger gold
# set, which is what the labelling rounds are for — not a different threshold.
# Re-run `tools/score_cascade --title-tier cosine` when gold_pairs grows; the
# placement maps are cached under .cache/cascade_placements_*.json so re-scoring
# a past run is free.
#
# Fifth time a pairwise number has over-promised here: the plan's table records
# this signal at Cdet 0.083.
TITLE_TIER = "trigram"
TITLE_COSINE_THRESHOLD = 0.39


async def _match_by_title(session: AsyncSession, title: str, published_at) -> Match | None:
    if TITLE_TIER == "cosine":
        return await _match_by_title_cosine(session, title, published_at)
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


async def _match_by_title_cosine(
    session: AsyncSession, title: str, published_at
) -> Match | None:
    """Best in-window event by IDF-weighted word cosine over titles.

    No trigram prefilter. One would be cheap, but every prefilter is a ceiling on
    recall, and the pairs this tier exists to catch are exactly the ones trigram
    scores low — a prefilter would silently cap the thing being measured. The
    scan it replaces was a full scan anyway: `similarity(e.title, :title) >= 0.6`
    is a function call per row, not an index probe, so this moves the same work
    into Python and does less of it in the database.
    """
    from tools.title_cosine import cosine, load_idf

    rows = (await session.execute(
        text(
            f"""
            SELECT e.id, e.title
            FROM events e
            WHERE e.title IS NOT NULL AND e.title <> ''
              AND (CAST(:published_at AS timestamptz) IS NULL
                   OR e.last_updated_at >= CAST(:published_at AS timestamptz) - interval '{TIME_WINDOW_DAYS} days')
            -- Ordered so a tie between two equally-scoring events resolves the
            -- same way every run. Leiden's order-sensitivity already cost this
            -- repo a silently-varying boundary on identical data.
            ORDER BY e.id
            """
        ),
        {"published_at": published_at},
    )).all()
    if not rows:
        return None
    idf = load_idf()
    best, best_score = None, 0.0
    for row in rows:
        score = cosine(title, row.title, idf)
        if score > best_score:
            best, best_score = row.id, score
    if best is None or best_score < TITLE_COSINE_THRESHOLD:
        return None
    return Match(event_id=best, match_type="title_time", match_score=best_score)


# Optional confirming gate on the entity path: require the candidate event's
# title to agree with this article's, by IDF-weighted word cosine.
#
# OFF BY DEFAULT AND NOT YET SHIPPED. The attribution that motivates it is sound
# — entity_overlap made 22 of 25 wrong merges at precision 0.353 while the other
# tiers were near-perfect — but a headline-agreement gate on this exact path was
# already built on this exact data and LOST at replay:
#
#                             without gate      with gate
#     clusters (41 gold)           40               80
#     B-cubed recall             0.8227           0.5178
#
# Predicted recall cost 9%, actual 37%. The cause is compounding, which pairwise
# scoring cannot see: every rejected merge starts a NEW event, that event becomes
# a smaller wrong candidate for the next article, and the story shatters. So this
# is wired as a measurable switch, not a default — flip it only on cascade-replay
# evidence (tools/score_cascade), never on a pairwise number.
#
# MEASURED 2026-08-28, and it LOSES — the third time this shape has been tried
# here and the third time the cascade contradicted the pairwise number:
#
#     pairwise, threshold 0.45      P 0.9706  fp 1     (looks excellent)
#     cascade, no gate              tp 28  fp 3  P 0.9032  R 0.4590  Cdet 0.5766
#     cascade, gate at 0.45         tp 24  fp 0  P 1.0000  R 0.3934  Cdet 0.6066
#
# The gate does exactly what it promised — it eliminates EVERY false merge, P 1.0 —
# and still loses, because it costs 4 true merges to save 3 false ones. Cdet
# already weights a false alarm 4x a miss, so this is not a weighting artefact:
# perfect precision is not worth having when recall pays for it.
#
# The mechanism is compounding, which no pairwise measurement can see: a rejected
# merge does not merely fail to merge, it CREATES a new event, and that event is
# then a smaller, wronger candidate for the next article. Leave this off.
TITLE_COSINE_GATE: float | None = None


async def _match_by_entities(
    session: AsyncSession,
    entity_slugs: list[str],
    embedding: list[float],
    published_at,
    allow_single_actor: bool = True,
    title: str = "",
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
            -- The event's OWN cast: actors named by at least :min_articles of the
            -- articles it currently holds, rather than every actor it has ever
            -- absorbed. This is what stops a bad merge from widening the gate.
            JOIN (
                SELECT em.event_id, ae.entity_id
                FROM event_memberships em
                JOIN article_entities ae ON ae.article_id = em.article_id
                -- Only THIS article's actors can survive the join below
                -- (ee.entity_id = d.id), so restricting here is exactly
                -- equivalent: the aggregate is already grouped BY entity_id, and
                -- filtering rows by entity_id cannot change a count within a
                -- group keyed on it.
                --
                -- Without it Postgres has no parameterised path into the
                -- aggregate, so it materialises (event, entity) over the WHOLE
                -- corpus on every article that reaches this path — measured on
                -- production at 51,840 rows sorted with a 2,952 kB external merge
                -- to disk. 273.7ms -> 5.9ms, identical output.
                WHERE ae.entity_id IN (SELECT id FROM ent_df)
                GROUP BY em.event_id, ae.entity_id
                HAVING count(DISTINCT em.article_id) >= :min_articles
                    OR (SELECT count(*) FROM event_memberships m2
                        WHERE m2.event_id = em.event_id) < :min_articles
            ) ee ON ee.entity_id = d.id
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
                   AND (max(1.0 / d.df) >= :min_top_idf
                        OR count(DISTINCT d.id) >= :broad_shared)
            ORDER BY idf DESC, dist ASC
            LIMIT 1
            """
        ),
        {
            "vec": vector_literal,
            "slugs": entity_slugs,
            "types": list(ENTITY_MATCH_TYPES),
            "min_articles": ENTITY_MATCH_MIN_ARTICLES,
            "min_idf": ENTITY_MATCH_MIN_IDF,
            "min_top_idf": ENTITY_MATCH_MIN_TOP_IDF,
            "broad_shared": ENTITY_MATCH_BROAD_SHARED,
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
    if not row:
        return None
    if TITLE_COSINE_GATE is not None and title:
        from tools.title_cosine import cosine, load_idf

        cand = (await session.execute(
            text("SELECT title FROM events WHERE id = :i"), {"i": str(row.id)}
        )).scalar_one_or_none()
        if cand and cosine(title, cand, load_idf()) < TITLE_COSINE_GATE:
            return None
    return Match(event_id=row.id, match_type="entity_overlap", match_score=1.0 - float(row.dist))


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
