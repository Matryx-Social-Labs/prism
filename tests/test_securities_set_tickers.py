"""tools.securities --revalidate --apply writes ticker lists into records whose
JSON can be null at either level (prod, 2026-09-27: "cannot set path in scalar")."""

import json
import uuid

import asyncpg
import pytest

from common.config import get_settings
from tools.securities import SET_TICKERS

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _conn() -> asyncpg.Connection:
    url = get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        return await asyncpg.connect(url, timeout=5)
    except (OSError, asyncpg.PostgresError):
        pytest.skip("no database — run `docker compose up -d postgres`")


@pytest.mark.parametrize(
    "projection",
    ["null", '{"finance": null, "source_count": 2}', '{"source_count": 2}', '{"finance": {"catalyst": "earnings", "tickers": ["F"]}}'],
)
async def test_set_tickers_writes_into_any_projection_shape(projection: str):
    c = await _conn()
    eid = uuid.uuid4()
    try:
        await c.execute("INSERT INTO events (id, title, projection) VALUES ($1, 'Test', $2::jsonb)", eid, projection)
        await c.execute(SET_TICKERS.format(table="events", col="projection"), json.dumps(["SUNPHARMA"]), eid)
        got = json.loads(await c.fetchval("SELECT projection::text FROM events WHERE id = $1", eid))
        assert got["finance"]["tickers"] == ["SUNPHARMA"]
        before = json.loads(projection) or {}
        # Nothing else in the record is lost: its other keys, and the finance read's other fields.
        for k, v in before.items():
            if k != "finance":
                assert got[k] == v
        if isinstance(before.get("finance"), dict) and "catalyst" in before["finance"]:
            assert got["finance"]["catalyst"] == "earnings"
    finally:
        await c.execute("DELETE FROM events WHERE id = $1", eid)
        await c.close()
