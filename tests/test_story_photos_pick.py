"""A story's photo pick: the early stop must pick exactly what a full scan picks,
and stop. A full scan compares every photo with every one kept: 17.7M hamming
calls and 10s on a 3,699-record story, every /trending request (2026-10-16)."""

import random

import common.imagehash
from api.routes.trending import _pick_photos
from common.imagehash import hamming


def _full_scan(cands, publisher, limit):
    """The pick as it was before the early stop: every photo, then the split."""
    seen, hashes, picked = set(), [], []
    for r in cands:
        if r["image_url"] in seen:
            continue
        h = r["image_phash"]
        if h and any(hamming(h, x) <= 8 for x in hashes):
            continue
        seen.add(r["image_url"])
        if h:
            hashes.append(h)
        picked.append(r)
    first, lead, rest = set(), [], []
    for r in picked:
        pub = publisher(r)
        (rest if pub in first else lead).append(r)
        first.add(pub)
    return (lead + rest)[:limit]


def _cands(rng, n, n_publishers):
    base = [rng.getrandbits(64) for _ in range(max(1, n // 4))]
    out = []
    for i in range(n):
        h = rng.choice(base) ^ (1 << rng.randrange(64)) if rng.random() < 0.5 else rng.getrandbits(64)
        out.append({
            "image_url": f"u{rng.randrange(n)}" if rng.random() < 0.2 else f"u{i}",
            "image_phash": None if rng.random() < 0.15 else f"{h:016x}",
            "source_slug": f"s{rng.randrange(n_publishers)}",
        })
    return out


def _publisher(r):
    return r["source_slug"][:2]  # s1x sources share a publisher, like BBC's editions


def test_the_early_stop_picks_exactly_what_a_full_scan_picks():
    rng = random.Random(7)
    for _ in range(400):
        cands = _cands(rng, rng.randrange(0, 60), rng.randrange(1, 15))
        for limit in (1, 3, 8, 20):
            assert _pick_photos(cands, _publisher, limit) == _full_scan(cands, _publisher, limit)


def test_a_big_story_stops_scanning_once_the_pick_is_settled(monkeypatch):
    calls = 0

    def counting(a, b):
        nonlocal calls
        calls += 1
        return hamming(a, b)

    monkeypatch.setattr(common.imagehash, "hamming", counting)
    cands = _cands(random.Random(1), 6000, 40)
    picked = _pick_photos(cands, _publisher, 8)
    assert len(picked) == 8
    # A full scan of these 6,000 makes 6,578,718 calls; the early stop makes 2,346.
    assert calls < 10_000, f"{calls} hamming calls for 8 photos"
