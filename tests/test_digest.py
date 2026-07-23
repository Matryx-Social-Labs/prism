"""Market Pulse digest degrades instead of 500-ing.

The Pulse is a pure LLM synthesis. When the model is unavailable (quota
exhausted, timeout), _generate must return None so the route 204s and the feed
hides the card — never a 500 to every reader (the bug design-review caught: the
browser reported the 500 as a CORS failure)."""

import pytest

import correlation.digest as digest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_generate_returns_none_when_llm_unavailable(monkeypatch):
    async def _stories():
        return [{"id": "e1", "title": "Reliance jumps", "summary": "up", "tickers": ["RELIANCE"], "catalyst": None}]

    async def _boom(*a, **k):
        raise RuntimeError("llm quota exhausted (402)")

    monkeypatch.setattr(digest, "_top_stories", _stories)
    monkeypatch.setattr(digest, "structured_chat", _boom)
    monkeypatch.setattr(digest, "fetch_prompt", lambda name: type("P", (), {"version": None, "compile": lambda self, **kw: []})())

    assert await digest._generate() is None  # synthesis failed → no digest, not an exception


async def test_generate_quiet_when_no_stories(monkeypatch):
    async def _none():
        return []

    monkeypatch.setattr(digest, "_top_stories", _none)
    out = await digest._generate()
    assert out is not None and out["movers"] == []  # empty market ≠ failure; still a valid 200 payload
