"""Market Pulse degrades to its board, never to a 500 and never to an empty page.

The board is the record; the three-line read is the model's. When the model is
unavailable (quota exhausted, timeout) the board is served without the read —
the old essay had nothing else to show, so the route 204'd and the page went
blank (the bug design-review caught: the browser reported the 500 as a CORS
failure)."""

import pytest

import correlation.digest as digest
from common.llm import REASONING_OFF

pytestmark = pytest.mark.asyncio(loop_scope="session")

BOARD = {
    "companies": [{"symbol": "SBIN", "company": "State Bank of India", "headline": "Bank strike deferred",
                   "catalyst": None, "reading": "positive", "outlets": 3}],
    "market_wide": [],
}


class _Prompt:
    version = None

    def compile(self, **_kw):
        return []


async def test_a_failed_read_leaves_the_board_without_it(monkeypatch):
    async def _boom(**_k):
        raise RuntimeError("llm quota exhausted (402)")

    monkeypatch.setattr(digest, "structured_chat", _boom)
    monkeypatch.setattr(digest, "fetch_prompt", lambda name: _Prompt())
    assert await digest._read(BOARD) == []


async def test_an_empty_day_never_calls_the_model(monkeypatch):
    called = []

    async def _spy(**_k):
        called.append(1)

    monkeypatch.setattr(digest, "structured_chat", _spy)
    monkeypatch.setattr(digest, "fetch_prompt", lambda name: _Prompt())
    assert await digest._read({"companies": [], "market_wide": []}) == []
    assert called == []


async def test_the_read_is_a_record_shaped_call_without_reasoning(monkeypatch):
    """Three lines from the rows need no thinking aloud; thinking tokens share
    the ceiling and are billed (memory: openrouter reasoning tokens)."""
    seen = {}

    async def _fake(**k):
        seen.update(k)
        return digest.MarketReadLLM(lines=["State Bank of India leads the board.", "Its shares jumped 9%."])

    monkeypatch.setattr(digest, "structured_chat", _fake)
    monkeypatch.setattr(digest, "fetch_prompt", lambda name: _Prompt())
    assert await digest._read(BOARD) == ["State Bank of India leads the board."], "9 is on no row"
    assert seen["reasoning"] == REASONING_OFF
