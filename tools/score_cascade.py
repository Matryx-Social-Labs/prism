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

import asyncpg

from tools.scratch import _local_url, _prod_url, build_scratch, replay

TITLE_GATE: list[float | None] = [None]

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
    """Events holding any gold_pairs article, plus each article's title."""
    from tools.gold_pairs import GOLD_PAIRS

    ids = sorted({a for pair in GOLD_PAIRS for a in pair})
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


def _score(pred_event_of: dict[str, str]) -> dict:
    """Pairwise P/R/F1/Cdet over gold_pairs, from replayed co-membership."""
    from tools.gold_pairs import GOLD_PAIRS

    tp = fp = fn = tn = 0
    for (a, b), same in GOLD_PAIRS.items():
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
            from common.embeddings import _get_model, embed_texts_sync

            get_settings.cache_clear()
            _get_model.cache_clear()
            ids = sorted(titles)
            vecs = embed_texts_sync([titles[i] or "" for i in ids])
            vectors = dict(zip(ids, vecs, strict=True))

            # Apply the model's own calibrated thresholds before replaying.
            import correlation.clustering as clu

            original = {k: getattr(clu, k) for k in
                        ("EMBEDDING_DISTANCE_THRESHOLD", "ENTITY_MATCH_NEAR_DISTANCE",
                         "ENTITY_MATCH_LOOSE_DISTANCE")}
            clu.TITLE_COSINE_GATE = TITLE_GATE[0]
            if TITLE_GATE[0] is not None:
                print(f"  entity-path title-cosine gate: {TITLE_GATE[0]}")
            applied = THRESHOLDS.get(model, {})
            for k, v in applied.items():
                setattr(clu, k, v)
            if applied:
                print(f"  thresholds: {applied}")
            else:
                print(f"  thresholds: model defaults {original}")

            local = await asyncpg.connect(local_url, timeout=120)
            try:
                await build_scratch(prod, local, targets)
            finally:
                await local.close()

            placed_all: dict[str, str] = {}
            for ev in targets:
                placed, _created = await replay(prod, local_url, ev, vectors=vectors)
                for cluster, members in placed.items():
                    for m in members:
                        placed_all[str(m["aid"])] = cluster

            for k, v in original.items():
                setattr(clu, k, v)
            s = _score(placed_all)
            print(f"=== {model} ===")
            print(f"  {s['scored']} pairs scored   tp {s['tp']}  fp {s['fp']}  fn {s['fn']}")
            print(f"  P {s['P']:.4f}  R {s['R']:.4f}  F1 {s['F1']:.4f}  Cdet {s['Cdet']:.4f}\n")
    finally:
        await prod.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--limit", type=int, default=None, help="cap events replayed (smoke test)")
    ap.add_argument("--title-gate", type=float, default=None,
                    help="entity-path title-cosine gate; measures the change that "
                         "previously LOST at replay despite a good pairwise number")
    a = ap.parse_args()
    TITLE_GATE[0] = a.title_gate
    asyncio.run(run([m.strip() for m in a.models.split(",")], a.limit))


if __name__ == "__main__":
    main()
