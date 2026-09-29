"""The week's record by email: opt-in only, counted, once a week, one click out.

Pinned: the toggle starts off and keeps a consent record (on, off, on again);
the Sunday job does nothing with the flag off, sends one copy per account per
ISO week (a rerun sends nothing; over the cap the rest go next run), says
nothing for a week with fewer than three multi-outlet records, and counts its
content from the database; the unsubscribe token refuses anything it did not
sign and the link withdraws consent without a sign-in; every copy carries
List-Unsubscribe and its one-click twin, and Resend is handed them.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import common.email as email_mod
import common.weekly_digest as wd
from common import auth, outlets
from common.config import get_settings
from common.db import session_scope
from tests.test_projection_summary import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")

# Sundays far from any real corpus, so the local database's own events never count.
SUNDAY = datetime(2031, 1, 12, 3, 0, tzinfo=UTC)  # 08:30 IST, ISO week 2031-W02
THIN_SUNDAY = datetime(2031, 3, 16, 3, 0, tzinfo=UTC)


class _Sender:
    def __init__(self):
        self.sent = []

    async def send(self, *, to, subject, body, html=None, reply_to=None, headers=None):
        self.sent.append(SimpleNamespace(to=to, subject=subject, body=body, html=html, headers=headers))


def _client():
    from api.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="https://t")


def _ours() -> dict:
    return {"Origin": get_settings().cors_origin_list[0]}


async def _user(email: str, *, on: bool = False) -> str:
    async with session_scope() as s:
        uid = (await s.execute(text("INSERT INTO users (id, email) VALUES (gen_random_uuid(), :e) RETURNING id"), {"e": email})).scalar_one()
        if on:
            await wd.set_digest(s, uid, True)
    return str(uid)


async def _drop_users(emails: list[str]):
    async with session_scope() as s:
        for t in ("usage_quota", "sessions"):
            await s.execute(text(f"DELETE FROM {t} WHERE user_id IN (SELECT id FROM users WHERE email = ANY(:e))"), {"e": emails})
        await s.execute(text("DELETE FROM users WHERE email = ANY(:e)"), {"e": emails})
        await s.execute(text("DELETE FROM auth_tokens WHERE email = ANY(:e)"), {"e": emails})


async def _row(uid: str):
    async with session_scope() as s:
        return (await s.execute(text(
            "SELECT digest_opted_in_at, digest_unsubscribed_at, digest_last_week FROM users WHERE id = :u"), {"u": uid})).mappings().one()


@pytest.fixture
def enabled(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "prism_digest_enabled", True)
    monkeypatch.setattr(wd, "SEND_INTERVAL_S", 0)
    sender = _Sender()
    monkeypatch.setattr(wd, "get_email_sender", lambda: sender)

    async def _monitored(_db):
        return outlets.Monitored(feeds=(), outlets=27, checked_at=None)

    monkeypatch.setattr(outlets, "monitored", _monitored)
    return sender


class _Corpus:
    """Three outlets in three languages, and the records a week is counted from."""

    def __init__(self):
        tag = uuid.uuid4().hex[:8]
        self.slugs = {k: f"wd-{tag}-{k}" for k in ("a", "a2", "b", "c")}
        self.events: list[str] = []

    async def __aenter__(self):
        pubs = {"a": ("pa", "en"), "a2": ("pa", "en"), "b": ("pb", "hi"), "c": ("pc", "kn")}
        async with session_scope() as s:
            for k, slug in self.slugs.items():
                await s.execute(text("INSERT INTO sources (id, slug, name, source_type, publisher, country, language) "
                                     "VALUES (gen_random_uuid(), :s, :n, 'rss', :p, 'IN', :l)"),
                                {"s": slug, "n": slug, "p": pubs[k][0], "l": pubs[k][1]})
        outlets.reset_cache()
        return self

    async def event(self, title: str, keys: list[str], seen: datetime, *, merged: bool = False) -> str:
        eid = str(uuid.uuid4())
        async with session_scope() as s:
            await s.execute(text(
                "INSERT INTO events (id, title, first_seen_at, last_updated_at, projection, merged_into) "
                "VALUES (:i, :t, :f, :f, CAST(:p AS jsonb), CAST(:m AS uuid))"),
                {"i": eid, "t": title, "f": seen, "m": eid if merged else None,
                 "p": json.dumps({"source_slugs": [self.slugs[k] for k in keys]})})
        self.events.append(eid)
        return eid

    async def correction(self, at: datetime):
        async with session_scope() as s:
            await s.execute(text("INSERT INTO event_corrections (event_id, reason, note, actor, created_at) "
                                 "VALUES (:i, 'prism_error', 'The headline named the wrong district; fixed.', 't', :at)"),
                            {"i": self.events[0], "at": at})

    async def __aexit__(self, *exc):
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_corrections WHERE event_id = ANY(CAST(:e AS uuid[]))"), {"e": self.events})
            await s.execute(text("DELETE FROM event_revisions WHERE event_id = ANY(CAST(:e AS uuid[]))"), {"e": self.events})
            await s.execute(text("UPDATE events SET merged_into = NULL WHERE id = ANY(CAST(:e AS uuid[]))"), {"e": self.events})
            await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"), {"e": self.events})
            await s.execute(text("DELETE FROM sources WHERE slug = ANY(:s)"), {"s": list(self.slugs.values())})
        outlets.reset_cache()


def _days(sunday: datetime):
    """Sunday's window is the seven IST days before it: day 0 is the Sunday before."""
    start, _ = wd.week_window(sunday)
    day = lambda n, h=6: start + timedelta(days=n, hours=h)  # noqa: E731
    return start, day


