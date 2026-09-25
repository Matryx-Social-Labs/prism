"""The largest sensible rendition of a publisher's photo.

Feeds ship thumbnails: BBC's media tag is `/ace/ws/240/…` (240 px wide),
Prajavani's `?w=280`. The rail draws a tile at 232 CSS px, which on a 2×
screen is 464 device pixels, so those looked soft (founder, 2026-09-20). The
same CDNs take a size token in the URL; this asks for a rendition wide enough
for the tile and no wider. Applied where a report is served, so it covers
every report already stored. Still the publisher's own file, hotlinked.
"""
from __future__ import annotations

import re

TARGET_W = 800

_BBC = re.compile(r"(https?://ichef\.bbci\.co\.uk/(?:ace|news)/ws/)(\d+)(/)")
_ASSETTYPE_W = re.compile(r"([?&]w=)(\d+)")


def hi_res(url: str | None) -> str | None:
    if not url:
        return url
    if "ichef.bbci.co.uk" in url:
        # 800 wide, and BBC serves a WebP of any rendition by suffix at about
        # half the bytes (measured 2026-09-20: 48 KB jpeg → 27 KB webp).
        out = _BBC.sub(lambda m: f"{m.group(1)}{TARGET_W}{m.group(3)}", url, count=1)
        return out if out.endswith(".webp") else out + ".webp"
    if "assettype.com" in url or "amarujala.com" in url:
        # Only a stated width below the target is raised; an empty `?w=` on
        # Amar Ujala already returns the 1080 master (measured), leave it.
        m = _ASSETTYPE_W.search(url)
        if m and int(m.group(2)) < TARGET_W:
            return _ASSETTYPE_W.sub(lambda mm: f"{mm.group(1)}{TARGET_W}", url, count=1)
        return url
    return url


# ── Placeholders: the outlet's logo or a stock district photo, not this story ──
# The Hindu's og-image.png appeared on 363 reports in a fortnight, TOI's generic
# msid on 87, Prajavani's district stock shots on 13–28 each (prod, 2026-09-21).
# A photograph OF a story is not shared by a dozen unrelated ones, so a hash
# seen on PLACEHOLDER_REPEATS reports within PLACEHOLDER_WINDOW is treated as
# furniture and never shown as the story's picture.
#
# The URL counts too. 16% of reports carry no hash — the fetch failed — and a
# fallback served that way walked straight past the hash rule: TOI's generic
# msid-47529300 on 16 articles, HT's generic logo, Prajavani's horoscope art
# (prod, 2026-09-25). By URL the repeat is counted over distinct ARTICLES, since
# one article carried by four edition feeds is one use of its photo, not four.
PLACEHOLDER_REPEATS = 4
PLACEHOLDER_WINDOW = "14 days"
_PLACEHOLDER_TTL_S = 300.0
_placeholders: tuple[float, frozenset[str]] = (0.0, frozenset())

# The one test every route applies to a report's photo (`ri` is raw_items): its
# hash and its URL are both checked against placeholders(). A hash never looks
# like a URL, so one set carries both.
REAL_PHOTO_SQL = (
    "NOT (coalesce(ri.image_phash, '') = ANY(CAST(:placeholders AS text[])) "
    "OR ri.image_url = ANY(CAST(:placeholders AS text[])))"
)


def report_photo_join(alias: str) -> str:
    """The row's picture as `img.image_url` / `img.slug`: a report's own
    photograph OF this story, with the outlet that took it for the credit —
    never an outlet's logo or stock shot. The event's first image wins when it
    is a real one, else the earliest real one. `alias` names the outer events
    row; it is a constant at every call site, never input. Needs :placeholders."""
    return f"""
        LEFT JOIN LATERAL (
            SELECT ri.image_url, s.slug FROM event_memberships m
            JOIN articles a ON a.id = m.article_id
            JOIN raw_items ri ON ri.id = a.raw_item_id
            JOIN sources s ON s.id = ri.source_id
            WHERE m.event_id = {alias}.id AND ri.image_url IS NOT NULL AND {REAL_PHOTO_SQL}
            ORDER BY (ri.image_url = {alias}.image_url) DESC, ri.published_at ASC NULLS LAST
            LIMIT 1
        ) img ON true
    """


def is_placeholder(phash: str | None, url: str | None, keys: frozenset[str]) -> bool:
    return bool((phash and phash in keys) or (url and url in keys))


async def placeholders(session) -> frozenset[str]:
    """Hashes and URLs of the current placeholder pictures, refreshed every five minutes."""
    global _placeholders
    import time

    from sqlalchemy import text

    now = time.monotonic()
    stamp, cached = _placeholders
    if cached and now - stamp < _PLACEHOLDER_TTL_S:
        return cached
    rows = (
        await session.execute(
            text(
                f"""
                SELECT image_phash FROM raw_items
                WHERE image_phash IS NOT NULL AND created_at > now() - interval '{PLACEHOLDER_WINDOW}'
                GROUP BY image_phash HAVING count(*) >= :n
                UNION
                SELECT image_url FROM raw_items
                WHERE image_url IS NOT NULL AND created_at > now() - interval '{PLACEHOLDER_WINDOW}'
                GROUP BY image_url HAVING count(DISTINCT coalesce(url_canonical, url)) >= :n
                """
            ),
            {"n": PLACEHOLDER_REPEATS},
        )
    ).scalars().all()
    _placeholders = (now, frozenset(rows))
    return _placeholders[1]
