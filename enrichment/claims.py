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


# ── Reported speech, Indian-language articles only (founder decision, 28 Sep) ─
#
# Direct-only cost 55% of Indian-language claims against 16% of English ones
# (live window, 27 Sep): Hindi, Kannada, Malayalam and Odia outlets mostly print
# what someone said without quotation marks — "X ने कहा कि…", "…ಎಂದು X
# ಹೇಳಿದರು". Such words are kept when the article attributes them with a speech
# verb in its language's own pattern AND names the speaker near them, and they
# are served as "reported", never as a quote. English stays direct only.
#
# Every pattern below was read off the unquoted claims of 6,987 Indian-language
# articles (21 days, prod, read-only), not written from memory. Measured: 2,520
# claims come back; a hand check of 40 of them found every attribution right
# (3 are joint statements, credited to one of the people who made them).

REPORTED_LANGS = frozenset({"hi", "mr", "ur", "gu", "pa", "bn", "as", "or", "ta", "te", "kn", "ml"})
# A speech verb, then "that" or a comma, right before the words.
_SAID_THAT = {
    "hi": r"कहा|बताया|कहना\s+(?:है|था|हैं|थे)|कहते\s+हैं|लिखा|पूछा|जोड़ा|दावा\s+किया|आरोप\s+लगाया|चेतावनी\s+दी|जानकारी\s+दी|स्पष्ट\s+किया",
    "mr": r"म्हणाले|म्हणाल्या|म्हणाला|सांगितले|सांगितलं|म्हटले|म्हटलं",
    "ur": r"کہا|بتایا|کہنا\s+(?:ہے|تھا)|کہتے\s+ہیں|لکھا|پوچھا",
    "gu": r"કહ્યું|જણાવ્યું|કહે\s+છે|કહેવું\s+છે",
    "pa": r"ਕਿਹਾ|ਦੱਸਿਆ|ਆਖਿਆ|ਕਹਿਣਾ\s+ਹੈ",
    "bn": r"বলেন|বলেছেন|বলছেন|জানান|জানিয়েছেন",
    "as": r"কয়|কৈছে|ক'লে|কলে|জনায়|জনাইছে",
    "or": r"କହିଛନ୍ତି|କହିଥିଲେ|କହିଲେ|କହନ୍ତି",
    "ta": r"கூறியது|கூறியதாவது|தெரிவித்ததாவது|கூறுகையில்|பேசுகையில்|கூறியிருப்பதாவது|பதிவிட்டுள்ளதாவது",
    "te": r"మాట్లాడుతూ|అన్నారు|తెలిపారు|పేర్కొన్నారు",
    "kn": r"ಮಾತನಾಡಿ|ಹೇಳಿದರು|ತಿಳಿಸಿದರು",
    "ml": r"പറഞ്ഞു|വ്യക്തമാക്കി",
}
_THAT = r"(?:\s*(?:कि|की|کہ|કે|ਕਿ|যে|ଯେ))?\s*[,:\-–—]*\s*\.{0,2}\s*$"
# A quotative right after the words ("…ಎಂದು", "…என்று", "…ବୋଲି")…
_QUOTATIVE = {
    "kn": r"ಎಂದು|ಎಂದರು|ಎಂದಿದ್ದಾರೆ|ಎಂದಿದ್ದರು|ಎಂಬುದಾಗಿ", "ta": r"என்று|என்றார்|என்றாா்|என்றனர்|என|எனத்|என்றும்",
    "te": r"అని|అన్నారు", "ml": r"എന്ന്|എന്നും|എന്നാണ്", "or": r"ବୋଲି", "as": r"বুলি", "mr": r"असं|असे|अशी|असा",
    "bn": r"বলে", "gu": r"એમ|તેમ",
}
# …then, before the sentence ends, a verb that reports speech.
_SPEECH_ACT = {
    "kn": r"ಎಂದರು|ಎಂದಿದ್ದಾರೆ|ಎಂದಿದ್ದರು|ಹೇಳಿದ|ಹೇಳು|ತಿಳಿಸಿದ|ನೀಡಿದ|ಒತ್ತಾಯಿಸಿದ|ವ್ಯಕ್ತಪಡಿಸಿದ|ಆಗ್ರಹಿಸಿದ|ಎಚ್ಚರಿಸಿದ|ಆರೋಪಿಸಿದ|ದೂರಿದ|ಸೂಚಿಸಿದ|ವಿವರಿಸಿದ|ಅಭಿಪ್ರಾಯಪಟ್ಟ|ಸ್ಪಷ್ಟಪಡಿಸಿದ|ಟೀಕಿಸಿದ|ಪ್ರಶ್ನಿಸಿದ|ಮನವಿ\s+ಮಾಡಿದ|ಕರೆ\s+ನೀಡಿದ",
    "ta": r"என்றார்|என்றாா்|என்றனர்|என்கிற|தெரிவித்|கூறி|கூறின|விடுத்|எச்சரித்|வலியுறுத்தின|பதிவிட்|சாட்டின|சாட்டியிருந்|குறிப்பிட்",
    "te": r"అన్నారు|దుయ్యబట్టారు|చెప్పుకొచ్చా|రాశారు|విమర్శించారు|తోసిపుచ్చారు|ధ్వజమెత్తారు|హెచ్చరించారు|తెలిపారు|పేర్కొన్నారు|చెప్పారు|వెల్లడించారు",
    "ml": r"പറഞ്ഞു|വ്യക്തമാക്കി|ആവശ്യപ്പെട്ടു|അറിയിച്ചു|ആരോപിച്ചു|പ്രതികരിച്ചു|കുറ്റപ്പെടുത്തി|കൂട്ടിച്ചേർത്തു|അഭിപ്രായപ്പെട്ടു|ചൂണ്ടിക്കാട്ടി|കുറിച്ചു|പറയുന്നു|വിമർശിച്ചു|പ്രസ്താവിച്ചു|ഓർമിപ്പിച്ചു|പറയുന്നത്|വിശദീകരിച്ചു",
    "or": r"କହିଛନ୍ତି|କହିଥିଲେ|କହିଲେ|ଅଭିଯୋଗ\s+କରିଛନ୍ତି|ସୂଚନା\s+ଦେଇଛନ୍ତି",
    "as": r"কয়|কৈছে|মন্তব্য|জনায়|দাবী",
    "mr": r"सांगितले|सांगितलं|म्हटलं|म्हटले|म्हणाले|म्हणाला|म्हणाल्या",
    "bn": r"দাবি|বলেন|জানান",
    "gu": r"કહ્યું|જણાવ્યું",
}
_SAID_THAT_RE = {lang: re.compile(f"(?:{p}){_THAT}") for lang, p in _SAID_THAT.items()}
_QUOTATIVE_RE = {lang: re.compile(rf"[\W]*(?:{p})(?!\w)") for lang, p in _QUOTATIVE.items()}
_SPEECH_ACT_RE = {lang: re.compile(f"(?:{p})") for lang, p in _SPEECH_ACT.items()}
# The reporter's own framing inside the words: a second "he said that" ("…है.
# उन्होंने इसे … बताया है."), or a quotative and its verb ending a sentence
# ("…ಎಂದು ಆರೋಪಿಸಿದರು.") — the span ran on past what was reported.
_NOT_A_LETTER = r"(?![ऀ-ॿ])"
_REPORTER_INSIDE = {
    "hi": re.compile(r"(?:उन्होंने|उनका|उनके)(?:\s+\S+){0,10}?\s+(?:कहा|बताया|कहना\s+(?:है|था)|मुताबिक|अनुसार)"
                     rf"{_NOT_A_LETTER}(?:\s*(?:कि|,|-|:)|\s+है\s*[.।])"),
    "ur": re.compile(r"(?:انہوں نے|انھوں نے|ان کا|ان کے)(?:\s+\S+){0,10}?\s+(?:کہا|بتایا|کہنا\s+(?:ہے|تھا)|مطابق)\s*(?:کہ|،|,)"),
    **{lang: re.compile(rf"(?:{q})(?:\s+\S+){{0,8}}?\s+(?:{_SPEECH_ACT[lang]})\S*\s*[.।]") for lang, q in _QUOTATIVE.items()},
}
# Malayalam fuses its quotative onto the last word ("…സ്വീകരിക്കണമെന്ന്").
_FUSED_QUOTATIVE = re.compile(r"(?:ന്ന്|ന്നും)$")
# A sentence ends at a danda, "?", "!", or a full stop after a word of four or
# more characters — "ಡಾ." and "ಎಚ್.ಸಿ." are initials, not sentence ends.
_REPORT_END = re.compile(r"[।॥۔!?]|(?<=[^\s.]{4})\.(?=\s|$)")

