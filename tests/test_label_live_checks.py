"""Hidden check items in work batches, and what a run of wrong ones costs (phase 5).

A work batch carries a known-answer item every so often, indistinguishable from
the rest. An account's accuracy on its last CHECK_WINDOW definite answers to
them is watched; below LIVE_MIN (after CHECK_MIN) the kind is withdrawn and its
credential stops working at once. Unsure is not penalised, ordinary work never
counts, and a founder's anonymous link is never checked.
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
from common.label_scoring import CHECK_MIN

pytestmark = pytest.mark.asyncio(loop_scope="session")
KIND = "claim_attribution"


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _qualified_labeller() -> tuple[uuid.UUID, dict]:
    uid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": uid, "e": f"lc-{uid.hex[:10]}@example.test"})
        await s.execute(text("INSERT INTO labellers (user_id, languages_read, status) VALUES (:u, '{en}', 'active')"), {"u": uid})
        await s.execute(text("INSERT INTO labeller_qualifications (user_id, kind, passed_at, attempts) VALUES (:u, :k, now(), 1)"),
                        {"u": uid, "k": KIND})
        bearer = await auth.create_session(s, uid)
    return uid, {"Authorization": f"Bearer {bearer}"}


async def _work_with_checks(n_checks: int, n_plain: int) -> tuple[str, dict[str, bool]]:
    """A listed work batch: checks (expected set, alternating yes/no) then plain tasks."""
    key = f"w{uuid.uuid4().hex[:12]}"
    bid = uuid.uuid4()
    answers: dict[str, bool] = {}
    async with session_scope() as s:
        await s.execute(text("INSERT INTO label_batches (id, key, name, kind, open, listed) VALUES (:i, :k, 'w', :kind, true, true)"),
                        {"i": bid, "k": key, "kind": KIND})
        for pos in range(n_checks + n_plain):
            tid = uuid.uuid4()
            check = pos < n_checks
            yes = pos % 2 == 0
            if check:
                answers[str(tid)] = yes
            await s.execute(
                text("INSERT INTO label_tasks (id, batch_id, position, candidates, payload, expected) "
                     "VALUES (:i, :b, :p, '[]'::jsonb, CAST(:pl AS jsonb), CAST(:e AS jsonb))"),
                {"i": tid, "b": bid, "p": pos, "pl": json.dumps({"kind": KIND, "speaker": "S", "quote_text": f"w{pos}"}),
                 "e": json.dumps({"selected": [str(tid)] if yes else []}) if check else None})
    return key, answers


async def _cleanup(uid: uuid.UUID) -> None:
    async with session_scope() as s:
        await s.execute(text("DELETE FROM sessions WHERE user_id = :u"), {"u": uid})
        await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def _answer(c, key, token, tid, selected, *, unsure=False):
    return await c.post(f"/api/v1/label/{key}/answer", json={"task_id": tid, "token": token, "selected": selected, "unsure": unsure})


async def test_a_run_of_wrong_checks_withdraws_the_kind_and_stops_the_credential():
    if not await _db_reachable():
        pytest.skip("no database")
    key, answers = await _work_with_checks(CHECK_MIN, 2)
    uid, h = await _qualified_labeller()
    try:
        async with _client() as c:
            tok = (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=h)).json()["token"]
            last = None
            for i in range(CHECK_MIN):
                task = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": tok})).json()["task"]
                assert "expected" not in json.dumps(task), "a check item looks like any other task"
                wrong = [] if answers[task["id"]] else [task["id"]]
                last = (await _answer(c, key, tok, task["id"], wrong)).json()
                if i < CHECK_MIN - 1:
                    assert last["requalify"] is False, "fewer than CHECK_MIN checks decide nothing"
            assert last["requalify"] is True
            assert (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": tok})).status_code == 403
            kinds = {k["kind"]: k for k in (await c.get("/api/v1/labeller/batches", headers=h)).json()["kinds"]}
            assert kinds[KIND]["qualified"] is False and kinds[KIND]["retake_at"], "the way back is the test, tomorrow"
    finally:
        await _cleanup(uid)


async def test_unsure_and_ordinary_work_never_count_against_a_labeller():
    if not await _db_reachable():
        pytest.skip("no database")
    key, answers = await _work_with_checks(CHECK_MIN, 5)
    uid, h = await _qualified_labeller()
    try:
        async with _client() as c:
            tok = (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=h)).json()["token"]
            while True:
                nxt = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": tok})).json()
                if nxt["task"] is None:
                    break
                tid = nxt["task"]["id"]
                # every check answered "unsure"; every ordinary task answered anything
                r = (await _answer(c, key, tok, tid, [], unsure=tid in answers)).json()
                assert r.get("requalify") in (None, False)
        async with session_scope() as db:
            passed = (await db.execute(text("SELECT passed_at FROM labeller_qualifications WHERE user_id = :u AND kind = :k"),
                                       {"u": uid, "k": KIND})).scalar_one()
        assert passed is not None
    finally:
        await _cleanup(uid)


async def test_a_founders_anonymous_link_is_never_checked():
    """Checks watch ACCOUNTS. The founders' own invite links carry no account,
    and their answers are the reference the checks are built from."""
    if not await _db_reachable():
        pytest.skip("no database")
    key, answers = await _work_with_checks(CHECK_MIN, 0)
    async with session_scope() as s:
        await s.execute(text("UPDATE label_batches SET listed = false WHERE key = :k"), {"k": key})  # a founder batch
    async with _client() as c:
        tok = (await c.post(f"/api/v1/label/{key}/join", json={"name": "founder"})).json()["token"]
        for _ in range(CHECK_MIN):
            task = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": tok})).json()["task"]
            r = (await _answer(c, key, tok, task["id"], [] if answers[task["id"]] else [task["id"]])).json()
            assert "requalify" not in r


async def test_seeding_checks_interleaves_them_and_refuses_a_batch_already_answered():
    if not await _db_reachable():
        pytest.skip("no database")
    import asyncpg

    from tools.label_qualify import seed_checks
    from tools.scratch import _local_url

    work_key, _ = await _work_with_checks(0, 18)
    round_key = f"r{uuid.uuid4().hex[:12]}"
    rid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("UPDATE label_batches SET listed = false WHERE key = :k"), {"k": work_key})
        await s.execute(text("INSERT INTO label_batches (id, key, name, kind, purpose, open) VALUES (:i, :k, 'r', :kind, 'qualify', false)"),
                        {"i": rid, "k": round_key, "kind": KIND})
        for pos in range(4):
            await s.execute(text("INSERT INTO label_tasks (id, batch_id, position, candidates, payload, expected, explanation) "
                                 "VALUES (:i, :b, :p, '[]'::jsonb, CAST(:pl AS jsonb), CAST(:e AS jsonb), 'why')"),
                            {"i": uuid.uuid4(), "b": rid, "p": pos,
                             "pl": json.dumps({"kind": KIND, "speaker": "S", "quote_text": f"c{pos}"}), "e": json.dumps({"selected": []})})
    c = await asyncpg.connect(_local_url(), timeout=30)
    try:
        await seed_checks(c, work_key, round_key, every=10, apply=True)
        rows = await c.fetch("SELECT position, expected IS NOT NULL AS chk FROM label_tasks t JOIN label_batches b ON b.id = t.batch_id "
                             "WHERE b.key = $1 ORDER BY position", work_key)
        assert [r["position"] for r in rows] == list(range(len(rows))), "positions stay contiguous"
        checks = [r["position"] for r in rows if r["chk"]]
        # One per block of ten, somewhere in it — not always the tenth, which made
        # them countable (security review 2026-09-23). Blocks: positions 0-9, 10-19.
        assert len(checks) == 2 and checks[0] // 10 == 0 and checks[1] // 10 == 1
        bid = await c.fetchval("SELECT id FROM label_batches WHERE key = $1", work_key)
        tid = await c.fetchval("SELECT id FROM label_tasks WHERE batch_id = $1 ORDER BY position LIMIT 1", bid)
        iid = uuid.uuid4()
        await c.execute("INSERT INTO label_invites (id, token, batch_id, name) VALUES ($1, $2, $3, 'x')", iid, uuid.uuid4().hex, bid)
        await c.execute("INSERT INTO label_responses (id, task_id, invite_id, labeller, selected) VALUES ($1, $2, $3, 'x', '[]'::jsonb)",
                        uuid.uuid4(), tid, iid)
        with pytest.raises(SystemExit, match="already has answers"):
            await seed_checks(c, work_key, round_key, every=10, apply=True)
    finally:
        await c.close()


async def test_the_reply_to_a_check_is_the_reply_to_any_task():
    """A reply that differed on check items would point them out."""
    if not await _db_reachable():
        pytest.skip("no database")
    key, answers = await _work_with_checks(2, 2)
    uid, h = await _qualified_labeller()
    try:
        async with _client() as c:
            tok = (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=h)).json()["token"]
            shapes = set()
            for _ in range(4):
                task = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": tok})).json()["task"]
                shapes.add(tuple(sorted((await _answer(c, key, tok, task["id"], [])).json())))
            assert shapes == {("ok", "requalify")}
    finally:
        await _cleanup(uid)


async def test_check_placement_is_not_a_fixed_period():
    """Seed the same batch shape repeatedly: a fixed period would put every check
    at the same offset every time. Five blocks at random offsets agree by chance
    with probability 1e-5 per pair."""
    if not await _db_reachable():
        pytest.skip("no database")
    import asyncpg

    from tools.label_qualify import seed_checks
    from tools.scratch import _local_url

    round_key = f"r{uuid.uuid4().hex[:12]}"
    rid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO label_batches (id, key, name, kind, purpose, open) VALUES (:i, :k, 'r', :kind, 'qualify', false)"),
                        {"i": rid, "k": round_key, "kind": KIND})
        for pos in range(10):
            await s.execute(text("INSERT INTO label_tasks (id, batch_id, position, candidates, payload, expected) "
                                 "VALUES (:i, :b, :p, '[]'::jsonb, CAST(:pl AS jsonb), '{\"selected\": []}'::jsonb)"),
                            {"i": uuid.uuid4(), "b": rid, "p": pos, "pl": json.dumps({"kind": KIND, "quote_text": f"c{pos}"})})
    layouts = []
    c = await asyncpg.connect(_local_url(), timeout=30)
    try:
        for _ in range(3):
            work_key, _ = await _work_with_checks(0, 45)
            await c.execute("UPDATE label_batches SET listed = false WHERE key = $1", work_key)
            await seed_checks(c, work_key, round_key, every=10, apply=True)
            layouts.append(tuple(r["position"] for r in await c.fetch(
                "SELECT t.position FROM label_tasks t JOIN label_batches b ON b.id = t.batch_id "
                "WHERE b.key = $1 AND t.expected IS NOT NULL ORDER BY t.position", work_key)))
    finally:
        await c.close()
    assert len(set(layouts)) > 1, f"three seedings placed the checks identically: {layouts}"


async def test_an_accounts_work_answer_is_final_check_or_not():
    """Security review 2026-09-23: rewriting an answer let a labeller who spotted
    a check resend it as "unsure", which the checks do not score. Every rewrite
    is refused the same way, so the refusal points at nothing."""
    if not await _db_reachable():
        pytest.skip("no database")
    key, answers = await _work_with_checks(1, 1)
    uid, h = await _qualified_labeller()
    try:
        async with _client() as c:
            tok = (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=h)).json()["token"]
            codes = []
            for _ in range(2):
                task = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": tok})).json()["task"]
                assert (await _answer(c, key, tok, task["id"], [])).status_code == 200
                again = await _answer(c, key, tok, task["id"], [], unsure=True)
                codes.append((again.status_code, again.json()))
            assert codes[0] == codes[1] and codes[0][0] == 409
    finally:
        await _cleanup(uid)
