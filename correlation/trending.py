"""Trending stories: promote hot communities to durable, shareable identities.

Community detection already exists per-event (threads.story_timeline / _story_component).
This module runs a global pass — off the ingest hot path — that:

  detect_trending_communities()   rank events by velocity → group into communities → dedupe
  reconcile_stories()             match communities to existing `stories`, keeping slugs stable

Reconciliation state machine (why /trending/<slug> URLs don't silently change meaning):

    community C (member event-ids)                       existing stories (member sets)
        │  overlap = |C ∩ S| / min(|C|,|S|)
        ▼
    ┌── 0 matches ≥0.6 ──▶ CREATE  (new id + FROZEN slug from cast; status=active)
    ├── 1 match   ≥0.6 ──▶ UPDATE  (merge members, refresh label/velocity; id + slug PERSIST)
    └── ≥2 matches≥0.6 ──▶ MERGE   (keep the OLDEST story; others → merged_into + dormant → URL 301s)

    A story not refreshed by any community this pass, older than DORMANT_AFTER → status='dormant'
    (never deleted, so shared links keep resolving). Slug is frozen; only the label refines.

No LLM. Labels are extractive (top cast). Persistence is EARNED: a community must clear the
min-support gate (>= news sources + members) before it gets a durable story.
"""

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.logging import get_logger
from common.text import slugify
from correlation.threads import _story_component

logger = get_logger(__name__)

# Sort key for a just-created (first_seen=None) story on merge — treat as newest.
_MAX_TS = datetime.max.replace(tzinfo=UTC)

TRENDING_CANDIDATES = 30  # top events to seed communities from
OVERLAP_THRESHOLD = 0.6  # |A∩B| / min(|A|,|B|) to call two member-sets "the same story"
MIN_SUPPORT_SOURCES = 2  # a community earns a durable story only with >= this many news outlets
MIN_SUPPORT_MEMBERS = 2  # ...and >= this many member events
VELOCITY_WINDOW_HOURS = 6  # "recent" coverage window
DORMANT_AFTER_HOURS = 24  # an un-refreshed active story goes dormant after this


def _overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


async def _candidate_events(session: AsyncSession) -> list[dict]:
    """Recent news events ranked by trending signal. Velocity = DISTINCT NEWS source
    slugs added in the window (not raw membership rows — a backfill or one chatty source
    can't fake a trend; CVE/raw feeds excluded)."""
    rows = (
        await session.execute(
            text(
                f"""
                WITH vel AS (
                    SELECT em.event_id,
                           count(DISTINCT s.slug) FILTER (
                               WHERE em.created_at > now() - interval '{VELOCITY_WINDOW_HOURS} hours'
                           ) AS recent_sources,
                           count(DISTINCT s.slug) AS total_sources
                    FROM event_memberships em
                    JOIN articles a ON a.id = em.article_id
                    JOIN raw_items ri ON ri.id = a.raw_item_id
                    JOIN sources s ON s.id = ri.source_id AND s.source_type = 'rss'
                    GROUP BY em.event_id
                )
                SELECT e.id
                FROM events e
                JOIN vel v ON v.event_id = e.id
                WHERE e.sector <> 'cybersecurity' AND e.embedding IS NOT NULL
                  AND v.total_sources >= :min_sources
                ORDER BY (v.recent_sources * 2.0 + v.total_sources)
                         * exp(-0.03 * extract(epoch FROM (now() - e.last_updated_at)) / 86400.0) DESC
                LIMIT :lim
                """
            ),
            {"min_sources": MIN_SUPPORT_SOURCES, "lim": TRENDING_CANDIDATES},
        )
    ).scalars().all()
    return [{"id": str(r)} for r in rows]


