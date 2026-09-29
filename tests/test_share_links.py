"""Founder share links (/admin/marketing; common/share_links.py).

Pinned: a link opens only a public Prism page, whatever is pasted; its tags
carry the platform, medium, campaign and its code, and its short address drops
the www; only a founder makes, lists or archives one, on the record; an
archived link still resolves, because a posted link must keep working; the
beacon counts a code only when it is a link, and never takes `account` from a
browser; an account made by a sign-in that carried a code is counted once
against the link, and the code is stored nowhere on the account; the Overview
adds the visits up by platform and by campaign.
"""

import re
import uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import api.routes.auth as auth_routes
from api.main import app
from common import auth, metrics, share_links, stream, usage
from common.config import get_settings
from common.db import session_scope
from tests.test_projection_summary import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")
WEB = "https://www.readprism.news"
ATTRIBUTION_TS = Path(__file__).resolve().parents[1] / "web" / "src" / "lib" / "attribution.ts"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.setattr(stream, "_redis", None)  # bound to another test module's loop otherwise
    share_links.forget()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def _reader() -> dict[str, str]:
    n = uuid.uuid4().int
    return {"user-agent": f"Mozilla/5.0 (iPhone) test-{uuid.uuid4().hex}",
            "x-forwarded-for": f"10.{n % 256}.{(n >> 8) % 256}.{(n >> 16) % 256}"}


async def _count(event: str, dim: str) -> int:
    async with session_scope() as s:
        return (await s.execute(text("SELECT coalesce(sum(count), 0) FROM usage_daily WHERE day = :d AND event = :e AND dim = :m"),
                                {"d": usage.today(), "e": event, "m": dim})).scalar()


# ── The rules (no database) ─────────────────────────────────────────────────

@pytest.mark.parametrize("pasted,path", [
    ("https://www.readprism.news/story/abc123?utm_source=x#quotes", "/story/abc123"),
    ("readprism.news/entity/nirmala-sitharaman/", "/entity/nirmala-sitharaman"),
    ("/feed/2026-09-27", "/feed/2026-09-27"),
    ("https://readprism.news", "/"),
    ("/", "/"),
    ("/story/abc/quote/q2", "/story/abc/quote/q2"),
    # An Indian-language slug arrives percent-encoded, and stays so.
    ("https://www.readprism.news/entity/%E0%A4%85%E0%A4%AE%E0%A4%BF%E0%A4%A4", "/entity/%E0%A4%85%E0%A4%AE%E0%A4%BF%E0%A4%A4"),
])
async def test_a_link_opens_the_page_that_was_pasted(pasted, path):
    assert share_links.target_path(pasted, WEB) == path


@pytest.mark.parametrize("pasted", [
    "https://evil.example/story/abc", "//evil.example/story/abc", "javascript:alert(1)", "/admin", "/account",
    "/signin", "/label/abc", "/auth/verify", "/story/a/b/c/d/e", "/story/<script>", "", "https://readprism.news.evil.example/",
    "ftp://readprism.news/story/abc",
    # Dot segments, however encoded: a browser resolves each of these to a private page.
    "/story/../admin", "/story/%2e%2e/admin", "/feed/../account", "/story/%2E/x", "/story/a%2Fb",
    "/plus/welcome", "http://[::1", "/story/a%00b",
])
async def test_a_link_never_opens_anything_but_a_public_page(pasted):
    assert share_links.target_path(pasted, WEB) is None


async def test_the_tags_and_the_short_address():
    row = {"code": "k3f9qa", "path": "/story/abc", "platform": "whatsapp", "medium": "message", "campaign": "launch-week"}
    assert share_links.long_url(WEB, row) == (
        f"{WEB}/story/abc?utm_source=whatsapp&utm_medium=message&utm_campaign=launch-week&utm_content=k3f9qa")
    assert "utm_campaign" not in share_links.long_url(WEB, {**row, "campaign": ""})
    assert share_links.short_url(WEB, "k3f9qa") == "https://readprism.news/go/k3f9qa"
    assert share_links.short_url("http://localhost:3000", "k3f9qa") == "http://localhost:3000/go/k3f9qa"
    assert {share_links.kind(p) for p in ("/story/a/quote/q1", "/feed/2026-09-27", "/feed", "/", "/state/kerala")} == {
        "quote", "day", "feed", "landing", "state"}
    assert all(share_links.CODE.fullmatch(share_links.new_code()) for _ in range(200))
    assert not share_links.CODE.fullmatch("k3f0qa") and not share_links.CODE.fullmatch("k3f9qa1")


