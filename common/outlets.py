"""Outlet identity for the reader: a short code, and where the outlet stands.

The coverage bar on every story splits its reporting by ORIGIN — English-language
national outlets, Indian-language outlets, international outlets, wire agencies —
and the monogram stack names the mastheads. Both are derived from the `sources`
table (country, language, publisher), never asserted per article, so a new feed
gets its place on the bar the moment it is registered.

Origin is the axis Prism measures coverage on instead of a left/right spectrum:
no rating body covers Indian outlets, Indian alignment is not one axis, and a
label is an opinion — country and language are facts of the source.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Short codes the reader sees inside a 26px circle. Keyed by PUBLISHER so The
# Hindu's six state feeds share one monogram. Anything unlisted gets initials.
CODES: dict[str, str] = {
    "thehindu": "TH",
    "timesofindia": "TOI",
    "ndtv": "NDTV",
    "hindustantimes": "HT",
    "livemint": "MINT",
    "hindu_businessline": "BL",
    "espncricinfo": "ESPN",
    "aajtak": "AT",
    "amarujala": "AU",
    "prajavani": "PV",
    "tv9kannada": "TV9",
    "thehackernews": "THN",
    "bleepingcomputer": "BC",
    "bbc": "BBC",
    "aljazeera": "AJ",
    "anadolu": "AA",
    "cgtn": "CGTN",
    "dawn": "DAWN",
    "dw": "DW",
    "france24": "F24",
    "guardian_world": "GDN",
    "presstv": "PTV",
    "scmp": "SCMP",
    "tass": "TASS",
    "nvd": "NVD",
    "cisa_kev": "CISA",
    "gdelt": "GD",
}

ORIGINS = ("national", "intl", "regional", "wire")  # the bar's fixed slot order


@dataclass(frozen=True)
class Outlet:
    slug: str
    publisher: str
    name: str
    code: str
    origin: str  # one of ORIGINS
    language: str | None
    country: str | None


def classify(country: str | None, language: str | None, source_type: str | None = None) -> str:
    """Where an outlet sits on the coverage bar. Facts of the source, not a rating."""
    if source_type in ("cve_feed", "advisory"):
        return "wire"
    if country == "IN":
        return "national" if (language or "en") == "en" else "regional"
    return "intl"


def _initials(name: str) -> str:
    stop = {"the", "of", "news", "&", "—", "-", "and"}
    words = [w for w in name.replace("—", " ").split() if w.lower() not in stop] or name.split()
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:3]).upper()


def code_for(publisher: str, name: str) -> str:
    return CODES.get(publisher) or _initials(name)


_cache: tuple[float, dict[str, Outlet]] | None = None
TTL_S = 600


async def registry(db: AsyncSession) -> dict[str, Outlet]:
    """slug → Outlet for every registered source. One query every ten minutes;
    the table has forty rows and changes when a feed is added."""
    global _cache
    now = time.monotonic()
    if _cache and now - _cache[0] < TTL_S:
        return _cache[1]
    rows = (
        await db.execute(text("SELECT slug, name, source_type, publisher, country, language FROM sources"))
    ).mappings().all()
    reg = {}
    for r in rows:
        publisher = r["publisher"] or r["slug"]
        reg[r["slug"]] = Outlet(
            slug=r["slug"],
            publisher=publisher,
            name=r["name"],
            code=code_for(publisher, r["name"]),
            origin=classify(r["country"], r["language"], r["source_type"]),
            language=r["language"],
            country=r["country"],
        )
    _cache = (now, reg)
    return reg


def reset_cache() -> None:
    global _cache
    _cache = None