# ── Consent ──────────────────────────────────────────────────────────────────


async def test_the_toggle_starts_off_and_keeps_a_consent_record():
    if not await _db_reachable():
        pytest.skip("no database")
    email = f"wd-{uuid.uuid4().hex[:8]}@example.com"
    try:
        async with _client() as c:
            assert (await c.get("/api/v1/me/digest")).status_code == 401
            async with session_scope() as s:
                raw = await auth.request_magic_link(s, email)
            assert (await c.post("/api/v1/auth/verify", json={"token": raw})).status_code == 200
            uid = (await c.get("/api/v1/auth/me")).json()["user_id"]

            assert (await c.get("/api/v1/me/digest")).json() == {"on": False}, "never pre-ticked"
            assert (await c.put("/api/v1/me/digest", json={"on": "yes"}, headers=_ours())).status_code == 422
            assert (await _row(uid))["digest_opted_in_at"] is None, "a coerced 'yes' is not consent"

            r = await c.put("/api/v1/me/digest", json={"on": True}, headers=_ours())
            assert r.status_code == 200 and r.json() == {"on": True}
            first = await _row(uid)
            assert first["digest_opted_in_at"] is not None and first["digest_unsubscribed_at"] is None

            await c.put("/api/v1/me/digest", json={"on": True}, headers=_ours())
            assert (await _row(uid))["digest_opted_in_at"] == first["digest_opted_in_at"], "consent is stamped once"

            r = await c.put("/api/v1/me/digest", json={"on": False}, headers=_ours())
            assert r.json() == {"on": False}
            off = await _row(uid)
            assert off["digest_unsubscribed_at"] is not None
            assert off["digest_opted_in_at"] == first["digest_opted_in_at"], "withdrawal keeps when consent was given"

            assert (await c.put("/api/v1/me/digest", json={"on": True}, headers=_ours())).json() == {"on": True}
            again = await _row(uid)
            assert again["digest_unsubscribed_at"] is None and again["digest_opted_in_at"] >= off["digest_unsubscribed_at"]
    finally:
        await _drop_users([email])


# ── The unsubscribe link ─────────────────────────────────────────────────────


async def test_the_token_refuses_anything_it_did_not_sign():
    uid = uuid.uuid4()
    token = wd.unsubscribe_token(uid)
    assert wd.verify_unsubscribe_token(token) == uid
    who, _, sig = token.partition(".")
    other = uuid.uuid4()
    assert wd.verify_unsubscribe_token(f"{other}.{sig}") is None, "a signature is for one account"
    assert wd.verify_unsubscribe_token(f"{who}.{sig[:-1]}{'A' if sig[-1] != 'A' else 'B'}") is None
    assert wd.verify_unsubscribe_token(who) is None
    assert wd.verify_unsubscribe_token(f"{who}.") is None
    assert wd.verify_unsubscribe_token("not-a-uuid.abc") is None
    assert wd.verify_unsubscribe_token("") is None
    # Review 2026-09-29: a non-ASCII signature raised in compare_digest (a 500).
    assert wd.verify_unsubscribe_token(f"{who}.é") is None


def test_the_digest_refuses_to_send_links_nobody_can_open(monkeypatch):
    # Every copy carries an unsubscribe link on PRISM_API_URL; a public site
    # mailing localhost links would leave readers no way to withdraw.
    s = get_settings()
    monkeypatch.setattr(s, "prism_web_url", "https://www.readprism.news")
    monkeypatch.setattr(s, "prism_api_url", "http://localhost:8000")
    with pytest.raises(RuntimeError, match="PRISM_API_URL"):
        wd._assert_links_reachable(s)
    monkeypatch.setattr(s, "prism_api_url", "https://api.readprism.news")
    wd._assert_links_reachable(s)
    monkeypatch.setattr(s, "prism_web_url", "http://localhost:3000")
    monkeypatch.setattr(s, "prism_api_url", "http://localhost:8000")
    wd._assert_links_reachable(s)  # local development


