"""The numbers behind /admin (admin dashboard, phase C).

Seeded in January 2031, where nothing else in a developer's database lives, and
read with `today` fixed there, so every figure below is exact. Pinned: a
period and the one before it; a day before counting began is None, not zero;
revenue counts a yearly price as a twelfth a month and leaves complimentary
out; retention is counted per sign-up week; "who reports first" measures each
outlet against the first report of a story by the outlets' own clocks; and
only a founder can read any of it.
"""

import csv
import io
import uuid
from datetime import UTC, date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common import auth, metrics
from common.config import get_settings
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")

TODAY = date(2031, 1, 31)
IST = timezone(timedelta(hours=5, minutes=30))


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


def _at(d: date, hour: int = 12) -> datetime:
    return datetime(d.year, d.month, d.day, hour, tzinfo=IST)


def _row(section: dict, key: str) -> dict:
    return next(r for r in section["rows"] if r["key"] == key)


@pytest_asyncio.fixture(loop_scope="session")
async def seeded():
    """Usage, accounts, activity and subscriptions in January 2031; removed after."""
    tag = uuid.uuid4().hex[:8]
    users = [uuid.uuid4() for _ in range(3)]
    async with session_scope() as s:
        for day, event, dim, n in [
            (date(2031, 1, 30), "view", "story", 5), (TODAY, "view", "feed", 2), (TODAY, "visitors", "", 3),
            (date(2031, 1, 2), "view", "story", 4),  # the period before
        ]:
            await s.execute(text("INSERT INTO usage_daily (day, event, dim, count) VALUES (:d, :e, :m, :n) "
                                 "ON CONFLICT (day, event, dim) DO UPDATE SET count = EXCLUDED.count"),
                            {"d": day, "e": event, "m": dim, "n": n})
        for uid, day in zip(users, (date(2031, 1, 6), TODAY, date(2030, 12, 20)), strict=True):
            await s.execute(text("INSERT INTO users (id, email, created_at) VALUES (:i, :e, :c)"),
                            {"i": uid, "e": f"m-{tag}-{uid.hex[:6]}@example.test", "c": _at(day)})
        # Signed up the week of 6 Jan; back the week after.
        await s.execute(text("INSERT INTO user_days (user_id, day) VALUES (:u, :d)"), {"u": users[0], "d": date(2031, 1, 15)})
    yield {"users": users, "tag": tag}
    async with session_scope() as s:
        await s.execute(text("DELETE FROM usage_daily WHERE day BETWEEN '2030-12-01' AND '2031-02-28'"))
        await s.execute(text("DELETE FROM subscriptions WHERE user_id = ANY(:u)"), {"u": users})
        await s.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": users})


async def test_a_period_is_read_against_the_one_before_and_by_kind(seeded):
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        visits = await metrics.visits(s, metrics.window(28, TODAY), since=date(2031, 1, 1))
    views = _row(visits, "views")
    assert (views["current"], views["previous"]) == (7, 4)
    assert views["series"][-2:] == [5, 2] and len(views["series"]) == 28
    assert _row(visits, "visitor_days")["current"] == 3
    pages = {r["label"]: (r["current"], r["previous"]) for r in visits["breakdowns"][1]["rows"]}
    assert pages == {"story": (5, 4), "feed": (2, 0)}


