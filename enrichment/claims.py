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
_WORD = re.compile(r"[^\W\d_]+")

# A role longer than this is a description, not a title.
MAX_ROLE_CHARS = 60
_ROLE_GLUE = {"of", "the", "and", "for", "in", "at", "to", "a", "an"}


def flat_ws(s: str) -> str:
    """Whitespace-collapsed text. quote_start/quote_end index THIS string, not
    the raw clean_text — every reader of the offsets must flatten first."""
    return _WS.sub(" ", s or "").strip()


def faithful_role(role: str | None, flat_text: str) -> str | None:
    """The speaker's role only if the article's own words support it.

    Every content word of the role must appear in the article (casefolded),
    nothing composed with brackets or clauses, and no longer than a title.
    Asked for "EXACTLY as the article gives it", the model still writes
    "Agriculture Minister (Andhra Pradesh)" or a 30-word description from what
    it knows; a null prints no role, which is better than a plausible one. An
    English role on a Hindi article is unverifiable and so also null.
    """
    if not role:
        return None
    # "(OCA)" after "Olympic Council of Asia" is the article's own shorthand;
    # "(Andhra Pradesh)" after "Agriculture Minister" is the model's addition.
    r = re.sub(r"\s*\([A-Z]{2,7}\)$", "", _WS.sub(" ", role).strip().strip(" .,"))
    if r[:4].casefold() == "the ":
        r = r[4:]
    if not r or len(r) > MAX_ROLE_CHARS or any(ch in r for ch in ";()[]"):
        return None
    words = set(_WORD.findall(flat_text.casefold()))
    for tok in _WORD.findall(r.casefold()):
        if len(tok) >= 3 and tok not in _ROLE_GLUE and tok not in words:
            return None
    return r


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
                "speaker_role": faithful_role(c.speaker_role, flat_text),
            })
        )
    if any(rejected.values()):
        logger.info("claims_verified", kept=len(kept), **rejected)
    return kept, rejected
