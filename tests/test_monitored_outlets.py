"""The monitored set: the denominator every story's outlet count is out of.

"2 outlets" has to read as "2 of the N outlets Prism reads", never as everyone who
covered the story (strategy report, 2026-09-24). Pinned: the set is the ENABLED
feeds only, counted by publisher; a feed is reachable only when it answered
recently; the public list carries nothing operational; and the extraction's tone
label never reaches a reader (founder D-a).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from common import outlets

NOW = datetime.now(UTC)


def _wm(status=200, ago=timedelta(minutes=4), error=None, ok=True):
    checked = (NOW - ago).isoformat()
    wm = {"rss_last_checked_at": checked, "rss_last_status": status, "rss_etag": "secret-etag"}
    if ok:
        wm["rss_last_success_at"] = checked
    if error:
        wm["rss_last_error"] = error
    return wm


ROWS = [
    {"slug": "thehindu", "name": "The Hindu", "source_type": "rss", "publisher": None, "country": "IN", "language": "en", "funding": None, "watermark": _wm()},
    {"slug": "thehindu_kerala", "name": "The Hindu — Kerala", "source_type": "rss", "publisher": "thehindu", "country": "IN", "language": "en", "funding": None, "watermark": _wm(ago=timedelta(minutes=9))},
    {"slug": "bbc_hindi", "name": "BBC News Hindi", "source_type": "rss", "publisher": "bbc", "country": "IN", "language": "hi", "funding": None, "watermark": _wm(status=304, ok=False)},
    {"slug": "bbc_tamil", "name": "BBC Tamil", "source_type": "rss", "publisher": "bbc", "country": "IN", "language": "ta", "funding": "public", "watermark": _wm(error="ConnectTimeout: boom")},
    {"slug": "rbi", "name": "Reserve Bank of India", "source_type": "rss", "publisher": None, "country": "IN", "language": "en", "funding": "state", "watermark": _wm(ago=timedelta(hours=3))},
    {"slug": "prajavani", "name": "Prajavani", "source_type": "rss", "publisher": None, "country": "IN", "language": "kn", "funding": None, "watermark": None},
]


class _R:
    def __init__(self, rows): self.rows = rows
    def mappings(self): return self
    def all(self): return self.rows


class _S:
    def __init__(self): self.seen: list[tuple[str, dict]] = []
    async def execute(self, stmt, params=None, *a, **kw):
        self.seen.append((str(stmt), params or {}))
        return _R(ROWS if "FROM sources" in str(stmt) else [])


@pytest.fixture(autouse=True)
def _fresh_cache():
    outlets.reset_monitored_cache()
    yield
    outlets.reset_monitored_cache()


@pytest.mark.asyncio(loop_scope="session")
async def test_the_set_is_enabled_feeds_counted_by_publisher():
    db = _S()
    m = await outlets.monitored(db)
    slugs = db.seen[0][1]["slugs"]
    # Disabled feeds are not monitored, whatever the sources table still holds.
    assert "pib" not in slugs and "sebi" not in slugs and "bleepingcomputer" not in slugs
    assert "thehindu" in slugs
    # The Hindu's two feeds are one masthead; BBC's two services are one.
    assert m.outlets == 4  # thehindu, bbc, rbi, prajavani
    assert len(m.feeds) == 6
    assert m.checked_at == ROWS[0]["watermark"]["rss_last_checked_at"]  # the most recent poll
    by = {f.slug: f for f in m.feeds}
    assert by["thehindu_kerala"].state == "IN-KL"
    assert by["rbi"].official and not by["thehindu"].official


@pytest.mark.asyncio(loop_scope="session")
async def test_a_feed_is_reachable_only_when_it_answered_within_the_hour():
    by = {f.slug: f for f in (await outlets.monitored(_S())).feeds}
    assert by["thehindu"].reachable
    assert by["bbc_hindi"].reachable, "304 is 'nothing new', still an answer"
    assert by["bbc_hindi"].ok_at is None
    assert not by["bbc_tamil"].reachable, "the last poll failed"
    assert not by["rbi"].reachable, "three hours without a poll"
    assert not by["prajavani"].reachable, "never polled"


@pytest.mark.asyncio(loop_scope="session")
async def test_the_public_list_carries_nothing_operational():
    import api.routes.meta as meta
    from api.main import app

    async def fake_db():
        yield _S()

    app.dependency_overrides[meta.get_db] = fake_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/api/v1/sources")
    finally:
        app.dependency_overrides.pop(meta.get_db, None)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["outlets"] == 4
    text = r.text
    assert "boom" not in text and "secret-etag" not in text and "feeder" not in text
    assert set(body["feeds"][0]) == {"slug", "name", "publisher", "code", "origin", "language", "state", "sector", "domain", "official", "checked_at", "ok_at", "reachable"}


def test_no_tone_label_in_the_reader_payload():
    from api.schemas import PerspectiveOut, SourceRef

    assert "stance" not in SourceRef.model_fields
    assert "stance" not in PerspectiveOut.model_fields


@pytest.mark.asyncio(loop_scope="session")
async def test_the_event_carries_the_denominator_and_no_stance():
    import api.routes.events as events
    from api.main import app

    eid = uuid.uuid4()
    seen: list[str] = []

    class _ER:
        def __init__(self, sql): self.sql = sql
        def mappings(self): return self
        def scalars(self): return self
        def first(self):
            if "FROM events WHERE id" in self.sql:
                return {"id": eid, "title": "t", "headline_by": None, "summary": "s", "sector": None, "subsector": None,
                        "image_url": None, "regions": [], "occurred_at": None, "last_updated_at": NOW, "projection": {}}
            return None
        def all(self): return ROWS if "FROM sources WHERE slug = ANY" in self.sql else []

    class _ES:
        async def execute(self, stmt, params=None, *a, **kw):
            seen.append(str(stmt))
            return _ER(str(stmt))

    async def fake_db():
        yield _ES()

    app.dependency_overrides[events.get_db] = fake_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get(f"/api/v1/events/{eid}")
    finally:
        app.dependency_overrides.pop(events.get_db, None)
    assert r.status_code == 200, r.text
    assert r.json()["monitored_outlets"] == 4
    assert r.json()["monitored_checked_at"] == ROWS[0]["watermark"]["rss_last_checked_at"]
    assert not any("'stance'" in sql for sql in seen), "the tone label is not even read"