async def _community_facts(session: AsyncSession, member_ids: list[str]) -> dict:
    """Aggregate the display + ranking facts for a community from its members."""
    agg = (
        await session.execute(
            text(
                f"""
                SELECT count(DISTINCT s.slug) AS total_sources,
                       count(DISTINCT s.slug) FILTER (
                           WHERE em.created_at > now() - interval '{VELOCITY_WINDOW_HOURS} hours'
                       ) AS recent_sources
                FROM event_memberships em
                JOIN articles a ON a.id = em.article_id
                JOIN raw_items ri ON ri.id = a.raw_item_id
                JOIN sources s ON s.id = ri.source_id AND s.source_type = 'rss'
                WHERE em.event_id = ANY(CAST(:ids AS uuid[]))
                """
            ),
            {"ids": member_ids},
        )
    ).mappings().one()
    cast = (
        await session.execute(
            text(
                """
                SELECT ent.name, count(DISTINCT ee.event_id) n
                FROM event_entities ee
                JOIN entities ent ON ent.id = ee.entity_id AND ent.entity_type IN ('person', 'organization')
                WHERE ee.event_id = ANY(CAST(:ids AS uuid[]))
                GROUP BY ent.name HAVING count(DISTINCT ee.event_id) >= 2
                ORDER BY n DESC LIMIT 8
                """
            ),
            {"ids": member_ids},
        )
    ).scalars().all()
    # Hero = the most-covered, most-recent member (the card's title + image + regions/sector).
    hero = (
        await session.execute(
            text(
                """
                SELECT e.id, e.title, e.sector, e.regions
                FROM events e
                LEFT JOIN (SELECT event_id, count(*) c FROM event_memberships GROUP BY 1) m ON m.event_id = e.id
                WHERE e.id = ANY(CAST(:ids AS uuid[]))
                ORDER BY coalesce(m.c, 0) DESC, e.last_updated_at DESC LIMIT 1
                """
            ),
            {"ids": member_ids},
        )
    ).mappings().first()
    regions = (
        await session.execute(
            text(
                "SELECT DISTINCT r FROM events e, unnest(e.regions) r "
                "WHERE e.id = ANY(CAST(:ids AS uuid[])) AND r IS NOT NULL"
            ),
            {"ids": member_ids},
        )
    ).scalars().all()
    return {
        "cast": list(cast),
        "total_sources": int(agg["total_sources"] or 0),
        "recent_sources": int(agg["recent_sources"] or 0),
        "hero_event_id": str(hero["id"]) if hero else None,
        "hero_title": hero["title"] if hero else None,
        "sector": hero["sector"] if hero else None,
        "regions": sorted(regions),
    }


async def detect_trending_communities(session: AsyncSession) -> list[dict]:
    """Top trending communities, deduped by member-set overlap and gated by min-support.
    Ordered by aggregate signal (recent sources × 2 + total sources) descending."""
    candidates = await _candidate_events(session)
    communities: list[dict] = []
    covered: list[set[str]] = []  # member-sets already claimed by a higher-ranked community
    for cand in candidates:
        members = await _story_component(session, uuid.UUID(cand["id"]))
        mset = {str(m) for m in members}
        if any(_overlap(mset, c) >= OVERLAP_THRESHOLD for c in covered):
            continue  # same story as a higher-ranked candidate
        facts = await _community_facts(session, list(mset))
        # min-support: a real story, not a transient blip.
        if facts["total_sources"] < MIN_SUPPORT_SOURCES or len(mset) < MIN_SUPPORT_MEMBERS:
            continue
        covered.append(mset)
        communities.append({"member_ids": sorted(mset), **facts})
    communities.sort(key=lambda c: c["recent_sources"] * 2 + c["total_sources"], reverse=True)
    return communities


def _label(cast: list[str], hero_title: str | None) -> str:
    return " · ".join(cast[:3]) if cast else (hero_title or "Developing story")


