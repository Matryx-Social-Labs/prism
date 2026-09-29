"""State hubs and the day archive (marketing audit 02, P1-1 and P1-2).

Both are counted from the record and ask to be indexed only above a floor of
records from two or more outlets. A day Prism did not read says so and counts
nothing; a day after which Prism stopped reading is not settled.
"""

import datetime as dt
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from api.routes.entity import INDEXABLE_MIN_RECORDS
from api.routes.hubs import (
    DAY_FLOOR,
    HUB_FLOOR,
    IST,
    day_bounds,
    day_indexable,
    ist_today,
    parse_day,
    reading,
)
from common import outlets
from common.db import session_scope
from common.regions import HUB_SLUGS, HUB_STATES, state_slug

# ── Pure rules ──────────────────────────────────────────────────────────────


def test_every_hub_slug_round_trips_to_its_code():
    assert len(HUB_STATES) == 33
    assert {HUB_SLUGS[state_slug(n)] for c, n in HUB_STATES} == {c for c, _ in HUB_STATES}
    assert HUB_SLUGS["jammu-and-kashmir"] == "IN-JK"
    assert HUB_SLUGS["uttarakhand"] == "IN-UK"
    assert "andaman-and-nicobar" not in HUB_SLUGS, (
        "no hub, so its entity page is not deferred to one"
    )


@pytest.mark.parametrize(
    "raw", ["2026-9-27", "2026-02-30", "27-09-2026", "2026-09-27T00:00", "20260927", "today", ""]
)
def test_a_malformed_day_is_not_a_day(raw):
    assert parse_day(raw) is None


def test_the_day_is_the_ist_calendar_day():
    assert parse_day("2026-09-27") == dt.date(2026, 9, 27)
    assert ist_today(dt.datetime(2026, 9, 28, 20, 0, tzinfo=dt.UTC)) == dt.date(2026, 9, 29)
    start, end = day_bounds(dt.date(2026, 9, 28))
    assert start == dt.datetime(2026, 9, 27, 18, 30, tzinfo=dt.UTC)
    assert end - start == dt.timedelta(days=1)


def _at(day: dt.date, hh: int, mm: int) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(hh, mm), IST)


D = dt.date(2026, 9, 28)


def test_reading_says_what_was_read():
    assert reading(D, None, None, True)["read"] is False
    whole = reading(D, _at(D, 0, 1), _at(D, 23, 56), True)
    assert whole["read"] and whole["whole_day"] and whole["settled"]
    # 28 Sep 2026: read from midnight to 07:41 IST, then nothing since.
    stopped = reading(D, _at(D, 0, 0), _at(D, 7, 41), False)
    assert stopped["read"] and not stopped["whole_day"] and not stopped["settled"]
    assert (
        dt.datetime.fromisoformat(stopped["read_to"]).astimezone(IST).strftime("%H:%M") == "07:41"
    )


def test_a_day_asks_to_be_indexed_only_read_settled_and_at_the_floor():
    read = reading(D, _at(D, 0, 1), _at(D, 23, 56), True)
    assert day_indexable(read, DAY_FLOOR) is True
    assert day_indexable(read, DAY_FLOOR - 1) is False
    assert day_indexable(reading(D, _at(D, 0, 0), _at(D, 7, 41), False), 500) is False, (
        "stopped mid-day: not settled"
    )
    assert day_indexable(reading(D, None, None, True), None) is False, (
        "not read: never, whatever it holds"
    )


# ── Against the database ────────────────────────────────────────────────────


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _get(path: str):
    # Each request here must read the database it just seeded, not the
    # handlers' in-process cache (hubs.ttl_cached, covered by its own test).
    import api.routes.hubs as hubs

    hubs._memo.clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        return await c.get(path)


