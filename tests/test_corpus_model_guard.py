"""A model swap that forgets the corpus is silent, and expensive.

Cosine distance is not comparable across embedding models. Running mE5 against
mpnet's stored vectors was measured at 76 false merges versus 3 — a 25x increase
— with nothing logged: vectors still come out, neighbours are still returned,
the feed just starts fusing unrelated stories.

Nothing recorded which model wrote a stored vector, so nothing could notice.
"""

import pytest

from common import embeddings as emb
from common.config import get_settings

pytestmark = pytest.mark.asyncio


class FakeSession:
    def __init__(self, row):
        self._row = row

    async def execute(self, *a, **kw):
        if isinstance(self._row, Exception):
            raise self._row
        row = self._row

        class R:
            def first(self_inner):
                return row

        return R()


@pytest.fixture(autouse=True)
def _clear():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_a_matching_corpus_passes(monkeypatch):
    monkeypatch.setenv("PRISM_EMBED_MODEL", "intfloat/multilingual-e5-base")
    monkeypatch.setattr(emb, "DOC_PREFIX", "query")
    await emb.assert_corpus_model(FakeSession(("intfloat/multilingual-e5-base", "query")))


async def test_a_different_model_halts_rather_than_corrupting(monkeypatch):
    """The whole point. Starting is the failure, not stopping."""
    monkeypatch.setenv("PRISM_EMBED_MODEL", "intfloat/multilingual-e5-base")
    monkeypatch.setattr(emb, "DOC_PREFIX", "query")
    with pytest.raises(emb.CorpusModelMismatch) as e:
        await emb.assert_corpus_model(
            FakeSession(("sentence-transformers/paraphrase-multilingual-mpnet-base-v2", None))
        )
    assert "re-embed" in str(e.value).lower()


async def test_the_PREFIX_alone_is_enough_to_halt(monkeypatch):
    """`query:` and `passage:` put the same text in different places. A corpus
    embedded with one is not comparable to queries expecting the other, and the
    model name is identical in both cases — so name-only checking would miss it."""
    monkeypatch.setenv("PRISM_EMBED_MODEL", "intfloat/multilingual-e5-base")
    monkeypatch.setattr(emb, "DOC_PREFIX", "query")
    with pytest.raises(emb.CorpusModelMismatch):
        await emb.assert_corpus_model(FakeSession(("intfloat/multilingual-e5-base", "passage")))


async def test_an_unknown_corpus_warns_but_does_not_halt(monkeypatch):
    """A database predating the table has no row. Refusing there would block every
    existing deployment, which is the kind of guard people disable rather than
    satisfy."""
    monkeypatch.setenv("PRISM_EMBED_MODEL", "intfloat/multilingual-e5-base")
    await emb.assert_corpus_model(FakeSession(None))


async def test_healthz_reports_unknown_rather_than_failing(monkeypatch):
    """A health endpoint that dies on a degraded dependency reports nothing at all."""
    monkeypatch.setenv("PRISM_EMBED_MODEL", "intfloat/multilingual-e5-base")
    out = await emb.check_corpus_model(FakeSession(RuntimeError("no such table")))
    assert out["ok"] is None and out["corpus"] is None
