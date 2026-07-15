"""Seed the sources table (idempotent)."""

from sqlalchemy.dialects.postgresql import insert as pg_insert

from common.db import session_scope
from common.models import Source

SOURCES = [
    {
        "slug": "cisa_kev",
        "name": "CISA Known Exploited Vulnerabilities",
        "source_type": "cve_feed",
        "country": "US",
        "language": "en",
    },
    {
        "slug": "nvd",
        "name": "NVD / CVE",
        "source_type": "cve_feed",
        "country": "US",
        "language": "en",
    },
    {
        "slug": "gdelt",
        "name": "GDELT DOC 2.0",
        "source_type": "news_api",
        "country": None,
        "language": None,
    },
    {
        "slug": "thehackernews",
        "name": "The Hacker News",
        "source_type": "rss",
        "country": "IN",
        "language": "en",
    },
    {
        "slug": "bleepingcomputer",
        "name": "BleepingComputer",
        "source_type": "rss",
        "country": "US",
        "language": "en",
    },
    {
        "slug": "bbc_world",
        "name": "BBC World",
        "source_type": "rss",
        "country": "GB",
        "language": "en",
    },
    {
        "slug": "aljazeera",
        "name": "Al Jazeera English",
        "source_type": "rss",
        "country": "QA",
        "language": "en",
    },
    {
        "slug": "guardian_world",
        "name": "The Guardian World",
        "source_type": "rss",
        "country": "GB",
        "language": "en",
    },
]


async def seed_sources() -> None:
    async with session_scope() as session:
        for src in SOURCES:
            stmt = (
                pg_insert(Source)
                .values(**src)
                .on_conflict_do_nothing(index_elements=["slug"])
            )
            await session.execute(stmt)
