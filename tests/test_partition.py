"""Storyline partitioner: Leiden determinism, branch-tree spine gate, verdict
signature/reuse, and the persisted base-run invariants that serving depends on.

Pure-logic tests need no DB. The persistence/read tests run against the local DB
(skipped when unreachable, like test_story_timeline.py) and mock the LLM so the
grounded veto is exercised deterministically and for free.
"""

import contextlib
import datetime as dt
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from correlation.partition import (
    Node,
    _StoryVeto,
    _vet_with_reuse,
    build_branch_tree,
    leiden_partition,
    persist_base_run,
    story_signature,
)
from correlation.threads import _current_run_id, _partitioned_members

pytestmark = pytest.mark.asyncio(loop_scope="session")

UTC = dt.UTC


def _n(i: str, actors: dict | None = None, srcs: int = 1) -> Node:
    return Node(id=i, title=f"t-{i}", sector=None, regions=[], occurred_at=dt.datetime(2026, 7, 1, tzinfo=UTC),
                source_count=srcs, actors=actors or {})


@contextlib.asynccontextmanager
async def _events(titles: list[str]):
    """Insert throwaway events and remove them again.

    DATABASE_URL here is the developer's own database — there is no separate test
    DB — so events left behind show up as fake developments in the local feed.
    """
    ids = [uuid.uuid4() for _ in titles]
    async with session_scope() as s:
        for eid, title in zip(ids, titles, strict=True):
            await s.execute(
                text("INSERT INTO events (id,title,summary,last_updated_at) VALUES (:i,:t,'s',now())"),
                {"i": str(eid), "t": title},
            )
    try:
        yield ids
    finally:
        async with session_scope() as s:
            await s.execute(
                text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"),
                {"e": [str(i) for i in ids]},
            )


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


# ── Pure logic ───────────────────────────────────────────────────────────────
def test_leiden_partition_deterministic():
    nodes = {f"n{i}": _n(f"n{i}") for i in range(6)}
    edges = [("n0", "n1", 1.0), ("n1", "n2", 1.0), ("n3", "n4", 1.0), ("n4", "n5", 1.0)]
    a = leiden_partition(nodes, edges)
    b = leiden_partition(nodes, edges)
    assert a == b  # seed=42 → identical run to run
    assert len({a[k] for k in a}) >= 2  # two disconnected chains → ≥2 stories


def test_story_signature_label_independent_and_versioned():
    m = [_n("a"), _n("b"), _n("c")]
    assert story_signature(m, "v1") == story_signature(list(reversed(m)), "v1")  # order-independent
    assert story_signature(m, "v1") != story_signature([_n("a"), _n("b")], "v1")  # membership change
    assert story_signature(m, "v1") != story_signature(m, "v2")  # config version change


def test_build_branch_tree_spine_gate():
    t0 = dt.datetime(2026, 7, 1, tzinfo=UTC)
    root = Node(id="r", title="root", sector=None, regions=[], occurred_at=t0, source_count=5, actors={"A": 2.0})
    on = Node(id="c1", title="on", sector=None, regions=[], occurred_at=t0, source_count=1, actors={"A": 2.0})
    off = Node(id="c2", title="off", sector=None, regions=[], occurred_at=t0, source_count=1, actors={"B": 2.0})
    from correlation.partition import _spine

    members = [root, on, off]
    spine = _spine(members)  # root's distinctive actors → {A: 1/df}
    edge_w = {("r", "c1"): 0.5, ("c1", "r"): 0.5}
    embed = {("r", "c1"): 0.05, ("c1", "r"): 0.05, ("r", "c2"): 0.99, ("c2", "r"): 0.99}
    root_id, parent, off_spine = build_branch_tree(members, edge_w, embed, spine)
    assert root_id == "r"
    assert "c2" in off_spine  # shares no root actor AND embeds far → off-spine satellite
    assert "c1" not in off_spine  # shares the root actor + embeds near → on-spine branch


