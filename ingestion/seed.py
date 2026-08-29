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
    # ── India, other languages (BBC's Indian-language services) ──
    # One newsroom across eight languages, which is the point: BBC Hindi and BBC
    # Tamil frequently cover the SAME story, so these supply genuine cross-lingual
    # same-event pairs — the thing mE5-base was chosen for (Kannada cross-lingual
    # retrieval 0.444 -> 0.778 on real news).
    #
    # publisher="bbc" on all of them so corroboration counts ONE masthead, not
    # eight. Without it a story carried by three BBC services would look
    # three-times corroborated by a single newsroom.
    {"slug": "bbc_hindi", "name": "BBC News Hindi", "source_type": "rss", "country": "IN", "language": "hi", "publisher": "bbc"},
    {"slug": "bbc_telugu", "name": "BBC News Telugu", "source_type": "rss", "country": "IN", "language": "te", "publisher": "bbc"},
    {"slug": "bbc_marathi", "name": "BBC News Marathi", "source_type": "rss", "country": "IN", "language": "mr", "publisher": "bbc"},
    {"slug": "bbc_gujarati", "name": "BBC News Gujarati", "source_type": "rss", "country": "IN", "language": "gu", "publisher": "bbc"},
    {"slug": "bbc_punjabi", "name": "BBC News Punjabi", "source_type": "rss", "country": "IN", "language": "pa", "publisher": "bbc"},
    {"slug": "bbc_bengali", "name": "BBC News Bengali", "source_type": "rss", "country": "IN", "language": "bn", "publisher": "bbc"},
    {"slug": "bbc_urdu", "name": "BBC News Urdu", "source_type": "rss", "country": "IN", "language": "ur", "publisher": "bbc"},
    # ── India state editions ──
    {"slug": "thehindu_tamilnadu", "publisher": "thehindu", "name": "The Hindu — Tamil Nadu", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "thehindu_kerala", "publisher": "thehindu", "name": "The Hindu — Kerala", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "thehindu_karnataka", "publisher": "thehindu", "name": "The Hindu — Karnataka", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "thehindu_andhra", "publisher": "thehindu", "name": "The Hindu — Andhra Pradesh", "source_type": "rss", "country": "IN", "language": "en"},
    {"slug": "thehindu_telangana", "publisher": "thehindu", "name": "The Hindu — Telangana", "source_type": "rss", "country": "IN", "language": "en"},
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
