"""Shadow relevance gate — embedding-based relevance score, logged next to the
LLM gate decision for calibration. Behavior-neutral: this does NOT filter.

Plan (freemium-lens-model, PR0 / eng-review E4, D6): the existing LLM
`relevance-gate` runs an LLM call on *every* ingested news item — the top LLM
cost line. Before replacing it, run this cheap embedding scorer alongside it in
shadow mode and log (score, llm_decision) pairs. Later, back-sample the logs to
pick the score band that reproduces the LLM's pass/fail, then flip
`prism_gate_mode` to "enforce" so only borderline items fall through to the LLM.

Score = max cosine similarity of the item to a set of positive "covered news"
anchors. fastembed (bge-small) is already in-process for clustering/RAG, so this
adds one CPU embedding per gated item and zero new dependencies.

# ponytail: max-cosine-to-positive-anchors is a coarse "on-topic" signal. It
# catches off-topic/spam (low sim) but NOT near-duplicates (external_id dedup
# already handles those) or thin on-topic items. Upgrade path once calibration
# data exists: add negative (spam/ad) anchors and score = pos - neg, or fit a
# tiny logistic head on the logged (embedding, llm_label) pairs.
"""

import math

from common.embeddings import embed_query, embed_texts

# Broad exemplars of the domains a relevant item resembles. The gate rejects
# spam/ads/off-topic, not any one sector, so the anchor set is deliberately wide.
RELEVANCE_ANCHORS = [
    "armed conflict, military strikes, and geopolitical escalation between nations",
    "company earnings, stock moves, mergers, central bank rate decisions, market catalysts",
    "cybersecurity breach, disclosed vulnerability, CVE, ransomware, exploited software flaw",
    "government policy, regulation, legislation, elections, and court rulings",
    "technology launches, AI research, semiconductors, and infrastructure developments",
    "corporate leadership changes, layoffs, funding rounds, and business strategy",
    "natural disaster, public health emergency, and humanitarian crisis",
]

MAX_SCORE_CHARS = 4000

# Async, computed once. Module-level cache (not lru_cache — that doesn't play
# well with coroutines) keeps the first call from blocking the event loop.
_anchor_vectors: list[list[float]] | None = None


async def _get_anchor_vectors() -> list[list[float]]:
    global _anchor_vectors
    if _anchor_vectors is None:
        _anchor_vectors = await embed_texts(RELEVANCE_ANCHORS)
    return _anchor_vectors


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


async def shadow_score(title: str, body: str | None) -> float:
    """Max cosine similarity (0..1) of the item to any relevance anchor."""
    text = f"{title}\n\n{body or ''}"[:MAX_SCORE_CHARS]
    vec = await embed_query(text)
    anchors = await _get_anchor_vectors()
    return max(_cosine(vec, a) for a in anchors)


def demo() -> None:
    """Self-check: clearly-relevant news outscores obvious spam, in [0,1]."""
    import asyncio

    news = "Reserve Bank of India holds repo rate; Nifty Bank falls 1.2% as PSU lenders slide"
    spam = "You won't BELIEVE these 10 celebrity weight-loss tricks — click here to buy now!!!"
    news_score = asyncio.run(shadow_score(news, None))
    spam_score = asyncio.run(shadow_score(spam, None))
    print(f"news={news_score:.3f} spam={spam_score:.3f}")
    assert 0.0 <= spam_score <= 1.0 and 0.0 <= news_score <= 1.0, (news_score, spam_score)
    assert news_score > spam_score, (news_score, spam_score)
    print("shadow_gate demo OK")


if __name__ == "__main__":
    demo()
