"""Two page families counted from the record (marketing audit 02, P1-1 and P1-2).

State hubs, /state/<slug>: the records placed in one state or union territory.
Day archives, /feed/<yyyy-mm-dd>: the records Prism first saw on one IST day.

Both are counts, never a ranking: a state's volume is explained by the outlets
with a desk there (printed as the denominator), and a day's by what Prism read
that day. Each asks to be indexed only above a floor of records from two or
more outlets (common/outlets.record_indexable, the record's own rule), so a
thin hub never spends the crawl budget the records need.

A day is dated by the record's `first_seen_at` on the IST clock: Prism's own
clock, stable once set. Dating by the first report's publication scattered
records over 77 days back to 2019 (misdated feeds, backlog) and cost 3.5 s on
production; first-seen puts every record on a day Prism was working.

Whether Prism was READING on a day is not assumed: it is the articles it
fetched (`articles.created_at`). A day with none says so and counts nothing
(DESIGN.md: a figure not counted is never 0). A day read only in part carries
its reading window; a day after which Prism has read nothing is not settled
(reading stopped mid-day on 28 Sep 2026) and does not ask to be indexed.
"""

import datetime as dt
import functools
import re
import time
from collections import Counter
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.entity import indexable_sql, speaker_fold, speaker_keys
from api.routes.events import event_claim_verdicts, group_claims
from api.routes.feed import CVE_ONLY_JSON
from api.routes.serialization import build_feed_item
from api.schemas import FeedItem
from common import outlets
from common.db import get_db
from common.images import placeholders, report_photo_join
from common.lenses import get_lens
from common.outlets import monitored, record_indexable
from common.regions import HUB_STATES, state_slug
from common.subjects import ROOTS
from enrichment.claims import dedupe_sources

router = APIRouter()

# Railway's edge caches nothing (api/cache_headers.py), so the s-maxage headers
# below only help the web's data cache; a direct call to api.readprism.news ran
# the full scans every time (the archive index scans every article, ~0.5 s on
# prod). Each worker keeps a result for CACHE_TTL_S (review 2026-09-29).
# ponytail: in-process, per worker, keyed by path args; bounded because codes
# and days are validated before anything is stored. Redis if workers multiply.
CACHE_TTL_S = 600
_memo: dict[tuple, tuple[float, Any, str | None]] = {}


def ttl_cached(fn):
    """Serve a handler's result from memory for CACHE_TTL_S, replaying the
    Cache-Control it set. Errors (a 404) are never stored."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        response: Response = kwargs["response"]
        key = (fn.__name__, *(v for k, v in sorted(kwargs.items()) if k not in {"response", "db"}))
        now = time.monotonic()
        hit = _memo.get(key)
        if hit and now - hit[0] < CACHE_TTL_S:
            if hit[2]:
                response.headers["Cache-Control"] = hit[2]
            return hit[1]
        value = await fn(*args, **kwargs)
        _memo[key] = (now, value, response.headers.get("Cache-Control"))
        return value

    return wrapper

IST = ZoneInfo("Asia/Kolkata")
# A hub asks to be indexed from this many records from two or more outlets
# placed in the state in the last HUB_WINDOW_DAYS; 15 of 33 passed on 2026-09-29.
HUB_FLOOR = 20
HUB_WINDOW_DAYS = 30
# A day asks to be indexed from this many records from two or more outlets.
DAY_FLOOR = 20
# Reading within this long of both midnights is a whole day's reading; the
# collector polls every five minutes, so a longer silence at an edge is a stop.
EDGE_SLACK = dt.timedelta(hours=1)
# "Quoted in <State> records": speakers checked across this many of the newest
# records, as the entity page checks its newest 60 (api/routes/entity), and
# listed from two records up: one quote is a record's cast, not the state's.
QUOTE_WINDOW = 60
MIN_QUOTED = 2
MAX_SPEAKERS = 8
# The hub lists its newest this-many records from two or more outlets.
HUB_ITEMS = 60
# The day page lists every record from two or more outlets; the busiest day so
# far had 460. A bound, not a page size.
DAY_CAP = 1000
HUB_CACHE = "public, s-maxage=600, stale-while-revalidate=1800"
ARCHIVE_CACHE = "public, s-maxage=3600, stale-while-revalidate=7200"

_HUB_NAMES = dict(HUB_STATES)
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")

# A served record, as the feed serves it: not merged away, from at least one
# report, and not wholly a raw-record feed (api/routes/feed._WINDOW_FILTERS).
_SERVED = """e.merged_into IS NULL
    AND COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) > 0
    AND NOT ((e.projection->'source_slugs') <@ CAST(:cve_only AS jsonb))"""


# ── State hubs ──────────────────────────────────────────────────────────────


@router.get("/api/v1/regions/hubs")
@ttl_cached
async def state_hubs(response: Response, db: AsyncSession = Depends(get_db)):
    """Every hub with its records from two or more outlets in the window, and
    whether that clears the floor: the /state index, the sitemap and the record
    page's region chips read this. In the ISO order, never ranked."""
    response.headers["Cache-Control"] = HUB_CACHE
    rows = (
        await db.execute(
            text(
                f"""
                SELECT DISTINCT e.id, r.code, e.projection->'source_slugs' AS slugs
                FROM events e CROSS JOIN LATERAL unnest(e.regions) AS r(code)
                WHERE r.code = ANY(:codes)
                  AND e.first_seen_at >= now() - make_interval(days => :days)
                  AND COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) >= 2
                  AND {_SERVED}
                """
            ),
            {"codes": list(_HUB_NAMES), "days": HUB_WINDOW_DAYS, "cve_only": CVE_ONLY_JSON},
        )
    ).all()
    reg = await outlets.registry(db)
    multi = Counter(code for _, code, slugs in rows if record_indexable(slugs or [], reg))
    return {
        "floor": HUB_FLOOR,
        "window_days": HUB_WINDOW_DAYS,
        "states": [
            {
                "code": c,
                "name": n,
                "slug": state_slug(n),
                "multi_outlet": multi[c],
                "indexable": multi[c] >= HUB_FLOOR,
            }
            for c, n in HUB_STATES
        ],
    }


