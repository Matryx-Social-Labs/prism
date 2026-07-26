"""Feed route: the personalized, lens-ranked event list."""

import json

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.serialization import build_feed_item
from api.schemas import FeedItem, FeedResponse
from common.db import get_db
from common.lenses import get_lens
from common.taxonomy import TAXONOMY

router = APIRouter()

# Feeds that publish raw database records rather than journalism. An event
# sourced WHOLLY from these is a record; one that also carries a newsroom slug is
# real coverage. Declared once — the SQL and the JSON form have to agree, and
# when they drifted the window quotaed one set of rows while the filter dropped
# another.
CVE_ONLY_SOURCES = frozenset({"nvd", "cisa_kev"})
CVE_ONLY_JSON = json.dumps(sorted(CVE_ONLY_SOURCES))


@router.get("/api/v1/feed", response_model=FeedResponse)
async def get_feed(
    lens: str | None = None,
    sector: str | None = None,
    interests: str | None = None,
    region: str | None = None,
    state: str | None = None,  # ISO 3166-2 (e.g. IN-KA) — surfaces the reader's state first
    languages: str | None = None,  # comma-sep, preference order; ranks + localises (never filters)
    sort: str = "latest",
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    active_lens = get_lens(lens)
    langs = [c.strip() for c in (languages or "").split(",") if c.strip()] or None
    # Interest pairs from the profile: "sports:cricket,politics,technology:ai".
    # A bare sector means the whole sector; explicit ?sector= wins over both.
    interest_pairs: dict[str, set[str]] = {}
    for token in (interests or "").split(","):
        token = token.strip()
        if not token:
            continue
        sec, _, sub = token.partition(":")
        if sec not in TAXONOMY:
            continue
        interest_pairs.setdefault(sec, set())
        if sub and sub in TAXONOMY[sec]:
            interest_pairs[sec].add(sub)
    if sector:
        # An explicit ?sector= is the reader asking for exactly that — honour it.
        sectors = [sector]
    elif interest_pairs:
        sectors = list(interest_pairs)
    else:
        # NOT active_lens.sectors. A lens is a way of RE-READING the world, not a
        # filter that shrinks it: the cyber lens declares sectors=["cybersecurity"],
        # so this line turned the entire feed into a cybersecurity-only feed for a
        # signed-in cyber reader — no elections, no markets, no world news at all.
        #
        # The lens still shapes the feed through score_event()'s RankingWeights
        # (severity, exploited, price_impact), which is the right lever: it moves
        # relevant stories UP without making everything else disappear. Raw CVE
        # records are still gated separately by include_cve_records below.
        #
        # Same principle already settled for languages: hard-filtering a news feed
        # hides major events from the reader entirely. Rank, don't filter; leave
        # hard filters to explicit user action.
        sectors = None
    # Candidate window is per-sector so a high-churn sector (thousands of
    # CVE updates a day) can't evict everyone else's news before ranking.
    #
    # Raw records are excluded HERE rather than in Python afterwards. The
    # cybersecurity corpus is 5.6k records against ~70 real stories, so a window
    # ranked on recency alone came back 120/120 record: the general lens dropped
    # every one and showed zero cybersecurity, while the cyber lens kept them and
    # showed a changelog with no journalism in it. Filtering in the WHERE keeps
    # the news quota real while leaving PARTITION BY on the bare column, so this
    # still rides ix_events_sector_last_updated — putting the record test in the
    # PARTITION BY instead cost an index scan and spilled ~10MB of temp files per
    # request (measured: 5ms index scan → 29ms parallel seq scan + external merge).
    rows = (
        await db.execute(
            text(
                """
                SELECT id, title, summary, sector, subsector, regions, image_url,
                       projection, last_updated_at, occurred_at
                FROM (
                    SELECT e.*, ROW_NUMBER() OVER (
                        PARTITION BY e.sector ORDER BY e.last_updated_at DESC
                    ) AS rn
                    FROM events e
                    WHERE (CAST(:sectors AS text[]) IS NULL
                           OR e.sector = ANY(CAST(:sectors AS text[])))
                      AND NOT (
                          COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) > 0
                          AND (e.projection->'source_slugs') <@ CAST(:cve_only AS jsonb)
                      )
                ) windowed
                WHERE rn <= 120
                """
            ),
            {"sectors": sectors or None, "cve_only": CVE_ONLY_JSON},
        )
    ).mappings().all()

    items: list[FeedItem] = []
    for row in rows:
        # Subsector narrowing: an interest like sports:cricket drops other
        # subsectors of that sector (unclassified subsectors stay visible
        # only when the whole sector was selected).
        wanted_subs = interest_pairs.get(row["sector"] or "")
        if wanted_subs and row["subsector"] not in wanted_subs:
            continue
        # is_regional reflects the state when the reader gave one (India-first
        # tiering), else the country region.
        items.append(build_feed_item(row, active_lens, state or region, langs))

    # Raw records come from their own bounded query — only for the lenses that
    # want them (cyber/GRC); they're noise for readers and traders. Fetching just
    # the page's worth keeps this a top-N heapsort instead of dragging thousands
    # of rows through the ranker to throw them away.
    records: list[FeedItem] = []
    if active_lens.include_cve_records:
        record_rows = (
            await db.execute(
                text(
                    """
                    SELECT id, title, summary, sector, subsector, regions, image_url,
                           projection, last_updated_at, occurred_at
                    FROM events e
                    WHERE (CAST(:sectors AS text[]) IS NULL
                           OR e.sector = ANY(CAST(:sectors AS text[])))
                      AND COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) > 0
                      AND (e.projection->'source_slugs') <@ CAST(:cve_only AS jsonb)
                    ORDER BY e.last_updated_at DESC
                    LIMIT :cap
                    """
                ),
                # A page's worth, not the cap: the cap governs how many records
                # get WOVEN in while there is news to weave them between. The
                # surplus is the backfill reserve for a sector that has records
                # and almost no journalism — better a full page that leans
                # changelog than a third of a page and no way to ask for more.
                {"sectors": sectors or None, "cve_only": CVE_ONLY_JSON, "cap": limit},
            )
        ).mappings().all()
        records = [build_feed_item(r, active_lens, state or region, langs) for r in record_rows]

    if sort == "top":
        items.sort(key=lambda i: i.score, reverse=True)
        records.sort(key=lambda i: i.score, reverse=True)
    else:  # latest — a news feed reads newest-first by default
        items.sort(key=lambda i: i.last_updated_at, reverse=True)
        records.sort(key=lambda i: i.last_updated_at, reverse=True)
    # Geo tier: the reader's state first, then the rest (national). Stable sort
    # keeps the score/recency order within each band. Runs BEFORE the interleave
    # below — the other way round it re-partitioned the page and undid it, and
    # since records carry no regions they all sank into the national band and got
    # cut by the page slice, making include_cve_records a no-op for any reader
    # with a state (i.e. every onboarded one).
    if state:
        items.sort(key=lambda i: not i.is_regional)

    # Records are machine-written and re-stamped on every scan, so they are
    # permanently "newer" than journalism — for a lens that wants them, a latest
    # sort handed back a page of pure changelog. Two stories, then a record,
    # keeps the page recognisably a news feed at any scroll depth.
    #
    # The ratio is the whole mechanism: it holds records to a third while there
    # is news to weave them between, and when the news runs out the remaining
    # records simply follow, so a sector with two stories and a thousand CVE rows
    # still fills a page instead of handing back a stub. An explicit limit//3 cap
    # and a backfill pass both turned out to be dead code against it.
    #
    # Not applied to sort=top: that one promises score order, and the feed's lead
    # rail reads items[:3] straight off it.
    if records and sort != "top":
        merged: list[FeedItem] = []
        n = r = 0
        while n < len(items) or r < len(records):
            merged.extend(items[n : n + 2])
            n += 2
            if r < len(records):
                merged.append(records[r])
                r += 1
        items = merged
    elif records:
        items.extend(records)
        items.sort(key=lambda i: i.score, reverse=True)
    return FeedResponse(items=items[:limit], lens=active_lens.slug)