# ── Verdict reuse + fail-open (mocked LLM) ───────────────────────────────────
async def test_vet_with_reuse_caches_then_skips_llm(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    calls = {"n": 0}

    async def fake_chat(**kwargs):
        calls["n"] += 1
        return _StoryVeto(same_story=True, confidence=0.9, reason="ok")

    monkeypatch.setattr("correlation.partition.structured_chat", fake_chat)
    ver = "test-v1"
    async with _events([f"story dev {i}" for i in range(4)]) as ids:
        members = [_n(str(e), srcs=10 - i) for i, e in enumerate(ids)]
        root = members[0]
        async with session_scope() as s:
            keep1, v1 = await _vet_with_reuse(s, root, members, "m", ver, None)
        assert calls["n"] == 3  # three candidates judged by the LLM
        assert keep1 == {m.id for m in members}  # all same_story=True
        assert not any(x["reused"] for x in v1)

        # Same signature (same members+version) → verdicts reused, LLM NOT called again.
        async with session_scope() as s:
            keep2, v2 = await _vet_with_reuse(s, root, members, "m", ver, None)
        assert calls["n"] == 3  # unchanged
        assert keep2 == keep1
        assert all(x["reused"] for x in v2)


async def test_vet_fail_open_keeps_member(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    async def boom(**kwargs):
        raise RuntimeError("llm down")

    monkeypatch.setattr("correlation.partition.structured_chat", boom)
    async with _events([f"dev {i}" for i in range(2)]) as ids:
        members = [_n(str(e), srcs=5 - i) for i, e in enumerate(ids)]
        async with session_scope() as s:
            keep, _ = await _vet_with_reuse(s, members[0], members, "m", "fail-v", None)
        assert keep == {m.id for m in members}  # fail-open: a failed veto keeps the member


# ── Persist invariant + read (DB) ────────────────────────────────────────────
async def test_persist_base_run_invariant_and_read():
    if not await _db_reachable():
        pytest.skip("no database")
    # This one publishes REAL runs over the whole corpus — that is the behaviour
    # under test, so it can't use the throwaway fixtures above. But publishing
    # retires the developer's current run, which is what the local trending page
    # reads, so it hands that run back at the end.
    async with session_scope() as s:
        prior = (await s.execute(text("SELECT id FROM partition_runs WHERE status='current'"))).scalar()
    try:
        run_id = await persist_base_run()
        async with session_scope() as s:
            assert (await s.execute(text("SELECT count(*) FROM partition_runs WHERE status='current'"))).scalar() == 1
            assert await _current_run_id(s) == run_id
            rows = (await s.execute(text("SELECT count(*) FROM event_story WHERE run_id=:r"), {"r": run_id})).scalar()
            assert rows >= 0  # every windowed event got a membership row
            # a member reads its own story's full set from any entry point
            sample = (await s.execute(text("SELECT event_id FROM event_story WHERE run_id=:r LIMIT 1"), {"r": run_id})).scalar()
            if sample is not None:
                members = await _partitioned_members(s, sample)
                assert members is not None and str(sample) in members
        # republish → exactly one current still (atomic cutover), old superseded
        run2 = await persist_base_run()
        async with session_scope() as s:
            assert (await s.execute(text("SELECT count(*) FROM partition_runs WHERE status='current'"))).scalar() == 1
            assert (await s.execute(text("SELECT status FROM partition_runs WHERE id=:r"), {"r": run_id})).scalar() == "superseded"
        assert run2 != run_id
    finally:
        async with session_scope() as s:
            # Only hand the old run back if it still EXISTS. persist_base_run
            # prunes to PARTITION_RETENTION, and this test publishes two runs per
            # call, so `prior` ages out of the keep-window after a few runs.
            # Retiring the live run and then failing to restore a deleted one
            # left the database with ZERO current runs — worse than the drift
            # this teardown exists to undo. A freshly computed run is a perfectly
            # valid current; only reclaim the old one when it's really there.
            still_there = prior and (
                await s.execute(
                    text("SELECT 1 FROM partition_runs WHERE id = :p"), {"p": str(prior)}
                )
            ).scalar()
            if still_there:
                await s.execute(text("UPDATE partition_runs SET status='superseded' WHERE status='current'"))
                await s.execute(
                    text("UPDATE partition_runs SET status='current' WHERE id = :p"), {"p": str(prior)}
                )


async def test_partitioned_members_none_for_unknown_event():
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        assert await _partitioned_members(s, uuid.uuid4()) is None  # not in any run → BFS fallback


def _dated(i: str, day: int, srcs: int = 1) -> Node:
    """A member on a distinct day — the shared _n() pins them all to one date,
    which collapses the prior-in-time ordering the arborescence depends on."""
    return Node(id=i, title=f"t-{i}", sector=None, regions=[],
                occurred_at=dt.datetime(2026, 7, day, tzinfo=UTC), source_count=srcs, actors={})


def test_the_hub_does_not_collect_every_development():
    """REGRESSION: the tree came back a star, not a tree.

    _root picks the most-corroborated event, and the raw score is shared-actor
    weight + embedding closeness — so the hub, which by construction is close to
    everything, outscored every rival parent for nearly every child and collected
    them all. Measured on a real 22-development storyline: the root won 19 of 21
    attachments, none by a tie-break. The page then showed a single
    "21 developments" row: a list wearing a tree's UI.

    Here `r` is that hub (strong with everyone) while a→b→c→d is a genuine chain.
    The chain must survive.
    """
    members = [_dated("r", 1, srcs=100), _dated("a", 2), _dated("b", 3), _dated("c", 4), _dated("d", 5)]
    chain = {("a", "b"), ("b", "c"), ("c", "d")}
    edge_w: dict[tuple[str, str], float] = {}
    for x in "abcd":
        edge_w[("r", x)] = edge_w[(x, "r")] = 1.0  # the hub is plausible for all of them
    for a, b in chain:
        edge_w[(a, b)] = edge_w[(b, a)] = 0.9
    embed = {(x.id, y.id): 0.5 for x in members for y in members if x.id != y.id}
    spine = {}

    root_id, parent, _ = build_branch_tree(members, edge_w, embed, spine)
    assert root_id == "r"  # still the most-corroborated event

    fan_out = sum(1 for p in parent.values() if p == "r")
    assert fan_out < 4, f"the hub took {fan_out}/4 children — that is a star, not a tree"
    # And the real chain is what survived.
    assert parent["b"] == "a"
    assert parent["c"] == "b"
    assert parent["d"] == "c"


def test_a_genuine_chain_is_left_alone():
    """Normalising must not invent structure where the raw score already agreed."""
    members = [_dated("r", 1, srcs=10), _dated("a", 2), _dated("b", 3)]
    edge_w = {("r", "a"): 0.9, ("a", "r"): 0.9, ("a", "b"): 0.9, ("b", "a"): 0.9}
    embed = {(x.id, y.id): 0.5 for x in members for y in members if x.id != y.id}
    root_id, parent, _ = build_branch_tree(members, edge_w, embed, {})
    assert root_id == "r"
    assert parent["a"] == "r"
    assert parent["b"] == "a"


def test_a_member_with_no_affinity_at_all_does_not_crash_the_partitioner():
    """A member connected to nothing has a mean pull of exactly 0.

    Normalising by it is a float division by zero, which takes down the whole
    partition run — every storyline, not just this one. Isolated members are
    ordinary in a freshly-ingested corpus, so this is the common case, not a
    corner. (It cannot instead be a *hijack*: a member with no affinity to
    anything also has no affinity to this child, so its numerator is 0 too.)"""
    members = [_dated("r", 1, srcs=10), _dated("lonely", 2), _dated("x", 3)]
    edge_w = {("r", "x"): 0.8, ("x", "r"): 0.8}
    embed = {("r", "x"): 0.2, ("x", "r"): 0.2}  # 'lonely' has no pairs at all
    _, parent, _ = build_branch_tree(members, edge_w, embed, {})
    assert parent["x"] == "r"
