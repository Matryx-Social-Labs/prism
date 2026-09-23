"""Running the labeller workspace from /admin (admin dashboard, phase 2).

Pinned: only a founder can change anything; every change leaves an audit row
naming them; removing someone keeps their answers and takes every kind away,
and they cannot re-apply their way back; a round a constant strategy could
pass is never published; and the command line runs the same operations.
"""

import json
import sys
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common import auth
from common.config import get_settings
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _account(email: str, status: str | None = None, kinds: tuple[str, ...] = ()) -> tuple[uuid.UUID, str]:
    uid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": uid, "e": email})
        if status:
            await s.execute(text("INSERT INTO labellers (user_id, languages_read, status) "
                                 "VALUES (:u, ARRAY['en'], :s)"), {"u": uid, "s": status})
        for kind in kinds:
            await s.execute(text("INSERT INTO labeller_qualifications (user_id, kind, passed_at, best_score, attempts) "
                                 "VALUES (:u, :k, now(), 1.0, 1)"), {"u": uid, "k": kind})
        bearer = await auth.create_session(s, uid)
    return uid, bearer


async def _round(purpose: str, answers: list[bool], explained: bool = True) -> str:
    """A claim round whose items' answers are `answers` (True = yes)."""
    key = f"r{uuid.uuid4().hex[:12]}"
    bid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO label_batches (id, key, name, kind, purpose, open) "
                             "VALUES (:i, :k, 'test round', 'claim_attribution', :p, false)"),
                        {"i": bid, "k": key, "p": purpose})
        for pos, yes in enumerate(answers):
            tid = uuid.uuid4()
            await s.execute(text(
                "INSERT INTO label_tasks (id, batch_id, position, candidates, payload, expected, explanation) "
                "VALUES (:i, :b, :p, '[]'::jsonb, CAST(:pl AS jsonb), CAST(:e AS jsonb), :x)"),
                {"i": tid, "b": bid, "p": pos,
                 "pl": json.dumps({"kind": "claim_attribution", "speaker": "S", "quote_text": f"q{pos}", "language": "en"}),
                 "e": json.dumps({"selected": [str(tid)] if yes else []}),
                 "x": "because the article says so" if explained else None})
    return key


async def _cleanup(uids: list[uuid.UUID], keys: list[str], tag: str) -> None:
    async with session_scope() as s:
        for key in keys:
            await s.execute(text("DELETE FROM label_tasks WHERE batch_id = (SELECT id FROM label_batches WHERE key = :k)"), {"k": key})
            await s.execute(text("DELETE FROM label_batches WHERE key = :k"), {"k": key})
            await s.execute(text("DELETE FROM admin_audit WHERE target = :k"), {"k": key})
        for uid in uids:
            await s.execute(text("DELETE FROM sessions WHERE user_id = :u"), {"u": uid})
            await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})
        await s.execute(text("DELETE FROM admin_audit WHERE target LIKE :t"), {"t": f"%{tag}%"})


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


@pytest.fixture
def founder_list(monkeypatch):
    def set_(value: str) -> None:
        monkeypatch.setattr(get_settings(), "prism_admin_emails", value)
    return set_


async def _status(uid: uuid.UUID) -> str:
    async with session_scope() as s:
        return (await s.execute(text("SELECT status FROM labellers WHERE user_id = :u"), {"u": uid})).scalar()


async def _audit(target: str) -> list[dict]:
    async with session_scope() as s:
        rows = (await s.execute(text("SELECT actor, action, detail FROM admin_audit WHERE target = :t ORDER BY id"),
                                {"t": target})).mappings().all()
    return [dict(r) for r in rows]


