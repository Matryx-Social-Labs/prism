"""In-process embeddings via fastembed (ONNX, CPU).

Free and portable: the same code path runs on a laptop and on Railway.
The model (~34MB for bge-small) downloads once into the local cache.
CPU-bound work runs in a thread so the event loop stays responsive.
"""

import asyncio
from functools import lru_cache

from fastembed import TextEmbedding

from common.config import get_settings


@lru_cache
def _get_model() -> TextEmbedding:
    settings = get_settings()
    return TextEmbedding(model_name=settings.prism_embed_model, cache_dir=".fastembed_cache")


def embed_texts_sync(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    return [vec.tolist() for vec in model.embed(texts)]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return await asyncio.to_thread(embed_texts_sync, texts)


async def embed_query(text: str) -> list[float]:
    result = await embed_texts([text])
    return result[0]