async def test_every_platform_is_a_campaign_word_on_both_sides():
    """A founder link's utm_source must count as its platform on the Overview,
    so every platform is on the campaign list, and the web's copy of the list
    (lib/attribution.CAMPAIGNS) is the API's."""
    assert set(share_links.PLATFORMS) <= usage.CAMPAIGNS
    assert set(share_links.PLATFORMS.values()) <= share_links.MEDIA
    block = re.search(r"CAMPAIGNS = \[(.*?)\] as const", ATTRIBUTION_TS.read_text(), re.S).group(1)
    assert set(re.findall(r'"([a-z]+)"', block)) == usage.CAMPAIGNS


# ── The admin and the short address ─────────────────────────────────────────

async def _founder(tag: str, monkeypatch) -> tuple[dict, dict, list]:
    founder, reader = uuid.uuid4(), uuid.uuid4()
    monkeypatch.setattr(get_settings(), "prism_admin_emails", f"founder-{tag}@example.test")
    monkeypatch.setattr(get_settings(), "prism_web_url", WEB)
    async with session_scope() as s:
        for uid, who in ((founder, "founder"), (reader, "reader")):
            await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": uid, "e": f"{who}-{tag}@example.test"})
        fb, rb = await auth.create_session(s, founder), await auth.create_session(s, reader)
    return {"Authorization": f"Bearer {fb}"}, {"Authorization": f"Bearer {rb}"}, [founder, reader]


async def _cleanup(tag: str, users: list) -> None:
    async with session_scope() as s:
        codes = (await s.execute(text("SELECT code FROM share_links WHERE created_by = :a"),
                                 {"a": f"founder-{tag}@example.test"})).scalars().all()
        for code in codes:
            await s.execute(text("DELETE FROM usage_daily WHERE event IN ('link', 'goal') AND (dim = :c OR dim LIKE :p)"),
                            {"c": code, "p": f"{code}:%"})
        await s.execute(text("DELETE FROM share_links WHERE created_by = :a"), {"a": f"founder-{tag}@example.test"})
        await s.execute(text("DELETE FROM admin_audit WHERE actor = :a"), {"a": f"founder-{tag}@example.test"})
        await s.execute(text("DELETE FROM sessions WHERE user_id = ANY(:u)"), {"u": users})
        await s.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": users})


