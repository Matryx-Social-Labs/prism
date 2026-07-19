"""Watchlist routes: read-only follows of tickers/sectors + their matching events.

Read-only by design (the design review split push/alerts into Phase 2). All
routes are auth-gated; a follow is one row per (user, kind, value).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from common.db import get_db

router = APIRouter()

VALID_KINDS = {"ticker", "sector"}


class WatchItem(BaseModel):
    id: str
    kind: str
    value: str


class WatchlistResponse(BaseModel):
    items: list[WatchItem]


class FollowRequest(BaseModel):
    kind: str
    value: str


class WatchEvent(BaseModel):
    id: str
    title: str
    summary: str | None
    sector: str | None
    tickers: list[str]
    catalyst: str | None
    last_updated_at: str


class WatchEventsResponse(BaseModel):
    items: list[WatchEvent]


def _normalize(kind: str, value: str) -> str:
    v = value.strip()
    return v.upper() if kind == "ticker" else v.lower()


async def _list(db: AsyncSession, user_id: uuid.UUID) -> WatchlistResponse:
    rows = (
        await db.execute(
            text("SELECT id, kind, value FROM watchlist WHERE user_id = :u ORDER BY created_at DESC"),
            {"u": str(user_id)},
        )
    ).mappings().all()
    return WatchlistResponse(
        items=[WatchItem(id=str(r["id"]), kind=r["kind"], value=r["value"]) for r in rows]
    )


@router.get("/api/v1/watchlist", response_model=WatchlistResponse)
async def get_watchlist(
    user_id: uuid.UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await _list(db, user_id)


@router.post("/api/v1/watchlist", response_model=WatchlistResponse)
async def follow(
    body: FollowRequest,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.kind not in VALID_KINDS:
        raise HTTPException(status_code=422, detail="kind must be 'ticker' or 'sector'")
    value = _normalize(body.kind, body.value)
    if not value or len(value) > 40:
        raise HTTPException(status_code=422, detail="value must be 1-40 chars")
    await db.execute(
        text(
            "INSERT INTO watchlist (id, user_id, kind, value) "
            "VALUES (gen_random_uuid(), :u, :k, :v) "
            "ON CONFLICT (user_id, kind, value) DO NOTHING"
        ),
        {"u": str(user_id), "k": body.kind, "v": value},
    )
    return await _list(db, user_id)


@router.delete("/api/v1/watchlist", response_model=WatchlistResponse)
async def unfollow(
    kind: str,
    value: str,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text("DELETE FROM watchlist WHERE user_id = :u AND kind = :k AND value = :v"),
        {"u": str(user_id), "k": kind, "v": _normalize(kind, value)},
    )
    return await _list(db, user_id)


@router.get("/api/v1/watchlist/events", response_model=WatchEventsResponse)
async def watchlist_events(
    user_id: uuid.UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    follows = (
        await db.execute(
            text("SELECT kind, value FROM watchlist WHERE user_id = :u"), {"u": str(user_id)}
        )
    ).mappings().all()
    sectors = [f["value"] for f in follows if f["kind"] == "sector"]
    tickers = [f["value"] for f in follows if f["kind"] == "ticker"]
    if not sectors and not tickers:
        return WatchEventsResponse(items=[])
    # jsonb_exists_any(projection->finance->tickers, :tickers) is the function
    # form of the ?| operator — avoids the `?` clashing with bind-param parsing.
    rows = (
        await db.execute(
            text(
                """
                SELECT id, title, summary, sector, projection, last_updated_at
                FROM events
                WHERE sector = ANY(:sectors)
                   OR jsonb_exists_any(projection -> 'finance' -> 'tickers', :tickers)
                ORDER BY last_updated_at DESC
                LIMIT 40
                """
            ),
            {"sectors": sectors, "tickers": tickers},
        )
    ).mappings().all()
    items = []
    for r in rows:
        finance = (r["projection"] or {}).get("finance") or {}
        items.append(
            WatchEvent(
                id=str(r["id"]),
                title=r["title"],
                summary=r["summary"],
                sector=r["sector"],
                tickers=(finance.get("tickers") or [])[:4],
                catalyst=finance.get("catalyst"),
                last_updated_at=r["last_updated_at"].isoformat(),
            )
        )
    return WatchEventsResponse(items=items)
