"""Embedding model selection, instruction prefixes, and the distance scale.

Two traps live here, and both fail SILENTLY — embeddings still come out, they
are just wrong or weaker, so nothing errors and quality drops in a way that
reads as "the model is bad".
"""

import inspect

import pytest

import common.embeddings as emb
from common.config import get_settings


@pytest.fixture(autouse=True)
def _clear():
    get_settings.cache_clear()
    emb._get_model.cache_clear()
    yield
    get_settings.cache_clear()
    emb._get_model.cache_clear()


def test_e5_models_get_an_instruction_prefix():
    """E5 is trained with "query: " / "passage: " and is measurably worse without
    them. Omitting the prefix produces perfectly valid, quietly degraded vectors —
    which would be misread as the model underperforming rather than being misused."""
    assert emb._needs_prefix("intfloat/multilingual-e5-base")
    assert emb._needs_prefix("intfloat/multilingual-e5-large")


def test_non_e5_models_get_no_prefix():
    """The counterpart: prefixing a model that was not trained with one corrupts
    it just as silently."""
    assert not emb._needs_prefix("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
    assert not emb._needs_prefix("sentence-transformers/LaBSE")


def test_documents_and_queries_use_DIFFERENT_prefixes():
    """E5 is asymmetric: it scores query-vs-passage, not passage-vs-passage. Using
    one prefix for both silently discards that asymmetry."""
    assert 'f"passage: {t}"' in inspect.getsource(emb.embed_texts_sync)
    assert 'f"query: {text}"' in inspect.getsource(emb._embed_query_sync)


def test_embed_query_does_not_delegate_to_embed_texts():
    """It used to. Once the model is asymmetric that shortcut applies the document
    prefix to a search query."""
    assert "embed_texts" not in inspect.getsource(emb._embed_query_sync)


def test_custom_models_declare_the_dimension_the_orm_expects():
    """common/models.py reads prism_embed_dim at import time into the vector
    column type. A model registered at a different dimension does not fail at
    registration — it fails later, on insert, per row."""
    for name, spec in emb._CUSTOM.items():
        assert spec["dim"] == 768, f"{name} would need a vector-column migration"


def test_the_configured_model_is_loadable():
    """Either fastembed ships it, or _CUSTOM knows how to register it. Anything
    else raises at the first embed call — i.e. mid-pipeline, in production."""
    from fastembed import TextEmbedding

    name = get_settings().prism_embed_model
    known = {m["model"] for m in TextEmbedding.list_supported_models()}
    assert name in known or name in emb._CUSTOM, (
        f"{name} is neither in fastembed's registry nor in _CUSTOM"
    )
