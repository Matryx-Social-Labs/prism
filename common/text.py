"""Text utilities shared across stages."""


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
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
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
    return re.sub(r"\s+", " ", s).strip()


def entity_slug(name: str) -> str:
    """Identity slug for an entity, folding punctuation variants together."""
    return slugify(canonical_entity_name(name))


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
)


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