async def test_only_a_founder_can_approve_and_the_approval_names_them(founder_list):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    founder, fb = await _account(f"founder-{tag}@example.test")
    applicant, ab = await _account(f"applicant-{tag}@example.test", status="applied")
    founder_list(f"founder-{tag}@example.test")
    body = {"email": f"applicant-{tag}@example.test", "status": "active"}
    try:
        async with _client() as c:
            # The applicant approving themselves is the attack this whole guard exists for.
            r = await c.post("/api/v1/admin/labellers/status", json=body, headers={"Authorization": f"Bearer {ab}"})
            assert r.status_code == 403 and await _status(applicant) == "applied"
            r = await c.post("/api/v1/admin/labellers/status", json=body, headers={"Authorization": f"Bearer {fb}"})
            assert r.status_code == 200 and r.json()["from"] == "applied"
        assert await _status(applicant) == "active"
        async with session_scope() as s:
            by = (await s.execute(text("SELECT approved_by FROM labellers WHERE user_id = :u"), {"u": applicant})).scalar()
        assert by == f"founder-{tag}@example.test"
        assert await _audit(f"applicant-{tag}@example.test") == [
            {"actor": f"founder-{tag}@example.test", "action": "labeller.status", "detail": {"from": "applied", "to": "active"}}]
    finally:
        await _cleanup([founder, applicant], [], tag)


async def test_removing_keeps_answers_takes_every_kind_and_reapplying_does_not_undo_it(founder_list):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    founder, fb = await _account(f"founder-{tag}@example.test")
    who, wb = await _account(f"labeller-{tag}@example.test", status="active", kinds=("claim_attribution",))
    founder_list(f"founder-{tag}@example.test")
    key = await _round("work", [True])
    try:
        async with session_scope() as s:
            bid = (await s.execute(text("SELECT id FROM label_batches WHERE key = :k"), {"k": key})).scalar()
            tid = (await s.execute(text("SELECT id FROM label_tasks WHERE batch_id = :b"), {"b": bid})).scalar()
            inv = uuid.uuid4()
            await s.execute(text("INSERT INTO label_invites (id, token, batch_id, user_id) VALUES (:i, :h, :b, :u)"),
                            {"i": inv, "b": bid, "h": uuid.uuid4().hex, "u": who})
            await s.execute(text("INSERT INTO label_responses (id, invite_id, task_id, labeller, selected) "
                                 "VALUES (:i, :v, :t, 'x', '[]'::jsonb)"), {"i": uuid.uuid4(), "v": inv, "t": tid})
        async with _client() as c:
            r = await c.post("/api/v1/admin/labellers/status", headers={"Authorization": f"Bearer {fb}"},
                             json={"email": f"labeller-{tag}@example.test", "status": "removed"})
            assert r.status_code == 200
            # Re-applying changes languages, never status.
            r = await c.post("/api/v1/labeller/apply", headers={"Authorization": f"Bearer {wb}"},
                             json={"languages_read": ["en", "hi"]})
            assert r.status_code == 200
            r = await c.get("/api/v1/labeller/batches", headers={"Authorization": f"Bearer {wb}"})
            assert r.json()["ready"] == []
        assert await _status(who) == "removed"
        async with session_scope() as s:
            passed = (await s.execute(text("SELECT passed_at FROM labeller_qualifications WHERE user_id = :u"),
                                      {"u": who})).scalar()
            answers = (await s.execute(text("SELECT count(*) FROM label_responses WHERE invite_id = :v"),
                                       {"v": inv})).scalar()
            await s.execute(text("DELETE FROM label_responses WHERE invite_id = :v"), {"v": inv})
            await s.execute(text("DELETE FROM label_invites WHERE id = :v"), {"v": inv})
        assert passed is None and answers == 1
    finally:
        await _cleanup([founder, who], [key], tag)


