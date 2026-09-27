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
from collections.abc import Mapping
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any

from common.logging import get_logger
from common.urls import canonicalize_url
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


@lru_cache(maxsize=128)  # the story page flattens one article once per quote on it
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


# ── Direct speech only (founder decision, 27 Sep 2026) ──────────────────────
#
# VERBATIM IS TO THE ARTICLE, NOT TO THE SPEAKER. The check in verify_claims
# proves the words are in the article; the live window then printed a
# reporter's sentence ("…, DIG Jalandhar Range Naveen Singla said on…") and a
# reporter's paraphrase ("Saheb said he pointed out…") as quotes. So a quote is
# shown only when the article itself prints those words inside quotation marks,
# as one statement. Reported speech ("he said that…", "उन्होंने कहा कि…") is not
# a quote however faithful — measured 2026-09-27: it is 29% of the live window's
# claims, most of them from Indian-language outlets that print speech without
# marks, and 12 of the 58 adjudicated attributions in tools/gold_claims; none
# of the 46 it keeps is a misattribution.

_DOUBLE = '"“”„‟«»'
_SINGLE = "'‘’‛‚‹›`"
_MARK_RUN = re.compile(f"[{re.escape(_DOUBLE + _SINGLE)}]+")
_OPENS_AFTER = frozenset("([{—–-:;,/")  # a mark after one of these opens
_CLOSES_BEFORE = frozenset(".,;:!?)]}—–-।॥۔")  # a mark before one of these closes
_OPEN_SHAPE = frozenset("“„‟«‘‛‚‹`")
_CLOSE_SHAPE = frozenset("”»’›")
_OPEN, _CLOSE, _EITHER = 1, -1, 0

# Fewer words than this is a phrase, not a statement ("Unconstitutional,
# arbitrary, unacceptable").
MIN_QUOTE_WORDS = 4
# A list of single words, however many: `"false", "baseless" and "fabricated`.
_WORD_LIST = re.compile(r"[\W_]*\w+(?:[\W_]*(?:,|\band\b|\bor\b)[\W_]*\w+)+[\W_]*", re.I)
_SPEECH_VERB = (r"(?:said|says|told|tells|added|adds|stated|claimed|alleged|asserted|noted|wrote|tweeted|"
                r"posted|remarked|explained|announced|urged|asked|replied|argued|insisted|maintained|warned|reiterated)")
_WORD_BEFORE_VERB = re.compile(rf"\b([^\W\d_][\w-]*)\s+(?:(?:also|further|had|has)\s+)?{_SPEECH_VERB}\b", re.I)
_WORD_AFTER_VERB = re.compile(rf"\b{_SPEECH_VERB}\s+([^\W\d_][\w-]*)", re.I)
# A capitalised name word of the speaker's; not "Sahil" in "Sahil's mother".
_NAME_WORD = re.compile(r"\b[A-Z][\w-]{2,}\b(?!['’]s\b)")


def _marks(text: str, lo: int, hi: int) -> list[tuple[int, bool, int]]:
    """(position, is a double mark, role) for each quotation mark in text[lo:hi].

    The role is read from the neighbours first — `, "We` opens, `we," he`
    closes — because outlets are not consistent about shapes (Urdu prints
    ’…‘, scraped text loses spaces: `family.“When`), and from the shape only
    when the neighbours cannot tell. Two single marks are one double (’’…’’,
    common in Indian outlets); `.""` between two quotations is a close then an
    open; a single mark between two letters is an apostrophe.
    """
    out: list[tuple[int, bool, int]] = []
    for m in _MARK_RUN.finditer(text, lo, hi):
        run, a, b = m.group(), m.start(), m.end()
        prev = text[a - 1] if a else " "
        nxt = text[b] if b < len(text) else " "
        double = len(run) > 1 or run in _DOUBLE
        if not double and prev.isalnum() and nxt.isalnum():
            continue
        if sum(ch in _DOUBLE for ch in run) > 1 and not prev.isspace() and not nxt.isspace():
            out += [(a, True, _CLOSE), (b - 1, True, _OPEN)]
            continue
        opens = (prev.isspace() or prev in _OPENS_AFTER) and not nxt.isspace() and nxt not in _CLOSES_BEFORE
        closes = not prev.isspace() and (nxt.isspace() or nxt in _CLOSES_BEFORE)
        if opens == closes:
            opens, closes = run[0] in _OPEN_SHAPE, run[-1] in _CLOSE_SHAPE
        out.append((a, double, _OPEN if opens and not closes else _CLOSE if closes and not opens else _EITHER))
    return out


