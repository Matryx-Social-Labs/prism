"""Full-text retrieval — direct fetch tier only for the prototype.

CVE-feed and RSS bodies are used as-is (tier "body"); news URLs are
fetched and cleaned with trafilatura (tier "direct"). Proxy/archive
fallback tiers are deferred.
"""

import asyncio
import html
import re

import httpx
import trafilatura

from common.imagehash import refuse_non_public
from common.logging import get_logger

logger = get_logger(__name__)

MIN_USEFUL_CHARS = 400

# Named HTML tags only — NOT "anything in angle brackets". Articles legitimately
# contain the latter: a security piece describing `/proc/<pid>/root` is prose, and
# a looser pattern would quietly eat it. Every name below is a real HTML element,
# so a false positive needs an article that says "</div>" on purpose.
_HTML_TAG = re.compile(
    r"</?(?:p|div|span|a|em|strong|b|i|u|br|hr|ul|ol|li|h[1-6]|img|figure|figcaption"
    r"|blockquote|table|thead|tbody|tr|td|th|section|article|header|footer|nav|aside"
    r"|iframe|script|style|picture|source|video|audio|small|sup|sub|pre|code)"
    r"(?:\s[^>]*)?/?>",
    re.IGNORECASE,
)


def _markup_leaked(text: str) -> bool:
    """Two or more real HTML tags. One could be a stray literal; two is a document."""
    return len(_HTML_TAG.findall(text)) >= 2


def _demarkup(text: str, url: str | None) -> str:
    """Recover prose from an extraction that came back as markup.

    trafilatura is asked TWICE on purpose. Some sites carry the article body
    inside a JSON payload as an escaped HTML string, and the first pass returns
    that string as if it were text — tags, app-download footer and all. Feeding it
    back in treats it as the document it actually is, which drops the boilerplate
    a tag-strip would leave behind as bare anchor text.

    Falling back to stripping rather than to the original: if the second pass
    cannot parse the fragment, tags in the text are still worse than no tags. The
    text reaching here feeds the extractor's prompt, the embeddings, AND the
    verbatim quote gate, so markup is not cosmetic — a quote is checked for an
    exact match against this string.
    """
    try:
        again = trafilatura.extract(text, url=url, include_comments=False)
    except Exception:
        again = None
    if again and len(again) >= MIN_USEFUL_CHARS and not _markup_leaked(again):
        return again
    return html.unescape(_HTML_TAG.sub(" ", text)).strip()


async def retrieve_fulltext(url: str | None, body: str | None) -> tuple[str, str, str | None]:
    """Return (clean_text, retrieval_tier, og_image). Prefers a complete body.

    og_image comes for free from the metadata of the page we already fetch —
    never a separate request.
    """
    if body and len(body) >= MIN_USEFUL_CHARS:
        return body, "body", None

    if url:
        try:
            # The URL is the feed's. A compromised feed must not be able to
            # make the worker fetch an internal address; the hook checks the
            # first request and every redirect hop (common/imagehash.py).
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; prism-prototype/0.1)"},
                event_hooks={"request": [refuse_non_public]},
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
            if extracted and _markup_leaked(extracted):
                # 854 of prajavani's 880 direct-tier articles arrived like this,
                # while thehindu's 853 on the same path were clean — so this is a
                # per-site extraction failure, not a general one, and it is worth
                # repairing rather than accepting.
                logger.info("fulltext_markup_leaked", url=url, chars=len(extracted))
                extracted = _demarkup(extracted, url)
            if extracted and (len(extracted) >= MIN_USEFUL_CHARS or not body):
                return extracted, "direct", image
        except Exception:
            logger.warning("fulltext_fetch_failed", url=url, exc_info=True)

    if body:
        return body, "body", None
    return "", "none", None
