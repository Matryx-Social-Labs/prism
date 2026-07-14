"""Full-text retrieval — direct fetch tier only for the prototype.

CVE-feed and RSS bodies are used as-is (tier "body"); news URLs are
fetched and cleaned with trafilatura (tier "direct"). Proxy/archive
fallback tiers are deferred.
"""

import asyncio
import logging

import httpx
import trafilatura

logger = logging.getLogger(__name__)

MIN_USEFUL_CHARS = 400


async def retrieve_fulltext(url: str | None, body: str | None) -> tuple[str, str]:
    """Return (clean_text, retrieval_tier). Prefers an already-complete body."""
    if body and len(body) >= MIN_USEFUL_CHARS:
        return body, "body"

    if url:
        try:
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; prism-prototype/0.1)"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
            extracted = await asyncio.to_thread(
                trafilatura.extract, response.text, url=url, include_comments=False
            )
            if extracted and len(extracted) >= MIN_USEFUL_CHARS:
                return extracted, "direct"
            if extracted and not body:
                return extracted, "direct"
        except Exception:
            logger.warning("fulltext fetch failed for %s", url, exc_info=True)

    if body:
        return body, "body"
    return "", "none"