@router.get("/api/v1/regions/{code}")
@ttl_cached
async def state_hub(code: str, response: Response, db: AsyncSession = Depends(get_db)):
    """One hub over the window: records placed in the state, those from two or
    more outlets (the newest HUB_ITEMS of them as rows, most outlets first),
    their subjects and languages, the outlets with a desk in the state (the
    denominator), and who is quoted in them. Its one-source rows come from
    /api/v1/feed?scope=region, which filters in SQL."""
    name = _HUB_NAMES.get(code)
    if name is None:
        raise HTTPException(status_code=404, detail="no such state")
    response.headers["Cache-Control"] = HUB_CACHE
    rows = (
        (
            await db.execute(
                text(
                    # The state and the window first: the projection is TOASTed,
                    # and unpacking it for every event is most of a scan's cost.
                    f"""
                WITH placed AS MATERIALIZED (
                    SELECT e.id, e.subject_path, e.first_seen_at, e.merged_into, e.projection FROM events e
                    WHERE :code = ANY(e.regions) AND e.first_seen_at >= now() - make_interval(days => :days)
                )
                SELECT e.id, e.subject_path, e.projection->'source_slugs' AS slugs,
                       e.projection->'languages' AS langs
                FROM placed e
                WHERE {_SERVED}
                ORDER BY e.first_seen_at DESC
                """
                ),
                {"code": code, "days": HUB_WINDOW_DAYS, "cve_only": CVE_ONLY_JSON},
            )
        )
        .mappings()
        .all()
    )
    reg = await outlets.registry(db)
    multi = [r for r in rows if record_indexable(r["slugs"] or [], reg)]
    roots = Counter((r["subject_path"] or "").split(".")[0] for r in multi)
    langs = Counter(lang for r in multi for lang in set(r["langs"] or []))
    feeds = [f for f in (await monitored(db)).feeds if f.state == code]
    desks = list(
        {
            f.publisher: {"publisher": f.publisher, "name": f.name, "language": f.language}
            for f in reversed(feeds)
        }.values()
    )
    slug = state_slug(name)
    qid = (
        await db.execute(text("SELECT qid FROM entities WHERE slug = :s"), {"s": slug})
    ).scalar_one_or_none()
    window = [str(r["id"]) for r in multi[:QUOTE_WINDOW]]
    return {
        "code": code,
        "name": name,
        "slug": slug,
        "qid": qid,
        "window_days": HUB_WINDOW_DAYS,
        "floor": HUB_FLOOR,
        "records": len(rows),
        "multi_outlet": len(multi),
        "indexable": len(multi) >= HUB_FLOOR,
        "subjects": [{"root": root, "count": roots[root]} for root in ROOTS if roots[root]],
        "languages": [lang for lang, _ in sorted(langs.items(), key=lambda kv: (-kv[1], kv[0]))],
        "desks": sorted(desks, key=lambda d: d["name"]),
        "speakers": await _speakers(db, window),
        "speakers_window": len(window),
        "items": [
            i.model_dump()
            for i in by_outlets(
                await _feed_items(db, [str(r["id"]) for r in multi[:HUB_ITEMS]], reg)
            )
        ],
    }


