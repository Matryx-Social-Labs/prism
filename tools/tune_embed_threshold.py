"""Recalibrate the embedding distance thresholds for a candidate model. Offline.

    uv run python -m tools.tune_embed_threshold --snapshot   # titles for gold_pairs, read-only
    uv run python -m tools.tune_embed_threshold

WHY THIS MUST RUN BEFORE ANY MODEL SWAP (issue B0).

Cosine distances are NOT comparable between embedding models, and E5 compresses
the space hard. Measured on real text:

    mE5-base   EN<->HI  same story   distance 0.1527
    mE5-base   EN<->EN  unrelated    distance 0.1975

The live EMBEDDING_DISTANCE_THRESHOLD is 0.12, which rejects BOTH. Swap the model
and keep the number and the embedding match tier stops firing entirely — no
error, no log line, every health check green, just a quiet collapse in recall
that would be blamed on the model.

Six constants ride on this scale:
    clustering.EMBEDDING_DISTANCE_THRESHOLD   0.12
    clustering.ENTITY_MATCH_NEAR_DISTANCE     0.25
    clustering.ENTITY_MATCH_LOOSE_DISTANCE    0.45
    threads.EMBED_NEAR / EMBED_FAR            0.12 / 0.45
    threads.STORY_MAX_EMBED_DIST              0.55

The primary one is tuned directly against tools/gold_pairs (labelled same-event
article pairs — precisely what this threshold decides). The rest are mapped by
matching PERCENTILES of the pairwise distance distribution rather than rescaled
by a constant, because the two models' distributions differ in shape, not just
in width.

Cdet weights a false alarm 4x a miss, as everywhere else in this repo: a wrong
merge fuses two stories a reader can see, a miss is a duplicate card.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
from pathlib import Path

SNAPSHOT = Path(".cache/gold_pair_titles.json.gz")
INCUMBENT = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
CANDIDATE = "intfloat/multilingual-e5-base"
# The constants that ride on the distance scale, with their current values.
DEPENDENTS = {
    "clustering.EMBEDDING_DISTANCE_THRESHOLD": 0.12,
    "clustering.ENTITY_MATCH_NEAR_DISTANCE": 0.25,
    "clustering.ENTITY_MATCH_LOOSE_DISTANCE": 0.45,
    "threads.EMBED_FAR": 0.45,
    "threads.STORY_MAX_EMBED_DIST": 0.55,
}


async def build_snapshot() -> None:
    import asyncpg

    from tools.gold_pairs import GOLD_PAIRS
    from tools.score_embeddings import _db_url

    ids = sorted({a for pair in GOLD_PAIRS for a in pair})
    c = await asyncpg.connect(_db_url(), timeout=120)
    try:
        await c.execute("SET default_transaction_read_only = on")
        rows = await c.fetch(
            "SELECT a.id::text AS id, ri.title AS title FROM articles a "
            "JOIN raw_items ri ON ri.id = a.raw_item_id WHERE a.id = ANY($1::uuid[])",
            ids,
        )
    finally:
        await c.close()
    titles = {r["id"]: r["title"] for r in rows if r["title"]}
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(SNAPSHOT, "wt", encoding="utf-8") as fh:
        json.dump(titles, fh, ensure_ascii=False)
    print(f"wrote {SNAPSHOT}: {len(titles)} of {len(ids)} gold-pair articles have titles")


def _cdet(pos: list[float], neg: list[float], thr: float) -> tuple[float, float, float]:
    """(Cdet, precision, recall) treating distance <= thr as 'same event'."""
    tp = sum(1 for d in pos if d <= thr)
    fn = len(pos) - tp
    fp = sum(1 for d in neg if d <= thr)
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    cdet = (fn / len(pos) if pos else 0) + 4 * (fp / len(neg) if neg else 0)
    return cdet, p, r


def _distances(model: str, titles: dict, usable: list):
    import numpy as np

    from tools.score_embeddings import _embed

    ids = sorted({x for a, b, _ in usable for x in (a, b)})
    pre = "passage: " if "e5" in model.lower() else ""
    vecs = np.asarray(_embed(model, [pre + titles[i] for i in ids]), dtype="float32")
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
    idx = {i: k for k, i in enumerate(ids)}
    dist = {(a, b): float(1.0 - vecs[idx[a]] @ vecs[idx[b]]) for a, b, _ in usable}
    pos = [dist[(a, b)] for a, b, s in usable if s]
    neg = [dist[(a, b)] for a, b, s in usable if not s]
    return pos, neg, np.asarray(list(dist.values()))


def run(models: list[str]) -> None:
    import numpy as np

    from tools.gold_pairs import GOLD_PAIRS

    with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as fh:
        titles = json.load(fh)
    usable = [(a, b, same) for (a, b), same in GOLD_PAIRS.items() if a in titles and b in titles]
    print(f"  {len(usable)} scoreable gold pairs "
          f"({sum(1 for *_x, s in usable if s)} positive)\n")

    # The incumbent's distribution is the reference the dependent constants are
    # mapped against, so it is always computed first regardless of --models order.
    _, _, incumbent_all = _distances(INCUMBENT, titles, usable)

    for model in models:
        pos, neg, allv = _distances(model, titles, usable)
        cdet, thr, p, r = min(
            ((*_cdet(pos, neg, t)[:1], t, *_cdet(pos, neg, t)[1:]) for t in np.arange(0.02, 0.95, 0.005)),
            key=lambda x: x[0],
        )
        print(f"=== {model} ===")
        print(f"  same-event median distance {np.median(pos):.4f}   "
              f"different {np.median(neg):.4f}")
        print(f"  BEST primary threshold {thr:.3f}  ->  Cdet {cdet:.4f}  P {p:.4f}  R {r:.4f}")
        if model != INCUMBENT:
            print("  dependent constants, mapped by matching PERCENTILE (not a fixed ratio,")
            print("  because the two distributions differ in shape as well as width):")
            for name, cur in DEPENDENTS.items():
                pct = float((incumbent_all < cur).mean() * 100)
                print(f"    {name:42} {cur:5.2f}  ->  {float(np.percentile(allv, pct)):5.3f}   (p{pct:.1f})")
        print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--models", default=f"{INCUMBENT},{CANDIDATE}")
    a = ap.parse_args()
    if a.snapshot:
        asyncio.run(build_snapshot())
        return
    if not SNAPSHOT.exists():
        raise SystemExit("run with --snapshot first")
    run([m.strip() for m in a.models.split(",")])


if __name__ == "__main__":
    main()
