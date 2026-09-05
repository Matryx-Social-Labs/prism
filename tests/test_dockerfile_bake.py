"""The image must bake the embedding model the app actually loads.

The Dockerfile hardcoded `BAAI/bge-small-en-v1.5` (384-dim) long after
`prism_embed_model` moved to a 768-dim multilingual model. The bake therefore
cached a model nothing loads, and production re-downloaded the real one from
HuggingFace on every cold start — an optimization that silently did nothing.

Nothing failed, which is why it survived: a wrong cache is indistinguishable
from a cold cache at runtime, just slower.
"""

from pathlib import Path

from common.config import get_settings

DOCKERFILE = Path(__file__).resolve().parent.parent / "Dockerfile"


def _instructions() -> str:
    return "\n".join(
        ln for ln in DOCKERFILE.read_text().splitlines() if not ln.lstrip().startswith("#")
    )


def test_the_bake_goes_through_the_app_s_own_loader():
    """REGRESSION: the Railway build failed with

        ValueError: Model intfloat/multilingual-e5-base is not supported in TextEmbedding

    The bake called `TextEmbedding(name)` directly, which only works for models
    fastembed ships in its registry. common.embeddings._get_model() first
    registers the ones it does not (add_custom_model), and mE5 is one of them —
    so the image could not bake a model the application loads perfectly well.

    The previous test asserted the Dockerfile READ the model from config, which
    it did. Reading the right name and then loading it the wrong way still
    passed. Asserting the loader closes that.
    """
    src = _instructions()
    assert "from common.embeddings import _get_model" in src, (
        "the bake must use the app's loader, which registers custom models"
    )
    assert "from fastembed import TextEmbedding" not in src, (
        "calling fastembed directly bypasses add_custom_model and breaks the build "
        "for any model not in fastembed's registry"
    )


def test_the_bake_actually_loads_the_configured_model():
    """The check the source-reading tests cannot make: does it WORK?

    Skipped when the model is not already cached — this must not turn CI into a
    1 GB download — but on any machine that has run the app it is the real thing.
    """
    import pytest

    from common.embeddings import _get_model

    cache = DOCKERFILE.parent / ".fastembed_cache"
    if not cache.exists() or not any(cache.iterdir()):
        pytest.skip("model not cached locally; nothing to verify without a download")
    _get_model()  # raises if the configured model cannot be loaded


def test_no_stale_model_name_is_hardcoded_in_the_image():
    """Belt and braces: catch a literal reintroduced alongside the config read.

    Comments are excluded on purpose — the note explaining WHY this broke names
    the old model, and that history is worth more than a simpler assertion.
    """
    executable = [
        ln for ln in DOCKERFILE.read_text().splitlines() if not ln.lstrip().startswith("#")
    ]
    src = "\n".join(executable)
    for stale in ("BAAI/bge-small-en-v1.5", "bge-small"):
        assert stale not in src, f"{stale!r} is hardcoded in a Dockerfile instruction again"


def test_the_configured_model_is_the_multilingual_one():
    """If this fails the default moved; confirm the bake and the dim still agree
    before changing it — prism_embed_dim is read into the ORM at import time, so
    a mismatch silently breaks every vector column."""
    s = get_settings()
    assert s.prism_embed_dim == 768
    assert "multilingual" in s.prism_embed_model
