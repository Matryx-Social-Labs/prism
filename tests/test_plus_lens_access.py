"""Plus opens every lens on every story (docs/BUSINESS-MODEL.md §3).

2026-09-27: a reader on an active plus_yearly subscription (to 2027-09-20)
saw "You've used your free Markets reads, 0 left". None of the three lens
gates asked for the plan: the brief spent a free sample from every signed-in
reader, the record served paid lens fields only for per-story unlocks, and the
Cyber question did the same. Plus never spends a read; a free account keeps
its meter and the upgrade prompt; a lapsed Plus is a free account again.
"""

import datetime as dt
import json
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import api.routes.events as events_route
from api.main import app
from common import auth
from common.db import session_scope
from common.quota import lens_reads_today

pytestmark = pytest.mark.asyncio(loop_scope="session")

PROJECTION = {
    "source_slugs": ["zz_plus_a"],
    "lens_briefs": {"reader": "The reader read.", "markets": "The markets read.", "cyber": "The cyber read."},
    "lens_points": {"markets": ["a markets point"], "cyber": ["a cyber point"]},
    "finance": {"tickers": ["RELIANCE"]},
    "cyber": {"cve_ids": ["CVE-2099-0001"], "exploitation": {"kev_listed": True}},
}
KEV_QUESTION = "How is this being exploited in the wild?"
LONG_AGO = dt.datetime.now(dt.UTC) - dt.timedelta(days=60)  # out of the feed's way (test_geo)


@pytest_asyncio.fixture(loop_scope="session")
async def world():
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    event_id, users = uuid.uuid4(), {}
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO events (id, title, summary, sector, projection, last_updated_at) "
                 "VALUES (:i, 'Plus lens record', 's', 'technology', CAST(:p AS jsonb), :w)"),
            {"i": str(event_id), "p": json.dumps(PROJECTION), "w": LONG_AGO},
        )
        for who, status, ends in (
            ("plus", "active", dt.datetime.now(dt.UTC) + dt.timedelta(days=358)),
            ("lapsed", "cancelled", dt.datetime.now(dt.UTC) - dt.timedelta(days=40)),
            ("free", None, None),
        ):
            uid = uuid.uuid4()
            await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": uid, "e": f"{who}-{tag}@t.test"})
            if status:
                await s.execute(
                    text("INSERT INTO subscriptions (id, user_id, provider, plan, status, price_paise, current_period_end) "
                         "VALUES (:i, :u, 'razorpay', 'plus_yearly', :st, 149900, :e)"),
                    {"i": uuid.uuid4(), "u": uid, "st": status, "e": ends},
                )
            users[who] = (uid, await auth.create_session(s, uid))
    yield event_id, users
    ids = [u for u, _ in users.values()]
    async with session_scope() as s:
        await s.execute(text("DELETE FROM lens_unlocks WHERE user_id = ANY(:u)"), {"u": ids})
        await s.execute(text("DELETE FROM usage_quota WHERE user_id = ANY(:u)"), {"u": ids})
        await s.execute(text("DELETE FROM subscriptions WHERE user_id = ANY(:u)"), {"u": ids})
        await s.execute(text("DELETE FROM sessions WHERE user_id = ANY(:u)"), {"u": ids})
        await s.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": ids})
        await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": event_id})


async def _get(path: str, token: str):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.get(path, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def no_reads_left(monkeypatch):
    """Every free read of the day already spent."""
    monkeypatch.setattr(events_route, "USER_LENS_PER_DAY", 0)


@pytest.mark.parametrize("lens", ["markets", "cyber"])
async def test_a_plus_reader_with_no_reads_left_reads_the_lens(world, no_reads_left, lens):
    event_id, users = world
    uid, token = users["plus"]
    r = await _get(f"/api/v1/events/{event_id}/brief?lens={lens}", token)
    assert r.status_code == 200, r.text
    assert r.json()["brief"] == PROJECTION["lens_briefs"][lens]
    async with session_scope() as s:
        assert await lens_reads_today(s, uid) == 0, "Plus never spends a read"


async def test_a_plus_reader_gets_the_paid_fields_on_the_record(world):
    event_id, users = world
    body = (await _get(f"/api/v1/events/{event_id}", users["plus"][1])).json()
    assert set(body["lens_briefs"]) >= {"markets", "cyber"}
    assert body["projection"]["finance"] and body["projection"]["cyber"]


async def test_a_plus_reader_gets_the_cyber_question_the_record_earns(world):
    event_id, users = world
    body = (await _get(f"/api/v1/events/{event_id}/questions?lens=cyber", users["plus"][1])).json()
    assert KEV_QUESTION in body["questions"]


@pytest.mark.parametrize("who", ["free", "lapsed"])
async def test_a_free_or_lapsed_reader_with_no_reads_left_still_meets_the_upgrade_prompt(world, no_reads_left, who):
    event_id, users = world
    token = users[who][1]
    r = await _get(f"/api/v1/events/{event_id}/brief?lens=markets", token)
    assert r.status_code == 402 and r.json()["detail"]["remaining"] == 0
    assert r.json()["detail"]["plus_helps"] is True
    body = (await _get(f"/api/v1/events/{event_id}", token)).json()
    assert set(body["lens_briefs"]) == {"reader"}
    assert body["projection"].get("finance") is None and body["projection"].get("cyber") is None
    questions = (await _get(f"/api/v1/events/{event_id}/questions?lens=cyber", token)).json()["questions"]
    assert KEV_QUESTION not in questions
