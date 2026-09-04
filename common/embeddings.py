"""In-process embeddings via fastembed (ONNX, CPU).

Free and portable: the same code path runs on a laptop and on Railway.
The model (~34MB for bge-small) downloads once into the local cache.
CPU-bound work runs in a thread so the event loop stays responsive.
"""

import asyncio
import os
from functools import lru_cache

from fastembed import TextEmbedding

from common.config import get_settings
from common.logging import get_logger

# Models fastembed does not ship in its registry, registered on demand from their
# official ONNX export. This keeps production on the existing onnxruntime path —
# no torch, no sentence-transformers in the image.
logger = get_logger(__name__)

_CUSTOM = {
    "intfloat/multilingual-e5-base": {"dim": 768, "file": "onnx/model.onnx"},
}

# E5 REQUIRES an instruction prefix and is measurably worse without one. The
# failure is silent: embeddings still come out, just weaker, which reads as "the
# model is bad" rather than "we used it wrong".
#
# WHICH prefix is an open decision, and it is worth more than it looks. Measured
# 2026-09-03 on the production model over 163 cross-lingual news pairs
# (tools/score_crosslingual_news, which carries the full table):
#
#     script       passage:/passage:   query:/query:
#     devanagari               0.399           0.531      P@1
#     kannada                  0.611           0.778
#
# `passage:` on both sides — what embed_texts_sync does — is the WORST option for
# clustering, costing ~30% relative P@1, because comparing two articles is a
# SYMMETRIC task and E5 wants `query:` on both. It is right for search, which is
# asymmetric. One stored vector serves both jobs here (article_chunks for RAG,
# events for clustering), so a single prefix cannot satisfy both and the choice
# needs making deliberately rather than by default.
#
# INERT TODAY: mpnet takes no prefix, so nothing below runs. It starts mattering
# the day an E5 model ships, and it nearly killed that swap — the first pass made
# mE5 look worse than mpnet on Devanagari when it is in fact better.
_PREFIXED = ("e5",)

# Which prefix STORED document vectors get.
#
# The cascade CANNOT separate the two: held out, passage: scores Cdet 0.5837 and
# query: 0.5949, a difference of ONE event out of 242 pairs (tp 15/fp 2 against
# tp 14/fp 1). Choosing on that would be reading noise, the same mistake the
# title-cosine tier made.
#
# `query:` is chosen on evidence gold_pairs structurally cannot see. It is almost
# entirely monolingual English, while the reason for adopting mE5 at all is
# cross-lingual alignment: measured over 163 news pairs, query:/query: gives
# P@1 0.531 against passage:'s 0.399 on Devanagari, and 0.778 against 0.611 on
# Kannada. Comparing two ARTICLES is a symmetric task and that is the prefix E5
# wants for it; passage: is right for asymmetric search.
#
# It also has the better precision on the fold that decides — 0.9333 against
# 0.8824 — and a false merge fuses two unrelated stories in front of a reader,
# which is worse than Cdet's 4x weighting already implies.
#
# Recorded in corpus_meta and enforced: see assert_corpus_model below.
DOC_PREFIX = "query"

# See _get_model: 4 protects the worker's event loop; offline tools raise it.
EMBED_THREADS = int(os.environ.get("PRISM_EMBED_THREADS", "4"))


def _needs_prefix(model_name: str) -> bool:
    return any(k in model_name.lower() for k in _PREFIXED)


@lru_cache
def _get_model() -> TextEmbedding:
    settings = get_settings()
    name = settings.prism_embed_model
    if name in _CUSTOM and name not in {m["model"] for m in TextEmbedding.list_supported_models()}:
        from fastembed.common.model_description import ModelSource, PoolingType

        spec = _CUSTOM[name]
        TextEmbedding.add_custom_model(
            model=name,
            pooling=PoolingType.MEAN,        # E5 is mean-pooled, not CLS
            normalization=True,
            sources=ModelSource(hf=name),
            dim=spec["dim"],
            model_file=spec["file"],
        )
    # Cap ONNX threads so embedding bursts don't starve the event loop
    # (starvation surfaced as Redis read timeouts in the worker).
    #
    # Raisable for OFFLINE batch work, where there is no event loop to protect:
    # a whole-corpus re-embed measured 99 ms/chunk at 4 threads and 55 ms at 8 on
    # a 10-core machine, which is 1.3 hours against 0.7 for 46,635 chunks. The
    # default stays 4 so the worker keeps its guarantee.
    return TextEmbedding(model_name=name, cache_dir=".fastembed_cache", threads=EMBED_THREADS)


def embed_texts_sync(texts: list[str]) -> list[list[float]]:
    """Embed documents. Callers pass raw text; the instruction prefix is applied
    here so no caller can forget it."""
    model = _get_model()
    if _needs_prefix(get_settings().prism_embed_model):
        texts = [f"{DOC_PREFIX}: {t}" for t in texts]
    return [vec.tolist() for vec in model.embed(texts)]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return await asyncio.to_thread(embed_texts_sync, texts)


def _embed_query_sync(text: str) -> list[float]:
    model = _get_model()
    if _needs_prefix(get_settings().prism_embed_model):
        text = f"query: {text}"
    return next(iter(model.embed([text]))).tolist()


async def embed_query(text: str) -> list[float]:
    """Embed a SEARCH QUERY. Asymmetric models score query-vs-passage, not
    passage-vs-passage, so this cannot just call embed_texts."""
    return await asyncio.to_thread(_embed_query_sync, text)


class CorpusModelMismatch(RuntimeError):
    """The stored vectors were written by a different model than the one configured."""


async def check_corpus_model(session) -> dict:
    """Compare the configured embedding model against the one that wrote the corpus.

    Returns a dict for /healthz. Never raises: a health endpoint that dies on a
    degraded dependency reports nothing at all.
    """
    from sqlalchemy import text as sa_text

    settings = get_settings()
    want = (settings.prism_embed_model, DOC_PREFIX if _needs_prefix(settings.prism_embed_model) else None)
    try:
        row = (
            await session.execute(
                sa_text("SELECT embed_model, embed_prefix FROM corpus_meta WHERE id = 1")
            )
        ).first()
    except Exception:
        return {"ok": None, "configured": want[0], "corpus": None}
    if row is None:
        return {"ok": None, "configured": want[0], "corpus": None}
    have = (row[0], row[1])
    return {
        "ok": have == want,
        "configured": want[0],
        "corpus": have[0],
        "configured_prefix": want[1],
        "corpus_prefix": have[1],
    }


async def assert_corpus_model(session) -> None:
    """Refuse to continue when the configured model did not write the corpus.

    Called before any stage that WRITES vectors. Writing mE5 vectors into an mpnet
    corpus does not error — it produces a feed that fuses unrelated stories, which
    was measured at 25x the false merges with nothing logged. Halting is the
    correct outcome: a stopped pipeline is visible, a corrupted one is not.

    An UNKNOWN corpus (no row yet) is allowed through with a warning. Refusing
    there would block every database that predates this table, which is the kind
    of guard people disable rather than satisfy.
    """
    state = await check_corpus_model(session)
    if state["ok"] is None:
        logger.warning("corpus_embedding_model_unknown", configured=state["configured"])
        return
    if not state["ok"]:
        raise CorpusModelMismatch(
            f"corpus was embedded with {state['corpus']!r} (prefix {state['corpus_prefix']!r}) "
            f"but this process is configured for {state['configured']!r} "
            f"(prefix {state['configured_prefix']!r}). Re-embed with "
            f"`tools.repair --reembed --apply` before starting, or the two model's "
            f"vectors will be compared against each other."
        )
