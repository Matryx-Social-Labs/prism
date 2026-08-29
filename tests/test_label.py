"""The labelling API — the surface that produces the measurement everything is judged on.

Drives the real FastAPI app over httpx against a live Postgres. Skips without a
database.

The properties pinned here are the ones that decide whether the resulting gold set
is worth anything. A labelling tool that loses answers, or shows one person another
person's opinion, or lets two batches write to each other, does not fail loudly — it
produces a plausible-looking set of labels that quietly encodes the bug, and every
later measurement inherits it as evidence.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")

# Test events are dated far in the past, and that is load-bearing.
#
# A fresh row carries last_updated_at = now(), which sorts it to the top of every
# recency-ordered feed query in the suite and displaces whatever another test
# expected to find there. It surfaced as test_geo and test_personalization failing
# in the full run while passing alone — pollution wearing the costume of a flaky
# test. Backdating is the fix at source: nothing here can outrank real fixtures.
#
# An autouse teardown that deleted the rows was tried first and is worse. It races
# conftest's per-test engine disposal and dies in the event loop, which trades a
# silent ordering bug for a noisy teardown one.
STALE = "timestamp '2019-01-01T00:00:00+00'"


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _batch(n_tasks: int = 2, is_open: bool = True) -> tuple[str, list[str]]:
    """A batch of `n_tasks` tasks, each a seed plus two candidate events."""
    key = f"k{uuid.uuid4().hex[:12]}"
    bid = uuid.uuid4()
    tasks: list[str] = []
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO label_batches (id, key, name, open) "
                 "VALUES (:i, :k, 'test batch', :o)"),
            {"i": bid, "k": key, "o": is_open},
        )
        for pos in range(n_tasks):
            ev = [uuid.uuid4() for _ in range(3)]
            for e in ev:
                await s.execute(
                    text("INSERT INTO events (id, title, first_seen_at, last_updated_at) "
                         f"VALUES (:i, :t, {STALE}, {STALE})"),
                    {"i": e, "t": f"headline {e.hex[:6]}"},
                )
            tid = uuid.uuid4()
            await s.execute(
                text("INSERT INTO label_tasks (id, batch_id, position, seed_event_id, "
                     "candidates, sector) VALUES (:i,:b,:p,:s,CAST(:c AS jsonb),'politics')"),
                {"i": tid, "b": bid, "p": pos, "s": ev[0],
                 "c": f'[{{"id":"{ev[1]}","signals":["actors"]}},'
                      f'{{"id":"{ev[2]}","signals":["embedding"]}}]'},
            )
            tasks.append(str(tid))
    return key, tasks


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_a_labeller_is_served_tasks_they_have_not_answered():
    if not await _db_reachable():
        pytest.skip("no database")
    key, _ = await _batch(2)
    async with _client() as c:
        first = (await c.get(f"/api/v1/label/{key}/next", params={"labeller": "ana"})).json()
        assert first["task"]["position"] == 0
        await c.post(f"/api/v1/label/{key}/answer", json={
            "task_id": first["task"]["id"], "labeller": "ana",
            "selected": [first["task"]["candidates"][0]["id"]],
        })
        second = (await c.get(f"/api/v1/label/{key}/next", params={"labeller": "ana"})).json()
    assert second["task"]["position"] == 1, "an answered task was served again"


async def test_two_labellers_get_the_same_task_independently():
    """A second opinion is the whole reason responses are keyed per person. If one
    labeller's answer removed the task from another's queue there would never be two
    opinions to compare, and disagreement — the signal that a call is genuinely hard
    — would be unobservable."""
    if not await _db_reachable():
        pytest.skip("no database")
    key, _ = await _batch(1)
    async with _client() as c:
        a = (await c.get(f"/api/v1/label/{key}/next", params={"labeller": "ana"})).json()
        await c.post(f"/api/v1/label/{key}/answer", json={
            "task_id": a["task"]["id"], "labeller": "ana", "selected": [],
        })
        b = (await c.get(f"/api/v1/label/{key}/next", params={"labeller": "ben"})).json()
    assert b["task"] is not None and b["task"]["id"] == a["task"]["id"]


async def test_the_task_never_carries_another_persons_answer():
    """Anchoring would destroy the value of a second opinion silently — the labels
    would still look independent afterwards."""
    if not await _db_reachable():
        pytest.skip("no database")
    key, _ = await _batch(1)
    async with _client() as c:
        a = (await c.get(f"/api/v1/label/{key}/next", params={"labeller": "ana"})).json()
        await c.post(f"/api/v1/label/{key}/answer", json={
            "task_id": a["task"]["id"], "labeller": "ana",
            "selected": [a["task"]["candidates"][0]["id"]],
        })
        b = (await c.get(f"/api/v1/label/{key}/next", params={"labeller": "ben"})).json()
    blob = str(b["task"])
    assert "selected" not in blob and "ana" not in blob


async def test_changing_your_mind_replaces_rather_than_appends():
    """One person must leave one opinion. Two rows from one person would read as
    agreement between two people."""
    if not await _db_reachable():
        pytest.skip("no database")
    key, tasks = await _batch(1)
    async with _client() as c:
        t = (await c.get(f"/api/v1/label/{key}/next", params={"labeller": "ana"})).json()["task"]
        for sel in ([], [t["candidates"][0]["id"]]):
            r = await c.post(f"/api/v1/label/{key}/answer", json={
                "task_id": t["id"], "labeller": "ana", "selected": sel,
            })
            assert r.status_code == 200
    async with session_scope() as s:
        n = (await s.execute(
            text("SELECT count(*) FROM label_responses WHERE task_id = :t AND labeller = 'ana'"),
            {"t": tasks[0]},
        )).scalar_one()
    assert n == 1, f"{n} rows for one person on one task"


async def test_an_empty_selection_is_recorded_as_a_real_answer():
    """"None of these" is a judgement, and a valuable negative. If it were treated as
    "not answered" the labeller would be served the same task forever."""
    if not await _db_reachable():
        pytest.skip("no database")
    key, tasks = await _batch(1)
    async with _client() as c:
        await c.post(f"/api/v1/label/{key}/answer", json={
            "task_id": tasks[0], "labeller": "ana", "selected": [],
        })
        nxt = (await c.get(f"/api/v1/label/{key}/next", params={"labeller": "ana"})).json()
    assert nxt["task"] is None


async def test_a_task_from_another_batch_cannot_be_written_through_this_key():
    """The batch key is the only access control. Without this check it would gate
    reads while leaving every task in the database writable."""
    if not await _db_reachable():
        pytest.skip("no database")
    key_a, _ = await _batch(1)
    _, tasks_b = await _batch(1)
    async with _client() as c:
        r = await c.post(f"/api/v1/label/{key_a}/answer", json={
            "task_id": tasks_b[0], "labeller": "ana", "selected": [],
        })
    assert r.status_code == 404


async def test_a_closed_batch_refuses_writes():
    if not await _db_reachable():
        pytest.skip("no database")
    key, tasks = await _batch(1, is_open=False)
    async with _client() as c:
        assert (await c.get(f"/api/v1/label/{key}/next")).json()["closed"] is True
        r = await c.post(f"/api/v1/label/{key}/answer", json={
            "task_id": tasks[0], "labeller": "ana", "selected": [],
        })
    assert r.status_code == 409


async def test_progress_counts_only_this_labeller():
    """With several people on one batch a shared counter would tell someone they
    were nearly done when they had barely started."""
    if not await _db_reachable():
        pytest.skip("no database")
    key, tasks = await _batch(3)
    async with _client() as c:
        await c.post(f"/api/v1/label/{key}/answer", json={
            "task_id": tasks[0], "labeller": "ana", "selected": [],
        })
        ana = (await c.get(f"/api/v1/label/{key}", params={"labeller": "ana"})).json()
        ben = (await c.get(f"/api/v1/label/{key}", params={"labeller": "ben"})).json()
    assert (ana["done"], ana["total"]) == (1, 3)
    assert ben["done"] == 0


async def test_an_unknown_key_is_a_404_not_an_empty_batch():
    if not await _db_reachable():
        pytest.skip("no database")
    async with _client() as c:
        assert (await c.get("/api/v1/label/nope-not-a-key")).status_code == 404