class Seed:
    """Rows a test inserts, removed afterwards: the local database is shared."""

    def __init__(self) -> None:
        self.tag = uuid.uuid4().hex[:8]
        self.events: list[str] = []
        self.entities: list[str] = []
        self.links: list[str] = []

    async def source(self, s) -> uuid.UUID:
        sid = uuid.uuid4()
        await s.execute(
            text("INSERT INTO sources (id, slug, name, source_type) VALUES (:i, :s, :s, 'rss')"),
            {"i": str(sid), "s": f"zz_{self.tag}_src"},
        )
        return sid

    async def article(self, s, sid: uuid.UUID, at: dt.datetime) -> None:
        rid = uuid.uuid4()
        await s.execute(
            text(
                "INSERT INTO raw_items (id, source_id, external_id, title, raw, relevance, observed_at) "
                "VALUES (:i, :s, :e, 'h', '{}'::jsonb, 'relevant', :w)"
            ),
            {"i": str(rid), "s": str(sid), "e": f"ext-{rid}", "w": at},
        )
        await s.execute(
            text(
                "INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count, created_at, fetched_at) "
                "VALUES (:i, :r, 'body', 'rss', 1, :w, :w)"
            ),
            {"i": str(uuid.uuid4()), "r": str(rid), "w": at},
        )

    async def record(
        self,
        s,
        outlets_: int,
        seen: dt.datetime,
        regions: list[str],
        subject: str = "politics.elections",
    ) -> str:
        eid = str(uuid.uuid4())
        slugs = [
            f"zz_{self.tag}_{i}" for i in range(outlets_)
        ]  # unregistered: each counts as its own outlet
        await s.execute(
            text(
                "INSERT INTO events (id, title, summary, sector, subject_path, regions, projection, first_seen_at, last_updated_at) "
                "VALUES (:i, :t, 's', 'politics', :sp, :r, CAST(:p AS jsonb), :w, :w)"
            ),
            {
                "i": eid,
                "t": f"Record {eid[:6]}",
                "sp": subject,
                "r": regions,
                "p": json.dumps({"source_slugs": slugs, "languages": ["en", "kn"]}),
                "w": seen,
            },
        )
        self.events.append(eid)
        return eid

    async def teardown(self) -> None:
        async with session_scope() as s:
            await s.execute(
                text("DELETE FROM event_entities WHERE id = ANY(CAST(:l AS uuid[]))"),
                {"l": self.links},
            )
            await s.execute(
                text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"), {"e": self.events}
            )
            await s.execute(
                text("DELETE FROM entities WHERE id = ANY(CAST(:e AS uuid[]))"),
                {"e": self.entities},
            )
            await s.execute(
                text(
                    "DELETE FROM articles WHERE raw_item_id IN (SELECT ri.id FROM raw_items ri "
                    "JOIN sources src ON src.id = ri.source_id WHERE src.slug LIKE :p)"
                ),
                {"p": f"zz_{self.tag}_%"},
            )
            await s.execute(
                text(
                    "DELETE FROM raw_items WHERE source_id IN (SELECT id FROM sources WHERE slug LIKE :p)"
                ),
                {"p": f"zz_{self.tag}_%"},
            )
            await s.execute(
                text("DELETE FROM sources WHERE slug LIKE :p"), {"p": f"zz_{self.tag}_%"}
            )
        outlets.reset_cache()


# A day well before anything else in any database: Prism "first read" on it for
# the length of the test, so it and its neighbours are in and out of range.
FIRST = dt.date(2020, 1, 15)


@pytest.mark.asyncio(loop_scope="session")
async def test_the_day_archive_lists_what_was_first_seen_and_says_when_prism_was_not_reading():
    if not await _db_reachable():
        pytest.skip("no database")
    seed = Seed()
    async with session_scope() as s:
        sid = await seed.source(s)
        await seed.article(s, sid, _at(FIRST, 11, 10))
        await seed.article(s, sid, _at(FIRST, 16, 1))
        await seed.article(
            s, sid, _at(FIRST + dt.timedelta(days=3), 9, 0)
        )  # Prism read again later: FIRST is settled
        multi = await seed.record(s, 2, _at(FIRST, 12, 0), ["IN"])
        single = await seed.record(s, 1, _at(FIRST, 13, 0), ["IN"])
    outlets.reset_cache()
    try:
        day = await _get(f"/api/v1/archive/{FIRST.isoformat()}")
        gap = await _get(f"/api/v1/archive/{(FIRST + dt.timedelta(days=1)).isoformat()}")
        before = await _get(f"/api/v1/archive/{(FIRST - dt.timedelta(days=1)).isoformat()}")
        today = await _get(f"/api/v1/archive/{ist_today().isoformat()}")
        malformed = await _get("/api/v1/archive/2020-1-15")
        index = await _get("/api/v1/archive")
    finally:
        await seed.teardown()

    assert day.status_code == 200
    body = day.json()
    assert body["read"] is True and body["whole_day"] is False and body["settled"] is True
    assert [i["id"] for i in body["items"]] == [multi], (
        "two outlets are listed; one is counted, not listed"
    )
    assert single not in {i["id"] for i in body["items"]}
    assert (body["records"], body["multi_outlet"], body["single_source"]) == (2, 1, 1)
    assert body["indexable"] is False, "under the floor"
    assert body["prev"] is None

    assert gap.status_code == 200
    not_read = gap.json()
    assert not_read["read"] is False
    assert not_read["records"] is None and not_read["multi_outlet"] is None, (
        "not read: not counted, never 0"
    )
    assert not_read["items"] == [] and not_read["indexable"] is False
    assert not_read["prev"] == FIRST.isoformat()

    assert before.status_code == 404, "before the first day Prism read"
    assert today.status_code == 404, "today's record is /feed"
    assert malformed.status_code == 404

    days = {d["date"]: d for d in index.json()["days"]}
    assert index.json()["first_day"] == FIRST.isoformat()
    assert days[FIRST.isoformat()]["multi_outlet"] == 1
    assert days[(FIRST + dt.timedelta(days=1)).isoformat()]["records"] is None
    assert (FIRST - dt.timedelta(days=1)).isoformat() not in days
    assert ist_today().isoformat() not in days


