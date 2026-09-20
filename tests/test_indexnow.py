"""IndexNow: the records that moved go to the index at once; CVE-only records,
which the feed never serves, are never pinged; a dev host never pings; a
refusal is a zero, not an exception into the worker."""

import uuid

import httpx
import pytest
from sqlalchemy import text

from common import indexnow
from common.config import get_settings
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_the_key_is_served_from_the_web_root():
    # The protocol verifies ownership by fetching /<key>.txt; the file must
    # exist and hold exactly the key the module posts.
    from pathlib import Path

    f = Path(__file__).resolve().parents[1] / "web" / "public" / f"{indexnow.KEY}.txt"
    assert f.exists(), f
    assert f.read_text().strip() == indexnow.KEY
    assert len(indexnow.KEY) == 32 and all(c in "0123456789abcdef" for c in indexnow.KEY)


async def test_submit_posts_the_batch_with_the_key_and_reads_the_answer(monkeypatch):
    monkeypatch.setattr(get_settings(), "prism_web_url", "https://www.readprism.news")
    seen: list = []

    def handler(req: httpx.Request) -> httpx.Response:
        import json

        seen.append(json.loads(req.content))
        return httpx.Response(202)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        n = await indexnow.submit(["https://www.readprism.news/story/1", "https://www.readprism.news/feed"], c)
    assert n == 2
    assert seen[0]["host"] == "www.readprism.news" and seen[0]["key"] == indexnow.KEY
    assert seen[0]["keyLocation"] == f"https://www.readprism.news/{indexnow.KEY}.txt"
    assert seen[0]["urlList"] == ["https://www.readprism.news/story/1", "https://www.readprism.news/feed"]

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(422, text="bad key"))) as c:
        assert await indexnow.submit(["https://www.readprism.news/story/1"], c) == 0, "a refusal is a zero, never a raise"
    assert await indexnow.submit([]) == 0

    monkeypatch.setattr(get_settings(), "prism_web_url", "http://localhost:3000")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        assert await indexnow.submit(["http://localhost:3000/story/1"], c) == 0, "a dev machine never pings"
    assert len(seen) == 1


async def test_changed_urls_are_the_served_records_that_moved_and_never_cve_only(monkeypatch):
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("no local database")
    monkeypatch.setattr(get_settings(), "prism_web_url", "https://www.readprism.news")
    fresh, stale, cve = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    try:
        async with session_scope() as s:
            await s.execute(text("INSERT INTO events (id,title,summary,last_updated_at) VALUES (:i,'moved','s',now())"), {"i": str(fresh)})
            await s.execute(text("INSERT INTO events (id,title,summary,last_updated_at) VALUES (:i,'old','s',now() - interval '3 hours')"), {"i": str(stale)})
            await s.execute(
                text("INSERT INTO events (id,title,summary,last_updated_at,projection) VALUES (:i,'cve','s',now(), '{\"source_slugs\": [\"nvd\"]}'::jsonb)"),
                {"i": str(cve)},
            )
        async with session_scope() as s:
            urls = await indexnow.changed_urls(s, since_minutes=70)
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:ids AS uuid[]))"), {"ids": [str(fresh), str(stale), str(cve)]})
    assert f"https://www.readprism.news/story/{fresh}" in urls
    assert f"https://www.readprism.news/story/{stale}" not in urls
    assert f"https://www.readprism.news/story/{cve}" not in urls
    assert "https://www.readprism.news/feed" in urls and "https://www.readprism.news/trending" in urls
