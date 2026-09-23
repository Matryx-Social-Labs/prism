"""Counting how Prism is used, without knowing who (admin dashboard, phase 3).

FOUNDER DECISIONS D2/D3 (2026-09-23): first-party, cookieless counts in our own
Postgres, so visits, sign-ups and subscriptions can be read side by side; and
the days a signed-in account was active, so retention can be measured.

What is kept: per IST day, a count per (event, dimension) in usage_daily, and
(day, account) pairs in user_days. The dimension is a word from a fixed set or
a short slug — a kind of page, never which story; where a visit came from,
never the full referrer; how Ask was opened, never the question.

How a visitor is counted once a day without an identifier: sha256(daily salt,
IP, browser) goes into a Redis set for that day. The salt is random, made the
first time it is needed each day, and deleted with the set within two days, so
a hash cannot be tied to a person or to another day, and none reaches Postgres
— the table holds only the count. The same salt keys the per-visitor cap that
stops one script inflating the numbers.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.lenses import LENSES
from common.logging import get_logger

logger = get_logger(__name__)

IST = ZoneInfo("Asia/Kolkata")
TWO_DAYS_S = 2 * 24 * 60 * 60
# Beacons one visitor may send in a day before the rest are dropped. A reader
# who opens forty stories sends ~100; a script sends thousands.
EVENTS_PER_VISITOR_PER_DAY = 400
# The same, per ADDRESS, whatever browser it claims to be. The visitor hash
# includes the User-Agent, which the caller writes: rotating it minted a new
# visitor (and a fresh cap) per request from one machine (review, 2026-09-23).
# These are the ceilings a script cannot rotate its way past. Generous,
# because Indian mobile carriers put many readers behind one address (CGNAT).
# ponytail: a fixed per-address ceiling undercounts a busy carrier NAT; raise
# it or key on a /24 if the dashboard ever shows addresses pinned at it.
EVENTS_PER_IP_PER_DAY = 5000
NEW_VISITORS_PER_IP_PER_DAY = 50

# Kinds of page (web/src/lib/analytics.pageKind is the other half of this list).
PAGES = frozenset({
    "landing", "about", "feed", "story", "quote", "trending", "subject", "sector", "entity", "pulse",
    "search", "plus", "account", "signin", "label", "legal", "other",
})
SHARE_SURFACES = frozenset({"story", "quote", "trending", "other"})
SIGNIN_METHODS = frozenset({"link", "google"})
# Every word below is a closed list, never a pattern: a pattern let a script
# write a new row per request ("lens:<random>:open") into a table investors
# read (review, 2026-09-23). The web's own vocabularies, mirrored.
ASK_VIA = frozenset({"bar", "foot", "thumb", "selection", "quote", "entity", "chip"})  # AskContext.AskVia
LENS_STATES = frozenset({f"{slug}:{state}" for slug in LENSES for state in ("open", "locked")})
SUBSCRIBE_STAGES = frozenset({"prompt", "page", "welcome", "cancel-sheet", "paused", "cancelled",
                              "switched-yearly", "checkout", "paid"})
SUBSCRIBE_DETAIL = frozenset({
    "ask-limit", "ask-rest", "generic", "account", "header", "direct",  # the door (UpgradeReason, ?from=)
    "not-using", "too-expensive", "missing-something", "other", "none",  # billing.CancelReason
    "plus_monthly", "plus_yearly", "founding",  # common/billing plan ids
})
HOST = re.compile(r"^[a-z0-9.-]{1,253}$")

# Where an arrival came from, by referrer host. Suffix match on the host.
SOURCES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("search", ("google.com", "google.co.in", "bing.com", "duckduckgo.com", "yahoo.com", "yandex.ru",
                "ecosia.org", "baidu.com", "search.brave.com")),
    ("ai", ("chatgpt.com", "chat.openai.com", "perplexity.ai", "claude.ai", "gemini.google.com",
            "copilot.microsoft.com")),
    ("social:whatsapp", ("whatsapp.com", "wa.me")),
    ("social:x", ("t.co", "x.com", "twitter.com")),
    ("social:facebook", ("facebook.com", "fb.com", "m.facebook.com", "l.facebook.com")),
    ("social:instagram", ("instagram.com", "l.instagram.com")),
    ("social:linkedin", ("linkedin.com", "lnkd.in")),
    ("social:reddit", ("reddit.com",)),
    ("social:telegram", ("t.me", "telegram.org")),
)

# Fetchers that are not readers. Most never run the beacon (no JavaScript); the
# ones that do announce themselves here.
BOT = re.compile(r"bot|crawl|spider|slurp|headless|lighthouse|preview|curl|wget|python-|httpx|axios|"
                 r"node-fetch|go-http|java/|okhttp|phantomjs|puppeteer|playwright", re.IGNORECASE)


def today() -> date:
    return datetime.now(IST).date()


def is_bot(user_agent: str) -> bool:
    return not user_agent or bool(BOT.search(user_agent))


def source(ref_host: str, shared: str) -> str:
    """Where an arrival came from. A link carrying `?s=<surface>` came from a
    Share button, whatever app it travelled through — chat apps often strip the
    referrer, so the marker is the reliable half."""
    if shared in SHARE_SURFACES:
        return f"share:{shared}"
    host = ref_host.lower().strip(".")
    if not host:
        return "direct"
    if not HOST.match(host):
        return "other"
    for name, domains in SOURCES:
        if any(host == d or host.endswith("." + d) for d in domains):
            return name
    return "other"


def dimension(event: str, d: str, ref: str = "", s: str = "") -> str | None:
    """The one word stored for an event, or None to drop it. Everything the
    client sends is checked against a fixed set or a short slug pattern."""
    d = d.lower()
    if event == "view":
        return d if d in PAGES else None
    if event == "arrival":
        return source(ref, s)
    if event == "share":
        return d if d in SHARE_SURFACES else None
    if event == "signin":
        return d if d in SIGNIN_METHODS else None
    if event == "lens":
        return d if d in LENS_STATES else None
    if event == "ask":
        return d if d in ASK_VIA else None
    if event == "subscribe":
        # The step counts even when what led there is unknown: /plus?from= is
        # an address anyone can type, and a stray one must not lose the view.
        stage, _, detail = d.partition(":")
        if stage not in SUBSCRIBE_STAGES:
            return None
        return d if detail in SUBSCRIBE_DETAIL else stage
    return None


def visitor(salt: str, ip: str, user_agent: str) -> str:
    return hashlib.sha256(f"{salt}|{ip}|{user_agent}".encode()).hexdigest()[:24]


async def day_salt(r, day: str) -> str:
    """Today's salt: made the first time it is asked for, gone within two days."""
    key = f"prism:usage:salt:{day}"
    await r.set(key, secrets.token_hex(16), nx=True, ex=TWO_DAYS_S)
    return await r.get(key)


