"""Feed curation rules, exercised without a corpus.

The live-corpus tests in test_personalization.py can only assert these on a
populated database — on CI's empty Postgres they skip, so the rules that decide
what a reader actually sees ship untested. Here the route runs for real against
a stubbed session, so the sector filter, the CVE-record cap and the interleave
are all covered on every run.

What this deliberately does NOT cover: the SQL window itself (the per-(sector,
is-record) ROW_NUMBER quota). That needs a real Postgres with thousands of rows
— the corpus test is the right home for it.
"""

import contextlib
import datetime as dt
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from common.db import get_db

pytestmark = pytest.mark.asyncio(loop_scope="session")

NOW = dt.datetime.now(dt.UTC)


class _Rows:
    """Stands in for a SQLAlchemy Result: .mappings().all()."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    """Applies the one thing the route's SQL does that the route can observe:
    the sector WHERE clause. Everything after it is real route code."""

    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.params: dict = {}

    async def execute(self, _stmt, params=None):
        self.params = params or {}
        wanted = self.params.get("sectors")
        rows = self.rows if wanted is None else [r for r in self.rows if r["sector"] in wanted]
        return _Rows(rows)


@contextlib.contextmanager
def _corpus(rows: list[dict]):
    fake = _FakeSession(rows)
    app.dependency_overrides[get_db] = lambda: fake
    try:
        yield fake
    finally:
        app.dependency_overrides.pop(get_db, None)


def _row(title: str, sector: str, *, record: bool = False, age_min: int = 0) -> dict:
    """A raw CVE record is an event whose only sources are the vulnerability feeds."""
    return {
        "id": uuid.uuid4(),
        "title": title,
        "summary": "s",
        "sector": sector,
        "subsector": None,
        "regions": [],
        "image_url": None,
        "projection": {"source_slugs": ["nvd"] if record else ["thehindu", "reuters"]},
        "last_updated_at": NOW - dt.timedelta(minutes=age_min),
        "occurred_at": None,
    }


async def _feed(**params) -> list[dict]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/feed", params=params)
        assert r.status_code == 200, r.text
        return r.json()["items"]


async def test_a_lens_ranks_the_world_instead_of_filtering_it():
    """REGRESSION (ISSUE-003): `sectors = active_lens.sectors` made the cyber
    lens a cybersecurity-only feed — no elections, no markets, no world news."""
    rows = [_row("Election result", "politics"), _row("Breach at a bank", "cybersecurity")]
    with _corpus(rows) as db:
        items = await _feed(lens="cyber", limit=30)
    assert db.params["sectors"] is None, "the lens is being pushed into the SQL filter"
    assert {i["sector"] for i in items} == {"politics", "cybersecurity"}


async def test_an_explicit_sector_is_still_honoured():
    """Removing the lens filter must not remove the reader's own filter."""
    rows = [_row("Election result", "politics"), _row("Breach at a bank", "cybersecurity")]
    with _corpus(rows) as db:
        items = await _feed(sector="politics", limit=30)
    assert db.params["sectors"] == ["politics"]
    assert [i["sector"] for i in items] == ["politics"]


async def test_profile_interests_still_narrow_the_feed():
    rows = [_row("Election result", "politics"), _row("Breach at a bank", "cybersecurity")]
    with _corpus(rows) as db:
        items = await _feed(interests="politics", lens="cyber", limit=30)
    assert db.params["sectors"] == ["politics"]
    assert [i["title"] for i in items] == ["Election result"]


async def test_the_general_reader_never_sees_a_raw_cve_record():
    rows = [_row("CVE-2026-1", "cybersecurity", record=True), _row("Breach at a bank", "cybersecurity")]
    with _corpus(rows):
        items = await _feed(limit=30)  # no lens → the general reader
    assert [i["title"] for i in items] == ["Breach at a bank"]


async def test_raw_records_cannot_own_more_than_a_third_of_the_page():
    """A GRC reader is here for the records — but not for a page of nothing else.
    Records are machine-re-stamped, so they are permanently the newest rows."""
    rows = [_row(f"CVE-2026-{i}", "cybersecurity", record=True, age_min=i) for i in range(20)]
    rows += [_row(f"Story {i}", "cybersecurity", age_min=100 + i) for i in range(20)]
    with _corpus(rows):
        items = await _feed(lens="cyber", limit=9)
    records = [i for i in items if i["title"].startswith("CVE-")]
    assert len(items) == 9
    assert len(records) <= 3, f"{len(records)}/9 of the page is changelog"


async def test_raw_records_are_interleaved_not_stacked_at_the_top():
    """Capping alone left them clustered at the top (they sort newest), so the
    reader's whole first screen was still changelog."""
    rows = [_row(f"CVE-2026-{i}", "cybersecurity", record=True, age_min=i) for i in range(10)]
    rows += [_row(f"Story {i}", "cybersecurity", age_min=100 + i) for i in range(10)]
    with _corpus(rows):
        items = await _feed(lens="cyber", limit=12, sort="latest")
    kinds = ["record" if i["title"].startswith("CVE-") else "news" for i in items]
    assert kinds[:3] == ["news", "news", "record"], kinds
    assert kinds[3:6] == ["news", "news", "record"], kinds


async def test_scarce_news_does_not_let_records_flood_the_page():
    """The interleave alone can't hold the line: once the news runs out it
    appends records back to back, so a sector with 2 stories and a thousand CVE
    rows would still serve a changelog. The limit//3 cap is what stops it."""
    rows = [_row(f"CVE-2026-{i}", "cybersecurity", record=True, age_min=i) for i in range(50)]
    rows += [_row(f"Story {i}", "cybersecurity", age_min=100 + i) for i in range(2)]
    with _corpus(rows):
        items = await _feed(lens="cyber", limit=30)
    records = [i for i in items if i["title"].startswith("CVE-")]
    assert len(records) <= 10, f"{len(records)} records on a 30-item page"


async def test_a_records_only_corpus_still_returns_a_page():
    """No news to interleave with: the loop must still terminate and serve the
    records rather than emptying the feed."""
    rows = [_row(f"CVE-2026-{i}", "cybersecurity", record=True, age_min=i) for i in range(5)]
    with _corpus(rows):
        items = await _feed(lens="cyber", limit=30)
    assert len(items) == 5