# Consonant skeletons: speaker names are canonicalised to English by the
# extractor, while the article prints them in its script. Every Brahmic block
# (Devanagari U+0900 … Malayalam U+0D00) shares one layout, so one table of
# offsets reads nine scripts; Urdu has its own. Classes merge what one script
# cannot tell apart (Tamil has one letter for k/g, one for t/d, one for c/s).
_BRAHMIC = {
    0x01: "n", 0x02: "n", 0x0B: "r", 0x43: "r", 0x44: "r", 0x60: "r",
    0x15: "k", 0x16: "k", 0x17: "k", 0x18: "k", 0x19: "n",
    0x1A: "s", 0x1B: "s", 0x1C: "s", 0x1D: "s", 0x1E: "n",
    0x1F: "t", 0x20: "t", 0x21: "t", 0x22: "t", 0x23: "n",
    0x24: "t", 0x25: "t", 0x26: "t", 0x27: "t", 0x28: "n", 0x29: "n",
    0x2A: "p", 0x2B: "p", 0x2C: "p", 0x2D: "p", 0x2E: "n",
    0x30: "r", 0x31: "r", 0x32: "l", 0x33: "l", 0x34: "l", 0x36: "s", 0x37: "s", 0x38: "s",
    0x58: "k", 0x59: "k", 0x5A: "k", 0x5B: "s", 0x5C: "r", 0x5D: "r", 0x5E: "p",
    0x7A: "n", 0x7B: "n", 0x7C: "r", 0x7D: "l", 0x7E: "l", 0x7F: "k",
}
_ARABIC = {
    "ب": "p", "پ": "p", "ت": "t", "ٹ": "t", "ث": "s", "ج": "s", "چ": "s", "خ": "k", "د": "t", "ڈ": "t", "ذ": "s",
    "ر": "r", "ڑ": "r", "ز": "s", "ژ": "s", "س": "s", "ش": "s", "ص": "s", "ض": "s", "ط": "t", "ظ": "s", "غ": "k",
    "ف": "p", "ق": "k", "ک": "k", "ك": "k", "گ": "k", "ل": "l", "م": "n", "ن": "n", "ں": "n",
}
_LATIN_DIGRAPHS = (("sh", "s"), ("ch", "s"), ("th", "t"), ("dh", "t"), ("bh", "p"), ("ph", "p"), ("kh", "k"), ("gh", "k"), ("jh", "s"))
_LATIN_CLASS = str.maketrans({"g": "k", "q": "k", "c": "k", "x": "k", "j": "s", "z": "s", "d": "t", "b": "p", "f": "p", "m": "n"})
_REPEAT = re.compile(r"(.)\1+")
_NAME_SPLIT = re.compile(r"[\s.]+")


