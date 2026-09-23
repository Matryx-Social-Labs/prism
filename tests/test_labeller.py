"""The labeller workspace — apply, get approved, see your batches, start one.

Drives the real app against a live Postgres, like tests/test_label.py. The
properties pinned here are the ones founder decisions 2026-09-23 rest on: an
applicant cannot promote themselves, nobody unapproved is served a task, a
labeller is never served a task in a language they did not say they read,
pausing someone stops their writes, and a founder's own invite link behaves
exactly as it did before any of this existed.
"""

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common import auth
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _user(status: str | None = None, langs: tuple[str, ...] = ("en",)) -> tuple[uuid.UUID, str]:
    """A Prism account with a live session; optionally already a labeller."""
    uid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO users (id, email, name) VALUES (:i, :e, 'Test Labeller')"),
                        {"i": uid, "e": f"labeller-{uid.hex[:10]}@example.test"})
        if status:
            await s.execute(
                text("INSERT INTO labellers (user_id, languages_read, status) VALUES (:u, CAST(:l AS text[]), :s)"),
                {"u": uid, "l": list(langs), "s": status})
        bearer = await auth.create_session(s, uid)
    return uid, bearer


async def _batch(task_langs: list[list[str] | None], *, listed: bool = True, is_open: bool = True) -> str:
    """A claim batch whose tasks need the given languages (None = ungated)."""
    key = f"k{uuid.uuid4().hex[:12]}"
    bid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO label_batches (id, key, name, kind, open, listed) "
                 "VALUES (:i, :k, 'test batch', 'claim_attribution', :o, :l)"),
            {"i": bid, "k": key, "o": is_open, "l": listed})
        for pos, langs in enumerate(task_langs):
            await s.execute(
                text("INSERT INTO label_tasks (id, batch_id, position, candidates, payload, languages) "
                     "VALUES (:i, :b, :p, '[]'::jsonb, CAST(:pl AS jsonb), CAST(:l AS text[]))"),
                {"i": uuid.uuid4(), "b": bid, "p": pos, "l": langs,
                 "pl": json.dumps({"kind": "claim_attribution", "speaker": "S", "quote_text": f"quote {pos}",
                                   "language": (langs or ["en"])[0]})})
    return key


async def _cleanup(*uids: uuid.UUID) -> None:
    async with session_scope() as s:
        for uid in uids:
            await s.execute(text("DELETE FROM sessions WHERE user_id = :u"), {"u": uid})
            await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})  # cascades labellers


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_the_workspace_requires_a_signed_in_account():
    if not await _db_reachable():
        pytest.skip("no database")
    async with _client() as c:
        assert (await c.get("/api/v1/labeller/me")).status_code == 401
        assert (await c.post("/api/v1/labeller/apply", json={"languages_read": ["en"]})).status_code == 401


async def test_applying_never_approves_and_reapplying_never_promotes():
    if not await _db_reachable():
        pytest.skip("no database")
    uid, bearer = await _user()
    try:
        async with _client() as c:
            h = {"Authorization": f"Bearer {bearer}"}
            r = await c.post("/api/v1/labeller/apply", json={"languages_read": ["kn", "en"], "note": "I read both"}, headers=h)
            assert r.json() == {"status": "applied", "languages_read": ["en", "kn"]}
            # an unknown code is dropped, not stored
            r = await c.post("/api/v1/labeller/apply", json={"languages_read": ["en", "xx"]}, headers=h)
            assert r.json()["languages_read"] == ["en"] and r.json()["status"] == "applied"
            async with session_scope() as s:
                await s.execute(text("UPDATE labellers SET status = 'active' WHERE user_id = :u"), {"u": uid})
            r = await c.post("/api/v1/labeller/apply", json={"languages_read": ["hi"]}, headers=h)
            assert r.json()["status"] == "active", "changing your languages must not undo an approval"
    finally:
        await _cleanup(uid)


async def test_an_applicant_is_served_nothing_and_cannot_start():
    if not await _db_reachable():
        pytest.skip("no database")
    key = await _batch([None])
    uid, bearer = await _user(status="applied")
    try:
        async with _client() as c:
            h = {"Authorization": f"Bearer {bearer}"}
            r = await c.get("/api/v1/labeller/batches", headers=h)
            assert r.json() == {"status": "applied", "ready": [], "done": []}
            assert (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=h)).status_code == 403
    finally:
        await _cleanup(uid)


async def test_only_listed_open_batches_in_your_languages_are_shown():
    if not await _db_reachable():
        pytest.skip("no database")
    mine = await _batch([["en", "hi"], ["en", "kn"], None])
    unlisted = await _batch([None], listed=False)
    closed = await _batch([None], is_open=False)
    kannada_only = await _batch([["en", "kn"]])
    uid, bearer = await _user(status="active", langs=("en", "hi"))
    try:
        async with _client() as c:
            r = await c.get("/api/v1/labeller/batches", headers={"Authorization": f"Bearer {bearer}"})
            keys = {b["key"]: b for b in r.json()["ready"]}
            assert mine in keys and keys[mine]["eligible"] == 2, "the Kannada task is not theirs to do"
            assert unlisted not in keys and closed not in keys
            assert kannada_only not in keys, "a batch with nothing in your languages is not offered"
            assert "selected" not in json.dumps(r.json()), "never another labeller's answers"
    finally:
        await _cleanup(uid)


