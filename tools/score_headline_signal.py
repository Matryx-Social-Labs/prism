"""Which signal on the extractor's ENGLISH headlines separates same-happening pairs?

The cross-language tier (correlation/clustering._match_by_headline) compares an
incoming article's extracted English headline against events' Prism headlines by
IDF-weighted WORD cosine. Word tokens break on the ways two outlets name one
thing: "UN" against "UNGA", "India-Pakistan" as one token against "India" and
"Pakistan" as two. The founder-reported pair on 2026-09-22 — Trump at the UNGA,
once from Hindustan Times and Mint, once from TV9 Kannada — scores 0.331 there,
below every threshold the tier has been considered at, though it is plainly one
happening.

Every article in every language already carries an English headline written by
the extractor, so the same text can be embedded instead: mE5 in the Latin
subspace, where the model is healthy, turning a cross-language comparison into a
same-language one. This scores both signals on the same labelled pairs.

    uv run python -m tools.score_headline_signal

PAIRWISE, and pairwise numbers have over-promised in this repo five times (see
correlation/clustering.py). This decides which signal is worth a cascade
replay, not whether to ship one. No LLM calls; production read-only.
"""

from __future__ import annotations

import asyncio
import sys

import asyncpg
import numpy as np

from tools.snapshot_l2 import _prod_url
from tools.title_cosine import build_idf, cosine

REPORTED_PAIR = (
    "Trump Reiterates He Ended India-Pakistan War at UNGA",
    "Trump claims at UN he prevented war between India and Pakistan",
)


def auc(pos: list[float], neg: list[float]) -> float:
    """P(a random positive outscores a random negative); ties count half."""
    if not pos or not neg:
        return float("nan")
    p, n = np.array(pos)[:, None], np.array(neg)[None, :]
    return float(((p > n).sum() + 0.5 * (p == n).sum()) / (p.size * n.size))


def best_precision_recall(pos: list[float], neg: list[float], min_precision: float = 0.95) -> tuple[float, float]:
    """The lowest threshold keeping precision >= min_precision, and the recall it buys."""
    scores = sorted(set(pos + neg), reverse=True)
    best = (float("nan"), 0.0)
    for t in scores:
        tp = sum(s >= t for s in pos)
        fp = sum(s >= t for s in neg)
        if tp and tp / (tp + fp) >= min_precision:
            best = (t, tp / len(pos))
    return best


async def main() -> int:
    from tools.gold_pairs import GOLD_PAIRS

    ids = sorted({a for pair in GOLD_PAIRS for a in pair})
    c = await asyncpg.connect(_prod_url(), timeout=120)
    try:
        await c.execute("SET default_transaction_read_only = on")
        rows = await c.fetch(
            """
            SELECT a.id::text AS id, ri.language AS lang, en.shared_fields->>'headline' AS h
            FROM articles a JOIN raw_items ri ON ri.id = a.raw_item_id
            JOIN enrichments en ON en.article_id = a.id
            WHERE a.id = ANY($1::uuid[])
            """, ids)
        window = [r["title"] for r in await c.fetch(
            "SELECT title FROM events WHERE headline_by = 'prism' AND title <> '' "
            "AND last_updated_at > now() - interval '14 days'")]
    finally:
        await c.close()

    head = {r["id"]: r["h"] for r in rows if r["h"]}
    lang = {r["id"]: r["lang"] for r in rows}
    pairs = [(a, b, same) for (a, b), same in GOLD_PAIRS.items() if a in head and b in head]
    idf = build_idf(window + list(head.values()))

    import os

    os.environ.setdefault("PRISM_EMBED_MODEL", "intfloat/multilingual-e5-base")
    import common.embeddings as emb

    emb.DOC_PREFIX = "query"  # symmetric: headline against headline
    texts = sorted(head.values())
    vec = dict(zip(texts, np.array(emb.embed_texts_sync(texts)), strict=True))

    def emb_cos(x: str, y: str) -> float:
        u, v = vec[x], vec[y]
        return float(u @ v / (np.linalg.norm(u) * np.linalg.norm(v)))

    print(f"  {len(pairs)} gold_pairs with an English headline on both sides "
          f"({sum(s for *_, s in pairs)} positive)\n")
    for name, subset in (
        ("all pairs", pairs),
        ("cross-language", [p for p in pairs if lang.get(p[0]) != lang.get(p[1])]),
        ("same language", [p for p in pairs if lang.get(p[0]) == lang.get(p[1])]),
    ):
        for signal, fn in (("word cosine (today)", lambda a, b: cosine(head[a], head[b], idf)),
                           ("mE5 headline embedding", lambda a, b: emb_cos(head[a], head[b]))):
            pos = [fn(a, b) for a, b, s in subset if s]
            neg = [fn(a, b) for a, b, s in subset if not s]
            t, r = best_precision_recall(pos, neg)
            print(f"  {name:15} {signal:24} n={len(subset):4} pos={len(pos):3}  AUC {auc(pos, neg):.3f}   "
                  f"recall at P>=0.95: {r:.3f} (threshold {t:.3f})")
        print()

    extra = [t for t in REPORTED_PAIR if t not in vec]
    if extra:
        for t, v in zip(extra, emb.embed_texts_sync(extra), strict=True):
            vec[t] = np.array(v)
    a, b = REPORTED_PAIR
    print(f"  the reported UNGA pair:  word cosine {cosine(a, b, idf):.3f}   mE5 embedding {emb_cos(a, b):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