def _native_skeleton(word: str) -> str:
    out = []
    for ch in word:
        cp = ord(ch)
        c = _BRAHMIC.get(cp & 0x7F) if 0x0900 <= cp <= 0x0D7F else _ARABIC.get(ch)
        if c:
            out.append(c)
    return _REPEAT.sub(r"\1", "".join(out))


def _latin_skeleton(word: str) -> str:
    w = re.sub(r"[^a-z]", "", word.lower())
    for a, b in _LATIN_DIGRAPHS:
        w = w.replace(a, b)
    return _REPEAT.sub(r"\1", re.sub(r"[aeiouyhvw]", "", w).translate(_LATIN_CLASS))


def named_in(speaker: str, text: str) -> bool:
    """Is this (English-spelled) speaker named in `text`, in the article's own
    script? The surname's skeleton, three consonants or more, opening a word
    (a case ending may follow: "ಸಿದ್ದರಾಮಯ್ಯನವರು"), or every part of the name in
    a row. Shorter names prove nothing on their own."""
    names = [s for s in (_latin_skeleton(w) for w in _NAME_SPLIT.split(speaker)) if s]
    words = [s for s in (_native_skeleton(w) for w in _NAME_SPLIT.split(text)) if s]
    if not names:
        return False
    if len(names[-1]) >= 3 and any(w.startswith(names[-1]) for w in words):
        return True
    n = len(names)
    return n > 1 and any(all(words[i + j].startswith(names[j]) for j in range(n)) for i in range(len(words) - n + 1))


