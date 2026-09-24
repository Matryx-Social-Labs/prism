"""Which report each line of a brief came from, and whether its figures are there.

Phase 2 of the trust plan (.claude/plans/trust-india-indic.plan.md): every line
Prism writes should point at the report it restates, and a figure in a line must
be a figure in that report. Computed where every brief is saved (persist_briefs)
and stored beside it as projection.lens_cites; SHADOW until a labelled sample
confirms the rate (the plan's gate is 99.5% of reported lines evidenced), so no
page reads it yet.

Deterministic, no model: a model asked to cite invents citations as readily as
facts. Three ways a line gets its reports:
- single: the record has one report, which the brief was written from.
- lexical: the reports whose wording carries most of the line's content words
  (English reports; an Indian-language report shares no words with an English
  line, so it can only be cited by construction or by a figure).
- figures: no report shares the words, but one carries every figure the line
  states.
A line whose figures appear in none of its reports is `supported: false`: the
one thing a brief must never do is state a number its reports do not contain.
"""

import re
import uuid

# Indian-script digits read as the same numbers: a Hindi report printing ५.५ and
# an English brief saying 5.5 agree.
_DIGITS = str.maketrans({
    chr(base + i): str(i)
    for base in (0x0966, 0x09E6, 0x0A66, 0x0AE6, 0x0B66, 0x0BE6, 0x0C66, 0x0CE6, 0x0D66)
    for i in range(10)
})
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_WORD = re.compile(r"[a-z][a-z'-]{3,}")
_STOP = frozenset(
    "that this with from have been were will would said says also their there which about after before "
    "into over than them they when what where while more most such only other some could should these "
    "those being during under against between through still just very much many made make take taken".split()
)
# "N." in "N. Chandrasekaran", "Rs." — not the end of a sentence (mirrors web/src/lib/sentences.ts).
_NOT_AN_END = re.compile(
    r"(?:^|[\s(“\"'])(?:[A-Z]|Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|No|Nos|Rs|Re|vs|Lt|Col|Gen|Maj|Capt|Sgt|Hon|Rev|Fr|Smt|Shri|Md|Adv|"
    r"Justice|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|Inc|Ltd|Pvt|Co|Corp|Govt|Dept|Univ|approx|est)\.$"
)
# A sentence ends at . ! ? (and a closing quote) followed by a space; "5.5" does not end one.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|(?<=[.!?][\"’”])\s+")
LEXICAL_MIN = 0.5  # share of a line's content words a report must carry to be cited for it
MAX_CITES = 3


def split_lines(text: str) -> list[str]:
    """The brief one sentence per line, as the page prints it."""
    out: list[str] = []
    for s in (m.strip() for m in _SENTENCE_END.split((text or "").strip())):
        if not s:
            continue
        if out and _NOT_AN_END.search(out[-1]):
            out[-1] = f"{out[-1]} {s}"
        else:
            out.append(s)
    return out


def figures(text: str) -> set[str]:
    return {n.replace(",", "").rstrip(".") for n in _NUMBER.findall((text or "").translate(_DIGITS))}


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if w not in _STOP}


def cite_lines(text: str, reports: list[tuple[uuid.UUID, str]]) -> list[dict]:
    """[{text, cites: [article_id], method, supported}] for each line of `text`."""
    prepared = [(str(aid), _words(body), figures(body)) for aid, body in reports if body]
    out = []
    for line in split_lines(text):
        need = figures(line)
        words = _words(line)
        if len(prepared) == 1:
            cites, method = [prepared[0][0]], "single"
        else:
            scored = sorted(
                ((len(words & w) / len(words), aid) for aid, w, _ in prepared if words),
                reverse=True,
            )
            cites = [aid for score, aid in scored if score >= LEXICAL_MIN][:MAX_CITES]
            method = "lexical" if cites else "none"
            if not cites and need:
                cites = [aid for aid, _, f in prepared if need <= f][:MAX_CITES]
                method = "figures" if cites else "none"
        cited_figures = set().union(*(f for aid, _, f in prepared if aid in cites)) if cites else set()
        out.append({"text": line, "cites": cites, "method": method, "supported": bool(cites) and need <= cited_figures})
    return out
