"""Practise a task, pass its test, then label it (labeller workspace, phase 3).

The first labelling round came back with its two labellers disagreeing in
opposite systematic ways, "because nothing made them" read the guidance.
Founder decision 2026-09-23: a 90% test per task kind before any work of that
kind. The properties pinned here are the ones that decide whether the test
means anything: the answer never reaches the client before it should, an
attempt cannot be re-drawn by abandoning it, a scored attempt cannot be edited,
a failed one cannot be retaken at once, and passing is what opens the work.
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
from common.label_scoring import QUESTIONS_PER_TEST

pytestmark = pytest.mark.asyncio(loop_scope="session")
KIND = "claim_attribution"


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _labeller() -> tuple[uuid.UUID, dict]:
    uid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO users (id, email, name) VALUES (:i, :e, 'Q')"),
                        {"i": uid, "e": f"q-{uid.hex[:10]}@example.test"})
        await s.execute(text("INSERT INTO labellers (user_id, languages_read, status) VALUES (:u, '{en}', 'active')"),
                        {"u": uid})
        bearer = await auth.create_session(s, uid)
    return uid, {"Authorization": f"Bearer {bearer}"}


async def _round(purpose: str, n: int, *, lang: str | list[str] = "en") -> dict[str, bool]:
    """A practice or qualify batch of `n` claim items, alternating yes / no so no
    constant strategy passes. Returns task id -> the expected "yes"."""
    bid = uuid.uuid4()
    answers: dict[str, bool] = {}
    async with session_scope() as s:
        # One open round per kind is what the routes pick up; close any a
        # previous test left open so this one is the newest AND the only one.
        await s.execute(text("UPDATE label_batches SET open = false WHERE kind = :k AND purpose = :p"),
                        {"k": KIND, "p": purpose})
        await s.execute(
            text("INSERT INTO label_batches (id, key, name, kind, purpose, open) VALUES (:i, :k, 'q', :kind, :p, true)"),
            {"i": bid, "k": f"q{uuid.uuid4().hex[:12]}", "kind": KIND, "p": purpose})
        for pos in range(n):
            tid = uuid.uuid4()
            yes = pos % 2 == 0
            answers[str(tid)] = yes
            task_lang = lang[pos % len(lang)] if isinstance(lang, list) else lang
            await s.execute(
                text("INSERT INTO label_tasks (id, batch_id, position, candidates, payload, languages, expected, explanation) "
                     "VALUES (:i, :b, :p, '[]'::jsonb, CAST(:pl AS jsonb), CAST(:l AS text[]), CAST(:e AS jsonb), :x)"),
                {"i": tid, "b": bid, "p": pos, "l": [task_lang],
                 "pl": json.dumps({"kind": KIND, "speaker": "S", "quote_text": f"q{pos}", "language": task_lang}),
                 "e": json.dumps({"selected": [str(tid)] if yes else []}),
                 "x": f"because {pos}"})
    return answers


async def _work_batch() -> str:
    key = f"w{uuid.uuid4().hex[:12]}"
    async with session_scope() as s:
        bid = uuid.uuid4()
        await s.execute(text("INSERT INTO label_batches (id, key, name, kind, open, listed) VALUES (:i, :k, 'w', :kind, true, true)"),
                        {"i": bid, "k": key, "kind": KIND})
        await s.execute(text("INSERT INTO label_tasks (id, batch_id, position, candidates, payload) "
                             "VALUES (:i, :b, 0, '[]'::jsonb, CAST(:pl AS jsonb))"),
                        {"i": uuid.uuid4(), "b": bid, "pl": json.dumps({"kind": KIND, "speaker": "S", "quote_text": "w"})})
    return key


async def _cleanup(uid: uuid.UUID) -> None:
    async with session_scope() as s:
        await s.execute(text("DELETE FROM sessions WHERE user_id = :u"), {"u": uid})
        await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})
        # Leave no open practice/qualify round for the next test to pick up.
        await s.execute(text("UPDATE label_batches SET open = false WHERE kind = :k AND purpose <> 'work'"), {"k": KIND})


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def _answer_all(c: AsyncClient, key: str, token: str, answers: dict[str, bool], *, wrong: int = 0) -> dict:
    """Answer every task the attempt serves; get the first `wrong` of them wrong.
    Returns the final `next` payload (the result)."""
    served = 0
    while True:
        nxt = (await c.get(f"/api/v1/label/{key}/next", headers={"X-Label-Token": token})).json()
        if nxt["task"] is None:
            return nxt
        assert "expected" not in json.dumps(nxt) and "because" not in json.dumps(nxt), "the answer must not travel with the question"
        tid = nxt["task"]["id"]
        right = answers[tid] if served >= wrong else not answers[tid]
        r = await c.post(f"/api/v1/label/{key}/answer", json={"task_id": tid, "token": token, "selected": [tid] if right else []})
        assert r.status_code == 200, r.text
        assert "feedback" not in r.json(), "a test answers nothing until the end"
        served += 1


async def test_work_of_a_kind_waits_for_its_test():
    if not await _db_reachable():
        pytest.skip("no database")
    key = await _work_batch()
    uid, h = await _labeller()
    try:
        async with _client() as c:
            assert (await c.post(f"/api/v1/labeller/batches/{key}/start", headers=h)).status_code == 403
            board = (await c.get("/api/v1/labeller/batches", headers=h)).json()
            assert key not in [b["key"] for b in board["ready"]]
    finally:
        await _cleanup(uid)


async def test_practice_shows_the_answer_and_why_after_each_question_never_before():
    if not await _db_reachable():
        pytest.skip("no database")
    answers = await _round("practice", 4)
    uid, h = await _labeller()
    try:
        async with _client() as c:
            s = (await c.post(f"/api/v1/labeller/practice/{KIND}/start", headers=h)).json()
            nxt = (await c.get(f"/api/v1/label/{s['key']}/next", headers={"X-Label-Token": s["token"]})).json()
            assert "because" not in json.dumps(nxt)
            tid = nxt["task"]["id"]
            wrong = [] if answers[tid] else [tid]
            r = (await c.post(f"/api/v1/label/{s['key']}/answer", json={"task_id": tid, "token": s["token"], "selected": wrong})).json()
            assert r["feedback"]["correct"] is False
            assert r["feedback"]["expected"] == ([tid] if answers[tid] else [])
            assert r["feedback"]["explanation"].startswith("because")
    finally:
        await _cleanup(uid)


async def test_passing_the_test_opens_the_work():
    if not await _db_reachable():
        pytest.skip("no database")
    answers = await _round("qualify", QUESTIONS_PER_TEST + 5)
    work = await _work_batch()
    uid, h = await _labeller()
    try:
        async with _client() as c:
            s = (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).json()
            head = (await c.get(f"/api/v1/label/{s['key']}", headers={"X-Label-Token": s["token"]})).json()
            assert head["total"] == QUESTIONS_PER_TEST, "an attempt is a draw from the pool, not the pool"
            result = (await _answer_all(c, s["key"], s["token"], answers, wrong=1))["result"]
            assert result["passed"] is True and result["right"] == QUESTIONS_PER_TEST - 1  # 14/15 = 93%
            assert len(result["missed"]) == 1 and result["missed"][0]["explanation"].startswith("because")
            assert (await c.post(f"/api/v1/labeller/batches/{work}/start", headers=h)).status_code == 200
            assert (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).status_code == 409
    finally:
        await _cleanup(uid)


async def test_failing_means_a_fresh_draw_tomorrow_not_another_go_now():
    if not await _db_reachable():
        pytest.skip("no database")
    answers = await _round("qualify", QUESTIONS_PER_TEST + 5)
    uid, h = await _labeller()
    try:
        async with _client() as c:
            s = (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).json()
            result = (await _answer_all(c, s["key"], s["token"], answers, wrong=2))["result"]
            assert result["passed"] is False  # 13/15 = 87% < 90%
            assert (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).status_code == 429
            kinds = {k["kind"]: k for k in (await c.get("/api/v1/labeller/batches", headers=h)).json()["kinds"]}
            assert kinds[KIND]["can_test"] is False and kinds[KIND]["retake_at"]
    finally:
        await _cleanup(uid)


async def test_a_scored_attempt_cannot_be_edited_and_is_recorded_once():
    if not await _db_reachable():
        pytest.skip("no database")
    answers = await _round("qualify", QUESTIONS_PER_TEST)
    uid, h = await _labeller()
    try:
        async with _client() as c:
            s = (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).json()
            first = (await _answer_all(c, s["key"], s["token"], answers, wrong=3))["result"]
            again = (await c.get(f"/api/v1/label/{s['key']}/next", headers={"X-Label-Token": s["token"]})).json()["result"]
            assert again["score"] == first["score"]
            some_task = next(iter(answers))
            late = await c.post(f"/api/v1/label/{s['key']}/answer", json={"task_id": some_task, "token": s["token"], "selected": [some_task]})
            assert late.status_code == 409
        async with session_scope() as db:
            attempts = (await db.execute(text("SELECT attempts FROM labeller_qualifications WHERE user_id = :u AND kind = :k"),
                                         {"u": uid, "k": KIND})).scalar_one()
        assert attempts == 1, "reading the result twice must not count two attempts"
    finally:
        await _cleanup(uid)


async def test_abandoning_an_attempt_resumes_it_rather_than_redrawing():
    if not await _db_reachable():
        pytest.skip("no database")
    await _round("qualify", QUESTIONS_PER_TEST + 10)
    uid, h = await _labeller()
    try:
        async with _client() as c:
            a = (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).json()
            b = (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).json()
            assert a == b, "leaving halfway must not be a way to shop for easier questions"
    finally:
        await _cleanup(uid)


async def test_an_attempt_cannot_answer_a_question_outside_its_draw():
    if not await _db_reachable():
        pytest.skip("no database")
    answers = await _round("qualify", QUESTIONS_PER_TEST + 10)
    uid, h = await _labeller()
    try:
        async with _client() as c:
            s = (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).json()
            async with session_scope() as db:
                drawn = set(map(str, (await db.execute(text("SELECT task_ids FROM label_invites WHERE token = :t"),
                                                       {"t": s["token"]})).scalar_one()))
            outside = next(t for t in answers if t not in drawn)
            r = await c.post(f"/api/v1/label/{s['key']}/answer", json={"task_id": outside, "token": s["token"], "selected": []})
            assert r.status_code == 404
    finally:
        await _cleanup(uid)


async def test_a_test_needs_enough_questions_in_your_languages():
    if not await _db_reachable():
        pytest.skip("no database")
    await _round("qualify", QUESTIONS_PER_TEST + 5, lang="kn")  # the labeller reads only English
    uid, h = await _labeller()
    try:
        async with _client() as c:
            assert (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).status_code == 409
    finally:
        await _cleanup(uid)


async def test_the_scoring_and_the_pool_builder_hold_their_own_invariants():
    """The marking rule, the constant-strategy check, and the builder's pure
    parts: someone sharing a name with the speaker is never "someone else", a
    truncated gold quote is extended only within the article's own text, and a
    scarce "no" supply is used in full. Their self-checks, run where CI sees them."""
    from common import label_scoring
    from tools import label_qualify

    label_scoring.demo()
    label_qualify.demo()



async def test_dropping_a_language_mid_test_does_not_shrink_the_test():
    """Security review 2026-09-23 (CRITICAL): the draw was re-filtered by the
    labeller's CURRENT languages, so answering the easy ones, dropping a
    language and asking for the next question ended the test on a handful —
    and 3 of 3 is 100%. The draw is authoritative for the attempt's life."""
    if not await _db_reachable():
        pytest.skip("no database")
    answers = await _round("qualify", QUESTIONS_PER_TEST * 2, lang=["en", "kn"])
    uid, h = await _labeller()
    try:
        async with session_scope() as db:
            await db.execute(text("UPDATE labellers SET languages_read = '{en,kn}' WHERE user_id = :u"), {"u": uid})
        async with _client() as c:
            s = (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).json()
            first = (await c.get(f"/api/v1/label/{s['key']}/next", headers={"X-Label-Token": s["token"]})).json()["task"]
            await c.post(f"/api/v1/label/{s['key']}/answer",
                         json={"task_id": first["id"], "token": s["token"], "selected": [first["id"]] if answers[first["id"]] else []})
            await c.post("/api/v1/labeller/apply", json={"languages_read": ["en"]}, headers=h)
            after = (await c.get(f"/api/v1/label/{s['key']}/next", headers={"X-Label-Token": s["token"]})).json()
            assert after["task"] is not None and "result" not in after, "the rest of the draw must still be served"
            result = (await _answer_all(c, s["key"], s["token"], answers))["result"]
            assert result["total"] == QUESTIONS_PER_TEST, "scored over the whole draw"
        async with session_scope() as db:
            served = (await db.execute(text(
                "SELECT count(*) FROM label_responses r JOIN label_invites i ON i.id = r.invite_id WHERE i.token = :t"),
                {"t": s["token"]})).scalar_one()
        # Two defences, both pinned: the whole draw is SERVED (not just the part
        # in the languages they kept), and it is SCORED as a whole.
        assert served == QUESTIONS_PER_TEST, "every drawn question — Kannada included — was still served"
    finally:
        await _cleanup(uid)


