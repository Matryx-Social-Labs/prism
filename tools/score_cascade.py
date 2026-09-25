"""Score the FULL match cascade against gold_pairs, per embedding model. Offline.

    uv run python -m tools.score_cascade

WHY THIS AND NOT tools/tune_embed_threshold. That tool scores the embedding tier
ALONE — it asks "if cosine distance were the only signal, how good is it?". The
production matcher is a five-tier cascade (CVE id, canonical URL, title trigram,
embedding, entity overlap) with greedy first-match, and an article is matched to
an EVENT that accumulates actors as it grows, not to another article.

Those differ in a way that matters here. Judged alone, mE5-base LOSES to mpnet on
gold_pairs (Cdet 0.4957 vs 0.4613) — worse recall. But recall the embedding tier
misses may be recovered downstream by the title or entity tiers, in which case
the isolated number overstates the cost of the swap. gold_pairs' own docstring
carries this warning: pairwise scores over-predict the effect of a change,
because they cannot see the cascade.

So this replays the real find_event, through tools/scratch's machinery, once per
candidate model — re-embedding every article with that model rather than reusing
the stored vectors — and scores PAIRWISE co-membership against gold_pairs.

Production is opened READ ONLY and never written. Everything happens in a local
scratch schema. No LLM calls.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import asyncpg

from tools.scratch import SCRATCH, _local_url, _prod_url, build_scratch, replay

TITLE_GATE: list[float | None] = [None]
# The cross-language headline tier's threshold; 0 is production's "off".
HEADLINE_TIER: list[float] = [0.0]
TITLE_TIER: list[str] = ["trigram"]
DOC_PREFIX: list[str] = ["passage"]
# The verified tier's attach floor; 0 = off, as in production until it ships.
VERIFY: list[float] = [0.0]
# Which labelled pairs are replayed and scored: gold (July, gold_pairs), batch3
# (cross-language, September) and silver (same-language, September, unratified —
# tools/gold_same_happening).
SETS: list[str] = ["gold"]
VERIFY_CACHE = Path(".cache/verify_replay.json")


def _pairs() -> dict:
    from tools.gold_pairs import GOLD_PAIRS
    from tools.gold_same_happening import BATCH_3_CROSSLINGUAL, SILVER_SAME_LANGUAGE

    chosen = {"gold": GOLD_PAIRS, "batch3": BATCH_3_CROSSLINGUAL, "silver": SILVER_SAME_LANGUAGE}
    out: dict = {}
    for name in SETS:
        out |= chosen[name]
    return out


def _cached_decide():
    """correlation.verify.decide behind a content-keyed cache, so a re-run of the
    same replay pays nothing and two runs are judged identically."""
    import hashlib

    from common.decisions import Decisions, NoulAnswer, decide

    cache = json.loads(VERIFY_CACHE.read_text()) if VERIFY_CACHE.exists() else {}

    async def cached(state, questions, **kw):
        key = hashlib.sha1(json.dumps([state, sorted(questions)], sort_keys=True).encode()).hexdigest()
        if key not in cache:
            d = await decide(state, questions, **kw)
            cache[key] = {k: a.noul for k, a in d.answers.items()}
            VERIFY_CACHE.parent.mkdir(parents=True, exist_ok=True)
            VERIFY_CACHE.write_text(json.dumps(cache))
        return Decisions(answers={k: NoulAnswer(noul=v) for k, v in cache[key].items()}, model="jev-cached")

    return cached


async def _gists(prod: asyncpg.Connection, targets: list) -> dict:
    """The verified tier's retrieval vector for every article the replay will
    place, computed as enrichment computes it (E5 query: prefix, symmetric)."""
    import common.embeddings as emb
    from correlation.verify import gist_text

    rows = await prod.fetch(
        """SELECT a.id::text AS id, ri.title, en.shared_fields
           FROM event_memberships em JOIN articles a ON a.id = em.article_id
           JOIN raw_items ri ON ri.id = a.raw_item_id JOIN enrichments en ON en.article_id = a.id
           WHERE em.event_id = ANY($1::uuid[])""",
        [str(t) for t in targets],
    )
    texts = {}
    for r in rows:
        sf = r["shared_fields"]
        sf = json.loads(sf) if isinstance(sf, str) else (sf or {})
        g = gist_text(sf, r["title"] or "")
        if g:
            texts[r["id"]] = g
    saved, emb.DOC_PREFIX = emb.DOC_PREFIX, "query"
    try:
        ids = sorted(texts)
        vecs = emb.embed_texts_sync([texts[i] for i in ids])
    finally:
        emb.DOC_PREFIX = saved
    return dict(zip(ids, vecs, strict=True))

MODELS = [
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "intfloat/multilingual-e5-base",
]

# Distance thresholds are NOT comparable between models, so running a candidate
# with the incumbent's numbers is not a fair test — it is a test of the wrong
# configuration. E5's same-event median is 0.063 and its different-event median
# 0.145, so the live 0.12 sits BETWEEN them and sweeps in roughly a third of
# unrelated pairs: measured 76 false merges against mpnet's 3.
#
# Values below come from the percentile mapping in tools/tune_embed_threshold.
THRESHOLDS = {
    "intfloat/multilingual-e5-base": {
        "EMBEDDING_DISTANCE_THRESHOLD": 0.050,
        "ENTITY_MATCH_NEAR_DISTANCE": 0.079,
        "ENTITY_MATCH_LOOSE_DISTANCE": 0.106,
    },
}


async def _gold_events(prod: asyncpg.Connection) -> tuple[list, dict]:
    """Events holding any labelled article, plus each article's title."""
    ids = sorted({a for pair in _pairs() for a in pair})
    rows = await prod.fetch(
        """SELECT DISTINCT em.event_id AS ev FROM event_memberships em
           WHERE em.article_id = ANY($1::uuid[])""",
        ids,
    )
    titles = {
        r["id"]: r["title"]
        for r in await prod.fetch(
            "SELECT a.id::text AS id, ri.title AS title FROM articles a "
            "JOIN raw_items ri ON ri.id = a.raw_item_id WHERE a.id = ANY($1::uuid[])",
            ids,
        )
    }
    return [r["ev"] for r in rows], titles


