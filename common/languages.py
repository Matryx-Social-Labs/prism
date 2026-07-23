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


LANGUAGES: dict[str, Language] = {
    "en": Language("en", "English", "English"),
    "hi": Language("hi", "Hindi", "हिन्दी"),
    "kn": Language("kn", "Kannada", "ಕನ್ನಡ"),
    "ta": Language("ta", "Tamil", "தமிழ்"),
}

# The Bangalore-launch set the onboarding picker offers, in display order.
LAUNCH_LANGUAGES: list[str] = ["en", "hi", "kn"]
# Sensible default when a reader hasn't chosen (broad national coverage).
DEFAULT_LANGUAGES: list[str] = ["en", "hi"]


def is_valid_language(code: str) -> bool:
    return code in LANGUAGES


def offered() -> list[dict]:
    """Payload for /api/v1/languages — the onboarding picker renders whatever
    this returns (same data-driven contract as the lens picker)."""
    return [
        {"code": LANGUAGES[c].code, "name": LANGUAGES[c].name, "native": LANGUAGES[c].native}
        for c in LAUNCH_LANGUAGES
        if c in LANGUAGES
    ]
