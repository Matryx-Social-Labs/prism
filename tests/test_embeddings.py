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


# --- the distance scale must travel with the model ---------------------------


def test_thresholds_differ_per_model():
    """Measured through the FULL cascade against gold_pairs (tools/score_cascade):

        mpnet, its own thresholds   tp 28  fp  3   P 0.9032  Cdet 0.5766
        mE5,   MPNET's thresholds   tp 47  fp 76   P 0.3821  Cdet 1.1316   <-- 25x the false merges
        mE5,   its own thresholds   tp 31  fp  8   P 0.7949  Cdet 0.5868

    E5 compresses the space — same-event median distance 0.063, different-event
    0.145 — so mpnet's 0.12 sits BETWEEN them and sweeps in roughly a third of
    unrelated pairs. Nothing raises; the feed just starts fusing unrelated stories.
    """
    from correlation.clustering import _SCALE

    mpnet = _SCALE["sentence-transformers/paraphrase-multilingual-mpnet-base-v2"]
    e5 = _SCALE["intfloat/multilingual-e5-base"]
    assert e5["embedding"] < mpnet["embedding"], "E5's compressed scale needs a tighter threshold"
    for key in ("embedding", "entity_near", "entity_loose"):
        assert e5[key] != mpnet[key], f"{key} must be calibrated per model, not shared"


def test_every_calibrated_model_is_loadable():
    """A scale entry for a model nothing can load is a threshold that will never
    apply — and its absence is invisible until match quality drops."""
    from fastembed import TextEmbedding

    from correlation.clustering import _SCALE

    known = {m["model"] for m in TextEmbedding.list_supported_models()}
    for name in _SCALE:
        assert name in known or name in emb._CUSTOM, f"{name} is calibrated but not loadable"


def test_an_uncalibrated_model_falls_back_loudly(monkeypatch, caplog):
    """Silently guessing a scale for an unmeasured model is exactly how a swap
    becomes a quiet 25x rise in false merges."""
    import logging

    import correlation.clustering as clu

    monkeypatch.setenv("PRISM_EMBED_MODEL", "some/unmeasured-model")
    get_settings.cache_clear()
    with caplog.at_level(logging.WARNING):
        scale = clu._scale()
    assert scale == clu._SCALE["sentence-transformers/paraphrase-multilingual-mpnet-base-v2"]
    assert any("uncalibrated" in r.message for r in caplog.records)
