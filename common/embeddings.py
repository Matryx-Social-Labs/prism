"""In-process embeddings via fastembed (ONNX, CPU).

Free and portable: the same code path runs on a laptop and on Railway.
The model (~34MB for bge-small) downloads once into the local cache.
CPU-bound work runs in a thread so the event loop stays responsive.
"""

import asyncio
from functools import lru_cache

from fastembed import TextEmbedding

from common.config import get_settings

# Models fastembed does not ship in its registry, registered on demand from their
# official ONNX export. This keeps production on the existing onnxruntime path —
# no torch, no sentence-transformers in the image.
_CUSTOM = {
    "intfloat/multilingual-e5-base": {"dim": 768, "file": "onnx/model.onnx"},
}

# E5 REQUIRES an instruction prefix and is measurably worse without one. The
# failure is silent: embeddings still come out, just weaker, which reads as "the
# model is bad" rather than "we used it wrong".
_PREFIXED = ("e5",)


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
    return TextEmbedding(model_name=name, cache_dir=".fastembed_cache", threads=4)


def embed_texts_sync(texts: list[str]) -> list[list[float]]:
    """Embed documents. Callers pass raw text; the instruction prefix is applied
    here so no caller can forget it."""
    model = _get_model()
    if _needs_prefix(get_settings().prism_embed_model):
        texts = [f"passage: {t}" for t in texts]
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