async def test_a_retake_never_redraws_a_question_whose_answer_was_shown():
    """Security review 2026-09-23: a failed attempt explains the questions
    missed; drawing them again would let a few failures read the answer key."""
    if not await _db_reachable():
        pytest.skip("no database")
    answers = await _round("qualify", QUESTIONS_PER_TEST * 3)
    uid, h = await _labeller()
    try:
        async with _client() as c:
            s = (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).json()
            await _answer_all(c, s["key"], s["token"], answers, wrong=4)
            async with session_scope() as db:
                await db.execute(text("UPDATE labeller_qualifications SET last_attempt_at = now() - interval '25 hours' "
                                      "WHERE user_id = :u"), {"u": uid})
            again = (await c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h)).json()
            async with session_scope() as db:
                first_draw = set(map(str, (await db.execute(text("SELECT task_ids FROM label_invites WHERE token = :t"),
                                                            {"t": s["token"]})).scalar_one()))
                second_draw = set(map(str, (await db.execute(text("SELECT task_ids FROM label_invites WHERE token = :t"),
                                                             {"t": again["token"]})).scalar_one()))
            # _answer_all got the first four SERVED questions wrong: those are the revealed ones.
            async with session_scope() as db:
                served = [str(r[0]) for r in (await db.execute(text(
                    "SELECT r.task_id FROM label_responses r JOIN label_invites i ON i.id = r.invite_id "
                    "WHERE i.token = :t ORDER BY r.created_at"), {"t": s["token"]})).all()]
            revealed = set(served[:4])
            assert revealed <= first_draw and not (revealed & second_draw)
    finally:
        await _cleanup(uid)


