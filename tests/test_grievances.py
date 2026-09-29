"""The grievance mechanism (IT Rules Part III; docs/COMPLIANCE-INDIA.md N1–N3).

Pinned: what a complaint may say and where it may point; a complaint is saved
even when no email goes out, and is marked acknowledged only when the
acknowledgement did; the acknowledgement carries the complaint as recorded, the
officer and both clocks; a script is refused by the honeypot and the per-address
limit, and no address is stored; the public report prints every month since
September 2026, zeros included; only a founder reads the queue or decides, once,
on the record, and the complainant is told.
"""

import re
import uuid
from datetime import date
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from api.routes import grievances as gr
from common import auth, stream
from common.config import get_settings
from common.db import session_scope

on_session_loop = pytest.mark.asyncio(loop_scope="session")
WEB = Path(__file__).resolve().parents[1] / "web" / "src" / "lib"


@pytest.fixture(autouse=True)
def _fresh_redis(monkeypatch):
    monkeypatch.setattr(stream, "_redis", None)  # bound to another test module's loop otherwise


class Outbox:
    """Records every send; `fail` names the recipients whose send raises."""

    def __init__(self, fail: set[str] | None = None):
        self.sent: list[dict] = []
        self.fail = fail or set()

    async def send(self, *, to, subject, body, html=None, reply_to=None):
        if to in self.fail:
            raise RuntimeError("provider down")
        self.sent.append({"to": to, "subject": subject, "body": body, "reply_to": reply_to})


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def _address() -> str:
    n = uuid.uuid4().int
    return f"10.{n % 256}.{(n >> 8) % 256}.{(n >> 16) % 256}"


def _complaint(email: str, **over) -> dict:
    return {"email": email, "category": "A quote is not in the article", "body": "The quote is not in the linked article.",
            "subject_url": "https://www.readprism.news/story/abc", **over}


async def _cleanup(tag: str) -> None:
    async with session_scope() as s:
        await s.execute(text("DELETE FROM grievances WHERE email ILIKE :e"), {"e": f"%{tag}%"})


# ── Validation (no database) ────────────────────────────────────────────────

def _valid(**over) -> gr.GrievanceIn:
    return gr.GrievanceIn(**{"email": "a@example.test", "category": "Something else", "body": "0123456789", **over})


def test_the_form_takes_what_a_complaint_needs_and_refuses_the_rest():
    assert _valid(name="  Asha  ").name == "Asha"
    for bad in (
        {"email": ""},
        {"email": "not-an-address"},
        {"email": "a@example.test\nBcc: b@example.test"},  # a header, smuggled
        {"body": "too short"},
        {"body": "x" * 5001},
        {"name": "x" * 121},
        {"category": "Other"},
    ):
        with pytest.raises(ValidationError):
            _valid(**bad)
    assert len(gr.KINDS) == 7


def test_a_page_is_stored_as_its_path_and_only_ours_is_taken():
    assert _valid(subject_url="/story/abc").subject_url == "/story/abc"
    assert _valid(subject_url="https://www.readprism.news/story/abc?x=1#q").subject_url == "/story/abc"
    assert _valid(subject_url="https://www.readprism.news").subject_url == "/"
    assert _valid(subject_url="  ").subject_url == ""
    for elsewhere in ("https://evil.example/story/abc", "http://www.readprism.news/story/abc", "https://readprism.news/story/abc",
                      "https://www.readprism.news.evil.example/x", "//evil.example/x", "story/abc", "/story/a b", "/\\evil"):
        with pytest.raises(ValidationError):
            _valid(subject_url=elsewhere)


def test_the_report_prints_every_month_since_september_2026_with_zeros():
    rows = gr.monthly({"2026-10": {"received": 2, "resolved": 1, "rejected": 0, "open": 1, "median_days": 3.5}}, date(2026, 12, 2))
    assert [r["month"] for r in rows] == ["2026-12", "2026-11", "2026-10", "2026-09"]
    assert rows[0] == {"month": "2026-12", "received": 0, "resolved": 0, "rejected": 0, "open": 0, "median_days": None}
    assert rows[2]["received"] == 2
    assert [r["month"] for r in gr.monthly({}, date(2027, 1, 1))][:2] == ["2027-01", "2026-12"], "a year turns"