async def _feed_items(db: AsyncSession, ids: list[str], reg: dict) -> list[FeedItem]:
    """The feed's rows for these records, with their report photographs."""
    if not ids:
        return []
    rows = (
        (
            await db.execute(
                text(
                    f"""
                SELECT e.id, e.title, e.summary, e.sector, e.subsector, e.subject_path, e.regions,
                       img.image_url AS image_url, e.projection, e.last_updated_at, e.occurred_at,
                       img.slug AS image_source_slug
                FROM events e
                {report_photo_join("e")}
                WHERE e.id = ANY(CAST(:ids AS uuid[]))
                """
                ),
                {"ids": ids, "placeholders": list(await placeholders(db))},
            )
        )
        .mappings()
        .all()
    )
    lens = get_lens(None)
    return [build_feed_item(r, lens, None, None, reg) for r in rows]


def by_outlets(items: list[FeedItem]) -> list[FeedItem]:
    """Most outlets first (mastheads, as the row counts them), then newest."""
    newest = sorted(items, key=lambda i: i.last_updated_at, reverse=True)
    return sorted(
        newest, key=lambda i: len({o.publisher for o in i.outlets}) or i.source_count, reverse=True
    )


# Every report of the given records with its stored claims, as the story page
# reads them (api/routes/entity._QUOTED_RECORD_SOURCES); the text only where
# there are claims to check against it.
_RECORD_SOURCES = text(
    """
    SELECT em.event_id, a.id AS article_id, src.name AS source_name, ri.url, ri.url_canonical,
           ri.published_at, ri.language AS lang, c.claims,
           CASE WHEN jsonb_array_length(c.claims) > 0 THEN a.clean_text END AS clean_text
    FROM event_memberships em
    JOIN articles a ON a.id = em.article_id
    JOIN raw_items ri ON ri.id = a.raw_item_id
    JOIN sources src ON src.id = ri.source_id
    LEFT JOIN enrichments en ON en.article_id = a.id
    CROSS JOIN LATERAL (SELECT CASE WHEN jsonb_typeof(en.shared_fields -> 'claims') = 'array'
                                    THEN en.shared_fields -> 'claims' END AS claims) c
    WHERE em.event_id = ANY(CAST(:ids AS uuid[]))
    ORDER BY em.event_id, ri.published_at DESC NULLS LAST, a.id
    """
)


async def _speakers(db: AsyncSession, event_ids: list[str]) -> list[dict[str, Any]]:
    """Who is quoted, word for word, in these records: the entities named in a
    record whose name (or a full alias) is the speaker of a direct quote the
    story page would print there, with the records each is quoted in. The
    checks are the story page's own (group_claims), so this cannot count a
    quote its record would not print."""
    if not event_ids:
        return []
    sources: dict[str, list] = {}
    for r in (await db.execute(_RECORD_SOURCES, {"ids": event_ids})).mappings().all():
        sources.setdefault(str(r["event_id"]), []).append(r)
    cast: dict[str, list] = {}
    for r in (
        (
            await db.execute(
                text(
                    "SELECT ee.event_id, en.slug, en.name, en.aliases FROM event_entities ee "
                    "JOIN entities en ON en.id = ee.entity_id WHERE ee.event_id = ANY(CAST(:ids AS uuid[]))"
                ),
                {"ids": event_ids},
            )
        )
        .mappings()
        .all()
    ):
        cast.setdefault(str(r["event_id"]), []).append(
            (r["slug"], r["name"], speaker_keys(r["name"], r["aliases"]))
        )
    quoted: Counter[str] = Counter()
    names: dict[str, str] = {}
    for eid, rows in sources.items():
        said = {
            speaker_fold(g.speaker)
            for g in group_claims(dedupe_sources(rows), await event_claim_verdicts(db, eid))
            if any(c.speech == "direct" for c in g.claims)
        }
        for slug, name, keys in cast.get(eid, []):
            if keys & said:
                quoted[slug] += 1
                names[slug] = name
    top = sorted(
        ((s, n) for s, n in quoted.items() if n >= MIN_QUOTED),
        key=lambda kv: (-kv[1], names[kv[0]]),
    )[:MAX_SPEAKERS]
    if not top:
        return []
    indexable = dict(
        (
            await db.execute(
                text(
                    f"SELECT en.slug, {indexable_sql('en.id')} FROM entities en WHERE en.slug = ANY(:s)"
                ),
                {"s": [slug for slug, _ in top]},
            )
        ).all()
    )
    return [
        {"slug": s, "name": names[s], "records": n, "indexable": bool(indexable.get(s))}
        for s, n in top
    ]


