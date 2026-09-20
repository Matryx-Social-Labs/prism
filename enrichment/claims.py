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
# The press abbreviates offices; the role is asked for in full. Both sides are
# expanded before the word check so "Karnataka Chief Minister" holds against an
# article that only ever wrote "Karnataka CM".
_ROLE_ABBR = [
    (re.compile(r"\bdy\.?\s*cm\b", re.I), " deputy chief minister "),
    (re.compile(r"\bcm\b", re.I), " chief minister "),
    (re.compile(r"\bpm\b", re.I), " prime minister "),
    (re.compile(r"\bcji\b", re.I), " chief justice of india "),
    (re.compile(r"\bex-", re.I), " former "),
]


def _expand(s: str) -> str:
    for pat, full in _ROLE_ABBR:
        s = pat.sub(full, s)
    return s


def flat_ws(s: str) -> str:
    """Whitespace-collapsed text. quote_start/quote_end index THIS string, not
    the raw clean_text — every reader of the offsets must flatten first."""
    return _WS.sub(" ", s or "").strip()


_ROLE_QUALIFIERS = {"former", "ex", "senior", "junior", "acting", "deputy", "outgoing", "then", "interim"}
_CLAUSE = re.compile(r",|;| who | which | that | from | for | at | in | and |\bbelonging\b", re.I)


def faithful_role(role: str | None, flat_text: str, native: str | None = None) -> str | None:
    """The speaker's role only if the article's own words support it.

    Kept in full when every content word appears in the article (casefolded,
    CM/PM/CJI expanded on both sides); otherwise cut back to the longest
    leading run the article does support ("lawyer belonging to the Friends of
    the Earth organisation" → "lawyer"; "Kerala Chief Minister" on a Karnataka
    report → nothing, since the first word already fails). Brackets are
    rejected, clauses are cut at the title's length. Asked for "in the
    article's own words", the model still writes "Agriculture Minister
    (Andhra Pradesh)" or a 30-word description from what it knows; a null
    prints no role, which is better than a plausible one.

    `native` is the same title copied in the article's own script, for a
    Hindi or Kannada report whose English role no word check can reach: if
    that copy really is in the article, the English role stands.
    """
    if not role:
        return None
    # "(OCA)" after "Olympic Council of Asia" is the article's own shorthand;
    # "(Andhra Pradesh)" after "Agriculture Minister" is the model's addition.
    r = re.sub(r"\s*\([A-Z]{2,7}\)$", "", _WS.sub(" ", role).strip().strip(" .,"))
    if r[:4].casefold() == "the ":
        r = r[4:]
    if not r or any(ch in r for ch in "()[]"):
        return None
    if len(r) > MAX_ROLE_CHARS:
        r = _CLAUSE.split(r, 1)[0].strip(" .,")
        if not r or len(r) > MAX_ROLE_CHARS:
            return None
    n = _WS.sub(" ", native or "").strip()
    if n and n in flat_text:
        return r
    words = set(_WORD.findall(_expand(flat_text.casefold())))
    kept: list[str] = []
    for tok in r.split(" "):
        parts = _WORD.findall(_expand(tok.casefold()))
        if all(len(w) < 3 or w in _ROLE_GLUE or w in words for w in parts):
            kept.append(tok)
        else:
            break
    while kept and _WORD.findall(kept[-1].casefold()) and all(w in _ROLE_GLUE for w in _WORD.findall(kept[-1].casefold())):
        kept.pop()
    out = " ".join(kept).strip(" .,")
    content = [w for w in _WORD.findall(out.casefold()) if w not in _ROLE_GLUE and w not in _ROLE_QUALIFIERS]
    return out if content else None


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
                "speaker_role": faithful_role(c.speaker_role, flat_text, c.speaker_role_native),
                "speaker_role_native": None,
            })
        )
    if any(rejected.values()):
        logger.info("claims_verified", kept=len(kept), **rejected)
    return kept, rejected
