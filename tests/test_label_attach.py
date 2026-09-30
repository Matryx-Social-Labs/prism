"""The attach check in /label, and founders labelling without a test.

Founder decision 2026-09-30: the article-vs-record check (tools/gold_attaches)
goes in the labelling workspace, and founders — the accounts on
PRISM_ADMIN_EMAILS, who approve labellers and write the tests — label without
an approval or a test. No test exists for the attach check yet, so without this
nobody could answer it.
"""

import json
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text

import api.routes.labeller as labeller
from common import auth
from common.config import get_settings
from common.db import session_scope
from tests.test_labeller import _cleanup, _client, _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")

PAIR = {
    "kind": "attach_identity",
    "record": {"headline": "High Court disqualifies MLA", "summary": "s", "first_reported": "2026-09-21 10:00"},
    "article": {"outlet": "sakshi", "published": "2026-09-27 08:00", "language": "te", "title": "ఎమ్మెల్యే",
                "headline_english": "Supreme Court upholds MLA disqualification", "summary_english": "s"},
    "_pair": "p1", "_tier": "entity_overlap", "_same": 0.1, "_follows": 0.93,
}


async def _account(email: str, status: str | None = None) -> tuple[uuid.UUID, str]:
    uid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO users (id, email, name) VALUES (:i, :e, 'T')"), {"i": uid, "e": email})
        if status:
            await s.execute(text("INSERT INTO labellers (user_id, languages_read, status) VALUES (:u, ARRAY['en'], :s)"),
                            {"u": uid, "s": status})
        bearer = await auth.create_session(s, uid)
    return uid, bearer


async def _attach_batch() -> tuple[str, uuid.UUID]:
    key, bid, tid = f"k{uuid.uuid4().hex[:12]}", uuid.uuid4(), uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO label_batches (id, key, name, kind, open, listed) "
                             "VALUES (:i, :k, 'attach check', 'attach_identity', true, true)"), {"i": bid, "k": key})
        await s.execute(text("INSERT INTO label_tasks (id, batch_id, position, candidates, payload) "
                             "VALUES (:i, :b, 0, '[]'::jsonb, CAST(:p AS jsonb))"),
                        {"i": tid, "b": bid, "p": json.dumps(PAIR, ensure_ascii=False)})
    return key, tid


@pytest_asyncio.fixture(loop_scope="session")
async def people(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    founder_email = f"founder-{tag}@example.test"
    monkeypatch.setattr(get_settings(), "prism_admin_emails", f"someone@else.test, {founder_email.upper()}")
    founder = await _account(founder_email)
    labeller_ = await _account(f"labeller-{tag}@example.test", status="active")
    key, task = await _attach_batch()
    yield founder, labeller_, key, task
    async with session_scope() as s:
        await s.execute(text("DELETE FROM label_batches WHERE key = :k"), {"k": key})
    await _cleanup(founder[0], labeller_[0])


def _h(bearer: str) -> dict:
    return {"Authorization": f"Bearer {bearer}"}


async def test_a_founder_is_approved_on_applying_and_nobody_else_is(people):
    (_, founder), _, _, _ = people
    async with _client() as c:
        r = await c.post("/api/v1/labeller/apply", json={"languages_read": ["en", "kn"]}, headers=_h(founder))
        assert r.json()["status"] == "active"
        stranger_id, stranger = await _account(f"x-{uuid.uuid4().hex[:8]}@example.test")
        try:
            r = await c.post("/api/v1/labeller/apply", json={"languages_read": ["en"]}, headers=_h(stranger))
            assert r.json()["status"] == "applied"
        finally:
            await _cleanup(stranger_id)


async def test_a_founder_labels_the_attach_check_without_a_test_and_a_labeller_cannot(people):
    (_, founder), (_, labeller_), key, _ = people
    async with _client() as c:
        await c.post("/api/v1/labeller/apply", json={"languages_read": ["en"]}, headers=_h(founder))
        mine = (await c.get("/api/v1/labeller/batches", headers=_h(founder))).json()
        assert key in [b["key"] for b in mine["ready"]]
        assert (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=_h(founder))).status_code == 200
        theirs = (await c.get("/api/v1/labeller/batches", headers=_h(labeller_))).json()
        assert key not in [b["key"] for b in theirs["ready"]], "no test exists for the kind: no labeller qualifies"
        assert (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=_h(labeller_))).status_code == 403


async def test_the_attach_task_is_served_without_the_machines_answer(people):
    (_, founder), _, key, task = people
    async with _client() as c:
        await c.post("/api/v1/labeller/apply", json={"languages_read": ["en"]}, headers=_h(founder))
        token = (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=_h(founder))).json()["token"]
        served = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": token})).json()["task"]
    assert served["kind"] == "attach_identity" and served["id"] == str(task)
    assert served["pair"]["article"]["headline_english"].startswith("Supreme Court")
    assert not [k for k in served["pair"] if k.startswith("_")], "the verifier's own answer is never shown"


async def test_an_attach_answer_names_one_of_three_and_no_other_kind_can(people):
    (_, founder), _, key, task = people
    async with _client() as c:
        await c.post("/api/v1/labeller/apply", json={"languages_read": ["en"]}, headers=_h(founder))
        token = (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=_h(founder))).json()["token"]
        answer = lambda **kw: c.post(f"/api/v1/label/{key}/answer", json={"task_id": str(task), "token": token, **kw})  # noqa: E731
        assert (await answer()).status_code == 422, "a definite answer must say which"
        assert (await answer(choice="maybe")).status_code == 422
        assert (await answer(choice="follow_up")).status_code == 200
    async with session_scope() as s:
        stored = (await s.execute(text("SELECT selected FROM label_responses WHERE task_id = :t"),
                                  {"t": str(task)})).scalar_one()
    assert stored == ["follow_up"]


async def test_a_choice_on_another_kind_is_refused(people):
    from tests.test_labeller import _batch

    (_, founder), _, _, _ = people
    key = await _batch([None])
    try:
        async with _client() as c:
            await c.post("/api/v1/labeller/apply", json={"languages_read": ["en"]}, headers=_h(founder))
            token = (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=_h(founder))).json()["token"]
            task = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": token})).json()["task"]["id"]
            r = await c.post(f"/api/v1/label/{key}/answer", json={"task_id": task, "token": token, "choice": "same"})
        assert r.status_code == 422
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM label_batches WHERE key = :k"), {"k": key})


async def test_live_checks_never_withdraw_a_founder(people, monkeypatch):
    (founder_id, _), _, _, _ = people

    async def failing(*_a, **_k):
        return 0, 20  # every recent check wrong

    monkeypatch.setattr(labeller, "live_accuracy", failing)
    async with session_scope() as s:  # a founder who also took the test once
        await s.execute(text("INSERT INTO labeller_qualifications (user_id, kind, passed_at, best_score, attempts) "
                             "VALUES (:u, 'claim_attribution', now(), 1.0, 1)"), {"u": founder_id})
    async with session_scope() as s:
        assert await labeller.recheck(s, founder_id, "claim_attribution") is False
    async with session_scope() as s:
        passed = (await s.execute(text("SELECT passed_at FROM labeller_qualifications WHERE user_id = :u"),
                                  {"u": founder_id})).scalar_one()
    assert passed is not None