def test_the_web_prints_the_same_officer_and_the_same_kinds():
    legal = (WEB / "legal.ts").read_text()
    assert f'name: "{gr.OFFICER_NAME}"' in legal
    assert f'designation: "{gr.OFFICER_TITLE}"' in legal
    assert f'email: "{gr.GRIEVANCE_EMAIL}"' in legal
    kinds = re.search(r"GRIEVANCE_KINDS = \[(.*?)\] as const", (WEB / "grievance.ts").read_text(), re.S).group(1)
    assert tuple(re.findall(r'"([^"]+)"', kinds)) == gr.KINDS


def test_the_acknowledgement_is_a_copy_with_the_officer_and_both_clocks():
    from datetime import UTC, datetime

    g = {"ref": "PG-20260929-7K3Q", "created_at": datetime(2026, 9, 29, 8, 30, tzinfo=UTC), "name": None,
         "email": "a@example.test", "category": "A fact is wrong", "subject_url": "/story/abc", "body": "The date is wrong."}
    subject, body, html = gr.acknowledgement(g)
    assert subject == "We received your complaint · PG-20260929-7K3Q"
    for part in ("The date is wrong.", "A fact is wrong", "https://www.readprism.news/story/abc", "29 September 2026, 14:00 IST",
                 gr.OFFICER_NAME, gr.GRIEVANCE_EMAIL, "within 15 days", "14 October 2026"):
        assert part in body, part
    assert gr.OFFICER_NAME in html
    assert re.fullmatch(r"PG-\d{8}-[2-9A-HJ-NP-Z]{4}", gr.new_ref(datetime.now(UTC)))


# ── Filing (database + Redis) ──────────────────────────────────────────────