async def bump(db: AsyncSession, event: str, dim: str = "", day: date | None = None, n: int = 1) -> None:
    # ponytail: one upsert per event contends on hot rows (view:story) at high
    # traffic; batch in Redis and flush on a timer if that ever shows up.
    await db.execute(
        text("INSERT INTO usage_daily (day, event, dim, count) VALUES (:d, :e, :m, :n) "
             "ON CONFLICT (day, event, dim) DO UPDATE SET count = usage_daily.count + EXCLUDED.count"),
        {"d": day or today(), "e": event, "m": dim, "n": n},
    )


async def bump_detached(event: str, dim: str = "") -> None:
    """Count an event from a request that is about to fail (a refused Ask
    rolls its own transaction back), in a transaction of its own. Never raises:
    a count must not change what the reader gets."""
    from common.db import session_scope

    try:
        async with session_scope() as s:
            await bump(s, event, dim)
    except Exception as exc:  # noqa: BLE001 — counting is best-effort by design
        logger.warning("usage_bump_failed", usage_event=event, error_type=type(exc).__name__)


async def active(db: AsyncSession, user_id: uuid.UUID, day: date | None = None) -> None:
    await db.execute(
        text("INSERT INTO user_days (user_id, day) VALUES (:u, :d) ON CONFLICT DO NOTHING"),
        {"u": user_id, "d": day or today()},
    )


def demo() -> None:
    assert source("", "quote") == "share:quote"
    assert source("www.google.co.in", "") == "search"
    assert source("l.facebook.com", "") == "social:facebook"
    assert source("evilgoogle.com", "") == "other", "suffix match must be on a dot boundary"
    assert source("", "") == "direct"
    assert dimension("view", "story") == "story" and dimension("view", "story/abc") is None
    assert dimension("ask", "What is RBI doing?") is None, "a question must never become a dimension"
    assert dimension("lens", "markets:locked") == "markets:locked" and dimension("lens", "markets") is None
    assert dimension("lens", "made-up-lens:open") is None, "a lens must be a real one"
    assert dimension("ask", "bar") == "bar" and dimension("ask", "barx") is None
    assert dimension("subscribe", "prompt:ask-limit") == "prompt:ask-limit"
    assert dimension("subscribe", "page:anything-typed") == "page", "an unknown door keeps the step"
    assert dimension("subscribe", "made-up") is None
    assert dimension("admin", "x") is None
    assert is_bot("Mozilla/5.0 (compatible; Googlebot/2.1)") and is_bot("") and not is_bot("Mozilla/5.0 (iPhone)")
    assert visitor("s1", "1.2.3.4", "ua") != visitor("s2", "1.2.3.4", "ua"), "a new salt must give a new hash"


if __name__ == "__main__":
    demo()
    print("ok")