def _reported(flat: str, s: int, e: int, speaker: str, lang: str) -> str | None:
    """Why the unquoted words flat[s:e] are not the speaker's reported speech,
    or None when they are: a speech verb attributes them in the language's own
    pattern, and the speaker is named where the nearest-speaker rule looks —
    NEAR_CHARS before the words, or after them in the attribution itself."""
    ends = [m.end() for m in _REPORT_END.finditer(flat, max(0, s - NEAR_CHARS), s)]
    sentence_before = flat[ends[-1] if ends else max(0, s - NEAR_CHARS):s]
    attribution = ""  # after the words: the quotative up to its speech verb
    if lang in _SAID_THAT_RE and _SAID_THAT_RE[lang].search(sentence_before):
        pass  # "…X ने कहा कि" right before the words
    elif lang in _QUOTATIVE_RE and ((q := _QUOTATIVE_RE[lang].match(flat, e, e + 40)) or (lang == "ml" and _FUSED_QUOTATIVE.search(flat, s, e))):
        at = q.end() if q else e
        said = q and _SPEECH_ACT_RE[lang].search(q.group())  # "…ಎಂದರು": the quotative is the verb
        verb = None if said else _SPEECH_ACT_RE[lang].search(flat, at, at + NEAR_CHARS)
        if not said and (verb is None or _REPORT_END.search(flat, at, verb.start())):
            return "not_quoted"
        attribution = flat[e:verb.end() if verb else at]
    else:
        return "not_quoted"
    if not named_in(speaker, flat[max(0, s - NEAR_CHARS):s] + " " + attribution):
        return "not_named"
    if named_in(speaker, flat[s:e]) or (lang in _REPORTER_INSIDE and _REPORTER_INSIDE[lang].search(flat, s, e)):
        return "narration"
    return None


def check_quote(
    text: str, quote: str, speaker: str, start: int | None = None, lang: str | None = None,
) -> tuple[str | None, str, int, str]:
    """Why these words may not be shown as the speaker's (None when they may),
    the words as shown, where they start in flat_ws(text), and how the article
    gives them: "direct" (inside its quotation marks) or "reported" (an
    Indian-language article's "X said that…", when `lang` is one).

    `start` is the stored span, trusted only while the words are still there.
    The quotation marks the model sometimes copies with the words are trimmed:
    they are the article's punctuation, and the card prints its own.
    """
    flat = flat_ws(text)
    quote = flat_ws(quote)
    if start is None or flat[start:start + len(quote)] != quote:
        start = flat.find(quote) if quote else -1
        if start < 0:
            return "not_verbatim", quote, -1, "direct"
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
    speech = "direct"
    if raw is None or not _quoted(text, *raw):
        if not trimmed or lang not in REPORTED_LANGS:
            return "not_quoted", trimmed, start, speech
        why = _reported(flat, start, start + len(trimmed), speaker, lang)
        if why:
            return why, trimmed, start, speech
        speech = "reported"
    if len(trimmed.split()) < MIN_QUOTE_WORDS or _WORD_LIST.fullmatch(trimmed):
        return "fragment", trimmed, start, speech
    if _narrates(trimmed, speaker):
        return "narration", trimmed, start, speech
    return None, trimmed, start, speech


def verify_claims(claims: list[Claim], clean_text: str, lang: str | None = None) -> tuple[list[Claim], dict[str, int]]:
    """Keep the claims whose quote really appears in the article, inside its
    quotation marks — or, in an Indian-language article (`lang`), reported
    with a speech verb beside the speaker's name. Repair spans.

    Returns (kept, rejected_by_reason). The reasons are counted rather than
    discarded so extraction quality stays measurable without re-reading articles.
    """
    rejected = {"no_speaker": 0, "short_quote": 0, "not_verbatim": 0, "not_quoted": 0, "not_named": 0,
                "narration": 0, "fragment": 0}
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
        why, quote, at, _ = check_quote(clean_text, quote, c.speaker, at, lang)
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
    printed the same words, `speech` says how this article gives them
    ("direct" or "reported", check_quote)."""

    speaker: str
    quote: str
    start: int | None
    end: int | None
    src: Mapping[str, Any]
    role: str | None = None
    also: tuple[Said, ...] = ()
    speech: str = "direct"


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
    ×4): the earliest report is the citation, the rest ride on it as `also`;
    an outlet that quoted the words outranks one that only reported them.
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
        # The quoted words lead over a report of them, then the earliest report.
        lead, other = (s, r) if (s.speech != "direct", _published(s)) < (r.speech != "direct", _published(r)) else (r, s)
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
