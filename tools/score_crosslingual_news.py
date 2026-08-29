"""Cross-lingual retrieval on REAL NEWS, not FLORES prose.

    uv run python -m tools.score_crosslingual_news --snapshot
    uv run python -m tools.score_crosslingual_news

tools/score_crosslingual.py measures FLORES-200: professionally translated
Wikipedia-domain sentences, where a "positive" is an exact translation. That is
the standard benchmark and it is necessary — but it is NOT the product's task.

Here a positive is two DIFFERENT articles, by different outlets, in different
languages, about the same real event. No translation, different wording,
different framing, different length. If a model can rank the true English
sibling of a Hindi article above every unrelated English article, then
multilingual ingestion buys real corroboration; if it cannot, the non-English
half is dead weight in the story graph.

Labels come from production event membership. For Kannada and Tamil that is
independent of embeddings (EMBEDDING_TRUSTED_SCRIPTS excludes them, so those
events were formed by shared actors). For Devanagari the embedding contributed,
which biases the INCUMBENT optimistically — the safe direction for judging a
challenger.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
from pathlib import Path

SNAPSHOT = Path(".cache/crosslingual_news.json.gz")
MODELS = [
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "intfloat/multilingual-e5-base",
    "sentence-transformers/LaBSE",
]


async def build_snapshot() -> None:
    import asyncpg

    from common.text import detect_script
    from tools.score_embeddings import _db_url

    c = await asyncpg.connect(_db_url(), timeout=180)
    try:
        await c.execute("SET default_transaction_read_only = on")
        rows = await c.fetch(
            """
            SELECT m.event_id::text AS ev, ri.title AS title
            FROM event_memberships m
            JOIN articles a ON a.id = m.article_id
            JOIN raw_items ri ON ri.id = a.raw_item_id
            WHERE ri.title IS NOT NULL AND ri.title <> '' AND ri.title NOT LIKE 'CVE-%'
            """
        )
    finally:
        await c.close()

    by_event: dict[str, dict[str, list[str]]] = {}
    for r in rows:
        s = detect_script(r["title"])
        by_event.setdefault(r["ev"], {}).setdefault(s, []).append(r["title"])

    pairs = []
    for ev, scripts in by_event.items():
        if "latin" not in scripts:
            continue
        for script, titles in scripts.items():
            if script == "latin":
                continue
            pairs.append({"event": ev, "script": script,
                          "foreign": titles[0], "english": scripts["latin"][0]})
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(SNAPSHOT, "wt", encoding="utf-8") as fh:
        json.dump(pairs, fh, ensure_ascii=False)
    from collections import Counter
    print(f"wrote {SNAPSHOT}: {len(pairs)} cross-lingual news pairs")
    for s, n in Counter(p["script"] for p in pairs).most_common():
        print(f"  latin <-> {s:12} {n:4}")


def run(models: list[str]) -> None:
    import numpy as np

    from tools.score_embeddings import _embed

    with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as fh:
        pairs = json.load(fh)
    scripts = sorted({p["script"] for p in pairs})

    for model in models:
        pre = "query: " if "e5" in model.lower() else ""
        print(f"\n=== {model} ===")
        print(f"  {'script':12} {'pairs':>6} {'P@1':>7} {'MRR':>7}")
        print("  " + "-" * 36)
        for script in scripts:
            sub = [p for p in pairs if p["script"] == script]
            if len(sub) < 5:
                print(f"  {script:12} {len(sub):6}       -   too few")
                continue
            fv = np.asarray(_embed(model, [pre + p["foreign"] for p in sub]), dtype="float32")
            ev = np.asarray(_embed(model, [pre + p["english"] for p in sub]), dtype="float32")
            fv /= np.linalg.norm(fv, axis=1, keepdims=True) + 1e-12
            ev /= np.linalg.norm(ev, axis=1, keepdims=True) + 1e-12
            sim = fv @ ev.T
            order = np.argsort(-sim, axis=1)
            ranks = np.array([int(np.where(order[i] == i)[0][0]) + 1 for i in range(len(sub))])
            print(f"  {script:12} {len(sub):6} {(ranks == 1).mean():7.3f} {(1 / ranks).mean():7.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--models", default=",".join(MODELS))
    a = ap.parse_args()
    if a.snapshot:
        asyncio.run(build_snapshot())
        return
    if not SNAPSHOT.exists():
        raise SystemExit("run with --snapshot first")
    run([m.strip() for m in a.models.split(",")])


if __name__ == "__main__":
    main()
