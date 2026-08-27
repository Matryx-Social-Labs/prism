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


def test_the_bake_reads_the_model_from_config_not_a_literal():
    src = DOCKERFILE.read_text()
    assert "get_settings().prism_embed_model" in src, (
        "Dockerfile must bake the CONFIGURED embedding model, not a hardcoded name"
    )


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