def _quoted(text: str, s: int, e: int) -> bool:
    """Is text[s:e] inside quotation marks it never leaves?

    Double marks are tried, then single. Depth counts nesting (a film title in
    single quotes inside a single-quoted statement). The count starts at the
    span's paragraph: scraped text loses closing marks, and a quote that lost
    one must end with its paragraph rather than swallow the reporter's next.
    """
    marks = _marks(text, text.rfind("\n", 0, s) + 1, e)
    for double in (True, False):
        depth = 0
        for at, is_double, role in marks:
            if is_double != double:
                continue
            if at >= s and not depth:
                break  # outside at the span's start, or the span left the quotation
            if role == _OPEN or (role == _EITHER and not depth):
                depth += 1
            elif depth:
                depth -= 1
        else:
            if depth:
                return True
    return False


def _narrates(quote: str, speaker: str) -> bool:
    """The reporter's voice inside the marks: the speaker's own name beside a
    speech verb ("Singla said", "said Singla"). Pronouns and "according to" are
    NOT tested: on the live window 14 of their 15 hits inside quotation marks
    were real speech — a father's "He had told us…", "according to the 2022
    census…"."""
    names = {w.casefold() for w in _NAME_WORD.findall(speaker)}
    return any(m.group(1).casefold() in names
               for pattern in (_WORD_BEFORE_VERB, _WORD_AFTER_VERB) for m in pattern.finditer(quote))


def check_quote(text: str, quote: str, speaker: str, start: int | None = None) -> tuple[str | None, str, int]:
    """Why these words may not be shown as the speaker's quote (None when they
    may), the quote as shown, and where it starts in flat_ws(text).

    `start` is the stored span, trusted only while the words are still there.
    The quotation marks the model sometimes copies with the words are trimmed:
    they are the article's punctuation, and the card prints its own.
    """
    flat = flat_ws(text)
    quote = flat_ws(quote)
    if start is None or flat[start:start + len(quote)] != quote:
        start = flat.find(quote) if quote else -1
        if start < 0:
            return "not_verbatim", quote, -1
    trimmed = quote.strip(_DOUBLE + _SINGLE + " ")
    start += len(quote) - len(quote.lstrip(_DOUBLE + _SINGLE + " "))
    # The span in the raw text, whose line breaks mark the paragraphs. The raw
    # offset is never before the flat one, so the first match from there is it;
    # the pattern is compiled only when the raw text breaks a line inside it.
    at = text.find(trimmed, start) if trimmed else -1
    if at >= 0:
        raw: tuple[int, int] | None = (at, at + len(trimmed))
    else:
        m = re.compile(r"\s+".join(map(re.escape, trimmed.split(" ")))).search(text, start) if trimmed else None
        raw = m.span() if m else None
    if raw is None or not _quoted(text, *raw):
        return "not_quoted", trimmed, start
    if len(trimmed.split()) < MIN_QUOTE_WORDS or _WORD_LIST.fullmatch(trimmed):
        return "fragment", trimmed, start
    if _narrates(trimmed, speaker):
        return "narration", trimmed, start
    return None, trimmed, start


def verify_claims(claims: list[Claim], clean_text: str) -> tuple[list[Claim], dict[str, int]]:
    """Keep the claims whose quote really appears in the article, inside its
    quotation marks. Repair spans.

    Returns (kept, rejected_by_reason). The reasons are counted rather than
    discarded so extraction quality stays measurable without re-reading articles.
    """
    rejected = {"no_speaker": 0, "short_quote": 0, "not_verbatim": 0, "not_quoted": 0, "narration": 0, "fragment": 0}
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
        why, quote, at = check_quote(clean_text, quote, c.speaker, at)
        if why:
            rejected[why] += 1
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


