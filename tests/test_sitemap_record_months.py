"""The records sitemap is an index of one file per month. One file stopped at the
protocol's 50,000 URLs (LIMIT 50000), and at ~300 indexable records a day it
would have dropped the oldest without a word inside three months (2026-11-02).
A record files under the month Prism first saw it, which never changes."""

import datetime as dt
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from api.main import app
from common import outlets
from common.db import session_scope
from tests.test_sitemap_lastmod import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _record(tag: str, seen: dt.datetime, n_outlets: int) -> str:
    eid = str(uuid.uuid4())
    async with session_scope() as s:
        await s.execute(
            text(
                "INSERT INTO events (id, title, summary, sector, regions, projection, first_seen_at, last_updated_at) "
                "VALUES (:i, 'A record', 's', 'politics', ARRAY['IN'], CAST(:p AS jsonb), :w, :w)"
            ),
            {
                "i": eid,
                "p": json.dumps({"source_slugs": [f"zz_{tag}_{k}" for k in range(n_outlets)]}),
                "w": seen,
            },
        )
    return eid


async def test_each_month_lists_its_own_indexed_records_and_the_index_counts_them():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    outlets.reset_cache()
    aug, sep = (
        dt.datetime(2026, 8, 31, 23, 0, tzinfo=dt.UTC),
        dt.datetime(2026, 9, 1, 1, 0, tzinfo=dt.UTC),
    )
    in_aug, in_sep = await _record(tag, aug, 2), await _record(tag, sep, 3)
    single = await _record(tag, sep, 1)  # one outlet: not indexed, so in no file
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            months = {
                m["month"]: m
                for m in (await c.get("/api/v1/sitemap/records/months")).json()["months"]
            }
            ids = lambda month: {r["id"] for r in c_json[month]["records"]}  # noqa: E731
            c_json = {
                m: (await c.get(f"/api/v1/sitemap/records?month={m}")).json()
                for m in ("2026-08", "2026-09")
            }
            everything = {
                r["id"] for r in (await c.get("/api/v1/sitemap/records")).json()["records"]
            }
            bad = await c.get("/api/v1/sitemap/records?month=2026-9")
    finally:
        async with session_scope() as s:
            await s.execute(
                text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"),
                {"e": [in_aug, in_sep, single]},
            )
    assert in_aug in ids("2026-08") and in_aug not in ids("2026-09")
    assert in_sep in ids("2026-09") and single not in ids("2026-09")
    for m in ("2026-08", "2026-09"):
        assert months[m]["records"] == len(ids(m)), "the index counts exactly what its file lists"
        assert months[m]["lastmod"]
    assert {in_aug, in_sep} <= everything and single not in everything, (
        "the unfiltered list still works while the web deploys"
    )
    assert bad.status_code == 422
