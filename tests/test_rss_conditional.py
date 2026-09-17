import asyncio
import time
from datetime import UTC, datetime

import httpx
import pytest

import ingestion.rss as rss


def test_conditional_headers_use_last_successful_validators():
    assert rss._conditional_headers({
        "rss_etag": '"abc"', "rss_last_modified": "Wed, 16 Sep 2026 10:00:00 GMT",
        "unrelated_cursor": 7,
    }) == {
        "If-None-Match": '"abc"',
        "If-Modified-Since": "Wed, 16 Sep 2026 10:00:00 GMT",
    }


def test_response_watermark_preserves_other_collector_state():
    response = httpx.Response(
        200,
        headers={"ETag": '"new"', "Last-Modified": "Thu, 17 Sep 2026 10:00:00 GMT"},
        request=httpx.Request("GET", "https://example.test/feed"),
    )
    got = rss._response_watermark({"other": "keep", "rss_last_error": "old"}, response)
    assert got["other"] == "keep"
    assert got["rss_etag"] == '"new"'
    assert got["rss_last_modified"].startswith("Thu")
    assert got["rss_last_status"] == 200
    assert "rss_last_error" not in got
    datetime.fromisoformat(got["rss_last_success_at"]).astimezone(UTC)


def test_feed_timestamp_is_interpreted_as_utc_not_machine_local_time():
    parsed = time.struct_time((2026, 9, 17, 12, 30, 0, 3, 260, 0))
    assert rss._entry_datetime({"published_parsed": parsed}) == datetime(
        2026, 9, 17, 12, 30, tzinfo=UTC
    )


@pytest.mark.asyncio
async def test_not_modified_fetch_does_not_parse_or_persist(monkeypatch):
    saved = []

    async def watermark(_slug):
        return {"rss_etag": '"same"'}

    async def save(_slug, value):
        saved.append(value)

    async def forbidden(_envelopes):
        raise AssertionError("304 response reached persistence")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["if-none-match"] == '"same"'
        return httpx.Response(304, request=request)

    monkeypatch.setattr(rss, "get_watermark", watermark)
    monkeypatch.setattr(rss, "set_watermark", save)
    monkeypatch.setattr(rss, "persist_envelopes", forbidden)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        count = await rss._collect_one(
            client, rss.FeedSpec("test", "https://example.test/feed"),
            asyncio.Semaphore(1),
        )
    assert count == 0
    assert saved[-1]["rss_last_status"] == 304


@pytest.mark.asyncio
async def test_successful_fetch_persists_and_updates_validators(monkeypatch):
    persisted = []
    saved = []

    async def watermark(_slug):
        return {}

    async def save(_slug, value):
        saved.append(value)

    async def persist(envelopes):
        persisted.extend(envelopes)
        return len(envelopes)

    body = """<?xml version='1.0'?><rss version='2.0'><channel><title>T</title>
      <item><guid>one</guid><link>https://example.test/story?utm_source=rss</link>
      <title>Breaking headline</title><description>Useful summary</description></item>
      </channel></rss>"""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body, headers={"ETag": '"v2"'}, request=request)

    monkeypatch.setattr(rss, "get_watermark", watermark)
    monkeypatch.setattr(rss, "set_watermark", save)
    monkeypatch.setattr(rss, "persist_envelopes", persist)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        count = await rss._collect_one(
            client, rss.FeedSpec("test", "https://example.test/feed"),
            asyncio.Semaphore(1),
        )
    assert count == 1 and persisted[0].external_id == "one"
    assert saved[-1]["rss_etag"] == '"v2"'
