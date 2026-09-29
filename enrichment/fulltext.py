"""Full-text retrieval: a feed that carries the whole article is used as-is
(tier "body"); otherwise the page is fetched and cleaned with trafilatura (tier
"direct"), and the feed's summary is the fallback.
"""

import asyncio
import html
import re
import statistics

import httpx
import trafilatura

from common.imagehash import refuse_non_public
from common.logging import get_logger
from common.text import title_share
from ingestion.rss import USER_AGENT

logger = get_logger(__name__)

MIN_USEFUL_CHARS = 400
# A feed body this long is the article; anything shorter is the feed's summary
# and the page is fetched. The old floor was MIN_USEFUL_CHARS, and a summary
# clears 400: measured 2026-09-29 over 8 days, ~1,250 articles were enriched
# from a 400-1,500-character summary without a fetch — Times of India's run
# 400-460 (66 words) while the worker fetches the same pages at 635-984 words.
# Feeds that do carry the text (Sambad, Dainik Bhaskar, ET, Entrackr, RBI)
# average 1,700-4,000.
FULL_BODY_CHARS = 1500

# A fetched page is the article only if it is about the article's headline.
# Measured on 24,287 direct-tier articles (production, 30 days to 2026-09-27):
# below 15% of the title's content words, 75 pages were refused and nearly all
# were the wrong text — IE author bios, an embedded tweet in place of a Kannada
# story, a paywall notice, an app-download footer, a sidebar. The handful of
# real stories caught fall back to the feed's own description, not to nothing.
MIN_TITLE_SHARE = 0.15
# A page whose opening repeats another URL's on the same site is boilerplate
# unless that opening is about this headline (enrichment/consumer.py). A lead
# restates its headline; a byline bio or a site's navigation does not. Measured
# on the same set: 43 of 46 repeated bios and navigation pages open at <= 0.25 of
# their title, while the same story re-filed under a second URL mostly opens at
# >= 0.3 — the 3 of ~25 re-files below it fall back to the feed body.
HEAD_CHARS = 500
MIN_HEAD_SHARE = 0.3


# A page of OTHER stories' headlines. Aaj Tak's short-video pages extract as the
# story's own headline followed by the next videos' — the off-title guard passes
# them, since the story's headline is in the list — and 26 of them embedded
# together into one record of unrelated stories (2026-09-28). The shape:
# many headline-length lines that almost never end a sentence. Lines under
# three words ("Advertisement", "Swipe", "Live") are filler and not counted, so
# the rule does not depend on them. Measured on 25,287 production pages (30
# days): it flags all 72 short-video pages and 10 others (live blogs, a trains
# list, appointment lists), none of them an ordinary story.
HEADLINE_LIST_MIN_LINES = 12
HEADLINE_LIST_MIN_LINE_WORDS = 3
HEADLINE_LIST_WORDS = (6, 16)  # median words per line
HEADLINE_LIST_MAX_ENDED = 0.1  # share of lines that end a sentence
_SENTENCE_END = re.compile(r"[.।॥:;\"”’)]\s*$")


def is_headline_list(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if len(ln.split()) >= HEADLINE_LIST_MIN_LINE_WORDS]
    if len(lines) < HEADLINE_LIST_MIN_LINES:
        return False
    low, high = HEADLINE_LIST_WORDS
    ended = sum(bool(_SENTENCE_END.search(ln)) for ln in lines) / len(lines)
    return low <= statistics.median(len(ln.split()) for ln in lines) <= high and ended <= HEADLINE_LIST_MAX_ENDED


def off_title(title: str | None, text: str) -> float | None:
    """The title share when the text is too far off the headline to be its
    article, else None."""
    share = title_share(title or "", text)
    return share if share is not None and share < MIN_TITLE_SHARE else None


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


async def retrieve_fulltext(
    url: str | None, body: str | None, title: str | None = None
) -> tuple[str, str, str | None]:
    """Return (clean_text, retrieval_tier, og_image). Prefers a complete body.

    og_image comes for free from the metadata of the page we already fetch —
    never a separate request. A page off its `title` is refused for the feed
    body: the wrong text is worse than a short one, because it is what the
    extractor summarises and what the matcher embeds.
    """
    if body and len(body) >= FULL_BODY_CHARS:
        return body, "body", None

    if url:
        try:
            # The URL is the feed's. A compromised feed must not be able to
            # make the worker fetch an internal address; the hook checks the
            # first request and every redirect hop (common/imagehash.py).
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
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
            share = off_title(title, extracted) if extracted else None
            if share is not None:
                logger.info("fulltext_rejected", reason="off_title", url=url, title_share=round(share, 2))
                extracted = None
            if extracted and body and is_headline_list(extracted):
                # Only with a summary to fall back to: a real list article
                # (appointments, an award list) with no summary is still more
                # than nothing.
                logger.info("fulltext_rejected", reason="headline_list", url=url)
                extracted = None
            # A page shorter than the feed's own summary is a teaser or a failed
            # extraction, not the article.
            if extracted and (not body or len(extracted) >= max(MIN_USEFUL_CHARS, len(body))):
                return extracted, "direct", image
        except Exception:
            logger.warning("fulltext_fetch_failed", url=url, exc_info=True)

    if body:
        return body, "body", None
    return "", "none", None
