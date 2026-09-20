"""Which story a transcript window is about.

Two signals, both required: the window's embedding is near the event's (one
index scan on events.embedding, the vectors the events already carry) AND the
window names at least one of the event's cast — the entity check that keeps
"same topic" (another day's iPhone story) from passing as "same story". Then
consecutive matched windows of one episode merge into one clip of at most
CLIP_MAX_S, and each event keeps its best CLIPS_PER_EVENT, one per episode.

The threshold is a setting, calibrated on gold_clips (tools/gold_clips.py):
nothing here is shown until that gate reads ≥ 0.9.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from common.logging import get_logger

logger = get_logger(__name__)

CLIP_MAX_S = 90.0
CLIPS_PER_EVENT = 4
CANDIDATES = 8
# A window can only be about a story reported around when the episode aired.
BEFORE = timedelta(hours=72)
AFTER = timedelta(hours=72)


@dataclass
class Hit:
    event_id: uuid.UUID
    window_id: uuid.UUID
    episode_id: uuid.UUID
    seq: int
    start_s: float
    end_s: float
    score: float
    entity_hits: int


def entity_hits(window_text: str, names: list[str]) -> int:
    """How many of the event's cast the window names, whole-word, case-insensitive.
    Names under four letters (a party's initials) only count in upper case as written."""
    low = window_text.casefold()
    n = 0
    for name in names:
        name = name.strip()
        if len(name) < 3:
            continue
        pat = r"(?<!\w)" + re.escape(name if len(name) < 4 else name.casefold()) + r"(?!\w)"
        if re.search(pat, window_text if len(name) < 4 else low):
            n += 1
    return n


def merge_runs(hits: list[Hit]) -> list[Hit]:
    """Consecutive windows of one episode matched to one event become one clip,
    capped at CLIP_MAX_S from the run's best window outward. Pure; tested."""
    by: dict[tuple[uuid.UUID, uuid.UUID], list[Hit]] = {}
    for h in hits:
        by.setdefault((h.event_id, h.episode_id), []).append(h)
    out: list[Hit] = []
    for run_hits in by.values():
        run_hits.sort(key=lambda h: h.seq)
        run: list[Hit] = []
        for h in run_hits + [None]:  # type: ignore[list-item]
            if h is not None and (not run or h.seq == run[-1].seq + 1):
                run.append(h)
                continue
            if run:
                best = max(run, key=lambda x: x.score)
                lo = hi = run.index(best)
                # Grow around the best window while the clip stays under the cap.
                while True:
                    grew = False
                    if lo > 0 and run[hi].end_s - run[lo - 1].start_s <= CLIP_MAX_S:
                        lo -= 1
                        grew = True
                    if hi < len(run) - 1 and run[hi + 1].end_s - run[lo].start_s <= CLIP_MAX_S:
                        hi += 1
                        grew = True
                    if not grew:
                        break
                out.append(Hit(best.event_id, best.window_id, best.episode_id, best.seq, run[lo].start_s, run[hi].end_s, best.score, max(x.entity_hits for x in run[lo:hi + 1])))
            run = [h] if h is not None else []
    return out


async def match_recent(hours: int = 96) -> int:
    """Rematch every window from episodes published in the last `hours` against
    the events around them, and rewrite event_clips for the events touched.
    Idempotent: a whole recompute, small enough to run hourly (≈400 windows)."""
    min_cos = get_settings().prism_clip_min_cos
    since = datetime.now(UTC) - timedelta(hours=hours)
    async with session_scope() as s:
        wins = (await s.execute(text(
            """
            SELECT w.id, w.episode_id, w.seq, w.start_s, w.end_s, w.text, w.embedding::text AS vec, e.published_at
            FROM podcast_windows w JOIN podcast_episodes e ON e.id = w.episode_id
            WHERE e.published_at > :since AND w.embedding IS NOT NULL
            ORDER BY e.published_at, w.seq
            """
        ), {"since": since})).mappings().all()
        hits: list[Hit] = []
        for w in wins:
            cands = (await s.execute(text(
                """
                SELECT e.id, 1 - (e.embedding <=> CAST(:vec AS vector)) AS cos
                FROM events e
                WHERE e.embedding IS NOT NULL
                  AND e.last_updated_at > :lo AND e.first_seen_at < :hi
                ORDER BY e.embedding <=> CAST(:vec AS vector)
                LIMIT :k
                """
            ), {"vec": w["vec"], "lo": w["published_at"] - BEFORE, "hi": w["published_at"] + AFTER, "k": CANDIDATES})).mappings().all()
            cands = [c for c in cands if float(c["cos"]) >= min_cos]
            if not cands:
                continue
            names = (await s.execute(text(
                "SELECT ee.event_id, en.name FROM event_entities ee JOIN entities en ON en.id = ee.entity_id WHERE ee.event_id = ANY(:ids)"
            ), {"ids": [c["id"] for c in cands]})).all()
            cast: dict[uuid.UUID, list[str]] = {}
            for eid, name in names:
                cast.setdefault(eid, []).append(name)
            for c in cands:
                n = entity_hits(w["text"], cast.get(c["id"], []))
                if n:
                    hits.append(Hit(c["id"], w["id"], w["episode_id"], w["seq"], float(w["start_s"]), float(w["end_s"]), float(c["cos"]), n))
        clips = merge_runs(hits)
        # Best CLIPS_PER_EVENT per event, one per episode.
        per_event: dict[uuid.UUID, list[Hit]] = {}
        for h in sorted(clips, key=lambda h: -h.score):
            lst = per_event.setdefault(h.event_id, [])
            if len(lst) < CLIPS_PER_EVENT and all(x.episode_id != h.episode_id for x in lst):
                lst.append(h)
        touched = list(per_event)
        # Rewrite clips for every event that could have been touched by this window set.
        await s.execute(text(
            "DELETE FROM event_clips ec USING podcast_windows w JOIN podcast_episodes e ON e.id = w.episode_id "
            "WHERE ec.window_id = w.id AND e.published_at > :since"
        ), {"since": since})
        written = 0
        for eid, lst in per_event.items():
            for rank, h in enumerate(lst):
                await s.execute(text(
                    "INSERT INTO event_clips (event_id, window_id, start_s, end_s, score, entity_hits, rank) "
                    "VALUES (:e, :w, :s, :t, :sc, :n, :r) ON CONFLICT (event_id, window_id) DO UPDATE SET "
                    "start_s = EXCLUDED.start_s, end_s = EXCLUDED.end_s, score = EXCLUDED.score, entity_hits = EXCLUDED.entity_hits, rank = EXCLUDED.rank"
                ), {"e": eid, "w": h.window_id, "s": h.start_s, "t": h.end_s, "sc": round(h.score, 4), "n": h.entity_hits, "r": rank})
                written += 1
    logger.info("podcast_matched", windows=len(wins), hits=len(hits), clips=written, events=len(touched), min_cos=min_cos)
    return written