# ── Day archive ─────────────────────────────────────────────────────────────


EARLIEST_DAY = dt.date(2000, 1, 1)  # far before any read; only a guard on the date arithmetic


def ist_today(now: dt.datetime | None = None) -> dt.date:
    return (now or dt.datetime.now(dt.UTC)).astimezone(IST).date()


def day_bounds(day: dt.date) -> tuple[dt.datetime, dt.datetime]:
    """Midnight to midnight, IST, as instants."""
    start = dt.datetime.combine(day, dt.time(), IST)
    return start, start + dt.timedelta(days=1)


def parse_day(value: str) -> dt.date | None:
    """A strict yyyy-mm-dd, else None: /feed/2026-9-27 and /feed/2026-02-30 are 404s."""
    if not _DAY.fullmatch(value):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def reading(
    day: dt.date, first: dt.datetime | None, last: dt.datetime | None, read_after: bool
) -> dict[str, Any]:
    """What Prism read on the day, from the articles it fetched then: nothing
    (not read), part of it (the window), or all of it; and whether it has read
    since (settled). An unsettled day can still gain records."""
    if first is None or last is None:
        return {
            "read": False,
            "whole_day": False,
            "read_from": None,
            "read_to": None,
            "settled": read_after,
        }
    start, end = day_bounds(day)
    return {
        "read": True,
        "whole_day": first - start <= EDGE_SLACK and end - last <= EDGE_SLACK,
        "read_from": first.isoformat(),
        "read_to": last.isoformat(),
        "settled": read_after,
    }


def day_indexable(status: dict[str, Any], multi_outlet: int | None) -> bool:
    """Read, settled, and at the floor: a day Prism did not read, or stopped
    reading in, never asks to be indexed, whatever it holds."""
    return bool(
        status["read"]
        and status["settled"]
        and multi_outlet is not None
        and multi_outlet >= DAY_FLOOR
    )


@router.get("/api/v1/archive")
@ttl_cached
async def archive_index(response: Response, db: AsyncSession = Depends(get_db)):
    """Every day from the first Prism read to yesterday (IST), newest first:
    its reading and, for a day it read, its records and those from two or more
    outlets. A day it did not read carries no counts at all."""
    response.headers["Cache-Control"] = ARCHIVE_CACHE
    read_rows = (
        await db.execute(
            text(
                "SELECT (created_at AT TIME ZONE 'Asia/Kolkata')::date AS day, min(created_at), max(created_at) "
                "FROM articles GROUP BY 1"
            )
        )
    ).all()
    today = ist_today()
    if not read_rows:
        return {"first_day": None, "today": today.isoformat(), "floor": DAY_FLOOR, "days": []}
    read = {d: (first, last) for d, first, last in read_rows}
    last_read = max(last for _, last in read.values())
    # Records per first-seen day; only a record with two or more slugs can be
    # from two or more outlets, so only those carry their slugs out.
    rec_rows = (
        await db.execute(
            text(
                f"""
                SELECT (e.first_seen_at AT TIME ZONE 'Asia/Kolkata')::date AS day,
                       CASE WHEN jsonb_array_length(e.projection->'source_slugs') >= 2
                            THEN e.projection->'source_slugs' END AS slugs
                FROM events e WHERE {_SERVED}
                """
            ),
            {"cve_only": CVE_ONLY_JSON},
        )
    ).all()
    reg = await outlets.registry(db)
    served: Counter[dt.date] = Counter(d for d, _ in rec_rows)
    multi: Counter[dt.date] = Counter(
        d for d, slugs in rec_rows if slugs and record_indexable(slugs, reg)
    )
    first_day = min(read)
    days = []
    day = today - dt.timedelta(days=1)
    while day >= first_day:
        first, last = read.get(day, (None, None))
        status = reading(day, first, last, last_read >= day_bounds(day)[1])
        k = multi[day] if status["read"] else None
        days.append(
            {
                "date": day.isoformat(),
                **status,
                "records": served[day] if status["read"] else None,
                "multi_outlet": k,
                "indexable": day_indexable(status, k),
            }
        )
        day -= dt.timedelta(days=1)
    return {
        "first_day": first_day.isoformat(),
        "today": today.isoformat(),
        "floor": DAY_FLOOR,
        "days": days,
    }


