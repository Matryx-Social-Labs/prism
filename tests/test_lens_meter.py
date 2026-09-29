"""The lens brief route: metered like Ask, facts with the brief, nobody pays for
an empty panel, and a re-tap never pays the model twice.

Founder decision, 2026-09-27: free lens reads are metered like Ask — anonymous
3 per browser session (with a per-address ceiling), a free account 10 in a
rolling day, Plus every lens. Before it: anonymous 0, a free account 3 samples
for life, and on /story the lens FACTS were shown to nobody (the page fetches the
record anonymously and the record strips them), a Markets tap took ~30 s, an
empty brief kept the spent sample, and a re-tap generated twice.
"""

import asyncio
import datetime as dt
import json
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import api.routes.events as events_route
from api.main import app
from common import auth, usage
from common import quota as quota_mod
from common.db import session_scope
from common.quota import has_unlocked, lens_reads_today
from common.stream import get_redis

pytestmark = pytest.mark.asyncio(loop_scope="session")

FINANCE = {"tickers": ["RELIANCE"], "catalyst": "earnings"}
CYBER = {"cve_ids": ["CVE-2099-0002"], "exploitation": {"kev_listed": True}}
WRITTEN = {
    "lens_briefs": {"reader": "The reader read.", "markets": "The markets read.", "cyber": "The cyber read."},
    "lens_points": {"markets": ["a markets point"]},
    "finance": FINANCE,
    "cyber": CYBER,
}
UNWRITTEN = {"lens_briefs": {"reader": "The reader read."}, "finance": FINANCE}
LONG_AGO = dt.datetime.now(dt.UTC) - dt.timedelta(days=60)  # out of the feed's and the sweep's way


@pytest_asyncio.fixture(loop_scope="session")
async def world():
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        await get_redis().ping()
    except Exception:
        pytest.skip("no database or redis")
    tag = uuid.uuid4().hex[:8]
    written = [uuid.uuid4() for _ in range(12)]
    unwritten = uuid.uuid4()
    users = {}
    async with session_scope() as s:
        for eid, proj in [*((e, WRITTEN) for e in written), (unwritten, UNWRITTEN)]:
            await s.execute(
                text("INSERT INTO events (id, title, summary, sector, projection, last_updated_at) "
                     "VALUES (:i, 'Lens meter record', 's', 'business', CAST(:p AS jsonb), :w)"),
                {"i": str(eid), "p": json.dumps(proj), "w": LONG_AGO},
            )
        for who in ("free", "plus"):
            uid = uuid.uuid4()
            await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": uid, "e": f"{who}-{tag}@t.test"})
            if who == "plus":
                await s.execute(
                    text("INSERT INTO subscriptions (id, user_id, provider, plan, status, price_paise, current_period_end) "
                         "VALUES (:i, :u, 'razorpay', 'plus_yearly', 'active', 149900, :e)"),
                    {"i": uuid.uuid4(), "u": uid, "e": dt.datetime.now(dt.UTC) + dt.timedelta(days=300)},
                )
            users[who] = (uid, await auth.create_session(s, uid))
    yield written, unwritten, users
    ids = [u for u, _ in users.values()]
    events = [str(e) for e in [*written, unwritten]]
    async with session_scope() as s:
        await s.execute(text("DELETE FROM lens_unlocks WHERE user_id = ANY(:u)"), {"u": ids})
        await s.execute(text("DELETE FROM subscriptions WHERE user_id = ANY(:u)"), {"u": ids})
        await s.execute(text("DELETE FROM sessions WHERE user_id = ANY(:u)"), {"u": ids})
        await s.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": ids})
        await s.execute(text("DELETE FROM events WHERE id::text = ANY(:e)"), {"e": events})
    r = get_redis()
    for pattern in ("prism:lens:*", "sf:brief:*"):
        async for key in r.scan_iter(pattern):
            await r.delete(key)


async def _brief(event_id, lens="markets", *, token=None, anon=None, generate=True):
    params = {"lens": lens, "generate": str(generate).lower()}
    if anon:
        params["anon_session"] = anon
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.get(f"/api/v1/events/{event_id}/brief", params=params, headers=headers)


