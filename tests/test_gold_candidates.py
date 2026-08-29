"""The candidate proposer for gold labelling — properties a person cannot check.

A human reviewing the output will notice an irrelevant candidate. They will NOT
notice that one proposer silently contributed nothing, or that the time window
leaked, because a plausible-looking screen is produced either way. Those are the
failures worth pinning: a gold set built from a degraded proposer is biased in a
direction nobody can see afterwards, and it then becomes the thing every future
measurement is judged against.
"""

from collections import defaultdict

import numpy as np

from tools.gold_candidates import DAY, _neighbours
from tools.l2 import Snap

BASE = 1_700_000_000.0


def _snap(titles, actors, ts, vecs) -> Snap:
    ids = [f"e{i}" for i in range(len(titles))]
    emb = np.array(vecs, dtype=np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    df: dict[str, int] = {}
    for a in actors:
        for slug in set(a):
            df[slug] = df.get(slug, 0) + 1
    return Snap(
        ids=ids, index={e: i for i, e in enumerate(ids)}, emb=emb,
        ts=np.array(ts, dtype=np.float64), titles=titles, actors=actors,
        idf={k: 1.0 / v for k, v in df.items()},
    )


def _postings(snap):
    p = defaultdict(list)
    for i, acts in enumerate(snap.actors):
        for a in acts:
            p[a].append(i)
    return p


def test_each_proposer_contributes_independently():
    """The design rests on three signals with different blind spots. If one stops
    contributing, candidates narrow to what the others like and the gold set
    quietly inherits their bias."""
    snap = _snap(
        titles=[
            "Wangchuk begins hunger strike in Leh",
            "Something entirely unrelated about weather",   # embedding-near only
            "Wangchuk hunger strike enters third day",      # title + actors
            "Ladakh statehood talks resume in Delhi",       # actors only
        ],
        actors=[["wangchuk"], [], ["wangchuk"], ["wangchuk"]],
        ts=[BASE, BASE, BASE, BASE],
        vecs=[[1, 0, 0], [0.99, 0.1, 0], [0.9, 0.3, 0], [0.2, 0.9, 0]],
    )
    got = _neighbours(snap, _postings(snap), {}, 0)
    signals = set().union(*(s for _, s in got))
    assert {"embedding", "actors", "title"} <= signals, f"a proposer went silent: {signals}"


def test_the_seed_is_never_its_own_neighbour():
    snap = _snap(
        titles=["A story about something", "Another story about something"],
        actors=[["x"], ["x"]], ts=[BASE, BASE], vecs=[[1, 0, 0], [0.9, 0.1, 0]],
    )
    assert 0 not in {j for j, _ in _neighbours(snap, _postings(snap), {}, 0)}


def test_events_outside_the_window_are_not_proposed():
    """21 days apart is a new story even with an identical headline and cast. The
    window is a constraint, not a signal — a labeller should never be asked to
    adjudicate a pair the product does not claim is related."""
    snap = _snap(
        titles=["Budget session opens in parliament", "Budget session opens in parliament"],
        actors=[["parliament"], ["parliament"]], ts=[BASE, BASE + 40 * DAY],
        vecs=[[1, 0, 0], [1, 0, 0]],
    )
    assert _neighbours(snap, _postings(snap), {}, 0) == []


def test_an_unknown_timestamp_is_not_excluded():
    """Absence of evidence must not cut. An event with no date is not known to be
    far away, and dropping it would silently shrink the sample."""
    snap = _snap(
        titles=["Budget session opens in parliament", "Budget session opens in parliament"],
        actors=[["parliament"], ["parliament"]], ts=[BASE, float("nan")],
        vecs=[[1, 0, 0], [1, 0, 0]],
    )
    assert 1 in {j for j, _ in _neighbours(snap, _postings(snap), {}, 0)}


def test_candidates_agreed_by_more_proposers_come_first():
    """A person's attention is the scarce resource here, so the pair two
    independent signals both suggested belongs at the top of the screen."""
    snap = _snap(
        titles=[
            "Wangchuk begins hunger strike in Leh",
            "Wangchuk hunger strike enters third day",   # title + actors + embedding
            "Unrelated weather warning issued today",    # embedding only
        ],
        actors=[["wangchuk"], ["wangchuk"], []],
        ts=[BASE, BASE, BASE],
        vecs=[[1, 0, 0], [0.95, 0.2, 0], [0.99, 0.05, 0]],
    )
    got = _neighbours(snap, _postings(snap), {}, 0)
    assert len(got[0][1]) >= len(got[-1][1]), "weakest-supported candidate ranked first"
