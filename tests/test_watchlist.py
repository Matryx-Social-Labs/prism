"""Watchlist routes over HTTP (auth-gated CRUD + matching events).

Drives the real FastAPI app via httpx/ASGITransport against a live Postgres, so
it also exercises auth (bearer) and get_db's commit. Skips without a database.
"""

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common import auth
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _make_user(email: str) -> tuple[uuid.UUID, str]:
    uid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": str(uid), "e": email}
        )
        bearer = await auth.create_session(s, uid)
    return uid, bearer


async def _seed_event(title: str, sector: str, tickers: list[str]) -> uuid.UUID:
    eid = uuid.uuid4()
    proj = {"finance": {"tickers": tickers, "catalyst": "EARNINGS"}} if tickers else {}
    async with session_scope() as s:
        await s.execute(
            text(
                "INSERT INTO events (id, title, sector, projection) "
                "VALUES (:i, :t, :sec, CAST(:p AS jsonb))"
            ),
            {"i": str(eid), "t": title, "sec": sector, "p": json.dumps(proj)},
        )
    return eid


async def test_watchlist_crud_and_matching_events():
    if not await _db_reachable():
        pytest.skip("no database — run `docker compose up -d postgres`")
    email = f"wl-{uuid.uuid4()}@example.com"
    uid, bearer = await _make_user(email)
    e_ticker = await _seed_event("Reliance earnings beat expectations", "finance", ["RELIANCE"])
    e_sector = await _seed_event("Critical VPN advisory", "cybersecurity", [])
    transport = ASGITransport(app=app)
    auth_hdr = {"Authorization": f"Bearer {bearer}"}
    try:
        async with AsyncClient(transport=transport, base_url="http://t", headers=auth_hdr) as ac:
            # no follows → no matching events
            assert (await ac.get("/api/v1/watchlist/events")).json()["items"] == []

            # follow a ticker (lowercase → normalized to RELIANCE) + a sector
            await ac.post("/api/v1/watchlist", json={"kind": "ticker", "value": "reliance"})
            await ac.post("/api/v1/watchlist", json={"kind": "sector", "value": "Cybersecurity"})
            items = (await ac.get("/api/v1/watchlist")).json()["items"]
            assert {(i["kind"], i["value"]) for i in items} == {
                ("ticker", "RELIANCE"),
                ("sector", "cybersecurity"),
            }

            # both events match (one by ticker, one by sector)
            got = {i["id"] for i in (await ac.get("/api/v1/watchlist/events")).json()["items"]}
            assert str(e_ticker) in got and str(e_sector) in got

            # follow is idempotent
            await ac.post("/api/v1/watchlist", json={"kind": "ticker", "value": "RELIANCE"})
            assert len((await ac.get("/api/v1/watchlist")).json()["items"]) == 2

            # unfollow the ticker
            await ac.delete("/api/v1/watchlist", params={"kind": "ticker", "value": "RELIANCE"})
            left = (await ac.get("/api/v1/watchlist")).json()["items"]
            assert len(left) == 1 and left[0]["kind"] == "sector"

        # unauthenticated → 401
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            assert (await ac.get("/api/v1/watchlist")).status_code == 401
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM watchlist WHERE user_id = :u"), {"u": str(uid)})
            await s.execute(text("DELETE FROM sessions WHERE user_id = :u"), {"u": str(uid)})
            await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": str(uid)})
            await s.execute(
                text("DELETE FROM events WHERE id = ANY(:ids)"),
                {"ids": [str(e_ticker), str(e_sector)]},
            )
