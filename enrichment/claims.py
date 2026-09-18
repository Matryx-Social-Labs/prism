"""A claim is stored only if its quote is verbatim in the article.

MISATTRIBUTION IS THE WORST FAILURE THIS PRODUCT CAN HAVE. A wrong story boundary
shows a reader an unrelated card and they shrug; a wrong attribution puts words in
a named person's mouth, and no amount of clustering accuracy buys that back. So
the rule is verbatim or nothing, and this is where it is enforced — against the
article text, not by asking the model whether it was careful.

WHY THE OFFSETS ARE REPAIRED RATHER THAN TRUSTED. Models are reliable at copying a
sentence and unreliable at counting characters to it. Rejecting a correct quote
because the arithmetic was wrong would throw away good evidence for a bad reason,
so the QUOTE is the claim and the offsets are a lookup: if the text is present the
span is recomputed from it, and if it is absent the claim is dropped. The check
can then only ever be stricter than the model, never more lenient.

Whitespace is normalised on both sides before comparing, because extraction
routinely collapses a newline into a space inside a quotation — a transcription
artefact of the surrounding markup, not a change to what was said. Nothing else is
normalised: no case folding, no punctuation stripping. Those DO change words, and
would let a near-quote pass as a quote.
"""

from __future__ import annotations

import re

from common.logging import get_logger
from enrichment.schemas import Claim

logger = get_logger(__name__)

# A quote shorter than this is not evidence. "Yes", "We will" or a bare name
# matches somewhere in almost any article by accident, so a span for it proves
# nothing about attribution.
MIN_QUOTE_CHARS = 25

_WS = re.compile(r"\s+")


def flat_ws(s: str) -> str:
    """Whitespace-collapsed text. quote_start/quote_end index THIS string, not
    the raw clean_text — every reader of the offsets must flatten first."""
    return _WS.sub(" ", s or "").strip()


def verify_claims(claims: list[Claim], clean_text: str) -> tuple[list[Claim], dict[str, int]]:
    """Keep the claims whose quote really appears in the article. Repair spans.

    Returns (kept, rejected_by_reason). The reasons are counted rather than
    discarded so extraction quality stays measurable without re-reading articles.
    """
    rejected = {"no_speaker": 0, "short_quote": 0, "not_verbatim": 0}
    if not clean_text:
        return [], rejected

    flat_text = flat_ws(clean_text)
    kept: list[Claim] = []
    for c in claims:
        if not c.speaker:
            rejected["no_speaker"] += 1
            continue
        quote = flat_ws(c.quote_text)
        if len(quote) < MIN_QUOTE_CHARS:
            rejected["short_quote"] += 1
            continue
        at = flat_text.find(quote)
        if at < 0:
            # The model wrote something the article does not say. This is the case
            # the whole module exists for: dropped silently for the reader,
            # counted here so nobody has to guess how often it happens.
            rejected["not_verbatim"] += 1
            continue
        kept.append(
            c.model_copy(update={
                "quote_text": quote,
                "quote_start": at,
                "quote_end": at + len(quote),
            })
        )
    if any(rejected.values()):
        logger.info("claims_verified", kept=len(kept), **rejected)
    return kept, rejected
