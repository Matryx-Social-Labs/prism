"""The API host is data for the web app, never a page to index. Search Console,
2026-11-02: https://api.readprism.news/ sat in "Not found (404)", a host Google
should not be crawling as pages at all."""

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.mark.parametrize("path", ["/", "/healthz", "/api/v1/no-such-route"])
async def test_every_api_response_asks_not_to_be_indexed(path):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get(path)
    assert r.headers.get("x-robots-tag") == "noindex"
