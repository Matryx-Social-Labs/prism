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