async def test_only_a_founder_makes_a_link_and_a_posted_link_keeps_working(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    h, reader, users = await _founder(tag, monkeypatch)
    made = {"target": f"{WEB}/story/abc123?x=1", "platform": "whatsapp", "campaign": "launch-week", "title": "A headline"}
    try:
        async with _client() as c:
            for method, path, js in (("GET", "/api/v1/admin/links", None), ("POST", "/api/v1/admin/links", made),
                                     ("PATCH", "/api/v1/admin/links/k3f9qa", {"archived": True})):
                assert (await c.request(method, path, json=js)).status_code == 401
                assert (await c.request(method, path, json=js, headers=reader)).status_code == 403
            for bad in ({"target": "https://evil.example/story/x"}, {"target": "/admin"}, {"platform": "myspace"},
                        {"medium": "billboard"}, {"campaign": "Launch Week!"}):
                r = await c.post("/api/v1/admin/links", json={**made, **bad}, headers=h)
                assert r.status_code == 422, bad
            r = await c.post("/api/v1/admin/links", json=made, headers=h)
            assert r.status_code == 201
            link = r.json()
            code = link["code"]
            assert link["path"] == "/story/abc123" and link["kind"] == "story" and link["medium"] == "message"
            assert link["url"] == f"{WEB}/story/abc123?utm_source=whatsapp&utm_medium=message&utm_campaign=launch-week&utm_content={code}"
            assert link["short_url"] == f"https://readprism.news/go/{code}"

            listed = await c.get("/api/v1/admin/links?days=7", headers=h)
            assert listed.headers["cache-control"] == "no-store"
            mine = next(x for x in listed.json()["links"] if x["code"] == code)
            assert mine["visits"] == 0 and len(mine["series"]) == 7 and mine["series"][-1] == 0
            assert "launch-week" in listed.json()["campaigns"]

            assert (await c.patch(f"/api/v1/admin/links/{code}", json={"archived": True}, headers=h)).json()["archived_at"]
            resolved = await c.get(f"/api/v1/links/{code}")
            assert resolved.status_code == 200 and resolved.json() == {"path": "/story/abc123", "tags": {
                "utm_source": "whatsapp", "utm_medium": "message", "utm_campaign": "launch-week", "utm_content": code}}
            assert (await c.patch(f"/api/v1/admin/links/{code}", json={"archived": False}, headers=h)).json()["archived_at"] is None
            assert (await c.get("/api/v1/links/zzzzzz")).status_code == 404
            assert (await c.get("/api/v1/links/not-a-code")).status_code == 404
            assert (await c.patch("/api/v1/admin/links/zzzzzz", json={"archived": True}, headers=h)).status_code == 404
        async with session_scope() as s:
            audited = (await s.execute(text("SELECT action FROM admin_audit WHERE actor = :a AND target = :c ORDER BY id"),
                                       {"a": f"founder-{tag}@example.test", "c": code})).scalars().all()
        assert audited == ["link.create", "link.archive", "link.restore"]
    finally:
        await _cleanup(tag, users)


# ── Counting ────────────────────────────────────────────────────────────────

async def test_the_beacon_counts_a_code_only_when_it_is_a_link(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    h, _, users = await _founder(tag, monkeypatch)
    try:
        async with _client() as c:
            code = (await c.post("/api/v1/admin/links", json={"target": "/", "platform": "x"}, headers=h)).json()["code"]
            share_links.forget()
            before = {k: await _count(e, d) for k, (e, d) in {
                "link": ("link", code), "read2": ("goal", f"{code}:read2"), "account": ("goal", f"{code}:account")}.items()}
            strays = (("link", "zzzzzz"), ("goal", "zzzzzz:read2"), ("goal", f"{code}:bought-a-car"))
            strays_before = [await _count(e, d) for e, d in strays]
            beacon = [("link", code), ("goal", f"{code}:read2"), ("goal", f"{code}:account"),  # account: never from a browser
                      ("link", "zzzzzz"), ("goal", "zzzzzz:read2"), ("goal", f"{code}:bought-a-car"), ("link", "DROP TABLE")]
            for e, d in beacon:
                assert (await c.post("/api/v1/beacon", json={"e": e, "d": d}, headers=_reader())).status_code == 204
            bot = {**_reader(), "user-agent": "Twitterbot/1.0"}
            assert (await c.post("/api/v1/beacon", json={"e": "link", "d": code}, headers=bot)).status_code == 204
        assert await _count("link", code) == before["link"] + 1
        assert await _count("goal", f"{code}:read2") == before["read2"] + 1
        assert await _count("goal", f"{code}:account") == before["account"]
        assert [await _count(e, d) for e, d in strays] == strays_before, "a code that is not a link counts nothing"
    finally:
        await _cleanup(tag, users)


class _Sender:
    def __init__(self):
        self.sent = []

    async def send(self, *, to, subject, body, html=None, reply_to=None, headers=None):
        self.sent.append(SimpleNamespace(to=to, subject=subject, body=body))


async def test_an_account_made_by_a_linked_sign_in_counts_once_and_stores_no_code(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    h, _, users = await _founder(tag, monkeypatch)
    sender = _Sender()
    monkeypatch.setattr(auth_routes, "get_email_sender", lambda: sender)
    email = f"linked-{tag}@example.test"
    try:
        async with _client() as c:
            code = (await c.post("/api/v1/admin/links", json={"target": "/plus", "platform": "linkedin"}, headers=h)).json()["code"]
            before = await _count("goal", f"{code}:account")
            assert (await c.post("/api/v1/auth/request", json={"email": email, "link": code})).status_code == 200
            assert f"&l={code}" in sender.sent[-1].body, "the email link carries the code to the tab it opens"
            assert (await c.post("/api/v1/auth/request", json={"email": f"x{email}", "link": "../../x"})).status_code == 200
            assert "&l=" not in sender.sent[-1].body
            async with session_scope() as s:
                await s.execute(text("DELETE FROM auth_tokens WHERE email = :e"), {"e": email})
                raw = await auth.request_magic_link(s, email)
            assert (await c.post("/api/v1/auth/verify", json={"token": raw, "link": code})).status_code == 200
            async with session_scope() as s:
                await s.execute(text("DELETE FROM auth_tokens WHERE email = :e"), {"e": email})
                again = await auth.request_magic_link(s, email)
            assert (await c.post("/api/v1/auth/verify", json={"token": again, "link": code})).status_code == 200
        assert await _count("goal", f"{code}:account") == before + 1, "a second sign-in is not a new account"
        async with session_scope() as s:
            row = (await s.execute(text("SELECT to_jsonb(u) FROM users u WHERE email = :e"), {"e": email})).scalar_one()
        assert code not in str(row), "the code is counted, never kept on the account"
    finally:
        async with session_scope() as s:
            for e in (email, f"x{email}"):
                await s.execute(text("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email = :e)"), {"e": e})
                await s.execute(text("DELETE FROM users WHERE email = :e"), {"e": e})
                await s.execute(text("DELETE FROM auth_tokens WHERE email = :e"), {"e": e})
        await _cleanup(tag, users)


async def test_the_overview_adds_link_visits_up_by_platform_and_campaign(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    h, _, users = await _founder(tag, monkeypatch)
    try:
        async with _client() as c:
            made = [(await c.post("/api/v1/admin/links", json={"target": "/", "platform": p, "campaign": camp}, headers=h)).json()["code"]
                    for p, camp in (("x", f"t-{tag}"), ("x", f"t-{tag}"), ("whatsapp", ""), ("x", f"t-{tag}"))]
        w = metrics.window(7)
        last_week = w["prev_end"]
        async with session_scope() as s:
            for code, n in zip(made[:3], (3, 2, 4), strict=True):
                await usage.bump(s, "link", code, n=n)
            await usage.bump(s, "goal", f"{made[0]}:account")
            # Last period only: a code with nothing now must still count in "before".
            await usage.bump(s, "link", made[1], day=last_week, n=6)
            await usage.bump(s, "goal", f"{made[1]}:read2", day=last_week, n=20)
            await usage.bump(s, "link", made[3], day=last_week, n=7)  # no visits this period at all
        async with session_scope() as s:
            before = await metrics.links(s, w, last_week - timedelta(days=30))
        async with session_scope() as s:
            for code in (made[1], made[3]):
                await s.execute(text("DELETE FROM usage_daily WHERE day = :d AND dim LIKE :p"), {"d": last_week, "p": f"{code}%"})
            after = await metrics.links(s, w, last_week - timedelta(days=30))
        rows = {r["key"]: r for r in before["rows"]}
        split = {b["key"]: {r["label"]: r for r in b["rows"]} for b in before["breakdowns"]}
        assert rows["link_visits"]["current"] >= 9 and rows["link_account"]["current"] >= 1
        assert split["link_campaigns"][f"t-{tag}"]["current"] == 5
        assert split["link_platforms"]["whatsapp"]["current"] >= 4 and split["link_platforms"]["x"]["current"] >= 5
        # The period before, counted from every code it held (review 2026-09-29).
        gone = {r["key"]: r for r in after["rows"]}
        assert rows["link_read2"]["previous"] - gone["link_read2"]["previous"] == 20
        assert split["link_campaigns"][f"t-{tag}"]["previous"] == 6 + 7
    finally:
        await _cleanup(tag, users)


async def test_a_short_link_lands_where_the_page_now_lives():
    """A merged record, a folded story and a person page named after a state all
    redirect on the web and drop the tags there, so /go resolves them first."""
    if not await _db_reachable():
        pytest.skip("no database")
    import json

    survivor, absorbed = uuid.uuid4(), uuid.uuid4()
    live, folded = uuid.uuid4(), uuid.uuid4()
    tag = uuid.uuid4().hex[:8]
    async with session_scope() as s:
        for e in (survivor, absorbed):
            await s.execute(text("INSERT INTO events (id, title, summary, last_updated_at) VALUES (:i, 't', 's', now())"), {"i": e})
        await s.execute(text("UPDATE events SET merged_into = :s WHERE id = :a"), {"s": survivor, "a": absorbed})
        for sid, slug in ((live, f"live-{tag}"), (folded, f"folded-{tag}")):
            await s.execute(text('INSERT INTO stories (id, slug, label, "cast", member_event_ids) VALUES (:i, :s, \'x\', \'[]\'::jsonb, CAST(:m AS jsonb))'),
                            {"i": sid, "s": slug, "m": json.dumps([])})
        await s.execute(text("UPDATE stories SET merged_into = :l WHERE id = :f"), {"l": live, "f": folded})
    try:
        async with session_scope() as s:
            assert await share_links.landing(s, f"/story/{absorbed}") == f"/story/{survivor}"
            assert await share_links.landing(s, f"/story/{absorbed}/quote/q1") == f"/story/{survivor}/quote/q1"
            assert await share_links.landing(s, f"/story/{survivor}") == f"/story/{survivor}"
            assert await share_links.landing(s, "/story/not-a-uuid") == "/story/not-a-uuid"
            assert await share_links.landing(s, f"/trending/folded-{tag}") == f"/trending/live-{tag}"
            assert await share_links.landing(s, "/entity/karnataka") == "/state/karnataka"
            assert await share_links.landing(s, "/entity/nirmala-sitharaman") == "/entity/nirmala-sitharaman"
            assert await share_links.landing(s, "/") == "/"
    finally:
        async with session_scope() as s:
            await s.execute(text("UPDATE stories SET merged_into = NULL WHERE id = :f"), {"f": folded})
            await s.execute(text("DELETE FROM stories WHERE id = ANY(:i)"), {"i": [live, folded]})
            await s.execute(text("UPDATE events SET merged_into = NULL WHERE id = :a"), {"a": absorbed})
            await s.execute(text("DELETE FROM events WHERE id = ANY(:i)"), {"i": [survivor, absorbed]})
