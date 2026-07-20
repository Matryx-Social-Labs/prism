"""Digest route: the synthesized Market Pulse (cached, generated on demand)."""

from fastapi import APIRouter

from api.schemas import DigestResponse
from correlation.digest import get_market_digest

router = APIRouter()


@router.get("/api/v1/digest/markets", response_model=DigestResponse)
async def market_digest():
    return DigestResponse(**await get_market_digest())
