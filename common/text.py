"""Text utilities shared across stages."""

import re
import unicodedata

# Function words a headline shares with any page. English only: the other
# scripts' function words are short enough that the length floor drops them.
_STOPWORDS = frozenset(
    """the and but for from with are was were been being this that these those its into over after before
    about than then has have had not will would can could may might shall should does did they you his her
    their our your him them who whom which what when where why how all any some more most other such only
    own same too very just also new says said say amid upon via""".split()
)


def _words(text: str) -> list[str]:
    """Case-folded runs of letters, marks and digits. Marks are kept: Python's
    `\\w` does not match a Kannada or Devanagari vowel sign, so a regex tokenizer
    cuts every Indic word into fragments and finds no overlap anywhere."""
    return "".join(ch if unicodedata.category(ch)[0] in "LMN" else " " for ch in text.casefold()).split()


def title_share(title: str, text: str) -> float | None:
    """The fraction of a headline's content words that the text contains, or
    None when the headline has fewer than three — too little to judge by.

    A word counts when its stem (the word less up to two final letters) appears
    anywhere in the text, so an inflected form still counts: Kannada and Malayalam
    fuse case endings onto the noun a headline uses bare."""
    words = {w for w in _words(title) if len(w) >= 3 and not w.isdigit() and w not in _STOPWORDS}
    if len(words) < 3:
        return None
    haystack = " ".join(_words(text))
    return sum(1 for w in words if w[: max(4, len(w) - 2)] in haystack) / len(words)


# The model writing ABOUT its input instead of reporting news. Every alternative
# is a phrase seen in production 2026-09-27 (byline bios read as articles), and
# each is narrow on purpose. Scanned against 29,350 extractions and 27,409 stored
# briefs: "does not provide immunity" is a court ruling, and "the article does
# not specify", "provides no figures", "rather than news of a decision" are
# briefs naming a gap or framing a story — the product working. Looser patterns
# flagged all of them.
_MODEL_COMMENTARY = re.compile(
    r"\bthe provided (?:article |news )?(?:text|article|content|snippet|input|excerpt|passage)\b"
    r"|\b(?:the|this) (?:article|text) (?:is|serves as) (?:a|an) (?:author|journalist|biograph|profile of)"
    r"|\b(?:article|text) profiles\b[^.]{0,80}\b(?:correspondent|journalist|reporter|editor)\b"
    r"|\bdescribes the (?:author|journalist)"
    r"|\bdoes not report on (?:a |an |any )"
    r"|\bno news (?:content|event|report|story)"
    r"|\b(?:author|journalist|correspondent)(?:['’]s)? (?:bio|biography|biographical|profile)\b"
    r"|\b(?:biography|biographical profile|professional (?:background|biography)) of (?:a |an |the )?"
    r"(?:journalist|correspondent|author|reporter)\b",
    re.IGNORECASE,
)


