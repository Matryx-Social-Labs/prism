"""Which story a post is about.

Two ways in. (1) The post links an article we already hold: the URL, canonical,
resolves through raw_items → articles → event_memberships to the event — exact,
no model, method `url`. (2) The post's embedding is near the event's (one index
scan on events.embedding) AND it names one of the event's rarer cast or two of
the headline's words, and a model reading both says `event` — the chain
podcasts/match.py measured, method `judge`.

Every run rematches the last HOLD hours of posts, not just the new ones: an
official post often precedes the outlets' reports by hours, and the story it
belongs to may not exist yet when the post arrives. The verdict cache makes the
second look free. Nothing here is a membership; a post counts toward nothing.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from common.logging import get_logger
from common.urls import canonicalize_url
from podcasts.match import (
    AFTER,
    BEFORE,
    COMMON_ENTITY_DF,
    MAGNET_STORIES,
    PREVIEW_GRACE,
    TITLE_WORDS,
    TOP_BAND,
    entity_hits,
    is_preview,
    title_hits,
)
from xposts.judge import judge_pairs

logger = get_logger(__name__)

HOLD = 72  # hours a post waits for its story
CANDIDATES = 8
POSTS_PER_EVENT = 4


@dataclass
class Hit:
    event_id: uuid.UUID
    post_id: str
    handle: str
    score: float
    method: str  # url | judge
    story: str = ""


def one_per_story(hits: list[Hit]) -> list[Hit]:
    """A post backs at most one event per story: the best-scoring one. Pure; tested."""
    best: dict[tuple[str, str], Hit] = {}
    for h in hits:
        k = (h.post_id, h.story)
        if k not in best or h.score > best[k].score:
            best[k] = h
    return list(best.values())


def cap_per_event(hits: list[Hit], limit: int = POSTS_PER_EVENT) -> dict[uuid.UUID, list[Hit]]:
    """Best `limit` posts per event, one per account (PIB posts the Hindi twin
    of every English release). Pure; tested."""
    per_event: dict[uuid.UUID, list[Hit]] = {}
    for h in sorted(hits, key=lambda h: (-h.score, h.post_id)):
        lst = per_event.setdefault(h.event_id, [])
        if len(lst) < limit and all(x.handle != h.handle for x in lst):
            lst.append(h)
    return per_event


async def match_recent(hours: int = HOLD) -> int:
    """Rematch every live post of the last `hours` and rewrite event_x_posts
    for them. Idempotent: a whole recompute, small enough for the ten-minute run."""
    min_cos = get_settings().prism_x_min_cos
    since = datetime.now(UTC) - timedelta(hours=hours)
    async with session_scope() as s:
        total = (await s.execute(text("SELECT count(*) FROM events WHERE last_updated_at > now() - interval '30 days'"))).scalar() or 1
        common = {
            r[0] for r in (await s.execute(text(
                """
                SELECT en.name FROM event_entities ee JOIN entities en ON en.id = ee.entity_id
                JOIN events e ON e.id = ee.event_id
                WHERE e.last_updated_at > now() - interval '30 days'
                GROUP BY en.name HAVING count(DISTINCT ee.event_id) > :floor
                """
            ), {"floor": total * COMMON_ENTITY_DF})).all()
        }
        posts = (await s.execute(text(
            """
            SELECT post_id, handle, text, created_at, urls, embedding::text AS vec
            FROM x_posts WHERE created_at > :since AND deleted_at IS NULL ORDER BY created_at
            """
        ), {"since": since})).mappings().all()
        hits: list[Hit] = []
        for p in posts:
            cands: dict[uuid.UUID, dict] = {}
            urls = [c for c in (canonicalize_url(u) for u in (p["urls"] or [])) if c]
            if urls:
                for r in (await s.execute(text(
                    """
                    SELECT DISTINCT em.event_id AS id, e.title, e.first_seen_at
                    FROM raw_items ri JOIN articles a ON a.raw_item_id = ri.id
                    JOIN event_memberships em ON em.article_id = a.id JOIN events e ON e.id = em.event_id
                    WHERE ri.url_canonical = ANY(:urls)
                    """
                ), {"urls": urls})).mappings().all():
                    cands[r["id"]] = {"title": r["title"], "cos": 1.0, "method": "url"}
            near: list = []
            if p["vec"]:
                near = (await s.execute(text(
                    """
                    SELECT e.id, e.title, e.first_seen_at, 1 - (e.embedding <=> CAST(:vec AS vector)) AS cos
                    FROM events e
                    WHERE e.embedding IS NOT NULL
                      AND e.last_updated_at > :lo AND e.first_seen_at < :hi
                    ORDER BY e.embedding <=> CAST(:vec AS vector)
                    LIMIT :k
                    """
                ), {"vec": p["vec"], "lo": p["created_at"] - BEFORE, "hi": p["created_at"] + AFTER, "k": CANDIDATES})).mappings().all()
                near = [
                    c for c in near
                    if float(c["cos"]) >= min_cos and c["id"] not in cands
                    and not (is_preview(c["title"]) and p["created_at"] - c["first_seen_at"] > PREVIEW_GRACE)
                ]
                if near:
                    best = max(float(c["cos"]) for c in near)
                    near = [c for c in near if float(c["cos"]) >= best - TOP_BAND]
            if not cands and not near:
                continue
            ids = list(cands) + [c["id"] for c in near]
            stories = (await s.execute(text(
                "SELECT slug, member_event_ids FROM stories WHERE merged_into IS NULL AND member_event_ids ?| CAST(:ids AS text[])"
            ), {"ids": [str(i) for i in ids]})).all()
            story_of: dict[str, str] = {}
            for slug, members in stories:
                for m in members or []:
                    story_of.setdefault(str(m), slug)
            # A post near many stories at once is about a theme, not a happening.
            if len({story_of.get(str(c["id"]), str(c["id"])) for c in near}) > MAGNET_STORIES:
                near = []
            if near:
                names = (await s.execute(text(
                    "SELECT ee.event_id, en.name FROM event_entities ee JOIN entities en ON en.id = ee.entity_id WHERE ee.event_id = ANY(:ids)"
                ), {"ids": [c["id"] for c in near]})).all()
                cast: dict[uuid.UUID, list[str]] = {}
                for eid, name in names:
                    if name not in common:
                        cast.setdefault(eid, []).append(name)
                for c in near:
                    if entity_hits(p["text"], cast.get(c["id"], [])) or title_hits(p["text"], c["title"]) >= TITLE_WORDS:
                        cands[c["id"]] = {"title": c["title"], "cos": float(c["cos"]), "method": "judge"}
            for eid, c in cands.items():
                hits.append(Hit(eid, p["post_id"], p["handle"], c["cos"], c["method"], story_of.get(str(eid), str(eid))))
        # The judge reads both texts for the embedding tier; a link needs no judge.
        verdicts = await judge_pairs(s, [(h.event_id, h.post_id) for h in hits if h.method == "judge"])
        hits = one_per_story([h for h in hits if h.method == "url" or verdicts.get((h.event_id, h.post_id)) == "event"])
        per_event = cap_per_event(hits)
        await s.execute(text(
            "DELETE FROM event_x_posts ep USING x_posts p WHERE ep.post_id = p.post_id AND p.created_at > :since"
        ), {"since": since})
        written = 0
        for eid, lst in per_event.items():
            for rank, h in enumerate(lst):
                await s.execute(text(
                    "INSERT INTO event_x_posts (event_id, post_id, method, score, rank) VALUES (:e, :p, :m, :sc, :r) "
                    "ON CONFLICT (event_id, post_id) DO UPDATE SET method = EXCLUDED.method, score = EXCLUDED.score, rank = EXCLUDED.rank"
                ), {"e": eid, "p": h.post_id, "m": h.method, "sc": round(h.score, 4), "r": rank})
                written += 1
    logger.info("x_matched", posts=len(posts), attached=written, events=len(per_event), min_cos=min_cos)
    return written