def _no_model(monkeypatch):
    async def refuse(*a, **kw):
        raise AssertionError("the model was called")

    monkeypatch.setattr(events_route, "generate_briefs", refuse)


async def test_an_upcoming_lens_is_refused_before_any_gate_or_model(world, monkeypatch):
    written, _, _ = world
    _no_model(monkeypatch)
    # Anonymous with no session: the gate would answer 401 if it ran first.
    r = await _brief(written[0], "health")
    assert r.status_code == 422, r.text


async def test_an_anonymous_session_reads_three_lenses_then_is_asked_to_sign_in(world, monkeypatch):
    written, _, _ = world
    _no_model(monkeypatch)
    anon = str(uuid.uuid4())
    for eid in written[:3]:
        r = await _brief(eid, anon=anon)
        assert r.status_code == 200, r.text
        assert r.json()["brief"] == "The markets read."
    r = await _brief(written[3], anon=anon)
    assert r.status_code == 402, r.text
    assert {"used": 3, "limit": 3, "remaining": 0, "signin_helps": True, "plus_helps": True}.items() <= r.json()["detail"].items()
    # A lens it opened stays open on that story.
    assert (await _brief(written[0], anon=anon)).status_code == 200


async def test_a_page_that_keeps_no_session_is_asked_to_sign_in(world):
    written, _, _ = world
    assert (await _brief(written[0])).status_code == 401


async def test_an_address_cannot_mint_sessions_past_its_ceiling(world, monkeypatch):
    written, _, _ = world
    _no_model(monkeypatch)
    monkeypatch.setattr(quota_mod, "ANON_LENS_PER_IP_PER_DAY", 2)
    first, second = str(uuid.uuid4()), str(uuid.uuid4())
    assert (await _brief(written[4], anon=first)).status_code == 200
    assert (await _brief(written[5], anon=first)).status_code == 200
    # A fresh session id from the same address is no fresh allowance...
    assert (await _brief(written[6], anon=second)).status_code == 402
    # ...but a story the address already read costs it nothing.
    assert (await _brief(written[4], anon=second)).status_code == 200


async def test_a_free_account_reads_ten_a_day_then_meets_plus(world, monkeypatch):
    written, _, users = world
    _no_model(monkeypatch)
    uid, token = users["free"]
    for eid in written[:10]:
        r = await _brief(eid, token=token)
        assert r.status_code == 200, r.text
    r = await _brief(written[10], token=token)
    assert r.status_code == 402, r.text
    assert {"used": 10, "limit": 10, "remaining": 0, "signin_helps": False, "plus_helps": True}.items() <= r.json()["detail"].items()
    assert (await _brief(written[0], token=token)).status_code == 200, "an opened lens stays open"
    async with session_scope() as s:
        assert await lens_reads_today(s, uid) == 10


async def _lens_limits(who: str) -> int:
    async with session_scope() as s:
        return (await s.execute(text("SELECT coalesce(sum(count), 0) FROM usage_daily "
                                     "WHERE day = :d AND event = 'lens_limit' AND dim = :w"),
                                {"d": usage.today(), "w": who})).scalar()


async def test_a_refused_lens_is_counted_as_demand(world, monkeypatch):
    """The lens wall had no server count (Ask's has ask_limit), so the admin's
    demand read nothing for the one wall Plus answers (audit 2026-09-29, §2.5).
    The 402 rolls the request back; the count must survive it."""
    written, _, users = world
    _no_model(monkeypatch)
    anon, (_, token) = str(uuid.uuid4()), users["free"]
    before = await _lens_limits("anonymous"), await _lens_limits("free")
    for eid in written[:3]:
        assert (await _brief(eid, anon=anon)).status_code == 200
    for eid in written[:10]:
        assert (await _brief(eid, token=token)).status_code == 200
    assert (await _lens_limits("anonymous"), await _lens_limits("free")) == before, "a read is not a refusal"
    assert (await _brief(written[3], anon=anon)).status_code == 402
    assert (await _brief(written[10], token=token)).status_code == 402
    assert (await _lens_limits("anonymous"), await _lens_limits("free")) == (before[0] + 1, before[1] + 1)