async def test_starting_twice_returns_one_credential_that_works_on_the_task_routes():
    if not await _db_reachable():
        pytest.skip("no database")
    key = await _batch([None])
    uid, bearer = await _user(status="active")
    try:
        async with _client() as c:
            h = {"Authorization": f"Bearer {bearer}"}
            t1 = (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=h)).json()["token"]
            t2 = (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=h)).json()["token"]
            assert t1 == t2
            task = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": t1})).json()["task"]
            ok = await c.post(f"/api/v1/label/{key}/answer", json={"task_id": task["id"], "token": t1, "selected": []})
            assert ok.status_code == 200
            done = (await c.get("/api/v1/labeller/batches", headers=h)).json()
            assert [b["key"] for b in done["done"]] == [key]
    finally:
        await _cleanup(uid)


async def test_a_labeller_is_never_served_a_task_in_a_language_they_do_not_read():
    if not await _db_reachable():
        pytest.skip("no database")
    key = await _batch([["en", "kn"], ["en", "hi"]])  # position 0 is Kannada
    uid, bearer = await _user(status="active", langs=("en", "hi"))
    try:
        async with _client() as c:
            tok = (await c.post(f"/api/v1/labeller/batches/{key}/start",
                                headers={"Authorization": f"Bearer {bearer}"})).json()["token"]
            head = (await c.get(f"/api/v1/label/{key}", headers={"X-Label-Token": tok})).json()
            assert head["total"] == 1, "progress counts only the tasks they can do"
            task = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": tok})).json()["task"]
            assert task["claim"]["quote_text"] == "quote 1"
            await c.post(f"/api/v1/label/{key}/answer", json={"task_id": task["id"], "token": tok, "selected": []})
            after = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": tok})).json()
            assert after["task"] is None, "the Kannada task must never come round"
    finally:
        await _cleanup(uid)


async def test_pausing_a_labeller_stops_their_writes_at_once():
    if not await _db_reachable():
        pytest.skip("no database")
    key = await _batch([None, None])
    uid, bearer = await _user(status="active")
    try:
        async with _client() as c:
            tok = (await c.post(f"/api/v1/labeller/batches/{key}/start",
                                headers={"Authorization": f"Bearer {bearer}"})).json()["token"]
            task = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": tok})).json()["task"]
            async with session_scope() as s:
                await s.execute(text("UPDATE labellers SET status = 'paused' WHERE user_id = :u"), {"u": uid})
            r = await c.post(f"/api/v1/label/{key}/answer", json={"task_id": task["id"], "token": tok, "selected": []})
            assert r.status_code == 403
            assert (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": tok})).status_code == 403
    finally:
        await _cleanup(uid)


async def test_a_founders_invite_link_is_served_every_task_as_before():
    """An anonymous invite has no account and no gate — the path the existing
    batches and tools/gold_candidates --invite use must not change."""
    if not await _db_reachable():
        pytest.skip("no database")
    key = await _batch([["en", "kn"]], listed=False)
    async with _client() as c:
        tok = (await c.post(f"/api/v1/label/{key}/join", json={"name": "founder"})).json()["token"]
        task = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": tok})).json()["task"]
        assert task is not None and task["claim"]["quote_text"] == "quote 0"


async def test_a_listed_batch_cannot_be_joined_anonymously():
    """Security review 2026-09-23 (CRITICAL): the batch key is shown to every
    active labeller, and label.py's anonymous /join minted a credential on it
    with no approval, no language gate and no pause — a paused labeller holding
    the key, or anyone it was forwarded to, kept writing."""
    if not await _db_reachable():
        pytest.skip("no database")
    key = await _batch([["en", "kn"]])  # listed
    async with _client() as c:
        r = await c.post(f"/api/v1/label/{key}/join", json={"name": "stranger"})
        assert r.status_code == 403


async def test_an_answer_for_a_task_outside_your_languages_is_refused():
    """Security review 2026-09-23: `next` never serves it, but the answer route
    must refuse it too — a task id can be learnt from another labeller."""
    if not await _db_reachable():
        pytest.skip("no database")
    key = await _batch([["en", "kn"], ["en"]])
    uid, bearer = await _user(status="active", langs=("en",))
    try:
        async with session_scope() as s:
            kannada = (await s.execute(text(
                "SELECT t.id FROM label_tasks t JOIN label_batches b ON b.id = t.batch_id "
                "WHERE b.key = :k AND t.position = 0"), {"k": key})).scalar_one()
        async with _client() as c:
            tok = (await c.post(f"/api/v1/labeller/batches/{key}/start",
                                headers={"Authorization": f"Bearer {bearer}"})).json()["token"]
            r = await c.post(f"/api/v1/label/{key}/answer", json={"task_id": str(kannada), "token": tok, "selected": []})
            assert r.status_code == 404
    finally:
        await _cleanup(uid)
