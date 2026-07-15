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
    # India-first regional coverage
    {"slug": "thehindu", "name": "The Hindu", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "timesofindia", "name": "The Times of India", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "ndtv", "name": "NDTV", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "hindustantimes", "name": "Hindustan Times", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "livemint", "name": "Mint", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "hindu_businessline", "name": "The Hindu BusinessLine", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "espncricinfo", "name": "ESPNcricinfo", "source_type": "rss", "country": "IN", "language": "en"},
    # Origin diversity — funding labels surface as chips in the UI
    # ("state" = state-affiliated editorial control; "public" = publicly
    # funded with editorial independence).
    {"slug": "dw", "name": "DW News", "source_type": "rss", "country": "DE", "language": "en",
     "reliability": {"funding": "public"}},
    {"slug": "france24", "name": "France 24", "source_type": "rss", "country": "FR", "language": "en",
     "reliability": {"funding": "public"}},
    {"slug": "anadolu", "name": "Anadolu Agency", "source_type": "rss", "country": "TR", "language": "en",
     "reliability": {"funding": "state"}},
    {"slug": "scmp", "name": "South China Morning Post", "source_type": "rss", "country": "HK", "language": "en"},
    {"slug": "dawn", "name": "Dawn", "source_type": "rss", "country": "PK", "language": "en"},
    {"slug": "tass", "name": "TASS", "source_type": "rss", "country": "RU", "language": "en",
     "reliability": {"funding": "state"}},
    {"slug": "cgtn", "name": "CGTN", "source_type": "rss", "country": "CN", "language": "en",
     "reliability": {"funding": "state"}},
    {"slug": "presstv", "name": "Press TV", "source_type": "rss", "country": "IR", "language": "en",
     "reliability": {"funding": "state"}},
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