def is_model_commentary(text: str | None) -> bool:
    """True when a model's output describes the text it was given ("The provided
    text contains the biography of a journalist…") rather than reporting news."""
    return bool(text and _MODEL_COMMENTARY.search(text))


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> list[str]:
    """Split text into chunks near paragraph boundaries with a small overlap."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            # Prefer to break at a paragraph, then a sentence, then a space.
            for sep in ("\n\n", ". ", " "):
                cut = text.rfind(sep, start + max_chars // 2, end)
                if cut != -1:
                    end = cut + len(sep)
                    break
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def slugify(value: str) -> str:
    """Identity key for a name. Unicode-aware, because our entities are not ASCII.

    This was `[^a-z0-9]+` — an ASCII-only class that DELETED every other script
    rather than transliterating it. Nine Indian-language feeds now ingest, so the
    moment extraction emits a native-script name that rule fails in the worst
    available way: every Devanagari, Kannada, Bengali, Tamil and Urdu name folds
    to the empty string and then to the SAME fallback slug, so unrelated people
    become one entity with an enormous document frequency. Silent, and shaped
    exactly like a working system.

        entity_slug("भारतीय जनता पार्टी")  ->  "unknown"
        entity_slug("ನರೇಂದ್ರ ಮೋದಿ")        ->  "unknown"     # the same entity

    Latin diacritics are folded (`Ávila` == `Avila`) — the old rule dropped the
    accented letter outright and produced `vila`, a wrong slug rather than an
    obviously broken one. Marks in Indic scripts are NOT folded: a Devanagari
    matra or a Kannada vowel sign is a letter, not an accent, and stripping it
    would mangle the name into a different one. So the fold is applied per
    character and only where the base is Latin.
    """
    import re
    import unicodedata

    out = []
    for ch in unicodedata.normalize("NFKC", value):
        d = unicodedata.normalize("NFKD", ch)
        if d and unicodedata.name(d[0], "").startswith("LATIN"):
            out.append("".join(c for c in d if not unicodedata.combining(c)))
        else:
            out.append(ch)
    # Keep letters, marks and digits; everything else is a separator. Marks must
    # survive for the Indic reason above — they are not alphanumeric to Python.
    kept = "".join(
        c if unicodedata.category(c)[0] in "LMN" else "-" for c in "".join(out).casefold()
    )
    slug = re.sub(r"-+", "-", kept).strip("-")
    return slug[:120] or "unknown"


def canonical_entity_name(name: str) -> str:
    """Fold trivial punctuation variants of an entity name so 'D.K. Shivakumar' and
    'DK Shivakumar', or 'Cockroach Janta Party (CJP)' and 'Cockroach Janta Party',
    resolve to one entity (slug = slugify(canonical_entity_name(name))).

    Deterministic and CONSERVATIVE — punctuation only, never fuzzy edit-distance
    (fuzzy over-merges: CVE-2026-11090 and -11109 differ by one char but are distinct;
    fuzzy once merged 1638 CVEs into 7). It does NOT merge spelling variants like
    'Janta'/'Janata' — that needs judgement, not a rule."""
    import re

    s = name.strip()
    # Drop a trailing "(ACRONYM)" only when it's the initials of the preceding words:
    # 'Cockroach Janta Party (CJP)' -> strip; but 'CPI(M)' (M is not CPI's acronym) stays.
    m = re.match(r"^(.*?)\s*\(([A-Za-z]{2,})\)\s*$", s)
    if m:
        head, paren = m.group(1), m.group(2)
        initials = "".join(w[0] for w in re.findall(r"[A-Za-z]+", head))
        if initials.lower() == paren.lower():
            s = head.strip()
    # Collapse intra-word punctuation: D.K. -> DK, O'Brien -> OBrien.
    s = s.replace(".", "").replace("'", "").replace("’", "")
    # Join runs of single-letter initials: "V D Satheesan" -> "VD Satheesan".
    #
    # Without this the dotted and spaced forms of one name are different entities,
    # because removing dots turns "V.D. Satheesan" into "VD Satheesan" while
    # "V D Satheesan" keeps its spaces. Measured in production: vd-satheesan(23)
    # and v-d-satheesan(16) were separate rows for the Kerala LoP, and so were
    # kc-venugopal/k-c-venugopal, ps-narasimha/p-s-narasimha and eleven more.
    # Indian political coverage writes initials both ways constantly.
    #
    # Only single letters adjacent to another single letter are joined, so ordinary
    # words are untouched and a lone initial before a full name ("R Nirmal Kumar")
    # keeps its space — that pairing carries no evidence they are one name.
    s = re.sub(r"\b([A-Za-z])\s+(?=[A-Za-z]\b)", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def entity_slug(name: str) -> str:
    """Identity slug for an entity: punctuation variants fold by rule, spelling
    variants fold only via the curated table (see common/entity_aliases)."""
    from common.entity_aliases import resolve_alias

    return resolve_alias(slugify(canonical_entity_name(name)))


if __name__ == "__main__":
    # Self-check: variants fold, distinct entities do NOT.
    assert entity_slug("D.K. Shivakumar") == entity_slug("DK Shivakumar")
    assert entity_slug("J.P. Nadda") == entity_slug("JP Nadda")
    assert entity_slug("Cockroach Janta Party (CJP)") == entity_slug("Cockroach Janta Party")
    assert entity_slug("CPI(M)") != entity_slug("CPI")          # meaningful paren kept
    assert entity_slug("Janta") != entity_slug("Janata")        # spelling NOT fuzzed
    assert entity_slug("NDTV") != entity_slug("NDRF")           # distinct acronyms
    print("canonical_entity_name self-check OK")


# ── Script detection ────────────────────────────────────────────────────────
# The stored `language` field cannot be used for this: measured 2026-07-28,
# ALL 1,385 non-Latin articles in production are labelled `en` (Prajavani
# 519/519 Kannada, Aaj Tak 530 Devanagari, BBC Tamil 37/37). Zero correct
# labels, so script has to come from the text itself.
_SCRIPT_RANGES = (
    ("kannada", 0x0C80, 0x0CFF),
    ("tamil", 0x0B80, 0x0BFF),
    ("devanagari", 0x0900, 0x097F),
    ("telugu", 0x0C00, 0x0C7F),
    ("bengali", 0x0980, 0x09FF),
    ("malayalam", 0x0D00, 0x0D7F),
    ("gujarati", 0x0A80, 0x0AFF),
    ("gurmukhi", 0x0A00, 0x0A7F),
    ("odia", 0x0B00, 0x0B7F),
    # Arabic script — Urdu, and Kashmiri/Sindhi in the Perso-Arabic orthography.
    # Its absence was NOT harmless. Urdu fell through to "latin", which put it
    # inside EMBEDDING_TRUSTED_SCRIPTS with nothing having validated the embedding
    # there, and — worse — made correlation/partition.py's cross-script guard read
    # an Urdu/English pair as SAME script. content_similarity then compared them,
    # found zero shared words (different alphabets share none) and CUT the edge.
    # That is precisely the absence-of-evidence failure the guard exists to stop,
    # defeated by the script detector rather than by the guard's own logic.
    ("arabic", 0x0600, 0x06FF),
    ("arabic", 0x0750, 0x077F),          # Arabic Supplement
    ("arabic", 0xFB50, 0xFDFF),          # Presentation Forms-A
    ("arabic", 0xFE70, 0xFEFF),          # Presentation Forms-B
)


def is_latin_text(text: str) -> bool:
    """True when the words are written in Latin letters — an English headline,
    even one quoting an Indic word. Unlike detect_script (which names the
    Indic block that leads, for the embedding and cross-script guards, and does
    not count Latin at all), this weighs Latin letters against every other
    script's, so "Court reads ‘न्याय’ into the order" is Latin and a Hindi title
    carrying "UPSC" is not."""
    latin = other = 0
    for ch in text:
        cp = ord(ch)
        if (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A) or (0x00C0 <= cp <= 0x024F):
            latin += 1
        elif any(lo <= cp <= hi for _, lo, hi in _SCRIPT_RANGES):
            other += 1
    return latin > other


def detect_script(text: str) -> str:
    """The dominant script of `text` — 'latin' when no Indic block leads.

    Counts characters per block rather than taking the first hit: Indic
    headlines routinely carry Latin brand names and digits, and an English
    headline may quote a single Indic word.
    """
    if not text:
        return "latin"
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for name, lo, hi in _SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[name] = counts.get(name, 0) + 1
                break
    if not counts:
        return "latin"
    return max(counts.items(), key=lambda kv: kv[1])[0]
