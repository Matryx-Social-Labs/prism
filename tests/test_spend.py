"""The spend ledger and the cache-friendly prompt order (common/spend.py, common/llm.py).

Measured 2026-09-27: extraction was ~78% of the OpenRouter bill and every call
re-sent ~8,000 identical tokens AFTER the article, so nothing was cached.
Putting the schema before the article cut a call from $0.00298 to $0.00175.
These pin the order, and pin that the ledger adds up and never costs a call.
"""

import datetime as dt
import uuid
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from common import llm, spend
from common.stream import get_redis

pytestmark = pytest.mark.asyncio(loop_scope="session")


class Out(BaseModel):
    ok: bool


def _resp(content: str, *, cost: float | None = 0.0012, cached: int = 7000):
    usage = SimpleNamespace(
        prompt_tokens=8000, completion_tokens=600,
        prompt_tokens_details=SimpleNamespace(cached_tokens=cached),
        model_extra={"cost": cost} if cost is not None else {},
    )
    msg = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")], usage=usage,
                           model="google/gemini-3.1-flash-lite", model_extra={})


def _client(sent: list):
    class _Completions:
        async def create(self, **kw):
            sent.append(kw)
            return _resp('{"ok": true}')

    return SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))


async def _noop(*_a, **_k):
    return None


async def _redis_up() -> bool:
    try:
        await get_redis().ping()
        return True
    except Exception:  # noqa: BLE001
        return False


async def test_the_schema_sits_before_the_article_so_the_prefix_can_be_cached(monkeypatch):
    sent: list = []
    monkeypatch.setattr(llm, "get_llm", lambda: _client(sent))
    monkeypatch.setattr(llm, "_respect_cooldown", _noop)
    monkeypatch.setattr(spend, "record_response", _noop)
    messages = [
        {"role": "system", "content": "You extract news facts."},
        {"role": "user", "content": "ARTICLE: a different body every call"},
    ]
    await llm.structured_chat(model="m", messages=messages, output_model=Out, trace_name="extract-shared")
    roles = [(m["role"], m["content"][:24]) for m in sent[0]["messages"]]
    assert roles[0] == ("system", "You extract news facts.")
    assert roles[1][0] == "system" and "JSON Schema" in sent[0]["messages"][1]["content"]
    assert roles[2] == ("user", "ARTICLE: a different bod")
    # Nothing variable may precede the schema: it is the end of the cached prefix.
    assert all(m["role"] == "system" for m in sent[0]["messages"][:2])


async def test_a_prompt_with_no_system_message_still_leads_with_the_schema(monkeypatch):
    sent: list = []
    monkeypatch.setattr(llm, "get_llm", lambda: _client(sent))
    monkeypatch.setattr(llm, "_respect_cooldown", _noop)
    monkeypatch.setattr(spend, "record_response", _noop)
    await llm.structured_chat(model="m", messages=[{"role": "user", "content": "x"}], output_model=Out, trace_name="t")
    assert [m["role"] for m in sent[0]["messages"]] == ["system", "user"]


async def test_openrouter_is_asked_for_the_calls_cost(monkeypatch):
    sent: list = []
    monkeypatch.setattr(llm, "get_llm", lambda: _client(sent))
    monkeypatch.setattr(llm, "_respect_cooldown", _noop)
    monkeypatch.setattr(spend, "record_response", _noop)
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    from common.config import get_settings

    get_settings.cache_clear()
    try:
        await llm.structured_chat(model="m", messages=[{"role": "user", "content": "x"}], output_model=Out, trace_name="t")
    finally:
        get_settings.cache_clear()
    assert sent[0]["extra_body"]["usage"] == {"include": True}


async def test_every_chat_call_lands_in_the_ledger_under_its_stage(monkeypatch):
    sent: list = []
    recorded: list = []

    async def capture(response, stage, model):
        recorded.append((stage, spend.usage_of(response)))

    monkeypatch.setattr(llm, "get_llm", lambda: _client(sent))
    monkeypatch.setattr(llm, "_respect_cooldown", _noop)
    monkeypatch.setattr(spend, "record_response", capture)
    await llm.structured_chat(model="m", messages=[{"role": "user", "content": "x"}], output_model=Out, trace_name="extract-shared")
    assert recorded == [("extract-shared", (8000, 7000, 600, 0.0012))]


