"""The trending list as the chart of arcs reads it: a comma-separated ?sector=
(the reader's six subjects are groups of the pipeline's ten) and the three
additive fields the rows print — hero_event_id, first_seen_at, last_updated_at.

Runs against a stubbed session so it holds on CI's empty Postgres; the stub
emulates only what the route's SQL does that the route can observe (the
sectors ANY() clause), everything after it is real route code.
"""

import contextlib
import datetime as dt
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from common.db import get_db

pytestmark = pytest.mark.asyncio(loop_scope="session")

T0 = dt.datetime(2026, 9, 10, 6, 0, tzinfo=dt.UTC)
T1 = dt.datetime(2026, 9, 15, 6, 0, tzinfo=dt.UTC)


def _row(label: str, sector: str, hero: uuid.UUID | None = None) -> dict:
    return {
        "slug": label.lower().replace(" ", "-"), "label": label, "cast": [label], "source_count": 4,
        "velocity": 1, "sector": sector, "regions": ["IN"], "hero_event_id": hero,
        "first_seen_at": T0, "last_updated_at": T1, "developments": 3,
        "hero_title": None, "hero_image": None, "member_event_ids": [],
    }


class _Rows:
    def __init__(self, rows): self._rows = rows
    def mappings(self): return self
    def all(self): return self._rows


class _FakeSession:
    def __init__(self, rows): self.rows, self.params = rows, {}
    async def execute(self, _stmt, params=None):
        self.params = params or {}
        wanted = self.params.get("sectors")
        return _Rows(self.rows if wanted is None else [r for r in self.rows if r["sector"] in wanted])


@contextlib.contextmanager
def _corpus(rows):
    fake = _FakeSession(rows)
    async def _db():
        yield fake
    app.dependency_overrides[get_db] = _db
    try:
        yield fake
    finally:
        app.dependency_overrides.pop(get_db, None)


async def _trending(**params):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/trending", params=params)
    assert r.status_code == 200, r.text
    return r.json()["stories"]


async def test_a_comma_separated_sector_means_the_union():
    rows = [_row("Rupee", "finance"), _row("Tata", "business"), _row("Poll", "politics")]
    with _corpus(rows):
        assert {s["label"] for s in await _trending(sector="business,finance")} == {"Rupee", "Tata"}


async def test_an_unknown_name_is_dropped_and_an_all_unknown_list_matches_nothing():
    rows = [_row("Tata", "business"), _row("Poll", "politics")]
    with _corpus(rows):
        assert {s["label"] for s in await _trending(sector="business,nonsense")} == {"Tata"}
        assert await _trending(sector="nonsense") == []


async def test_no_sector_binds_null_so_the_sql_clause_is_skipped():
    with _corpus([_row("Poll", "politics")]) as fake:
        assert len(await _trending()) == 1
        assert fake.params["sectors"] is None


async def test_the_rows_carry_the_ticket_id_and_both_timestamps_as_iso():
    hero = uuid.uuid4()
    with _corpus([_row("Poll", "politics", hero), _row("Orphan", "politics", None)]):
        by = {s["label"]: s for s in await _trending()}
    assert by["Poll"]["hero_event_id"] == str(hero)
    assert by["Poll"]["first_seen_at"] == T0.isoformat()
    assert by["Poll"]["last_updated_at"] == T1.isoformat()
    assert by["Orphan"]["hero_event_id"] is None