async def test_a_day_before_counting_began_is_not_a_zero(seeded):
    """Visits were never recorded before deploy; a day with no record is not a
    day nobody came, and the period before has no total at all."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        visits = await metrics.visits(s, metrics.window(28, TODAY), since=date(2031, 1, 30))
    views = _row(visits, "views")
    assert views["series"][:-2] == [None] * 26 and views["series"][-2:] == [5, 2]
    assert views["previous"] is None


async def test_sign_ups_and_retention_are_counted_per_week(seeded):
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        signups = await metrics.signups(s, metrics.window(28, TODAY))
        retention = await metrics.retention(s, TODAY)
    new = _row(signups, "new_accounts")
    assert (new["current"], new["previous"]) == (2, 1)
    week = next(r for r in retention["rows"] if r["week"] == "2031-01-06")
    assert (week["accounts"], week["returned"], week["complete"]) == (1, 1, True)


async def test_revenue_counts_a_year_as_twelve_months_and_leaves_gifts_out(seeded):
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        before = await metrics.money(s, metrics.window(28, TODAY), since=None)
        u = seeded["users"]
        soon = datetime.now(UTC) + timedelta(days=5)
        lapsed = datetime.now(UTC) - timedelta(days=30)
        for uid, plan, status, price, provider, period_end in [
            (u[0], "plus_yearly", "active", 119900, "razorpay", soon),
            (u[1], "plus_monthly", "past_due", 14900, "razorpay", soon),
            (u[2], "plus_monthly", "active", 14900, "manual", soon),
            # "active" in the row, but its paid time ran out a month ago: not paying.
            (u[2], "plus_monthly", "active", 14900, "razorpay", lapsed),
        ]:
            await s.execute(text("INSERT INTO subscriptions (id, user_id, provider, plan, status, price_paise, current_period_end) "
                                 "VALUES (:i, :u, :p, :pl, :st, :pr, :e)"),
                            {"i": uuid.uuid4(), "u": uid, "p": provider, "pl": plan, "st": status, "pr": price, "e": period_end})
        await s.flush()
        after = await metrics.money(s, metrics.window(28, TODAY), since=None)
    assert _row(after, "paying")["current"] - _row(before, "paying")["current"] == 2
    # ₹1,199 a year is ₹99.92 a month; with ₹149 monthly that is ₹248.92.
    added = _row(after, "mrr")["current"] - _row(before, "mrr")["current"]
    assert added in (248, 249)
    assert _row(after, "complimentary")["current"] - _row(before, "complimentary")["current"] == 1


async def test_a_subscription_starts_when_it_is_paid_and_ends_when_plus_stops(seeded):
    """An abandoned checkout is a row with no paid cycle and must not count as
    a start; an end is the day Plus stopped, which a duplicate webhook touching
    the row later does not move (review, 2026-09-23: CRITICAL and HIGH)."""
    if not await _db_reachable():
        pytest.skip("no database")
    u = seeded["users"]
    w = metrics.window(28, TODAY)
    async with session_scope() as s:
        for uid, status, begun, ended in [
            (u[0], "created", None, None),                                # checkout opened, never paid
            (u[1], "active", _at(date(2031, 1, 10)), _at(date(2031, 2, 10))),  # paid in the period
            (u[2], "cancelled", _at(date(2030, 11, 1)), _at(date(2031, 1, 20))),  # paid before, stopped in the period
        ]:
            # Every row was CREATED inside the period — the checkout opening — so
            # only the paid-cycle test separates a start from an abandoned cart.
            await s.execute(text("INSERT INTO subscriptions (id, user_id, provider, plan, status, price_paise, "
                                 "current_period_start, current_period_end, created_at, updated_at) "
                                 "VALUES (:i, :u, 'razorpay', 'plus_monthly', :st, 14900, :b, :e, :c, now())"),
                            {"i": uuid.uuid4(), "u": uid, "st": status, "b": begun, "e": ended, "c": _at(date(2031, 1, 12))})
        await s.flush()
        money = await metrics.money(s, w, since=None)
        # A duplicate webhook weeks later re-touches the ended row.
        await s.execute(text("UPDATE subscriptions SET updated_at = :t WHERE user_id = :u"), {"t": _at(TODAY), "u": u[2]})
        again = await metrics.money(s, w, since=None)
        weeks = await metrics.weekly(s, 5, TODAY)
    assert _row(money, "started")["current"] == 1
    assert _row(money, "ended")["current"] == 1 and _row(again, "ended")["current"] == 1
    assert sum(r["subscriptions_started"] for r in weeks) == 1
    assert next(r for r in weeks if r["week_start"] == "2031-01-06")["new_accounts"] == 1


async def test_who_reports_first_is_measured_by_the_outlets_own_clocks(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    monkeypatch.setattr(metrics, "LAG_MIN_EVENTS", 2)
    tag = uuid.uuid4().hex[:8]
    first, late = uuid.uuid4(), uuid.uuid4()
    events = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    t0 = _at(date(2031, 1, 20), 9)
    try:
        async with session_scope() as s:
            for src, name in ((first, f"First {tag}"), (late, f"Late {tag}")):
                await s.execute(text("INSERT INTO sources (id, slug, name, source_type, publisher, country, language) "
                                     "VALUES (:i, :s, :n, 'rss', :s, 'IN', 'en')"), {"i": src, "s": f"lag-{src.hex[:10]}", "n": name})
            # The third story's other report came three weeks later: a new story,
            # so neither outlet shared it and "First" must not be credited with it.
            for ev, hours_late in zip(events, (2, 4, 21 * 24), strict=True):
                await s.execute(text("INSERT INTO events (id, title, summary, last_updated_at, created_at) "
                                     "VALUES (:e, 't', 's', now(), :c)"), {"e": ev, "c": t0})
                for src, at in ((first, t0), (late, t0 + timedelta(hours=hours_late))):
                    raw, art = uuid.uuid4(), uuid.uuid4()
                    await s.execute(text("INSERT INTO raw_items (id, source_id, external_id, url, title, published_at, language, raw, relevance) "
                                         "VALUES (:r, :s, :x, :u, 't', :p, 'en', '{}', 'relevant')"),
                                    {"r": raw, "s": src, "x": f"lag-{raw.hex}", "u": f"https://example.org/lag/{raw.hex}", "p": at})
                    await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                                         "VALUES (:a, :r, 'x', 'feed', 1)"), {"a": art, "r": raw})
                    await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
                                         "VALUES (gen_random_uuid(), :e, :a, 'new_event', true)"), {"e": ev, "a": art})
        async with session_scope() as s:
            lag = await metrics.reporting_lag(s, metrics.window(28, TODAY))
        mine = {r["outlet"]: r for r in lag["rows"] if tag in r["outlet"]}
        assert mine[f"First {tag}"]["median_hours"] == 0.0 and mine[f"First {tag}"]["first"] == 2
        assert mine[f"First {tag}"]["stories"] == 2 and mine[f"Late {tag}"]["stories"] == 2
        assert mine[f"Late {tag}"]["median_hours"] == 3.0 and mine[f"Late {tag}"]["first"] == 0
        assert list(mine) == [f"First {tag}", f"Late {tag}"], "the first to report is listed first"
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = ANY(:e)"), {"e": events})
            await s.execute(text("DELETE FROM articles WHERE raw_item_id IN (SELECT id FROM raw_items WHERE source_id = ANY(:s))"), {"s": [first, late]})
            await s.execute(text("DELETE FROM raw_items WHERE source_id = ANY(:s)"), {"s": [first, late]})
            await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"), {"e": events})
            await s.execute(text("DELETE FROM sources WHERE id = ANY(:s)"), {"s": [first, late]})


async def test_only_a_founder_reads_the_numbers_and_the_csv_is_counts(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
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
            for path in ("/api/v1/admin/metrics", "/api/v1/admin/metrics/weekly.csv"):
                assert (await c.get(path)).status_code == 401
                assert (await c.get(path, headers={"Authorization": f"Bearer {rb}"})).status_code == 403
            r = await c.get("/api/v1/admin/metrics?days=7", headers={"Authorization": f"Bearer {fb}"})
            assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
            assert [s_["key"] for s_ in r.json()["sections"]] == ["visits", "signups", "engagement", "money", "demand", "supply"]
            assert (await c.get("/api/v1/admin/metrics?days=100000", headers={"Authorization": f"Bearer {fb}"})).status_code == 422
            r = await c.get("/api/v1/admin/metrics/weekly.csv?weeks=3", headers={"Authorization": f"Bearer {fb}"})
            rows = list(csv.DictReader(io.StringIO(r.text)))
            assert len(rows) == 3 and list(rows[0]) == list(metrics.WEEKLY_COLUMNS)
            assert all(v == "" or v.isdigit() or k == "week_start" for row in rows for k, v in row.items())
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM sessions WHERE user_id = ANY(:u)"), {"u": [founder, reader]})
            await s.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": [founder, reader]})
