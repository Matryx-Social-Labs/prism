"""Seed the sources table (idempotent).

India-first scope: national + state general news + the cybersecurity lens.
International general outlets are intentionally out for now (see ingestion/rss.py).
State granularity lives on the feed spec (ISO 3166-2), not the source row.
"""

from sqlalchemy.dialects.postgresql import insert as pg_insert

from common.db import session_scope
from common.models import Source

SOURCES = [
    # ── Authoritative CVE feeds (cyber lens only; never in the general feed) ──
    {"slug": "cisa_kev", "name": "CISA Known Exploited Vulnerabilities", "source_type": "cve_feed", "country": "US", "language": "en"},
    {"slug": "nvd", "name": "NVD / CVE", "source_type": "cve_feed", "country": "US", "language": "en"},
    # ── India national ──
    {"slug": "thehindu", "name": "The Hindu", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "timesofindia", "name": "The Times of India", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "ndtv", "name": "NDTV", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "hindustantimes", "name": "Hindustan Times", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "livemint", "name": "Mint", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "hindu_businessline", "name": "The Hindu BusinessLine", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "espncricinfo", "name": "ESPNcricinfo", "source_type": "rss", "country": "IN", "language": "en"},
    # ── India national — other languages (multilingual clustering) ──
    {"slug": "aajtak", "name": "Aaj Tak", "source_type": "rss", "country": "IN", "language": "hi"},
    {"slug": "amarujala", "name": "Amar Ujala", "source_type": "rss", "country": "IN", "language": "hi"},
    {"slug": "bbc_tamil", "name": "BBC Tamil", "source_type": "rss", "country": "IN", "language": "ta", "reliability": {"funding": "public"}},
    {"slug": "prajavani", "name": "Prajavani", "source_type": "rss", "country": "IN", "language": "kn"},
    {"slug": "tv9kannada", "name": "TV9 Kannada", "source_type": "rss", "country": "IN", "language": "kn"},
    # ── India state editions ──
    {"slug": "thehindu_tamilnadu", "name": "The Hindu — Tamil Nadu", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "thehindu_kerala", "name": "The Hindu — Kerala", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "thehindu_karnataka", "name": "The Hindu — Karnataka", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "thehindu_andhra", "name": "The Hindu — Andhra Pradesh", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "thehindu_telangana", "name": "The Hindu — Telangana", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "toi_delhi", "name": "The Times of India — Delhi", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "toi_mumbai", "name": "The Times of India — Mumbai", "source_type": "rss", "country": "IN", "language": "en"},
    # ── Cybersecurity lens (global by nature) ──
    {"slug": "thehackernews", "name": "The Hacker News", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "bleepingcomputer", "name": "BleepingComputer", "source_type": "rss", "country": "US", "language": "en"},
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
