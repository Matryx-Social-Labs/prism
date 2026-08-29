"""IDF-weighted word cosine over titles — the one validated L1 signal.

tools/gold_pairs records this, fitted on batch 1 and frozen at 0.39, then measured
once on the held-out batch 2:

    production cascade (today)     P=0.629  R=0.667  F1=0.647  Cdet=0.260
    title IDF cosine >= 0.39       P=0.944  R=0.515  F1=0.667  Cdet=0.083
    intersect (merge if both)      P=1.000  R=0.455  F1=0.625  Cdet=0.074

It is a DIFFERENT FEATURE from production's `title_time` tier, which uses pg_trgm
CHARACTER trigrams on the same field. Word-level with IDF weighting means a rare
name carries the match and shared boilerplate does not.

This module only computes the signal. Where — or whether — to apply it is a
separate question that must be answered by cascade replay, because a
headline-agreement gate on the entity path was already tried on this data and
LOST: predicted 9% recall cost, actual 37%, cluster count doubled. Pairwise
scoring cannot see compounding, since every rejected merge starts a new event
that becomes a smaller wrong candidate for the next article.
"""

from __future__ import annotations

import gzip
import json
import math
import re
from pathlib import Path

IDF_CACHE = Path(".cache/term_idf.json.gz")
_WORD = re.compile(r"[^\W\d_][\wऀ-ൿ؀-ۿ]{2,}", re.UNICODE)


def tokens(title: str) -> list[str]:
    """Content words of a title, any script. Length >= 3 so that short function
    words do not dominate; no stoplist, because IDF already demotes ubiquitous
    terms and a hand stoplist would have to be maintained per language."""
    return [w.lower() for w in _WORD.findall(title or "")]


def build_idf(titles: list[str]) -> dict[str, float]:
    """Document frequency over the corpus, as 1/log-scaled IDF weights."""
    n = max(len(titles), 1)
    df: dict[str, int] = {}
    for t in titles:
        for w in set(tokens(t)):
            df[w] = df.get(w, 0) + 1
    return {w: math.log(n / (1 + c)) for w, c in df.items()}


def cosine(a: str, b: str, idf: dict[str, float], default_idf: float = 1.0) -> float:
    """IDF-weighted cosine between two titles' word bags.

    Unseen words get `default_idf` rather than 0 — a term absent from the IDF
    corpus is RARE, which is the opposite of uninformative, and scoring it zero
    would silently discard exactly the distinctive names this signal exists for.
    """
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    va: dict[str, float] = {}
    vb: dict[str, float] = {}
    for w in ta:
        va[w] = va.get(w, 0.0) + idf.get(w, default_idf)
    for w in tb:
        vb[w] = vb.get(w, 0.0) + idf.get(w, default_idf)
    dot = sum(v * vb.get(w, 0.0) for w, v in va.items())
    na = math.sqrt(sum(v * v for v in va.values()))
    nb = math.sqrt(sum(v * v for v in vb.values()))
    return dot / (na * nb) if na and nb else 0.0


def load_idf() -> dict[str, float]:
    if not IDF_CACHE.exists():
        raise SystemExit(f"no IDF at {IDF_CACHE} — run tools.title_cosine --build")
    with gzip.open(IDF_CACHE, "rt", encoding="utf-8") as fh:
        return json.load(fh)


async def build_from_production() -> None:
    import asyncpg

    from tools.scratch import _prod_url

    c = await asyncpg.connect(_prod_url(), timeout=180)
    try:
        await c.execute("SET default_transaction_read_only = on")
        rows = await c.fetch(
            "SELECT title FROM raw_items WHERE title IS NOT NULL AND title <> '' "
            "AND title NOT LIKE 'CVE-%'"
        )
    finally:
        await c.close()
    idf = build_idf([r["title"] for r in rows])
    IDF_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(IDF_CACHE, "wt", encoding="utf-8") as fh:
        json.dump(idf, fh)
    print(f"wrote {IDF_CACHE}: {len(idf)} terms from {len(rows)} titles")


def _reproduce() -> None:
    """Check this implementation against the number gold_pairs recorded (0.39 ->
    P 0.944, Cdet 0.083). A reimplementation that scores differently is a
    different signal wearing the same name."""
    import gzip as _gz

    from tools.gold_pairs import GOLD_PAIRS

    with _gz.open(".cache/gold_pair_titles.json.gz", "rt", encoding="utf-8") as fh:
        titles = json.load(fh)
    idf = load_idf()
    rows = [(titles[a], titles[b], same) for (a, b), same in GOLD_PAIRS.items()
            if a in titles and b in titles]
    print(f"  {len(rows)} scoreable pairs ({sum(1 for *_x, s in rows if s)} positive)")
    print(f"  {'thr':>6} {'P':>7} {'R':>7} {'F1':>7} {'Cdet':>7}  {'fp':>4}")
    for thr in (0.30, 0.35, 0.39, 0.45, 0.50):
        tp = sum(1 for a, b, s in rows if s and cosine(a, b, idf) >= thr)
        fp = sum(1 for a, b, s in rows if not s and cosine(a, b, idf) >= thr)
        npos = sum(1 for *_x, s in rows if s)
        nneg = len(rows) - npos
        fn = npos - tp
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / npos if npos else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        cdet = (fn / npos if npos else 0) + 4 * (fp / nneg if nneg else 0)
        mark = "   <- recorded" if abs(thr - 0.39) < 1e-9 else ""
        print(f"  {thr:6.2f} {p:7.4f} {r:7.4f} {f1:7.4f} {cdet:7.4f}  {fp:4}{mark}")


if __name__ == "__main__":
    import argparse
    import asyncio

    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true", help="build IDF from production titles")
    ap.add_argument("--reproduce", action="store_true", help="check against gold_pairs' recorded number")
    a = ap.parse_args()
    if a.build:
        asyncio.run(build_from_production())
    elif a.reproduce:
        _reproduce()