def speaker_key(name: str) -> str:
    """Fold punctuation and case ONLY: "D.K. Shivakumar" == "D K Shivakumar".

    Measured on the live window: 3% of events carry one person under two speaker
    strings, and every real duplicate was a punctuation or case variant. A surname
    key would also have merged Chinna Reddy with Komatireddy Rajagopal Reddy, who
    are different people, so tokens are kept: "Jaishankar" and "S Jaishankar" stay
    two keys. Within ONE record the shorter name folds into the longer
    (fold_speakers); across records that fold is the QID ledger's job (plan step 5).
    """
    return " ".join(name.replace(".", " ").split()).casefold()


# ── One record's quotes: one speaker per quote, one row per thing said ───────

# Two quotes whose word sets overlap this much are one statement: "We spoke to
# students who…" and "We spoke to the students who…" from two outlets.
SAME_WORDS = 0.8
# How far from a quote the article must name its speaker to settle a quote two
# speakers were given — the context the reader is shown either side of it.
NEAR_CHARS = 220
_SENTENCE_END = re.compile(r"""[.!?।]["'”’]*\s""")


@dataclass(frozen=True)
class Said:
    """One quote as the card will show it: `start` indexes flat_ws of the
    article (`src`, the article row), `also` holds the other reports that
    printed the same words."""

    speaker: str
    quote: str
    start: int | None
    end: int | None
    src: Mapping[str, Any]
    role: str | None = None
    also: tuple[Said, ...] = ()


@lru_cache(maxsize=4096)
def _words(quote: str) -> frozenset[str]:
    return frozenset(re.findall(r"\w+", quote.casefold()))


def _overlap(wa: frozenset[str], wb: frozenset[str]) -> bool:
    if not wa or not wb or min(len(wa), len(wb)) < SAME_WORDS * max(len(wa), len(wb)):
        return False  # the overlap can never reach SAME_WORDS: skips the set work for most pairs
    return len(wa & wb) / len(wa | wb) >= SAME_WORDS


def same_words(a: str, b: str) -> bool:
    return _overlap(_words(a), _words(b))


def _published(s: Said) -> float:
    pub = s.src.get("published_at")
    return pub.timestamp() if pub else float("inf")


def _person_like(name: str) -> bool:
    """Every word a capitalised name or an initial: "N Chandrababu Naidu", not
    "Bank of India" or "IIT-Bombay Faculty Forum"."""
    words = name.replace(".", " ").split()
    return bool(words) and all(w.isalpha() and w[0].isupper() and (len(w) <= 2 or w[1:].islower()) for w in words)


def fold_speakers(said: list[Said]) -> list[Said]:
    """"Saheb" and "Saheb Singh" on one record are one person (live, event
    8db8e742): a name whose words begin or end exactly one longer name on the
    record is shown under that name. "Singh" beside Saheb Singh and Jarnail
    Singh folds nowhere, and neither do bodies: on the live window the same
    rule put "Bank of India" under State Bank of India and "IIT-Bombay" under
    its Faculty Forum, so both names must read as a person's."""
    shown: dict[str, str] = {}
    for s in said:
        shown.setdefault(speaker_key(s.speaker), s.speaker)
    words = {k: k.split() for k in shown}
    into: dict[str, str] = {}
    for k in sorted(words, key=lambda k: -len(words[k])):  # longer names settle first
        n = len(words[k])
        longer = {into[o] for o in words
                  if len(words[o]) > n and n and words[k] in (words[o][:n], words[o][-n:])
                  and _person_like(shown[k]) and _person_like(shown[o])}
        into[k] = longer.pop() if len(longer) == 1 else k
    return [replace(s, speaker=shown[into[speaker_key(s.speaker)]]) for s in said]


