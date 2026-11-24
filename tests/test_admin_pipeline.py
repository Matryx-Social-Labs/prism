"""GET /api/v1/admin/pipeline and the hourly stage counts it serves
(common/freshness.stage_throughput). The web page is built against this exact
shape, so the shape is pinned here."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common import auth, freshness, timings
from common.config import get_settings
from common.db import session_scope
from common.stream import get_redis
from tests.test_pipeline_recovery import fresh_redis  # noqa: F401 — a client on this test's loop

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _redis_up() -> bool:
    try:
        await get_redis().ping()
        return True
    except Exception:  # noqa: BLE001
        return False


def _hour_row(rows: list[dict], hour: datetime) -> dict:
    zero = {"hour": hour.isoformat(), "observed": 0, "classified": 0, "enriched": 0, "correlated": 0}
    return next((r for r in rows if r["hour"] == hour.isoformat()), zero)


async def test_each_stage_is_counted_in_the_hour_it_completed():
    if not await _db_reachable():
        pytest.skip("no database")
    hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(hours=100)
    later = hour + timedelta(hours=1)
    src, event, done, waiting, late, art = (uuid.uuid4() for _ in range(6))
    async with session_scope() as s:
        rows = await freshness.stage_throughput(s, hours=168)
        before = {h: _hour_row(rows, h) for h in (hour, later)}
    try:
        async with session_scope() as s:
            await s.execute(text("INSERT INTO sources (id, slug, name, source_type, publisher, country, language) "
                                 "VALUES (:i, :s, :s, 'rss', :s, 'IN', 'en')"), {"i": src, "s": f"tp-{src.hex[:10]}"})
            await s.execute(text("INSERT INTO events (id, title, summary, last_updated_at) VALUES (:e, 't', 's', now())"),
                            {"e": event})
            # `late` is observed in one hour and classified in the next.
            for raw, observed, classified in ((done, 5, 10), (waiting, 40, None), (late, 50, 70)):
                await s.execute(
                    text("INSERT INTO raw_items (id, source_id, external_id, url, title, language, raw, relevance, "
                         "observed_at, classified_at) VALUES (:r, :s, :x, :u, 't', 'en', '{}', 'relevant', :o, :c)"),
                    {"r": raw, "s": src, "x": f"tp-{raw.hex}", "u": f"https://example.org/tp/{raw.hex}",
                     "o": hour + timedelta(minutes=observed),
                     "c": hour + timedelta(minutes=classified) if classified else None})
            await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count, fetched_at) "
                                 "VALUES (:a, :r, 'x', 'feed', 1, :f)"), {"a": art, "r": done, "f": hour + timedelta(minutes=20)})
            await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor, created_at) "
                                 "VALUES (gen_random_uuid(), :e, :a, 'new_event', true, :c)"),
                            {"e": event, "a": art, "c": hour + timedelta(minutes=30)})
        async with session_scope() as s:
            rows = await freshness.stage_throughput(s, hours=168)
            parallel = (await s.execute(text("SHOW max_parallel_workers_per_gather"))).scalar()
            current_only = await freshness.stage_throughput(s, hours=0)
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": event})
            await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": art})
            await s.execute(text("DELETE FROM raw_items WHERE source_id = :s"), {"s": src})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": event})
            await s.execute(text("DELETE FROM sources WHERE id = :s"), {"s": src})
    added = {h: {k: _hour_row(rows, h)[k] - before[h][k] for k in ("observed", "classified", "enriched", "correlated")}
             for h in (hour, later)}
    assert added[hour] == {"observed": 3, "classified": 1, "enriched": 1, "correlated": 1}
    assert added[later] == {"observed": 0, "classified": 1, "enriched": 0, "correlated": 0}
    assert parallel == "0", "no parallel workers for a whole-table scan"
    assert [r["hour"] for r in rows] == sorted((r["hour"] for r in rows), reverse=True), "newest first"
    assert all(set(r) == {"hour", "observed", "classified", "enriched", "correlated"} for r in rows)
    this_hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    assert all(r["hour"] >= (this_hour - timedelta(hours=1)).isoformat() for r in current_only), "0 clamps to 1 hour"


@pytest_asyncio.fixture(loop_scope="session")
async def tokens(monkeypatch, fresh_redis):  # noqa: F811
    """(founder, reader) bearer tokens; skips without the database or Redis."""
    if not await _db_reachable():
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
    yield fb, rb
    async with session_scope() as s:
        await s.execute(text("DELETE FROM sessions WHERE user_id = ANY(:u)"), {"u": [founder, reader]})
        await s.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": [founder, reader]})


async def _get(path: str, token: str | None = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.get(path, headers=headers)


async def test_only_a_founder_reads_the_pipeline_and_the_shape_is_fixed(tokens):
    fb, rb = tokens
    name = f"test.shape.{uuid.uuid4().hex[:8]}"
    await timings.observe(name, 12.5)  # today's row, so a timing row's shape is checked
    assert (await _get("/api/v1/admin/pipeline")).status_code == 401
    assert (await _get("/api/v1/admin/pipeline", rb)).status_code == 403
    assert (await _get("/api/v1/admin/pipeline?days=31", fb)).status_code == 422
    r = await _get("/api/v1/admin/pipeline?days=3", fb)
    await get_redis().hdel(timings._key(timings._today()), f"{name}|15", f"{name}|sum")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert set(body) == {"days", "sweeper", "throughput"}
    assert len(body["days"]) == 3
    assert all(set(d) == {"day", "recorded", "timings", "counters"} for d in body["days"])
    [row] = [t for t in body["days"][0]["timings"] if t["name"] == name]
    assert row == {"name": name, "n": 1, "p50_ms": 15, "p95_ms": 15, "mean_ms": 12.5}
    assert set(body["sweeper"]) == {"due", "oldest_due_age_s"}
    assert isinstance(body["throughput"], list)


async def test_unreadable_timings_blank_only_their_part(tokens, monkeypatch):
    async def unreadable(*_a, **_k):
        raise ConnectionError("redis down")

    monkeypatch.setattr(timings, "days", unreadable)
    r = await _get("/api/v1/admin/pipeline?days=3", tokens[0])
    assert r.status_code == 200
    body = r.json()
    assert body["days"] is None
    assert isinstance(body["throughput"], list) and set(body["sweeper"]) == {"due", "oldest_due_age_s"}


async def test_a_failed_throughput_query_blanks_only_its_part(tokens, monkeypatch):
    monkeypatch.setattr(freshness, "_THROUGHPUT_SQL", text("SELECT 1 / 0 AS hour"))
    r = await _get("/api/v1/admin/pipeline?days=3", tokens[0])
    assert r.status_code == 200, "the aborted transaction must not fail the request"
    body = r.json()
    assert body["throughput"] is None
    assert len(body["days"]) == 3 and set(body["sweeper"]) == {"due", "oldest_due_age_s"}
