"""GET /api/v1/admin/pipeline and the hourly stage counts it serves
(common/freshness.stage_throughput). The web page is built against this exact
shape, so the shape is pinned here."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common import auth, freshness
from common.config import get_settings
from common.db import session_scope
from common.stream import get_redis

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
    src, event, done, waiting, art = (uuid.uuid4() for _ in range(5))
    async with session_scope() as s:
        before = _hour_row(await freshness.stage_throughput(s, hours=168), hour)
    try:
        async with session_scope() as s:
            await s.execute(text("INSERT INTO sources (id, slug, name, source_type, publisher, country, language) "
                                 "VALUES (:i, :s, :s, 'rss', :s, 'IN', 'en')"), {"i": src, "s": f"tp-{src.hex[:10]}"})
            await s.execute(text("INSERT INTO events (id, title, summary, last_updated_at) VALUES (:e, 't', 's', now())"),
                            {"e": event})
            for raw, observed, classified in ((done, 5, 10), (waiting, 40, None)):
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
            current_only = await freshness.stage_throughput(s, hours=0)
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": event})
            await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": art})
            await s.execute(text("DELETE FROM raw_items WHERE source_id = :s"), {"s": src})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": event})
            await s.execute(text("DELETE FROM sources WHERE id = :s"), {"s": src})
    after = _hour_row(rows, hour)
    added = {k: after[k] - before[k] for k in ("observed", "classified", "enriched", "correlated")}
    assert added == {"observed": 2, "classified": 1, "enriched": 1, "correlated": 1}
    assert [r["hour"] for r in rows] == sorted((r["hour"] for r in rows), reverse=True), "newest first"
    assert all(set(r) == {"hour", "observed", "classified", "enriched", "correlated"} for r in rows)
    this_hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    assert all(r["hour"] >= (this_hour - timedelta(hours=1)).isoformat() for r in current_only), "0 clamps to 1 hour"


async def test_only_a_founder_reads_the_pipeline_and_the_shape_is_fixed(monkeypatch):
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
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            assert (await c.get("/api/v1/admin/pipeline")).status_code == 401
            assert (await c.get("/api/v1/admin/pipeline", headers={"Authorization": f"Bearer {rb}"})).status_code == 403
            assert (await c.get("/api/v1/admin/pipeline?days=31", headers={"Authorization": f"Bearer {fb}"})).status_code == 422
            r = await c.get("/api/v1/admin/pipeline?days=3", headers={"Authorization": f"Bearer {fb}"})
        assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
        body = r.json()
        assert set(body) == {"days", "sweeper", "throughput"}
        assert len(body["days"]) == 3
        assert all(set(d) == {"day", "recorded", "timings", "counters"} for d in body["days"])
        assert body["sweeper"] is None or set(body["sweeper"]) == {"due", "oldest_due_age_s"}
        assert isinstance(body["throughput"], list)
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM sessions WHERE user_id = ANY(:u)"), {"u": [founder, reader]})
            await s.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": [founder, reader]})