def one_speaker_per_quote(said: list[Said]) -> list[Said]:
    """One set of words, one speaker. The extractor sometimes gives a quote to
    two people (live: Majithia's post on X under both Majithia and SSP Gaurav
    Toora). The speaker the article names nearest the words — full name or
    surname, within NEAR_CHARS either side — keeps them; on a tie (two Ghoshes)
    the nearer full name decides; still tied, or no name nearby, and nobody
    does."""
    flat: dict[str, str] = {}
    beyond = NEAR_CHARS + 1

    def distance(name: str, s: Said) -> tuple[int, int] | None:
        """(nearest gap to the name or surname, nearest gap to the full name)."""
        if s.start is None:
            return None
        text = flat.setdefault(str(s.src["article_id"]), flat_ws(s.src.get("clean_text")))
        surname = name.split()[-1]
        alts = [f"(?P<full>{re.escape(name)})"] + ([re.escape(surname)] if len(surname) >= 3 and surname != name else [])
        pattern = re.compile(r"\b(?:" + "|".join(alts) + r")\b", re.I)
        end = s.start + len(s.quote)
        gaps = [(s.start - m.end(), m["full"] is not None)
                for m in pattern.finditer(text, max(0, s.start - NEAR_CHARS), s.start)]
        # After the words, only the attribution's own sentence counts:
        # `,” Majithia wrote on X`, never `,” he said. Union minister Sukanta
        # Majumdar, however…` nor `anyday.” Union minister Sukanta Majumdar…`
        # (live: both handed Kunal Ghosh's words to Majumdar). From the quote's
        # last character, so a quote that ends its own sentence counts.
        gaps += [(m.start() - end, m["full"] is not None) for m in pattern.finditer(text, end, end + NEAR_CHARS)
                 if not _SENTENCE_END.search(text, end - 1, m.start())]
        if not gaps:
            return None
        return min(g for g, _ in gaps), min((g for g, full in gaps if full), default=beyond)

    kept: list[Said] = []
    # ponytail: O(n²) over a record's quotes — 141 on the largest live record,
    # a few ms. Index by word set if a record ever carries thousands.
    words = [_words(s.quote) for s in said]
    for s, ws in zip(said, words, strict=True):
        rivals = [o for o, wo in zip(said, words, strict=True) if o is s or _overlap(ws, wo)]
        names = {speaker_key(o.speaker): o.speaker for o in rivals}
        if len(names) == 1:
            kept.append(s)
            continue
        best: dict[str, tuple[int, int]] = {}
        for k, name in names.items():
            gaps = [d for d in (distance(name, o) for o in rivals) if d is not None]
            if gaps:
                best[k] = (min(g for g, _ in gaps), min(f for _, f in gaps))
        nearest = [k for k, d in best.items() if d == min(best.values())]
        if nearest == [speaker_key(s.speaker)]:
            kept.append(s)
    return kept


def collapse_repeats(said: list[Said]) -> list[Said]:
    """One row per thing said. The same words from one speaker in four outlets
    are one quote carried four times (live: the SSP's "When we reached here…"
    ×4): the earliest report is the citation, the rest ride on it as `also`.
    Rows keep the order they were first met in."""
    rows: list[Said] = []
    keys: list[str] = []
    for s in said:
        key = speaker_key(s.speaker)
        at = next((i for i, r in enumerate(rows) if keys[i] == key and same_words(r.quote, s.quote)), None)
        if at is None:
            rows.append(s)
            keys.append(key)
            continue
        r = rows[at]
        if s.src["article_id"] in {m.src["article_id"] for m in (r, *r.also)}:
            continue  # one article printing it twice is still one report
        lead, other = (s, r) if _published(s) < _published(r) else (r, s)
        rows[at] = replace(lead, also=tuple(sorted((*r.also, replace(other, also=())), key=_published)))
    return rows


def dedupe_sources(sources: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Keep one reader-facing row per publisher document.

    A feed's external id is not always stable. BBC, for example, has emitted
    one article URL with ``#0``, ``#2`` and ``#5`` ids as the item moved in its
    feed. Those observations remain in the database for provenance, but they
    are one document, not three sources and not three copies of every quote.

    Rows arrive newest-first, so the first row is the latest observation. The
    runtime canonicalizer is a fallback for rows created before the canonical
    URL column was backfilled.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[Mapping[str, Any]] = []
    for src in sources:
        canonical = src.get("url_canonical") or canonicalize_url(src.get("url"))
        key = (
            ("url", canonical)
            if canonical
            else ("article", str(src["article_id"]))
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(src)
    return unique