# gold_pairs holds two independent random samples appended in order: batch 1
# (156 pairs, 28 positive) then batch 2 (242 pairs, 33 positive). The module keeps
# no batch marker, so the boundary is recovered by insertion order and CHECKED
# against the counts its docstring records — if either drifts, the split is wrong
# and scoring silently reports a training number as a held-out one.
#
# This matters because thresholds here are fitted on batch 1. Scoring a fitted
# threshold on all 398 pairs scores it partly on its own training data, which is
# exactly the pattern that produced a CPM configuration beating production on the
# full gold set and LOSING on both held-out folds.
BATCH1_PAIRS, BATCH1_POS = 156, 28
# 33 until 2026-09-25, when two positives were found wrong on re-reading: the
# Thrissur leopard was paired with a Palakkad one (tools/gold_same_happening).
BATCH2_PAIRS, BATCH2_POS = 242, 31


def _batches() -> dict[str, set]:
    from tools.gold_pairs import GOLD_PAIRS

    items = list(GOLD_PAIRS.items())
    b1, b2 = items[:BATCH1_PAIRS], items[BATCH1_PAIRS:]
    if (len(b1), sum(1 for _, v in b1 if v)) != (BATCH1_PAIRS, BATCH1_POS) or (
        len(b2), sum(1 for _, v in b2 if v)
    ) != (BATCH2_PAIRS, BATCH2_POS):
        raise SystemExit(
            "gold_pairs no longer splits into the two batches its docstring records; "
            "fix the boundary before trusting a held-out number"
        )
    return {"batch1 (fitted)": {k for k, _ in b1}, "batch2 (HELD OUT)": {k for k, _ in b2}}


def _score(pred_event_of: dict[str, str], only: set | None = None) -> dict:
    """Pairwise P/R/F1/Cdet over the chosen labelled pairs, from replayed co-membership."""
    tp = fp = fn = tn = 0
    for (a, b), same in _pairs().items():
        if only is not None and (a, b) not in only:
            continue
        if a not in pred_event_of or b not in pred_event_of:
            continue
        together = pred_event_of[a] == pred_event_of[b]
        tp += together and same
        fp += together and not same
        fn += (not together) and same
        tn += (not together) and not same
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    npos, nneg = tp + fn, fp + tn
    return {
        "P": p, "R": r,
        "F1": 2 * p * r / (p + r) if p + r else 0.0,
        # FA weighted 4x a miss, the TDT convention used everywhere in this repo.
        "Cdet": (fn / npos if npos else 0) + 4 * (fp / nneg if nneg else 0),
        "tp": tp, "fp": fp, "fn": fn, "scored": tp + fp + fn + tn,
    }