async def _create_story(session: AsyncSession, c: dict) -> str:
    sid = uuid.uuid4()
    label = _label(c["cast"], c["hero_title"])
    # Slug frozen at creation: readable prefix + the id suffix guarantees uniqueness.
    slug = f"{slugify(label)[:48] or 'story'}-{sid.hex[:6]}"
    await session.execute(
        text(
            """
            INSERT INTO stories (id, slug, label, "cast", member_event_ids, hero_event_id,
                                 sector, regions, source_count, velocity, status,
                                 first_seen_at, last_updated_at)
            VALUES (:id, :slug, :label, CAST(:cast AS jsonb), CAST(:members AS jsonb), :hero,
                    :sector, CAST(:regions AS text[]), :sc, :vel, 'active', now(), now())
            """
        ),
        _story_params(sid, slug, label, c),
    )
    return str(sid)


async def _update_story(session: AsyncSession, story_id: str, c: dict) -> None:
    """Refresh members/label/signal; slug + id + first_seen_at are NOT touched."""
    label = _label(c["cast"], c["hero_title"])
    await session.execute(
        text(
            """
            UPDATE stories SET label = :label, "cast" = CAST(:cast AS jsonb),
                   member_event_ids = CAST(:members AS jsonb), hero_event_id = :hero,
                   sector = :sector, regions = CAST(:regions AS text[]),
                   source_count = :sc, velocity = :vel, status = 'active', last_updated_at = now()
            WHERE id = :sid
            """
        ),
        {"sid": story_id, "label": label, **_facts_params(c)},
    )


def _story_params(sid: uuid.UUID, slug: str, label: str, c: dict) -> dict:
    return {"id": str(sid), "slug": slug, "label": label, **_facts_params(c)}


def _facts_params(c: dict) -> dict:
    return {
        "cast": json.dumps(c["cast"]),
        "members": json.dumps(c["member_ids"]),
        "hero": c["hero_event_id"],
        "sector": c["sector"],
        "regions": c["regions"],
        "sc": c["total_sources"],
        "vel": float(c["recent_sources"]),
    }


async def reconcile_stories(session: AsyncSession) -> int:
    """Run the detect → match → create/update/merge → dormant pass. Returns #active stories."""
    communities = await detect_trending_communities(session)
    rows = (
        await session.execute(
            text("SELECT id, member_event_ids, first_seen_at FROM stories WHERE merged_into IS NULL")
        )
    ).mappings().all()
    stories = {
        str(r["id"]): {"members": {str(m) for m in (r["member_event_ids"] or [])}, "first": r["first_seen_at"]}
        for r in rows
    }
    claimed: set[str] = set()
    seen: set[str] = set()
    for c in communities:
        cmembers = set(c["member_ids"])
        matches = [
            sid for sid, s in stories.items()
            if sid not in claimed and _overlap(cmembers, s["members"]) >= OVERLAP_THRESHOLD
        ]
        if not matches:
            sid = await _create_story(session, c)
            stories[sid] = {"members": cmembers, "first": None}
        elif len(matches) == 1:
            sid = matches[0]
            await _update_story(session, sid, c)
            stories[sid]["members"] = cmembers
        else:  # MERGE: oldest survives; younger point at it and go dormant → their URL 301s
            canonical = min(matches, key=lambda x: (stories[x]["first"] or _MAX_TS))
            await _update_story(session, canonical, c)
            stories[canonical]["members"] = cmembers
            for other in matches:
                if other == canonical:
                    continue
                await session.execute(
                    text("UPDATE stories SET merged_into = :into, status = 'dormant', "
                         "last_updated_at = now() WHERE id = :sid"),
                    {"into": canonical, "sid": other},
                )
                claimed.add(other)
            sid = canonical
        claimed.add(sid)
        seen.add(sid)
    # Anything active but not refreshed this pass, past the window → dormant (never deleted).
    await session.execute(
        text(
            f"""
            UPDATE stories SET status = 'dormant', last_updated_at = last_updated_at
            WHERE status = 'active' AND merged_into IS NULL
              AND id <> ALL(CAST(:seen AS uuid[]))
              AND last_updated_at < now() - interval '{DORMANT_AFTER_HOURS} hours'
            """
        ),
        {"seen": list(seen) or ["00000000-0000-0000-0000-000000000000"]},
    )
    logger.info("trending_reconciled", communities=len(communities), active=len(seen))
    return len(seen)