@router.get("/api/v1/archive/{day}")
@ttl_cached
async def archive_day(day: str, response: Response, db: AsyncSession = Depends(get_db)):
    """One IST day: its reading, the records first seen on it from two or
    more outlets (listed, most outlets first), the rest counted, and the read
    days either side. 404 for a malformed date, a day before Prism first read,
    today (the web sends it to /feed) and after."""
    when = parse_day(day)
    # Bounded before any arithmetic: 9999-12-31 + 1 day overflowed into a 500.
    if when is None or when < EARLIEST_DAY or when >= ist_today():
        raise HTTPException(status_code=404, detail="not a date in the archive")
    start, end = day_bounds(when)
    agg = (
        (
            await db.execute(
                text(
                    """
                SELECT min(created_at) AS first_ever,
                       min(created_at) FILTER (WHERE created_at >= :start AND created_at < :end) AS first,
                       max(created_at) FILTER (WHERE created_at >= :start AND created_at < :end) AS last,
                       max(created_at) FILTER (WHERE created_at < :start) AS prev_read,
                       min(created_at) FILTER (WHERE created_at >= :end) AS next_read
                FROM articles
                """
                ),
                {"start": start, "end": end},
            )
        )
        .mappings()
        .one()
    )
    today = ist_today()
    if (
        agg["first_ever"] is None
        or when < agg["first_ever"].astimezone(IST).date()
        or when >= today
    ):
        raise HTTPException(status_code=404, detail="no such day in the archive")
    response.headers["Cache-Control"] = ARCHIVE_CACHE
    status = reading(when, agg["first"], agg["last"], agg["next_read"] is not None)
    after = agg["next_read"].astimezone(IST).date() if agg["next_read"] else None
    out: dict[str, Any] = {
        "date": when.isoformat(),
        **status,
        "floor": DAY_FLOOR,
        "prev": agg["prev_read"].astimezone(IST).date().isoformat() if agg["prev_read"] else None,
        # The next day Prism read; today's is /feed, not an archive page.
        "next": after.isoformat() if after and after < today else None,
        "next_is_today": bool(after and after >= today),
        "records": None,
        "multi_outlet": None,
        "single_source": None,
        "languages": None,
        "indexable": False,
        "items": [],
    }
    if not status["read"]:
        return out
    rows = (
        await db.execute(
            text(
                f"""
                SELECT e.id, e.projection->'source_slugs' AS slugs FROM events e
                WHERE e.first_seen_at >= :start AND e.first_seen_at < :end AND {_SERVED}
                """
            ),
            {"start": start, "end": end, "cve_only": CVE_ONLY_JSON},
        )
    ).all()
    reg = await outlets.registry(db)
    listed = [str(i) for i, slugs in rows if record_indexable(slugs or [], reg)]
    items = by_outlets(await _feed_items(db, listed, reg))
    langs = {lang for i in items for lang in i.available_languages}
    out.update(
        records=len(rows),
        multi_outlet=len(listed),
        single_source=len(rows) - len(listed),
        languages=len(langs),
        indexable=day_indexable(status, len(listed)),
        items=[i.model_dump() for i in items[:DAY_CAP]],
    )
    return out