@pytest.mark.asyncio(loop_scope="session")
async def test_a_state_hub_counts_its_records_and_asks_to_be_indexed_from_the_floor():
    if not await _db_reachable():
        pytest.skip("no database")
    code = "IN-PY"  # Puducherry: the fewest records anywhere, so the floor is ours to cross
    start = (await _get(f"/api/v1/regions/{code}")).json()
    if start["multi_outlet"] >= HUB_FLOOR:
        pytest.skip("the local database already clears the floor here")
    seed = Seed()
    now = dt.datetime.now(dt.UTC)
    try:
        async with session_scope() as s:
            ids = [
                await seed.record(
                    s, 2, now - dt.timedelta(hours=i + 1), ["IN", code], "civic.crime"
                )
                for i in range(HUB_FLOOR - 1 - start["multi_outlet"])
            ]
            await seed.record(
                s, 1, now, ["IN", code]
            )  # one source: counted in all, never towards the floor
            await seed.record(
                s, 2, now - dt.timedelta(days=40), ["IN", code]
            )  # outside the 30 days
        outlets.reset_cache()
        under = (await _get(f"/api/v1/regions/{code}")).json()
        async with session_scope() as s:
            ids.append(await seed.record(s, 2, now, ["IN", code], "civic.crime"))
        at = (await _get(f"/api/v1/regions/{code}")).json()
        hubs = {h["code"]: h for h in (await _get("/api/v1/regions/hubs")).json()["states"]}
        missing = await _get("/api/v1/regions/IN-XX")
    finally:
        await seed.teardown()

    assert under["multi_outlet"] == HUB_FLOOR - 1 and under["indexable"] is False
    assert under["records"] == start["records"] + HUB_FLOOR - start["multi_outlet"]
    assert at["multi_outlet"] == HUB_FLOOR and at["indexable"] is True
    assert set(ids) <= {i["id"] for i in at["items"]}
    assert any(
        s["root"] == "civic" and s["count"] >= HUB_FLOOR - start["multi_outlet"]
        for s in at["subjects"]
    )
    assert "kn" in at["languages"]
    assert at["slug"] == "puducherry"
    assert hubs[code]["multi_outlet"] == HUB_FLOOR and hubs[code]["indexable"] is True
    assert len(hubs) == 33
    assert missing.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_a_states_own_name_is_left_out_of_the_entities_sitemap():
    """/entity/<state> 308s to the hub; offering it in a sitemap would send
    crawlers through a redirect to a page the sitemap already lists."""
    if not await _db_reachable():
        pytest.skip("no database")
    seed = Seed()
    actor = f"zz-{seed.tag}-actor"
    try:
        async with session_scope() as s:
            state_id = (
                await s.execute(text("SELECT id FROM entities WHERE slug = 'goa'"))
            ).scalar_one_or_none()
            if state_id is None:
                state_id = uuid.uuid4()
                seed.entities.append(str(state_id))
                await s.execute(
                    text(
                        "INSERT INTO entities (id, slug, name, entity_type) VALUES (:i, 'goa', 'Goa', 'place')"
                    ),
                    {"i": str(state_id)},
                )
            actor_id = uuid.uuid4()
            seed.entities.append(str(actor_id))
            await s.execute(
                text(
                    "INSERT INTO entities (id, slug, name, entity_type) VALUES (:i, :s, 'An Actor', 'person')"
                ),
                {"i": str(actor_id), "s": actor},
            )
            for _ in range(INDEXABLE_MIN_RECORDS):
                eid = await seed.record(s, 1, dt.datetime.now(dt.UTC), ["IN", "IN-GA"])
                for ent in (state_id, actor_id):
                    link = str(uuid.uuid4())
                    seed.links.append(link)
                    await s.execute(
                        text(
                            "INSERT INTO event_entities (id, event_id, entity_id, role) VALUES (:l, :e, :n, 'subject')"
                        ),
                        {"l": link, "e": eid, "n": str(ent)},
                    )
        listed = {e["slug"] for e in (await _get("/api/v1/sitemap/entities")).json()["entities"]}
    finally:
        await seed.teardown()
    assert actor in listed, "an ordinary actor over the floor is listed"
    assert "goa" not in listed
    assert not listed & set(HUB_SLUGS)


async def test_a_result_is_served_from_memory_and_errors_are_not_stored():
    # Review 2026-09-29: the scans ran on every direct call to the API.
    from fastapi import HTTPException, Response

    import api.routes.hubs as hubs

    hubs._memo.clear()
    calls = []

    @hubs.ttl_cached
    async def handler(key: str, response: Response, db=None):
        calls.append(key)
        if key == "missing":
            raise HTTPException(status_code=404)
        response.headers["Cache-Control"] = "public, s-maxage=600"
        return {"key": key}

    first, second = Response(), Response()
    assert await handler(key="a", response=first) == {"key": "a"}
    assert await handler(key="a", response=second) == {"key": "a"}
    assert calls == ["a"] and second.headers["Cache-Control"] == "public, s-maxage=600"
    for _ in range(2):
        with pytest.raises(HTTPException):
            await handler(key="missing", response=Response())
    assert calls == ["a", "missing", "missing"], "a 404 is computed again, never cached"
    hubs._memo.clear()


async def test_an_absurd_date_is_a_404_not_a_500():
    for day in ("9999-12-31", "0001-01-01"):
        r = await _get(f"/api/v1/archive/{day}")
        assert r.status_code == 404, (day, r.status_code)