@on_session_loop
async def test_a_complaint_is_saved_acknowledged_and_passed_to_the_officer(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    email = f"reader-{tag}@example.test"
    box = Outbox()
    monkeypatch.setattr(gr, "get_email_sender", lambda: box)
    try:
        async with _client() as c:
            r = await c.post("/api/v1/grievances", json=_complaint(email, name="Asha"), headers={"x-forwarded-for": _address()})
        assert r.status_code == 201, r.text
        ref = r.json()["ref"]
        assert r.json()["acknowledged"] is True
        async with session_scope() as s:
            row = (await s.execute(text("SELECT * FROM grievances WHERE ref = :r"), {"r": ref})).mappings().one()
        assert (row["subject_url"], row["status"], row["name"]) == ("/story/abc", "open", "Asha")
        assert row["acknowledged_at"] is not None
        ack, note = box.sent
        assert (ack["to"], ack["subject"], ack["reply_to"]) == (email, f"We received your complaint · {ref}", gr.GRIEVANCE_EMAIL)
        assert "The quote is not in the linked article." in ack["body"] and gr.OFFICER_NAME in ack["body"]
        assert (note["to"], note["reply_to"]) == (gr.GRIEVANCE_EMAIL, email), "the officer replies straight to the complainant"
    finally:
        await _cleanup(tag)


@on_session_loop
async def test_a_failed_acknowledgement_keeps_the_complaint_and_says_it_was_not_sent(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    email = f"reader-{tag}@example.test"
    box = Outbox(fail={email})
    monkeypatch.setattr(gr, "get_email_sender", lambda: box)
    try:
        async with _client() as c:
            r = await c.post("/api/v1/grievances", json=_complaint(email), headers={"x-forwarded-for": _address()})
        assert r.status_code == 201 and r.json()["acknowledged"] is False
        async with session_scope() as s:
            acked = (await s.execute(text("SELECT acknowledged_at FROM grievances WHERE ref = :r"), {"r": r.json()["ref"]})).scalar_one()
        assert acked is None, "never marked acknowledged when nothing went out"
        assert [m["to"] for m in box.sent] == [gr.GRIEVANCE_EMAIL]
        assert "could NOT be emailed" in box.sent[0]["body"]
    finally:
        await _cleanup(tag)


@on_session_loop
async def test_a_script_is_refused_and_no_address_is_kept(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    monkeypatch.setattr(gr, "get_email_sender", lambda: Outbox())
    monkeypatch.setattr(gr, "PER_ADDRESS_PER_DAY", 2)
    address = _address()
    h = {"x-forwarded-for": address}
    try:
        async with _client() as c:
            trap = await c.post("/api/v1/grievances", json=_complaint(f"bot-{tag}@example.test", website="http://spam.example"), headers=h)
            assert trap.status_code == 400 and gr.GRIEVANCE_EMAIL in trap.json()["detail"]
            codes = [(await c.post("/api/v1/grievances", json=_complaint(f"r{i}-{tag}@example.test"), headers=h)).status_code for i in range(3)]
            assert codes == [201, 201, 429]
            other = await c.post("/api/v1/grievances", json=_complaint(f"o-{tag}@example.test"), headers={"x-forwarded-for": _address()})
            assert other.status_code == 201, "the limit is per address"
        async with session_scope() as s:
            n = (await s.execute(text("SELECT count(*) FROM grievances WHERE email LIKE :e"), {"e": f"%{tag}%"})).scalar()
            cols = (await s.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'grievances'"))).scalars().all()
        assert n == 3, "the honeypot and the refused one are not saved"
        assert not {"ip", "ip_hash", "user_agent"} & set(cols)
        keys = [k async for k in stream.get_redis().scan_iter("prism:grievance:ip:*")]
        assert keys and not any(address in k for k in keys), "only a salted hash of the address is counted"
    finally:
        await _cleanup(tag)


@on_session_loop
async def test_one_address_is_mailed_a_few_acknowledgements_a_day_and_the_rest_are_saved(monkeypatch):
    # Review 2026-09-29: the acknowledgement copies the complaint's words to the
    # address typed, unconfirmed — without a per-recipient cap the form mails any
    # text to anyone. Past the cap the complaint is saved, unacknowledged.
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    victim = f"victim-{tag}@example.test"
    box = Outbox()
    monkeypatch.setattr(gr, "get_email_sender", lambda: box)
    monkeypatch.setattr(gr, "ACKS_PER_RECIPIENT_PER_DAY", 2)
    try:
        async with _client() as c:
            acks = [(await c.post("/api/v1/grievances", json=_complaint(victim.upper() if i else victim),
                                  headers={"x-forwarded-for": _address()})).json()["acknowledged"] for i in range(3)]
        assert acks == [True, True, False], "counted per recipient, whatever the case or the connection"
        assert [m["to"] for m in box.sent].count(victim) + [m["to"] for m in box.sent].count(victim.upper()) == 2
        async with session_scope() as s:
            n = (await s.execute(text("SELECT count(*) FROM grievances WHERE lower(email) = :e"), {"e": victim})).scalar()
        assert n == 3, "every complaint is still saved"
    finally:
        await _cleanup(tag)


# ── The report and the queue ───────────────────────────────────────────────

@on_session_loop
async def test_the_public_report_counts_decisions_and_the_median(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    async with session_scope() as s:
        before = (await s.execute(text("SELECT count(*) FROM grievances WHERE status = 'resolved' "
                                        "AND to_char(created_at AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM') = to_char(now() AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM')"))).scalar()
        await s.execute(text("INSERT INTO grievances (ref, email, category, body, status, resolved_at, outcome) "
                             "VALUES (:r, :e, 'Something else', 'A complaint body.', 'resolved', now(), 'Fixed.')"),
                        {"r": f"PG-T-{tag}", "e": f"x-{tag}@example.test"})
    try:
        async with _client() as c:
            body = (await c.get("/api/v1/grievances/report")).json()
        months = body["months"]
        assert months[-1]["month"] == "2026-09" and months[0]["month"] == gr.usage.today().strftime("%Y-%m")
        assert len(months) == len(gr.months(gr.REPORT_FROM, gr.usage.today()))
        assert months[0]["resolved"] == before + 1 and months[0]["median_days"] is not None
        assert set(months[0]) == {"month", "received", "resolved", "rejected", "open", "median_days"}, "counts only, never a complaint"
    finally:
        await _cleanup(tag)


@on_session_loop
async def test_only_a_founder_reads_the_queue_and_decides_once_on_the_record(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    founder, reader = uuid.uuid4(), uuid.uuid4()
    box = Outbox()
    monkeypatch.setattr(gr, "get_email_sender", lambda: box)
    monkeypatch.setattr(get_settings(), "prism_admin_emails", f"founder-{tag}@example.test")
    ref = f"PG-T-{tag}"
    async with session_scope() as s:
        for uid, who in ((founder, "founder"), (reader, "reader")):
            await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": uid, "e": f"{who}-{tag}@example.test"})
        await s.execute(text("INSERT INTO grievances (ref, email, category, body) VALUES (:r, :e, 'Payments or my plan', 'Charged twice this month.')"),
                        {"r": ref, "e": f"complainant-{tag}@example.test"})
        fb, rb = await auth.create_session(s, founder), await auth.create_session(s, reader)
    decision = {"status": "resolved", "outcome": "The duplicate charge was refunded."}
    try:
        async with _client() as c:
            for method, path, js in (("GET", "/api/v1/admin/grievances", None), ("PATCH", f"/api/v1/admin/grievances/{ref}", decision)):
                assert (await c.request(method, path, json=js)).status_code == 401
                assert (await c.request(method, path, json=js, headers={"Authorization": f"Bearer {rb}"})).status_code == 403
            h = {"Authorization": f"Bearer {fb}"}
            q = await c.get("/api/v1/admin/grievances?status=open", headers=h)
            assert q.status_code == 200 and q.headers["cache-control"] == "no-store"
            mine = next(g for g in q.json()["grievances"] if g["ref"] == ref)
            assert mine["body"] == "Charged twice this month." and mine["decide_by"]
            assert (await c.patch(f"/api/v1/admin/grievances/{ref}", json={"status": "resolved", "outcome": "ok"}, headers=h)).status_code == 422
            r = await c.patch(f"/api/v1/admin/grievances/{ref}", json=decision, headers=h)
            assert r.status_code == 200 and r.json()["emailed"] is True
            assert (await c.patch(f"/api/v1/admin/grievances/{ref}", json={**decision, "status": "rejected"}, headers=h)).status_code == 409
            assert (await c.patch("/api/v1/admin/grievances/PG-NONE", json=decision, headers=h)).status_code == 404
            assert ref not in [g["ref"] for g in (await c.get("/api/v1/admin/grievances?status=open", headers=h)).json()["grievances"]]
        [told] = box.sent
        assert told["to"] == f"complainant-{tag}@example.test" and ref in told["subject"]
        assert "The duplicate charge was refunded." in told["body"]
        async with session_scope() as s:
            row = (await s.execute(text("SELECT status, outcome, resolved_at FROM grievances WHERE ref = :r"), {"r": ref})).one()
            audited = (await s.execute(text("SELECT action, detail FROM admin_audit WHERE actor = :a AND target = :r"),
                                       {"a": f"founder-{tag}@example.test", "r": ref})).all()
        assert row[0] == "resolved" and row[2] is not None
        assert audited == [("grievance.decide", {"status": "resolved"})]
    finally:
        await _cleanup(tag)
        async with session_scope() as s:
            await s.execute(text("DELETE FROM admin_audit WHERE actor = :a"), {"a": f"founder-{tag}@example.test"})
            await s.execute(text("DELETE FROM sessions WHERE user_id = ANY(:u)"), {"u": [founder, reader]})
            await s.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": [founder, reader]})


@on_session_loop
async def test_the_queue_lists_open_complaints_first_oldest_first(monkeypatch):
    # Review 2026-09-29: newest-first with a 500 cap let the oldest open
    # complaints — the ones nearest their 15-day deadline — fall off the page.
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    founder = uuid.uuid4()
    monkeypatch.setattr(get_settings(), "prism_admin_emails", f"founder-{tag}@example.test")
    rows = [(f"PG-T-{tag}-OLD", "open", 10), (f"PG-T-{tag}-NEW", "open", 1), (f"PG-T-{tag}-DONE", "resolved", 0)]
    async with session_scope() as s:
        await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": founder, "e": f"founder-{tag}@example.test"})
        for ref, status, days in rows:
            await s.execute(text("INSERT INTO grievances (ref, email, category, body, status, created_at) "
                                 "VALUES (:r, :e, 'Something else', 'A test complaint body.', :s, now() - make_interval(days => :d))"),
                            {"r": ref, "e": f"q-{tag}@example.test", "s": status, "d": days})
        token = await auth.create_session(s, founder)
    try:
        async with _client() as c:
            listed = [g["ref"] for g in (await c.get("/api/v1/admin/grievances", headers={"Authorization": f"Bearer {token}"})).json()["grievances"]]
        mine = [r for r in listed if tag in r]
        assert mine == [f"PG-T-{tag}-OLD", f"PG-T-{tag}-NEW", f"PG-T-{tag}-DONE"]
        assert listed.index(mine[0]) < listed.index(mine[1]) < listed.index(mine[2])
    finally:
        await _cleanup(tag)
        async with session_scope() as s:
            await s.execute(text("DELETE FROM sessions WHERE user_id = :i"), {"i": founder})
            await s.execute(text("DELETE FROM users WHERE id = :i"), {"i": founder})
