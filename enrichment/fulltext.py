"""Full-text retrieval — direct fetch tier only for the prototype.

CVE-feed and RSS bodies are used as-is (tier "body"); news URLs are
fetched and cleaned with trafilatura (tier "direct"). Proxy/archive
fallback tiers are deferred.
"""

import asyncio

import httpx
import trafilatura

from common.logging import get_logger

logger = get_logger(__name__)

MIN_USEFUL_CHARS = 400


async def retrieve_fulltext(url: str | None, body: str | None) -> tuple[str, str, str | None]:
    """Return (clean_text, retrieval_tier, og_image). Prefers a complete body.

    og_image comes for free from the metadata of the page we already fetch —
    never a separate request.
    """
    if body and len(body) >= MIN_USEFUL_CHARS:
        return body, "body", None

    if url:
        try:
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; prism-prototype/0.1)"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
            doc = await asyncio.to_thread(
                trafilatura.bare_extraction,
                response.text,
                url=url,
                include_comments=False,
                with_metadata=True,
            )
            extracted = getattr(doc, "text", None) if doc else None
            image = getattr(doc, "image", None) if doc else None
            if extracted and (len(extracted) >= MIN_USEFUL_CHARS or not body):
                return extracted, "direct", image
        except Exception:
            logger.warning("fulltext_fetch_failed", url=url, exc_info=True)

    if body:
        return body, "body", None
    return "", "none", None
