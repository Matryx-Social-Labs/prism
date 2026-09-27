"""Feed curation rules, exercised without a corpus.

The live-corpus tests in test_personalization.py can only assert these on a
populated database — on CI's empty Postgres they skip, so the rules that decide
what a reader actually sees ship untested. Here the route runs for real against
a stubbed session, so the sector filter and the raw-record exclusion are
covered on every run.

What this deliberately does NOT cover: the per-sector ROW_NUMBER quota in the
window, and whether the record predicate really rides the index. Both need a
real Postgres with thousands of rows — the seeded corpus test in
test_personalization.py is the right home for them.
"""

import contextlib
import datetime as dt
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.routes.feed import CVE_ONLY_SOURCES
from common.db import get_db

pytestmark = pytest.mark.asyncio(loop_scope="session")

NOW = dt.datetime.now(dt.UTC)


class _Rows:
    """Stands in for a SQLAlchemy Result: .mappings().all()."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def mappings(self):
        return self

    def scalars(self):
        return self

    def all(self):
        return self._rows


def _is_record(row: dict) -> bool:
    """Mirrors the SQL predicate: sourced WHOLLY from the raw-record feeds."""
    slugs = set((row.get("projection") or {}).get("source_slugs") or [])
    return bool(slugs) and slugs <= CVE_ONLY_SOURCES


class _FakeSession:
    """Emulates what the route's SQL does that the route can observe: the sector
    WHERE clause and the record exclusion. Everything after it is real route code.

    The exclusion lives in SQL (it has to: leaving it to Python let raw records
    fill the window and evict the news before the ranker ever saw it), so a stub
    that ignored it would let these tests pass against a route that filtered
    nothing.
    """

    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.params: dict = {}
        self.queries: list[dict] = []

    async def execute(self, _stmt, params=None):
        if "FROM sources" in str(_stmt):  # the outlet registry: no outlets in this corpus
            return _Rows([])
        if "GROUP BY image_phash" in str(_stmt):  # placeholder photographs: none in this corpus
            return _Rows([])
        self.params = params or {}
        self.queries.append(self.params)
        wanted = self.params.get("sectors")
        rows = self.rows if wanted is None else [r for r in self.rows if r["sector"] in wanted]
        if self.params.get("cve_only") is not None:  # the news window excludes raw records
            rows = [r for r in rows if not _is_record(r)]
        # The scope predicates, as the SQL has them: bound by the route, or absent.
        state_only = self.params.get("state_only")
        if state_only:
            rows = [r for r in rows if state_only in (r.get("regions") or [])]
        if self.params.get("national"):
            rows = [r for r in rows if "IN" in (r.get("regions") or []) and not any(x.startswith("IN-") for x in r["regions"])]
        if self.params.get("world"):
            rows = [r for r in rows if not any(x == "IN" or x.startswith("IN-") for x in (r.get("regions") or []))]
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


async def test_no_lens_weaves_raw_records_into_the_feed():
    """Founder, 2026-09-27: no vulnerability-record feeds — cyber comes from news
    that reports a story. The cyber lens used to weave raw NVD/KEV rows in, one
    in every three; the rows that remain are never served, to any lens."""
    rows = [_row(f"CVE-2026-{i}", "cybersecurity", record=True, age_min=i) for i in range(10)]
    rows += [_row(f"Story {i}", "cybersecurity", age_min=100 + i) for i in range(3)]
    with _corpus(rows):
        for lens in ("cyber", "reader", "markets"):
            titles = [i["title"] for i in await _feed(lens=lens, limit=30)]
            assert titles == ["Story 0", "Story 1", "Story 2"], (lens, titles)


async def test_sort_top_stays_score_ordered():
    """REVIEW (api-contract): the interleave ran unconditionally, so sort=top was
    no longer score-descending. The feed's lead rail reads items[:3] straight off
    it, so slot 3 became a changelog row regardless of score."""
    rows = [_row(f"CVE-2026-{i}", "cybersecurity", record=True, age_min=i) for i in range(10)]
    rows += [_row(f"Story {i}", "cybersecurity", age_min=100 + i) for i in range(10)]
    with _corpus(rows):
        items = await _feed(lens="cyber", limit=12, sort="top")
    scores = [i["score"] for i in items]
    assert scores == sorted(scores, reverse=True), scores


async def test_a_comma_separated_sector_means_the_union():
    """The reader's six subjects are groups of the pipeline's ten. "Business &
    Markets" is business+finance, and a single-sector parameter could only ever
    show half of it."""
    rows = [_row("Rupee falls", "finance"), _row("Tata results", "business"), _row("Poll result", "politics")]
    with _corpus(rows):
        titles = {i["title"] for i in await _feed(sector="business,finance", limit=30)}
    assert titles == {"Rupee falls", "Tata results"}


async def test_an_unknown_name_in_the_list_is_dropped_not_fatal():
    rows = [_row("Tata results", "business"), _row("Poll result", "politics")]
    with _corpus(rows):
        titles = {i["title"] for i in await _feed(sector="business,nonsense", limit=30)}
    assert titles == {"Tata results"}


async def test_the_scope_is_a_server_slice_not_a_filter_over_the_state_first_page():
    """REGRESSION: the page was sorted state-first and the three pills filtered it
    in the browser. A Karnataka reader (35% of two days' events) got a page that
    was all Karnataka, so "National" was empty and "All" was "Your state" again."""
    # The India-wide and foreign rows are the NEWEST, so an unfiltered page would
    # lead with them and a state-first page would bury them: each slice differs.
    rows = [dict(_row(f"India {i}", "politics", age_min=i), regions=["IN"]) for i in range(3)]
    rows += [dict(_row("Kerala", "politics", age_min=3), regions=["IN", "IN-KL"]), dict(_row("Washington", "politics", age_min=4), regions=["US"])]
    rows += [dict(_row(f"KA {i}", "politics", age_min=10 + i), regions=["IN", "IN-KA"]) for i in range(40)]
    with _corpus(rows):
        region = await _feed(state="IN-KA", scope="region", limit=30)
        national = await _feed(state="IN-KA", scope="national", limit=30)
        everything = await _feed(state="IN-KA", scope="all", limit=30)
    assert all(t["title"].startswith("KA") for t in region) and len(region) == 30
    assert {t["title"] for t in national} == {"India 0", "India 1", "India 2"}, "national is India-wide, no state — not 'not my state'"
    # All is newest-first, not state-first: India-wide and foreign lead because they are newer.
    assert [t["title"] for t in everything][:5] == ["India 0", "India 1", "India 2", "Kerala", "Washington"] and len(everything) == 30
    with _corpus(rows):
        world = await _feed(state="IN-KA", scope="world", limit=30)
    assert [t["title"] for t in world] == ["Washington"], "world is what does not involve India"
    # Without a scope the old state-first tiering still stands for other callers.
    with _corpus(rows):
        legacy = await _feed(state="IN-KA", limit=45)
    assert all(t["title"].startswith("KA") for t in legacy[:40])