async def test_the_link_asks_its_button_withdraws_consent_and_a_forged_one_changes_nothing():
    if not await _db_reachable():
        pytest.skip("no database")
    emails = [f"wd-u-{uuid.uuid4().hex[:8]}@example.com" for _ in range(2)]
    try:
        a, b = [await _user(e, on=True) for e in emails]
        token = wd.unsubscribe_token(a)
        async with _client() as c:
            forged = await c.get("/api/v1/digest/unsubscribe", params={"t": f"{b}.{token.partition('.')[2]}"})
            assert forged.status_code == 400 and "not valid" in forged.text
            assert (await _row(b))["digest_unsubscribed_at"] is None
            # Opening the link (as a mail scanner does) only asks; nothing changes.
            asked = await c.get("/api/v1/digest/unsubscribe", params={"t": token})
            assert asked.status_code == 200 and "Stop the week" in asked.text and 'method="post"' in asked.text
            assert (await _row(a))["digest_unsubscribed_at"] is None
            # Its button POSTs the same token.
            ok = await c.post("/api/v1/digest/unsubscribe", params={"t": token})
            assert ok.status_code == 200 and "You are unsubscribed" in ok.text
            assert (await _row(a))["digest_unsubscribed_at"] is not None
            # RFC 8058: the mail client's one-click POST, form-encoded, no cookie.
            one = await c.post("/api/v1/digest/unsubscribe", params={"t": wd.unsubscribe_token(b)},
                               content="List-Unsubscribe=One-Click",
                               headers={"Content-Type": "application/x-www-form-urlencoded"})
            assert one.status_code == 200
            assert (await _row(b))["digest_unsubscribed_at"] is not None
    finally:
        await _drop_users(emails)


# ── The Sunday job ───────────────────────────────────────────────────────────


async def test_flag_off_sends_nothing(monkeypatch):
    sender = _Sender()
    monkeypatch.setattr(wd, "get_email_sender", lambda: sender)
    monkeypatch.setattr(get_settings(), "prism_digest_enabled", False)
    assert (await wd.run_digest(SUNDAY)) == {"sent": 0, "skipped": "disabled"}
    assert sender.sent == []


async def test_the_week_is_counted_from_the_database(enabled):
    if not await _db_reachable():
        pytest.skip("no database")
    async with _Corpus() as c:
        start, day = _days(SUNDAY)
        three = await c.event("Three outlets", ["a", "b", "c"], day(1))
        older_two = await c.event("Two outlets, earlier", ["a", "b"], day(2))
        newer_two = await c.event("Two outlets, later", ["b", "c"], day(5))
        await c.event("One publisher, two feeds", ["a", "a2"], day(3))  # one outlet
        await c.event("One feed", ["c"], day(3))
        await c.event("Before the week", ["a", "b", "c"], start - timedelta(hours=1))
        await c.event("After the week", ["a", "b", "c"], start + timedelta(days=7, minutes=1))
        await c.event("Merged away", ["a", "b", "c"], day(4), merged=True)
        await c.correction(day(2))
        await c.correction(day(6))
        await c.correction(start - timedelta(days=1))
        async with session_scope() as s:
            week = await wd.count_week(s, *wd.week_window(SUNDAY))
        assert [eid for eid, _, _ in week.top] == [three, newer_two, older_two], "outlets first, then recency"
        assert [k for _, _, k in week.top] == [3, 2, 2]
        assert (week.records, week.languages, week.corrections, week.monitored) == (3, 3, 2, 27)

        text_body, html = wd.digest_email(week, to="r@example.com", unsubscribe="https://api.test/u?t=x")
        assert "3 of 27 monitored outlets" in text_body and "2 of 27 monitored outlets" in text_body
        assert f"{get_settings().prism_web_url.rstrip('/')}/story/{three}" in html
        assert "2 corrections this week" in text_body and "/corrections" in html
        assert "in 3 languages" in text_body
        assert "https://api.test/u?t=x" in html and "Unsubscribe in one click" in html


async def test_a_week_with_no_corrections_says_so():
    week = wd.Week(start=SUNDAY - timedelta(days=7), end=SUNDAY, top=(("e", "T", 2),) * 3, records=3,
                   languages=1, corrections=0, monitored=None)
    text_body, _ = wd.digest_email(week, to="r@example.com", unsubscribe="https://u")
    assert "No corrections this week" in text_body
    assert "2 outlets" in text_body and "of None" not in text_body, "no denominator, no 'k of n'"