async def run(models: list[str], limit: int | None) -> None:
    prod = await asyncpg.connect(_prod_url(), timeout=120)
    await prod.execute("SET default_transaction_read_only = on")
    local_url = _local_url()
    try:
        targets, titles = await _gold_events(prod)
        if limit:
            targets = targets[:limit]
        print(f"  replaying {len(targets)} events that hold gold_pairs articles\n")

        for model in models:
            # Re-embed with the candidate. The replay normally reuses the STORED
            # vector, which was produced by whatever model was live at ingest —
            # so without this every model would score identically.
            import os

            os.environ["PRISM_EMBED_MODEL"] = model
            from common.config import get_settings
            from common.embeddings import _get_model, _needs_prefix, embed_texts_sync

            os.environ["PRISM_HEADLINE_TIER_THRESHOLD"] = str(HEADLINE_TIER[0])
            os.environ["PRISM_EVENT_VERIFY"] = "live" if VERIFY[0] else "off"
            os.environ["PRISM_EVENT_VERIFY_MIN"] = str(VERIFY[0] or 0.85)
            get_settings.cache_clear()
            _get_model.cache_clear()
            print(f"  headline tier: {HEADLINE_TIER[0] or 'off'}")
            import common.embeddings as emb
            emb.DOC_PREFIX = DOC_PREFIX[0]
            if _needs_prefix(model):
                print(f"  E5 document prefix: {DOC_PREFIX[0]}:")
            ids = sorted(titles)
            vecs = embed_texts_sync([titles[i] or "" for i in ids])
            vectors = dict(zip(ids, vecs, strict=True))

            # Apply the model's own calibrated thresholds before replaying.
            import correlation.clustering as clu

            original = {k: getattr(clu, k) for k in
                        ("EMBEDDING_DISTANCE_THRESHOLD", "ENTITY_MATCH_NEAR_DISTANCE",
                         "ENTITY_MATCH_LOOSE_DISTANCE")}
            clu.TITLE_COSINE_GATE = TITLE_GATE[0]
            clu.TITLE_TIER = TITLE_TIER[0]
            print(f"  title tier: {TITLE_TIER[0]}")
            if TITLE_GATE[0] is not None:
                print(f"  entity-path title-cosine gate: {TITLE_GATE[0]}")
            applied = THRESHOLDS.get(model, {})
            for k, v in applied.items():
                setattr(clu, k, v)
            if applied:
                print(f"  thresholds: {applied}")
            else:
                print(f"  thresholds: model defaults {original}")

            gists = None
            if VERIFY[0]:
                import correlation.verify as ver

                gists = await _gists(prod, targets)
                ver.decide = _cached_decide()
                print(f"  verified tier: live at {VERIFY[0]} ({len(gists)} gists)")

            local = await asyncpg.connect(local_url, timeout=120)
            try:
                await build_scratch(prod, local, targets)
                if gists:
                    # Every replayed article carries its gist into scratch, so an
                    # article placed earlier is a candidate for a later one.
                    await local.executemany(
                        f"UPDATE {SCRATCH}.articles SET gist_embedding = $2::vector WHERE id = $1::uuid",
                        [(k, "[" + ",".join(str(x) for x in v) + "]") for k, v in gists.items()],
                    )
            finally:
                await local.close()

            placed_all: dict[str, str] = {}
            for ev in targets:
                placed, _created = await replay(prod, local_url, ev, vectors=vectors, gists=gists)
                for cluster, members in placed.items():
                    for m in members:
                        placed_all[str(m["aid"])] = cluster

            for k, v in original.items():
                setattr(clu, k, v)

            # Dumped so a re-score costs nothing. The replay is the expensive part
            # and its OUTPUT is just a placement map; re-running it to ask a second
            # question of the same run is pure waste.
            dump = Path(f".cache/cascade_placements_{TITLE_TIER[0]}_hl{HEADLINE_TIER[0]}_v{VERIFY[0]}_{'+'.join(SETS)}.json")
            dump.parent.mkdir(parents=True, exist_ok=True)
            dump.write_text(json.dumps(placed_all))

            print(f"=== {model} ===")
            folds = {f"all ({'+'.join(SETS)})": None} | (_batches() if SETS == ["gold"] else {})
            for name, subset in folds.items():
                s = _score(placed_all, subset)
                print(f"  {name:18} {s['scored']:>4} pairs   tp {s['tp']:>3}  fp {s['fp']:>3}  fn {s['fn']:>3}   "
                      f"P {s['P']:.4f}  R {s['R']:.4f}  F1 {s['F1']:.4f}  Cdet {s['Cdet']:.4f}")
            print(f"  placements -> {dump}\n")
    finally:
        await prod.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--limit", type=int, default=None, help="cap events replayed (smoke test)")
    ap.add_argument("--title-gate", type=float, default=None,
                    help="entity-path title-cosine gate; measures the change that "
                         "previously LOST at replay despite a good pairwise number")
    ap.add_argument("--doc-prefix", choices=("passage", "query"), default="passage",
                    help="E5 instruction prefix for STORED vectors. Comparing two "
                         "articles is a SYMMETRIC task and E5 wants query: on both "
                         "sides for that; passage: is right for search. One stored "
                         "vector serves both, so this picks which job wins.")
    ap.add_argument("--title-tier", choices=("trigram", "cosine"), default="trigram",
                    help="similarity used by the title_time tier; 'cosine' replaces "
                         "pg_trgm with IDF-weighted word cosine (plan step 4)")
    ap.add_argument("--headline-tier", type=float, default=0.0,
                    help="threshold for the cross-language headline tier "
                         "(correlation.clustering._match_by_headline); 0 = off, as in production")
    ap.add_argument("--verify", type=float, default=0.0,
                    help="attach floor for the verified tier (correlation/verify.py); 0 = off. "
                         "Jev answers are cached in .cache/verify_replay.json")
    ap.add_argument("--sets", default="gold",
                    help="comma-separated: gold (July), batch3 (cross-language, Sept), silver (same-language, Sept)")
    a = ap.parse_args()
    VERIFY[0] = a.verify
    SETS[:] = [x.strip() for x in a.sets.split(",")]
    HEADLINE_TIER[0] = a.headline_tier
    TITLE_GATE[0] = a.title_gate
    TITLE_TIER[0] = a.title_tier
    DOC_PREFIX[0] = a.doc_prefix
    asyncio.run(run([m.strip() for m in a.models.split(",")], a.limit))


if __name__ == "__main__":
    main()