def test_usage_reads_openrouter_cost_and_cached_tokens():
    assert spend.usage_of(_resp("{}")) == (8000, 7000, 600, 0.0012)
    assert spend.usage_of(_resp("{}", cost=None)) == (8000, 7000, 600, None)
    assert spend.usage_of(SimpleNamespace()) == (0, 0, 0, None)


async def test_the_ledger_adds_up_per_stage_and_day():
    if not await _redis_up():
        pytest.skip("no redis")
    day = dt.date(2001, 1, 1) + dt.timedelta(days=uuid.uuid4().int % 3000)  # a day no one else writes
    when = dt.datetime.combine(day, dt.time(12), tzinfo=dt.UTC)
    await get_redis().delete(spend._key(day))
    try:
        await spend.record("extract-shared", "gemini", input_tokens=8000, cached_tokens=7000, output_tokens=600, cost=0.0014, when=when)
        await spend.record("extract-shared", "gemini", input_tokens=8200, cached_tokens=0, output_tokens=700, cost=0.0030, when=when)
        await spend.record("gate-classify", "jev", input_tokens=5000, cost=0.0002, when=when)
        [today, before] = await spend.days(2, today=day)
    finally:
        await get_redis().delete(spend._key(day))
    assert before["recorded"] is False and before["cost"] == 0, "a day with no ledger must say so, not read as zero spend"
    assert today["recorded"] and today["calls"] == 3
    assert today["cost"] == pytest.approx(0.0046)
    top = today["stages"][0]
    assert (top["stage"], top["model"], top["calls"]) == ("extract-shared", "gemini", 2)
    assert (top["input_tokens"], top["cached_tokens"], top["output_tokens"]) == (16200, 7000, 1300)
    assert top["cost"] == pytest.approx(0.0044)


async def test_a_broken_ledger_never_costs_the_call(monkeypatch):
    """Recording is observability. A Redis outage must not fail an extraction."""

    class _Broken:
        def pipeline(self, **_k):
            raise ConnectionError("redis down")

    monkeypatch.setattr(spend, "get_redis", lambda: _Broken())
    await spend.record("extract-shared", "gemini", cost=0.001)  # must not raise


async def test_only_a_founder_reads_the_spend_and_uncounted_days_say_so(monkeypatch):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    from api.main import app
    from common import auth
    from common.config import get_settings
    from common.db import session_scope

    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        pytest.skip("no database")
    if not await _redis_up():
        pytest.skip("no redis")
    tag = uuid.uuid4().hex[:8]
    founder, reader = uuid.uuid4(), uuid.uuid4()
    async with session_scope() as s:
        for uid, who in ((founder, "founder"), (reader, "reader")):
            await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": uid, "e": f"{who}-{tag}@example.test"})
        fb = await auth.create_session(s, founder)
        rb = await auth.create_session(s, reader)
    monkeypatch.setattr(get_settings(), "prism_admin_emails", f"founder-{tag}@example.test")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            assert (await c.get("/api/v1/admin/spend")).status_code == 401
            assert (await c.get("/api/v1/admin/spend", headers={"Authorization": f"Bearer {rb}"})).status_code == 403
            assert (await c.get("/api/v1/admin/spend?days=1000", headers={"Authorization": f"Bearer {fb}"})).status_code == 422
            r = await c.get("/api/v1/admin/spend?days=3", headers={"Authorization": f"Bearer {fb}"})
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
        body = r.json()
        assert len(body["days"]) == 3 and "balance" in body and body["floor"] == get_settings().prism_llm_budget_floor_usd
        assert all({"day", "recorded", "cost", "calls", "stages"} <= set(d) for d in body["days"])
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM sessions WHERE user_id = ANY(:u)"), {"u": [founder, reader]})
            await s.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": [founder, reader]})