async def test_two_simultaneous_starts_open_one_attempt():
    """Code + security review 2026-09-23: two taps on "Take the test" read the
    same max(attempt) — a 500, or two open draws of one pool."""
    if not await _db_reachable():
        pytest.skip("no database")
    import asyncio

    await _round("qualify", QUESTIONS_PER_TEST + 5)
    uid, h = await _labeller()
    try:
        async with _client() as c:
            a, b = await asyncio.gather(
                c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h),
                c.post(f"/api/v1/labeller/qualify/{KIND}/start", headers=h),
            )
        assert a.status_code == b.status_code == 200 and a.json()["token"] == b.json()["token"]
        async with session_scope() as db:
            open_attempts = (await db.execute(text(
                "SELECT count(*) FROM label_invites WHERE user_id = :u AND finished_at IS NULL"), {"u": uid})).scalar_one()
        assert open_attempts == 1
    finally:
        await _cleanup(uid)

async def test_a_test_built_from_a_labelled_batch_uses_only_what_two_people_agreed():
    """--from-batch turns a founder-labelled batch into a kind's test. A task one
    person answered, or two people split on, has no answer to test against."""
    if not await _db_reachable():
        pytest.skip("no database")
    import asyncpg

    from tools.label_qualify import batch_items
    from tools.scratch import _local_url

    key = f"b{uuid.uuid4().hex[:12]}"
    bid = uuid.uuid4()
    tasks = {name: uuid.uuid4() for name in ("agreed", "split", "alone")}
    async with session_scope() as s:
        await s.execute(text("INSERT INTO label_batches (id, key, name, kind, open) VALUES (:i, :k, 'r', 'quote_rendering', true)"),
                        {"i": bid, "k": key})
        for pos, (name, tid) in enumerate(tasks.items()):
            await s.execute(text("INSERT INTO label_tasks (id, batch_id, position, candidates, payload) "
                                 "VALUES (:i, :b, :p, '[]'::jsonb, CAST(:pl AS jsonb))"),
                            {"i": tid, "b": bid, "p": pos, "pl": json.dumps({"kind": "quote_rendering", "name": name})})
        invites = []
        for n in range(2):
            iid = uuid.uuid4()
            invites.append(iid)
            await s.execute(text("INSERT INTO label_invites (id, token, batch_id, name) VALUES (:i, :t, :b, :n)"),
                            {"i": iid, "t": uuid.uuid4().hex, "b": bid, "n": f"founder{n}"})
        votes = {("agreed", 0): True, ("agreed", 1): True, ("split", 0): True, ("split", 1): False, ("alone", 0): True}
        for (name, who), yes in votes.items():
            tid = tasks[name]
            await s.execute(text("INSERT INTO label_responses (id, task_id, invite_id, labeller, selected) "
                                 "VALUES (:i, :t, :v, 'f', CAST(:sel AS jsonb))"),
                            {"i": uuid.uuid4(), "t": tid, "v": invites[who], "sel": json.dumps([str(tid)] if yes else [])})
    c = await asyncpg.connect(_local_url(), timeout=30)
    try:
        kind, items = await batch_items(c, key)
    finally:
        await c.close()
    assert kind == "quote_rendering"
    assert [it["payload"]["name"] for it in items] == ["agreed"] and items[0]["yes"] is True
