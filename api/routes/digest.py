"""Digest route: the synthesized Market Pulse (cached, generated on demand)."""

from fastapi import APIRouter, Response

from api.schemas import DigestResponse
from correlation.digest import get_market_digest

router = APIRouter()


@router.get("/api/v1/digest/markets", response_model=DigestResponse)
async def market_digest():
    digest = await get_market_digest()
    if digest is None:  # synthesis unavailable (e.g. LLM quota) — hide, don't 500
        return Response(status_code=204)
    return DigestResponse(**digest)
