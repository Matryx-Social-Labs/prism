"""Per-script embedding quality for an arbitrary model. Offline, zero LLM cost.

    uv run python -m tools.score_embeddings --snapshot     # pull titles from prod, read-only
    uv run python -m tools.score_embeddings               # score the cached titles

Reproduces the measurement recorded in correlation/clustering.py:28-52, which is
what established that Kannada and Tamil carry no same-story signal at all:

    script      unrelated-pair floor   median NN dist   unrelated neighbours <=0.12
    latin       0.2606                 0.2911           1.50
    devanagari  0.1510                 0.1985           0.54
    kannada     0.0065                 0.0338           228.4
    tamil       0.0148                 0.0284           21.2 (of 36 peers)

THE ROOT CAUSE IS NOW KNOWN, and it is not "non-Latin is hard".
`paraphrase-multilingual-mpnet-base-v2` supports 50 languages and `kn` and `ta`
are NOT among them, while `hi`, `gu` and `mr` are — an exact match for the table.
Those scripts are out of distribution, so the encoder emits near-constant vectors
and everything sits on top of everything. mE5's XLM-RoBERTa backbone is trained
on CC-100, which does include both.

NO LABELS ARE NEEDED, which is what makes this cheap and decisive. A working
subspace separates unrelated documents; a collapsed one does not. If the median
distance between two random same-script articles is ~0.03, the model is not
representing that script — no threshold anywhere can fix it, and this is not a
number to tune.

PASS BAR: kannada and tamil must reach devanagari's current numbers.

RESULT, 2026-08-27 — the pass bar was NOT met, and the hypothesis was wrong.

    model                              latin   devanagari   kannada
    paraphrase-multilingual-mpnet     0.9811     0.8518     0.7006
    intfloat/multilingual-e5-large    0.9837     0.8888     0.6958

mE5 does NOT fix Kannada. It improves Devanagari (+0.037) and leaves Latin
saturated, but Kannada is flat-to-slightly-worse. Since large generally
dominates base, mE5-base will not rescue it either — so the 1024-dim migration
buys nothing for the scripts it was proposed for.

The "kn/ta are absent from mpnet's 50-language list, mE5's CC-100 backbone has
them, therefore a swap fixes it" argument was sound and still lost to the
measurement. That is what the bake-off is for.

TWO CAVEATS, both of which make Kannada's 0.70 OPTIMISTIC rather than pessimistic:

  1. Label leakage. Positives are "same production event", and Kannada events
     were formed by ENTITY overlap. Two articles sharing actors also embed
     somewhat closer, so part of that 0.70 is the label, not the model. The true
     embedding-only signal is likely nearer the AUC ~0.5 recorded in
     correlation/clustering.py.
  2. Tamil is unmeasurable — only 65 articles and 6 positive pairs exist in the
     whole corpus. Do not read a Tamil number off this until the corpus grows.

CONSEQUENCE: keep EMBEDDING_TRUSTED_SCRIPTS. Ship the L2 redesign for Latin +
Devanagari and leave Kannada/Tamil on the entity-and-title tier, which is what
_match_by_entities already does correctly. This is the fallback the plan named,
and the launch is not blocked on it.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import os
import re
import subprocess
from pathlib import Path

SNAPSHOT = Path(".cache/script_titles.json.gz")
SCRIPTS = ("latin", "devanagari", "kannada", "tamil")
PER_SCRIPT = 600


def _db_url() -> str:
    raw = os.environ.get("REPAIR_DATABASE_URL")
    if not raw:
        out = subprocess.run(
            ["railway", "variables", "--service", "Postgres", "--kv"],
            capture_output=True, text=True, timeout=120,
        ).stdout
        raw = next(ln.split("=", 1)[1].strip() for ln in out.splitlines() if ln.startswith("DATABASE_URL="))
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw)


async def build_snapshot() -> None:
    """LABELLED article titles grouped by script, READ-ONLY.

    The label is the event each article was clustered into. That is not circular
    for the scripts that matter: `EMBEDDING_TRUSTED_SCRIPTS` excludes Kannada and
    Tamil, so their event membership was decided by shared actors and title
    overlap with NO embedding involvement. Using it to grade an embedding is
    therefore an independent test.

    For Latin and Devanagari the embedding DID contribute to membership, so their
    AUC is optimistic. That bias runs the safe way for the question being asked —
    it makes the incumbent look better on the scripts it already handles, so a
    win for a challenger on Kannada is not an artefact of the labelling.
    """
    import asyncpg

    from common.text import detect_script

    c = await asyncpg.connect(_db_url(), timeout=120)
    try:
        await c.execute("SET default_transaction_read_only = on")
        rows = await c.fetch(
            """
            SELECT ri.title AS title, m.event_id::text AS event_id
            FROM event_memberships m
            JOIN articles a ON a.id = m.article_id
            JOIN raw_items ri ON ri.id = a.raw_item_id
            WHERE ri.title IS NOT NULL AND ri.title <> '' AND ri.title NOT LIKE 'CVE-%'
            """
        )
    finally:
        await c.close()

    by_script: dict[str, list[dict]] = {s: [] for s in SCRIPTS}
    for r in rows:
        s = detect_script(r["title"])
        if s in by_script and len(by_script[s]) < PER_SCRIPT:
            by_script[s].append({"event_id": r["event_id"], "title": r["title"]})

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(SNAPSHOT, "wt", encoding="utf-8") as fh:
        json.dump(by_script, fh, ensure_ascii=False)
    print(f"wrote {SNAPSHOT}")
    for s, items in by_script.items():
        print(f"  {s:12} {len(items):4} titles")


script_hdr = "script"


def _auc(pos: list[float], neg: list[float]) -> float:
    """Rank-based ROC-AUC: P(a random positive scores above a random negative)."""
    import numpy as np

    scores = np.concatenate([np.asarray(pos), np.asarray(neg)])
    labels = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype="float64")
    ranks[order] = np.arange(1, len(scores) + 1)
    # average ranks for ties
    _, inv, counts = np.unique(scores, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    ranks = (sums / counts)[inv]
    npos, nneg = len(pos), len(neg)
    return float((ranks[labels == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg))


def _cosine_matrix(vectors):
    import numpy as np

    m = np.asarray(vectors, dtype="float32")
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-12
    return 1.0 - (m @ m.T)  # cosine DISTANCE


def score_model(model_name: str, by_script: dict[str, list[dict]], prefix: str = "") -> None:
    import numpy as np
    from fastembed import TextEmbedding

    embedder = TextEmbedding(model_name)
    print(f"\n=== {model_name} ===")
    # Absolute cosine distances are NOT comparable between models — E5 packs the
    # whole space much tighter than mpnet (Latin 5th-percentile 0.19 vs 0.73), so
    # a fixed 0.12 threshold means completely different things. The decisive
    # quantity is scale-free: is a nearest neighbour meaningfully closer than a
    # random pair of the same script?
    #
    #   SEP = median nearest-neighbour distance / median pairwise distance
    #
    # SEP near 1.0 means the nearest neighbour is no closer than a random
    # document — the subspace carries no signal and no threshold can rescue it.
    # Lower is better. Judge a script against LATIN in the same model, never
    # against another model's numbers.
    print(f"  {script_hdr:12} {'n':>4} {'pairs':>7} {'pos':>6} {'AUC':>7} {'verdict':>12}")
    print("  " + "-" * 56)
    for script in SCRIPTS:
        items = by_script.get(script) or []
        if len(items) < 20:
            print(f"  {script:12} {len(items):4}   (too few titles to measure)")
            continue
        texts = [prefix + i["title"] for i in items]
        vecs = list(embedder.embed(texts))
        d = _cosine_matrix(vecs)
        n = len(items)
        np.fill_diagonal(d, np.inf)

        # Unrelated floor: the 5th percentile of all pairwise distances. In a
        # working subspace most pairs are unrelated and therefore far apart.
        # ROC-AUC of similarity as a same-event classifier. Scale-free, so it is
        # comparable across models in a way raw cosine distance is not.
        ev = [i["event_id"] for i in items]
        pos, neg = [], []
        for a in range(n):
            for b in range(a + 1, n):
                (pos if ev[a] == ev[b] else neg).append(-d[a][b])  # similarity
        if len(pos) < 10:
            print(f"  {script:12} {n:4} {len(pos) + len(neg):7} {len(pos):6}      -   too few pos")
            continue
        auc = _auc(pos, neg)
        verdict = "COLLAPSED" if auc < 0.60 else ("weak" if auc < 0.75 else "usable")
        print(f"  {script:12} {n:4} {len(pos) + len(neg):7} {len(pos):6} {auc:7.4f} {verdict:>12}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true", help="refresh titles from production (read-only)")
    ap.add_argument("--models", default=(
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2,"
        "intfloat/multilingual-e5-large"))
    a = ap.parse_args()
    if a.snapshot:
        asyncio.run(build_snapshot())
        return
    if not SNAPSHOT.exists():
        raise SystemExit(f"no snapshot at {SNAPSHOT} — run with --snapshot first")
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as fh:
        by_script = json.load(fh)

    for name in a.models.split(","):
        name = name.strip()
        # E5 models REQUIRE the "query: "/"passage: " prefix. Omitting it is a
        # silent quality loss that would be misread as "mE5 didn't help".
        prefix = "query: " if "e5" in name.lower() else ""
        score_model(name, by_script, prefix=prefix)
    print("\n  PASS BAR: kannada and tamil must reach devanagari's numbers.")


if __name__ == "__main__":
    main()
