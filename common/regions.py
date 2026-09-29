"""Indian states/UTs (ISO 3166-2:IN) — the onboarding location vocabulary.

Country is India for now (international is out); the reader picks their state so
the feed can surface local(state) news first, then national. `covered` marks the
states we currently have a state-edition source for — the rest still get national
news and gain a local tier as we add feeds.
"""

import re

# (ISO 3166-2 code, display name)
IN_STATES: list[tuple[str, str]] = [
    ("IN-AP", "Andhra Pradesh"), ("IN-AR", "Arunachal Pradesh"), ("IN-AS", "Assam"),
    ("IN-BR", "Bihar"), ("IN-CT", "Chhattisgarh"), ("IN-GA", "Goa"), ("IN-GJ", "Gujarat"),
    ("IN-HR", "Haryana"), ("IN-HP", "Himachal Pradesh"), ("IN-JH", "Jharkhand"),
    ("IN-KA", "Karnataka"), ("IN-KL", "Kerala"), ("IN-MP", "Madhya Pradesh"),
    ("IN-MH", "Maharashtra"), ("IN-MN", "Manipur"), ("IN-ML", "Meghalaya"),
    ("IN-MZ", "Mizoram"), ("IN-NL", "Nagaland"), ("IN-OD", "Odisha"), ("IN-PB", "Punjab"),
    ("IN-RJ", "Rajasthan"), ("IN-SK", "Sikkim"), ("IN-TN", "Tamil Nadu"),
    ("IN-TG", "Telangana"), ("IN-TR", "Tripura"), ("IN-UP", "Uttar Pradesh"),
    ("IN-UK", "Uttarakhand"), ("IN-WB", "West Bengal"),
    # Union territories
    ("IN-AN", "Andaman & Nicobar"), ("IN-CH", "Chandigarh"),
    ("IN-DH", "Dadra & Nagar Haveli and Daman & Diu"), ("IN-DL", "Delhi"),
    ("IN-JK", "Jammu & Kashmir"), ("IN-LA", "Ladakh"), ("IN-LD", "Lakshadweep"),
    ("IN-PY", "Puducherry"),
]

# States with a dedicated state-edition source today (see ingestion/rss.py).
COVERED = {"IN-TN", "IN-KL", "IN-KA", "IN-AP", "IN-TG", "IN-DL", "IN-MH", "IN-OD", "IN-AS"}

_VALID = {code for code, _ in IN_STATES}


def is_valid_state(code: str) -> bool:
    return code in _VALID


def states_payload() -> list[dict]:
    return [{"code": c, "name": n, "covered": c in COVERED} for c, n in IN_STATES]


def is_state_code(code: str) -> bool:
    """True for a real ISO 3166-2:IN code we know (IN-KA), false for IN-BLR and friends."""
    return code in _VALID


# The states and union territories with a hub page, /state/<slug> (marketing
# audit 02, P1-1): the 33 names web/src/lib/regions.ts carries. Andaman &
# Nicobar, Dadra & Nagar Haveli and Daman & Diu, and Lakshadweep have no hub:
# the web names none of them and the corpus places almost nothing there.
_NO_HUB = {"IN-AN", "IN-DH", "IN-LD"}
HUB_STATES: list[tuple[str, str]] = [(c, n) for c, n in IN_STATES if c not in _NO_HUB]


def state_slug(name: str) -> str:
    """"Jammu & Kashmir" -> "jammu-and-kashmir". The hub's address, and the slug
    the entity folder gives the same name, so /entity/<slug> can defer to the
    hub instead of competing with it for "<state> news" (the same rule as
    web/src/lib/regions.ts stateSlug)."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower().replace("&", "and")).strip("-")


# slug -> ISO code, for every hub.
HUB_SLUGS: dict[str, str] = {state_slug(n): c for c, n in HUB_STATES}
