"""Supported reader languages (BCP-47), with native-script display names.

Language is NOT a lens — it never carries color in the UI (DESIGN.md: color only
means a lens is speaking). This registry is the single source of truth for which
languages onboarding offers and how they're labelled. Adding a language later is a
data change here + a source in ingestion/seed.py, not a code change.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str
    name: str  # English name
    native: str  # endonym, shown in the picker so a reader recognises their own


# Every language Prism INGESTS, not only the ones onboarding offers. A quote is
# now labelled with the language the article printed it in, so a language with a
# source but no picker entry would print as a bare "UR" — which reads as a code,
# not a language. `LAUNCH_LANGUAGES` below is still what the picker offers.
LANGUAGES: dict[str, Language] = {
    "en": Language("en", "English", "English"),
    "hi": Language("hi", "Hindi", "हिन्दी"),
    "kn": Language("kn", "Kannada", "ಕನ್ನಡ"),
    "ta": Language("ta", "Tamil", "தமிழ்"),
    "te": Language("te", "Telugu", "తెలుగు"),
    "mr": Language("mr", "Marathi", "मराठी"),
    "bn": Language("bn", "Bengali", "বাংলা"),
    "gu": Language("gu", "Gujarati", "ગુજરાતી"),
    "pa": Language("pa", "Punjabi", "ਪੰਜਾਬੀ"),
    "ur": Language("ur", "Urdu", "اردو"),
    "ml": Language("ml", "Malayalam", "മലയാളം"),
    "or": Language("or", "Odia", "ଓଡ଼ିଆ"),
    "as": Language("as", "Assamese", "অসমীয়া"),
}

# The Bangalore-launch set the onboarding picker offers, in display order.
LAUNCH_LANGUAGES: list[str] = ["en", "hi", "kn"]
# Sensible default when a reader hasn't chosen (broad national coverage).
DEFAULT_LANGUAGES: list[str] = ["en", "hi"]


def is_valid_language(code: str) -> bool:
    return code in LANGUAGES


def display_name(code: str | None) -> str:
    """The language's English name, for a label a reader reads once.

    An unknown code prints as itself uppercased rather than raising: this
    labels quotes on the most-read route, and a source added to
    ingestion/seed.py before its entry here must degrade to "UR", never to a
    500."""
    if not code:
        return ""
    lang = LANGUAGES.get(code)
    return lang.name if lang else code.upper()


def offered() -> list[dict]:
    """Payload for /api/v1/languages — the onboarding picker renders whatever
    this returns (same data-driven contract as the lens picker)."""
    return [
        {"code": LANGUAGES[c].code, "name": LANGUAGES[c].name, "native": LANGUAGES[c].native}
        for c in LAUNCH_LANGUAGES
        if c in LANGUAGES
    ]