async def test_fewer_than_three_records_sends_nothing(enabled):
    if not await _db_reachable():
        pytest.skip("no database")
    email = f"wd-thin-{uuid.uuid4().hex[:8]}@example.com"
    try:
        await _user(email, on=True)
        async with _Corpus() as c:
            _, day = _days(THIN_SUNDAY)
            await c.event("First", ["a", "b"], day(1))
            await c.event("Second", ["b", "c"], day(2))
            await c.event("One outlet", ["a", "a2"], day(3))
            result = await wd.run_digest(THIN_SUNDAY)
        assert result["skipped"] == "too_few_records" and result["records"] == 2
        assert enabled.sent == []
    finally:
        await _drop_users([email])


async def test_one_copy_a_week_the_cap_holds_and_every_copy_can_leave_in_one_click(enabled, monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    emails = [f"wd-run-{i}-{uuid.uuid4().hex[:8]}@example.com" for i in range(3)]
    try:
        first, second = await _user(emails[0], on=True), await _user(emails[1], on=True)
        never = await _user(emails[2])  # never turned it on
        async with _Corpus() as c:
            _, day = _days(SUNDAY)
            for i, keys in enumerate((["a", "b", "c"], ["a", "b"], ["b", "c"])):
                await c.event(f"Record {i}", keys, day(i + 1))
            monkeypatch.setattr(get_settings(), "prism_digest_max_per_run", 1)
            one = await wd.run_digest(SUNDAY)
            # Counted over every send, not just ours: the local database is shared.
            assert len(enabled.sent) == 1 and one["capped"] is True, "the cap holds; the rest wait"

            monkeypatch.setattr(get_settings(), "prism_digest_max_per_run", 90)
            await wd.run_digest(SUNDAY)
            await wd.run_digest(SUNDAY)  # a rerun, the same Sunday
        mine = [m for m in enabled.sent if m.to in emails]
        assert sorted(m.to for m in mine) == sorted(emails[:2]), "each once; never the account that did not opt in"
        assert {(await _row(u))["digest_last_week"] for u in (first, second)} == {"2031-W02"}
        # The claim is the guard a second worker meets: a sent week, or no consent, is never claimed.
        assert await wd._claim(first, "2031-W02") is False
        assert await wd._claim(never, "2031-W02") is False
        for m, uid in ((next(m for m in mine if m.to == emails[0]), first), (next(m for m in mine if m.to == emails[1]), second)):
            url = wd.unsubscribe_url(uid)
            assert m.subject == "The week's record"
            assert m.headers == {"List-Unsubscribe": f"<{url}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}
            assert url.replace("&", "&amp;") in m.html and url in m.body
    finally:
        await _drop_users(emails)


async def test_a_failed_send_gives_the_week_back(enabled, monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    email = f"wd-fail-{uuid.uuid4().hex[:8]}@example.com"

    class _Down:
        async def send(self, **_):
            raise RuntimeError("resend send failed (503)")

    try:
        uid = await _user(email, on=True)
        async with _Corpus() as c:
            _, day = _days(SUNDAY)
            for i in range(3):
                await c.event(f"Record {i}", ["a", "b"], day(i + 1))
            monkeypatch.setattr(wd, "get_email_sender", lambda: _Down())
            await wd.run_digest(SUNDAY)
            assert (await _row(uid))["digest_last_week"] is None, "unsent is not sent"
            monkeypatch.setattr(wd, "get_email_sender", lambda: enabled)
            await wd.run_digest(SUNDAY)
        assert [m.to for m in enabled.sent if m.to == email] == [email]
    finally:
        await _drop_users([email])


async def test_resend_is_handed_the_unsubscribe_headers(monkeypatch):
    sent = {}

    class _Client:
        def __init__(self, **_):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def post(self, url, headers, json):
            sent.update(json)
            return SimpleNamespace(status_code=200, text="")

    monkeypatch.setattr(get_settings(), "resend_api_key", "re_test")
    monkeypatch.setattr(email_mod.httpx, "AsyncClient", _Client)
    hdrs = {"List-Unsubscribe": "<https://api.test/u>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}
    await email_mod.ResendEmailSender().send(to="r@example.com", subject="s", body="b", headers=hdrs)
    assert sent["headers"] == hdrs
    sent.clear()
    await email_mod.ResendEmailSender().send(to="r@example.com", subject="s", body="b")
    assert "headers" not in sent, "no header block on the emails that carry none"