async def test_reads_older_than_a_day_do_not_count(world, monkeypatch):
    written, _, users = world
    _no_model(monkeypatch)
    uid, token = users["free"]
    async with session_scope() as s:
        for eid in written[:10]:
            await s.execute(
                text("INSERT INTO lens_unlocks (id, user_id, event_id, lens, created_at) "
                     "VALUES (gen_random_uuid(), :u, :e, 'cyber', now() - interval '2 days')"),
                {"u": uid, "e": eid},
            )
    assert (await _brief(written[11], token=token)).status_code == 200
    assert (await _brief(written[0], "cyber", token=token)).status_code == 200, "yesterday's lens is still open"


async def test_plus_reads_every_lens_and_spends_nothing(world, monkeypatch):
    written, _, users = world
    _no_model(monkeypatch)
    uid, token = users["plus"]
    for eid in written:
        assert (await _brief(eid, token=token)).status_code == 200
    async with session_scope() as s:
        assert await lens_reads_today(s, uid) == 0


@pytest.mark.parametrize(("lens", "facts"), [("markets", FINANCE), ("cyber", CYBER), ("reader", None)])
async def test_the_brief_carries_the_lens_facts(world, monkeypatch, lens, facts):
    """The page is fetched anonymously and the record strips finance/cyber for
    anyone who has not opened the lens, so this is the only way they arrive."""
    written, _, _ = world
    _no_model(monkeypatch)
    r = await _brief(written[7], lens, anon=str(uuid.uuid4()))
    assert r.status_code == 200, r.text
    assert r.json()["facts"] == facts


async def test_the_facts_arrive_before_the_prose_is_written(world, monkeypatch):
    _, unwritten, users = world
    uid, token = users["free"]
    _no_model(monkeypatch)
    first = await _brief(unwritten, token=token, generate=False)
    assert first.status_code == 200, first.text
    assert {"pending": True, "brief": None, "facts": FINANCE}.items() <= first.json().items()

    async def write(event_id, lenses):
        return {"markets": {"text": "Written now.", "points": []}}

    monkeypatch.setattr(events_route, "generate_briefs", write)
    second = await _brief(unwritten, token=token)
    assert {"pending": False, "brief": "Written now.", "facts": FINANCE}.items() <= second.json().items()
    async with session_scope() as s:
        assert await lens_reads_today(s, uid) == 1, "two requests, one read"


@pytest.mark.parametrize("who", ["free", "anonymous"])
async def test_an_empty_brief_gives_the_read_back(world, monkeypatch, who):
    """It used to refund only when generation raised; a model that answered
    with nothing kept the reader's read."""
    _, unwritten, users = world
    uid, token = users["free"]
    anon = str(uuid.uuid4())

    async def nothing(event_id, lenses):
        return {}

    monkeypatch.setattr(events_route, "generate_briefs", nothing)
    r = await _brief(unwritten, token=token if who == "free" else None, anon=anon if who == "anonymous" else None)
    assert r.status_code == 200 and r.json()["brief"] is None, r.text
    if who == "free":
        async with session_scope() as s:
            assert not await has_unlocked(s, uid, unwritten, "markets")
            assert await lens_reads_today(s, uid) == 0
    else:
        assert await get_redis().scard(f"prism:lens:anon:{anon}") == 0


async def test_a_waiter_outwaits_the_generation(world, monkeypatch):
    """Lock 30 s, wait 25 s, generation 25 s: the re-tap took over the lock
    while the first was still writing and the model was paid twice."""
    _, unwritten, users = world
    seen = {}
    real = events_route.single_flight

    def spy(key, **kw):
        seen.update(kw)
        return real(key, **kw)

    async def slow(event_id, lenses):
        await asyncio.sleep(1)
        return {"markets": {"text": "Too late."}}

    deadline = events_route.BRIEF_DEADLINE_S
    monkeypatch.setattr(events_route, "single_flight", spy)
    monkeypatch.setattr(events_route, "generate_briefs", slow)
    monkeypatch.setattr(events_route, "BRIEF_DEADLINE_S", 0.2)
    r = await _brief(unwritten, token=users["free"][1])
    assert r.json()["brief"] is None, "the deadline did not hold"
    assert seen["ttl"] > seen["wait_timeout"] > deadline