async def test_a_round_a_constant_strategy_passes_is_never_published(founder_list):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    founder, fb = await _account(f"founder-{tag}@example.test")
    founder_list(f"founder-{tag}@example.test")
    unfair = await _round("practice", [True, True, True, True])
    unexplained = await _round("practice", [True, False, True, False], explained=False)
    fair = await _round("practice", [True, False, True, False])
    try:
        async with _client() as c:
            h = {"Authorization": f"Bearer {fb}"}
            r = await c.post(f"/api/v1/admin/batches/{unfair}/open", json={"on": True}, headers=h)
            assert r.status_code == 409 and "without reading" in r.json()["detail"]
            r = await c.post(f"/api/v1/admin/batches/{unexplained}/open", json={"on": True}, headers=h)
            assert r.status_code == 409 and "explanation" in r.json()["detail"]
            # Writing the explanations is what makes it publishable.
            r = await c.put(f"/api/v1/admin/batches/{unexplained}/explanations", headers=h,
                            json={"edits": [{"position": p, "explanation": "said so"} for p in range(4)]})
            assert r.status_code == 200 and r.json()["check"]["ok"]
            r = await c.post(f"/api/v1/admin/batches/{fair}/open", json={"on": True}, headers=h)
            assert r.status_code == 200
            r = await c.get(f"/api/v1/admin/batches/{fair}/items", headers=h)
            assert [i["answer"] for i in r.json()["items"]] == ["yes", "no", "yes", "no"]
        async with session_scope() as s:
            opened = dict((await s.execute(text("SELECT key, open FROM label_batches WHERE key = ANY(:k)"),
                                           {"k": [unfair, fair]})).all())
        assert opened == {unfair: False, fair: True}
        assert [a["action"] for a in await _audit(fair)] == ["batch.open"]
        assert await _audit(unfair) == []
    finally:
        await _cleanup([founder], [unfair, unexplained, fair], tag)


async def test_listing_closes_anonymous_join_and_unknowns_are_refused(founder_list):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    founder, fb = await _account(f"founder-{tag}@example.test")
    stranger, _ = await _account(f"stranger-{tag}@example.test")
    founder_list(f"founder-{tag}@example.test")
    key = await _round("work", [True])
    async with session_scope() as s:
        await s.execute(text("UPDATE label_batches SET self_join = true WHERE key = :k"), {"k": key})
    try:
        async with _client() as c:
            h = {"Authorization": f"Bearer {fb}"}
            assert (await c.post(f"/api/v1/admin/batches/{key}/listed", json={"on": True}, headers=h)).status_code == 200
            r = await c.post("/api/v1/admin/labellers/qualify", headers=h,
                             json={"email": f"stranger-{tag}@example.test", "kind": "no_such_kind", "granted": True})
            assert r.status_code == 409
            r = await c.post("/api/v1/admin/labellers/add", headers=h,
                             json={"email": f"nobody-{tag}@example.test", "languages_read": ["en"]})
            assert r.status_code == 404
            r = await c.post("/api/v1/admin/labellers/add", headers=h,
                             json={"email": f"stranger-{tag}@example.test", "languages_read": ["kn", "xx"]})
            assert r.status_code == 200
            assert (await c.post("/api/v1/admin/batches/nokey/listed", json={"on": True}, headers=h)).status_code == 404
        async with session_scope() as s:
            listed, self_join = (await s.execute(text("SELECT listed, self_join FROM label_batches WHERE key = :k"),
                                                 {"k": key})).one()
            langs = (await s.execute(text("SELECT languages_read FROM labellers WHERE user_id = :u"),
                                     {"u": stranger})).scalar()
        assert listed and not self_join
        assert langs == ["kn"] and await _status(stranger) == "active"
    finally:
        await _cleanup([founder, stranger], [key], tag)


async def test_the_command_line_runs_the_same_operations(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    from tools import label_admin

    tag = uuid.uuid4().hex[:8]
    who, _ = await _account(f"cli-{tag}@example.test", status="applied")
    url = get_settings().database_url
    monkeypatch.setattr(sys, "argv", ["label_admin", "--db", url, "--by", f"cli-founder-{tag}",
                                      "--approve", f"cli-{tag}@example.test"])
    try:
        assert await label_admin.main() == 0
        assert await _status(who) == "active"
        assert [a["actor"] for a in await _audit(f"cli-{tag}@example.test")] == [f"cli-founder-{tag}"]
        # A typo in the second email must not undo the first. It used to: one
        # transaction for the whole run, so "--remove bad-actor typo" printed
        # bad-actor as removed and then rolled it back (review, 2026-09-23).
        monkeypatch.setattr(sys, "argv", ["label_admin", "--db", url, "--by", f"cli-founder-{tag}",
                                          "--pause", f"cli-{tag}@example.test", f"nobody-{tag}@example.test"])
        assert await label_admin.main() == 1
        assert await _status(who) == "paused"
        assert [a["action"] for a in await _audit(f"cli-{tag}@example.test")] == ["labeller.status"] * 2
    finally:
        await _cleanup([who], [], tag)
