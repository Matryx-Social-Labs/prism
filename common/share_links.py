"""Founder share links (/admin/marketing, 2026-09-29): a link to one Prism page
made for one platform, with its UTM tags and a short address, and what the
visits it brought went on to do.

A link is a row in share_links: a 6-character code, the page it opens, the
platform, the medium and the campaign. Its tags carry the code in utm_content;
a visit that arrives with a code counts one `link:<code>`, and what that visit
(that browser tab) goes on to do counts one `goal:<code>:<goal>`. They are
counted the way every usage count is (common/usage.py): a daily total of a
word, never who. The code is the only word a visitor sends, and it counts only
when it is a row here, so a script cannot write new rows into the dashboard
(usage.py's closed-list rule, with the list kept in a table because founders
add to it without a deploy).

`account` is never sent by a browser: the API counts it when a sign-in that
carried a code creates an account (api/routes/auth.py), and stores the code
nowhere on the account.
"""

from __future__ import annotations

import re
import secrets
import time
from datetime import date
from typing import Any
from urllib.parse import urlencode, urlsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common import usage

# Platform → the medium a link for it gets unless the founder picks another.
# Every one is a campaign word (usage.CAMPAIGNS), so the Overview's "by
# platform" count sees founder links and hand-made ?ref= links alike.
PLATFORMS: dict[str, str] = {
    "x": "social", "instagram": "social", "linkedin": "social", "facebook": "social", "threads": "social",
    "youtube": "social", "reddit": "community", "whatsapp": "message", "telegram": "message",
    "email": "email", "newsletter": "email", "producthunt": "launch", "hn": "launch", "peerlist": "launch",
    "launchpadindia": "launch", "devto": "community", "press": "press",
}
MEDIA = frozenset({"social", "message", "email", "community", "launch", "partner", "press", "paid"})
# What a visit that came by a link did next, in that tab: a 2nd story, a sign-in
# asked for, an account made (API only), the Plus page, the weekly email.
GOALS = frozenset({"read2", "signin", "account", "plus", "digest"})
BROWSER_GOALS = GOALS - {"account"}

# No 0/o or 1/l/i: a code is read off a phone and typed into another.
CODE_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"
CODE_LENGTH = 6
CODE = re.compile(r"[2-9a-hjkmnp-z]{6}")
CAMPAIGN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
CAMPAIGN_MAX = 32

# The pages a link may open, by first path segment, and what the admin calls
# them. Accounts, sign-in, the labeller and the admin are not on the list.
PAGES: dict[str, str] = {
    "": "landing", "about": "about", "plus": "plus", "feed": "feed", "archive": "archive", "story": "story",
    "trending": "trending", "entity": "entity", "state": "state", "sector": "sector", "subject": "subject",
    "sources": "sources", "pulse": "pulse", "press": "press", "for-publishers": "publishers",
}
SEGMENT = re.compile(r"[A-Za-z0-9._~%-]{1,120}")
SITE_HOSTS = frozenset({"readprism.news", "www.readprism.news"})


def target_path(value: str, web_url: str) -> str | None:
    """The page a link opens, as a path on this site, or None when it is not one
    of ours. Takes a path or a full address; drops the query and the fragment,
    since the link's own tags are the only query it carries."""
    v = value.strip()
    if not v or v.startswith("//"):
        return None
    if not v.startswith("/"):
        u = urlsplit(v if "://" in v else f"https://{v}")
        if u.scheme not in ("http", "https") or u.hostname not in SITE_HOSTS | {urlsplit(web_url).hostname}:
            return None
        v = u.path or "/"
    path = urlsplit(v).path.rstrip("/") or "/"
    segments = path.strip("/").split("/") if path != "/" else []
    if len(segments) > 4 or any(not SEGMENT.fullmatch(s) for s in segments):
        return None
    return path if (segments[0] if segments else "") in PAGES else None


def kind(path: str) -> str:
    """What the admin calls the page: a story, a quote, a day, a state…"""
    segments = path.strip("/").split("/") if path != "/" else [""]
    if segments[0] == "story" and len(segments) == 4 and segments[2] == "quote":
        return "quote"
    if segments[0] == "feed" and len(segments) == 2:
        return "day"
    return PAGES[segments[0]]


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def tags(row: dict[str, Any]) -> dict[str, str]:
    """The UTM tags, in the order people read them. No campaign, no utm_campaign."""
    t = {"utm_source": row["platform"], "utm_medium": row["medium"]}
    if row["campaign"]:
        t["utm_campaign"] = row["campaign"]
    return {**t, "utm_content": row["code"]}


def long_url(web_url: str, row: dict[str, Any]) -> str:
    return f"{web_url.rstrip('/')}{row['path']}?{urlencode(tags(row))}"


def short_url(web_url: str, code: str) -> str:
    """readprism.news/go/<code>: the bare host, which is what people type; it
    redirects to www with the path intact."""
    base = web_url.rstrip("/").replace("://www.", "://", 1)
    return f"{base}/go/{code}"


# The codes a beacon may count. ponytail: every code in memory per worker,
# fine for thousands of links; an indexed lookup per miss if it ever is not.
LIVE_TTL_S = 60
# A code not in memory reloads the set, at most this often: a link made on
# another worker counts within seconds, and a script sending made-up codes
# costs one small query every few seconds, not one per request.
MISS_RELOAD_S = 5
_codes: tuple[float, frozenset[str]] = (float("-inf"), frozenset())


async def known(db: AsyncSession, code: str) -> bool:
    global _codes
    if not CODE.fullmatch(code):
        return False
    loaded, codes = _codes
    age = time.monotonic() - loaded
    if age > LIVE_TTL_S or (code not in codes and age > MISS_RELOAD_S):
        codes = frozenset((await db.execute(text("SELECT code FROM share_links"))).scalars().all())
        _codes = (time.monotonic(), codes)
    return code in codes


def forget() -> None:
    """Drop the cached codes (a link was just made here, or a test reset)."""
    global _codes
    _codes = (float("-inf"), frozenset())


async def dimension(db: AsyncSession, event: str, d: str) -> str | None:
    """The word a `link` or `goal` beacon is counted under, or None to drop it."""
    d = d.lower()
    if event == "link":
        return d if await known(db, d) else None
    code, _, goal = d.partition(":")
    return d if goal in BROWSER_GOALS and await known(db, code) else None


async def count_account(db: AsyncSession, code: str | None) -> None:
    """A sign-in that carried a link's code made an account: one more for the link."""
    if code and await known(db, code.lower()):
        await usage.bump(db, "goal", f"{code.lower()}:account")


async def performance(db: AsyncSession, start: date, end: date) -> dict[str, dict[str, Any]]:
    """Per code, over [start, end]: visits in all and by day, and each goal."""
    rows = (await db.execute(text(
        "SELECT day, event, dim, count FROM usage_daily WHERE event IN ('link', 'goal') AND day BETWEEN :a AND :b"),
        {"a": start, "b": end})).mappings().all()
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        code, _, goal = r["dim"].partition(":")
        p = out.setdefault(code, {"visits": 0, "by_day": {}, "goals": dict.fromkeys(sorted(GOALS), 0)})
        if r["event"] == "link":
            p["visits"] += r["count"]
            p["by_day"][r["day"]] = p["by_day"].get(r["day"], 0) + r["count"]
        elif goal in GOALS:
            p["goals"][goal] += r["count"]
    return out
