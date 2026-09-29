"""The week's record by email: an opt-in Sunday digest of the week's counted records.

Consent (DPDP s.6, docs/COMPLIANCE-INDIA.md): an account turns it on with an
unticked toggle and turns it off the same way, or with the one-click link in
every copy. `digest_opted_in_at` and `digest_unsubscribed_at` are the consent
record; nothing is sent to an account that did not turn it on.

Content is counted from the database for the seven IST days before the send
day, never typed: the records two or more monitored outlets reported (the rule
that makes a record indexable, common/outlets), their "k of n monitored
outlets" as the story page prints it, how many there were and in how many
languages, and the week's corrections ("No corrections this week" is a count).
A week with fewer than DIGEST_MIN_RECORDS such records sends nothing: that is
a week the pipeline was idle, not a quiet week.

One copy per account per ISO week (`digest_last_week`), claimed before it is
sent so a rerun or a second worker never sends twice; a failed send gives the
claim back.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common import outlets
from common.config import get_settings
from common.db import session_scope
from common.email import get_email_sender
from common.email_templates import IST, render
from common.logging import get_logger

logger = get_logger(__name__)

SUBJECT = "The week's record"
DIGEST_TOP = 10  # records listed in one email
DIGEST_MIN_RECORDS = 3  # below this many multi-outlet records the week is not sent
DIGEST_DAYS = 7
SEND_INTERVAL_S = 0.6  # Resend's default limit is 2 requests a second
_TOKEN_PURPOSE = b"prism-digest-unsubscribe:"

_ON = "digest_opted_in_at IS NOT NULL AND digest_unsubscribed_at IS NULL"


# ── Consent ──────────────────────────────────────────────────────────────────


async def digest_on(db: AsyncSession, user_id: UUID | str) -> bool:
    row = (await db.execute(text(f"SELECT {_ON} FROM users WHERE id = :u"), {"u": str(user_id)})).scalar_one_or_none()
    return bool(row)


async def set_digest(db: AsyncSession, user_id: UUID | str, on: bool) -> bool:
    """On stamps the consent (kept, not re-stamped, while it stays on) and clears
    any earlier withdrawal; off stamps the withdrawal and keeps when consent was
    given. Off on an account that never turned it on records nothing."""
    if on:
        sql = (f"UPDATE users SET digest_opted_in_at = CASE WHEN {_ON} THEN digest_opted_in_at ELSE now() END, "
               "digest_unsubscribed_at = NULL WHERE id = :u")
    else:
        sql = ("UPDATE users SET digest_unsubscribed_at = COALESCE(digest_unsubscribed_at, now()) "
               "WHERE id = :u AND digest_opted_in_at IS NOT NULL")
    await db.execute(text(sql), {"u": str(user_id)})
    return await digest_on(db, user_id)


# ── One-click unsubscribe: an HMAC over the account id ──────────────────────
# Signed with PRISM_ADMIN_TOKEN (the API refuses to serve with the placeholder),
# so the worker that writes the link and the API that answers it must share it.
# Rotating that token invalidates every link already emailed (the account toggle
# still works): rotate it only with that in mind (docs/marketing/MARKETING-PLAN.md).


def _sign(user_id: str) -> str:
    key = get_settings().prism_admin_token.encode()
    mac = hmac.new(key, _TOKEN_PURPOSE + user_id.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac).rstrip(b"=").decode()


def unsubscribe_token(user_id: UUID | str) -> str:
    uid = str(UUID(str(user_id)))
    return f"{uid}.{_sign(uid)}"


def verify_unsubscribe_token(token: str) -> UUID | None:
    uid, _, sig = (token or "").partition(".")
    try:
        parsed = UUID(uid)
    except ValueError:
        return None
    # Bytes, not str: compare_digest raises on non-ASCII str, which was a 500.
    return parsed if sig and hmac.compare_digest(sig.encode(), _sign(str(parsed)).encode()) else None


def unsubscribe_url(user_id: UUID | str) -> str:
    return f"{get_settings().prism_api_url.rstrip('/')}/api/v1/digest/unsubscribe?t={unsubscribe_token(user_id)}"


async def unsubscribe(db: AsyncSession, user_id: UUID) -> None:
    await set_digest(db, user_id, False)


# ── The week, counted ────────────────────────────────────────────────────────


def week_window(now: datetime) -> tuple[datetime, datetime]:
    """The seven whole IST days before `now`'s IST day: Sunday's run reads Sunday to Saturday."""
    end = datetime.combine(now.astimezone(IST).date(), time(0), IST)
    return end - timedelta(days=DIGEST_DAYS), end


def iso_week(now: datetime) -> str:
    y, w, _ = now.astimezone(IST).date().isocalendar()
    return f"{y}-W{w:02d}"


def monitored_text(k: int, n: int | None) -> str:
    """web/src/lib/coverage.ts monitoredText, word for word."""
    if not n or n < k:
        return f"{k} {'outlet' if k == 1 else 'outlets'}"
    return f"{k} of {n} monitored outlets"


@dataclass(frozen=True)
class Week:
    start: datetime
    end: datetime
    top: tuple[tuple[str, str, int], ...]  # (event id, headline, outlets), most outlets first
    records: int  # records two or more monitored outlets reported
    languages: int  # languages across those records' reports
    corrections: int
    monitored: int | None  # the denominator, as /sources prints it


async def count_week(db: AsyncSession, start: datetime, end: datetime) -> Week:
    rows = (
        await db.execute(
            text(
                """
                SELECT id, title, projection->'source_slugs' AS slugs, first_seen_at FROM events
                WHERE merged_into IS NULL
                  AND last_updated_at >= :start
                  AND first_seen_at >= :start AND first_seen_at < :end
                  AND COALESCE(jsonb_array_length(projection->'source_slugs'), 0) >= 2
                """
            ),
            {"start": start, "end": end},
        )
    ).mappings().all()
    reg = await outlets.registry(db)
    multi, langs = [], set()
    for r in rows:
        slugs = r["slugs"] or []
        k = len(outlets.publishers_of(slugs, reg))
        if k < outlets.RECORD_MIN_OUTLETS:
            continue
        multi.append((k, r["first_seen_at"], str(r["id"]), r["title"]))
        langs |= {reg[s].language or "en" for s in slugs if s in reg and s not in outlets.RAW_RECORD_FEEDS}
    multi.sort(key=lambda m: (m[0], m[1]), reverse=True)
    corrections = (
        await db.execute(
            text("SELECT count(*) FROM event_corrections WHERE created_at >= :start AND created_at < :end"),
            {"start": start, "end": end},
        )
    ).scalar_one()
    mon = await outlets.monitored(db)
    return Week(
        start=start,
        end=end,
        top=tuple((eid, title, k) for k, _, eid, title in multi[:DIGEST_TOP]),
        records=len(multi),
        languages=len(langs),
        corrections=corrections,
        monitored=mon.outlets or None,
    )


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def digest_email(week: Week, *, to: str, unsubscribe: str) -> tuple[str, str]:
    web = get_settings().prism_web_url.rstrip("/")
    first, last = week.start.astimezone(IST), (week.end - timedelta(days=1)).astimezone(IST)
    span = f"{first:%-d %B} to {last:%-d %B %Y}"
    fixes = "No corrections this week" if week.corrections == 0 else f"{_plural(week.corrections, 'correction', 'corrections')} this week"
    return render(
        subject=SUBJECT,
        title=SUBJECT,
        meta=f"{first:%-d %b} – {last:%-d %b %Y} · IST",
        paragraphs=[
            f"From {span}, {_plural(week.records, 'record was', 'records were')} reported by two or more of the outlets "
            f"Prism monitors, in {_plural(week.languages, 'language', 'languages')}. "
            f"The {len(week.top)} most widely reported:",  # a sent week has at least DIGEST_MIN_RECORDS
        ],
        records=[(title, monitored_text(k, week.monitored), f"{web}/story/{eid}") for eid, title, k in week.top],
        facts=[
            ("Records, two or more outlets", str(week.records)),
            ("Languages", str(week.languages)),
            ("Corrections", fixes),
        ],
        cta=("Open the corrections log", f"{web}/corrections"),
        because=f"you turned on the week's record for {to} in your Prism account. Turn it off there, or with the link below.",
        preheader=f"{_plural(week.records, 'record', 'records')} from two or more outlets, {span}. {fixes}.",
        unsubscribe=unsubscribe,
    )


# ── The Sunday run ───────────────────────────────────────────────────────────


def _is_local(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _assert_links_reachable(settings) -> None:
    """Refuse to mail links a reader cannot open: every copy carries an
    unsubscribe link built on PRISM_API_URL, and a consent-based email whose
    withdrawal link points at localhost is worse than no email (review
    2026-09-29). Local development (the web on localhost too) is fine."""
    if _is_local(settings.prism_api_url) and not _is_local(settings.prism_web_url):
        raise RuntimeError("PRISM_API_URL points at localhost while the site is public; set it on the worker before the digest runs")


async def run_digest(now: datetime | None = None) -> dict:
    """Send this week's copy to every account that turned it on and has not had
    it, at most PRISM_DIGEST_MAX_PER_RUN; the rest go next run, longest-waiting first."""
    settings = get_settings()
    if not settings.prism_digest_enabled:
        logger.info("digest_skipped", reason="disabled")
        return {"sent": 0, "skipped": "disabled"}
    from api.deps import assert_admin_token_configured

    assert_admin_token_configured(settings)  # the unsubscribe links are signed with it
    _assert_links_reachable(settings)
    now = now or datetime.now(UTC)
    label = iso_week(now)
    async with session_scope() as db:
        week = await count_week(db, *week_window(now))
        if week.records < DIGEST_MIN_RECORDS:
            # An idle pipeline (ingestion paused) is not a quiet week: say nothing.
            logger.warning("digest_skipped", reason="too_few_records", week=label, records=week.records,
                           needed=DIGEST_MIN_RECORDS)
            return {"sent": 0, "skipped": "too_few_records", "records": week.records}
        due = (
            await db.execute(
                text(
                    f"SELECT id, email, digest_last_week FROM users WHERE {_ON} "
                    "AND digest_last_week IS DISTINCT FROM :w "
                    "ORDER BY digest_last_week NULLS FIRST, digest_opted_in_at LIMIT :n"
                ),
                {"w": label, "n": settings.prism_digest_max_per_run + 1},
            )
        ).all()
    batch, left_over = due[: settings.prism_digest_max_per_run], len(due) > settings.prism_digest_max_per_run
    sent = failed = 0
    sender = get_email_sender()
    for uid, email, prev in batch:
        if not await _claim(uid, label):
            continue  # turned off, or sent by another run, since the list was read
        url = unsubscribe_url(uid)
        body, html = digest_email(week, to=email, unsubscribe=url)
        try:
            await sender.send(to=email, subject=SUBJECT, body=body, html=html, headers={
                "List-Unsubscribe": f"<{url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            })
            sent += 1
        except Exception:
            failed += 1
            logger.exception("digest_send_failed", user_id=str(uid))
            await _release(uid, label, prev)
        await asyncio.sleep(SEND_INTERVAL_S)
    if left_over:
        logger.warning("digest_capped", week=label, cap=settings.prism_digest_max_per_run,
                       note="the rest go next run, longest-waiting first")
    logger.info("digest_sent", week=label, sent=sent, failed=failed, records=week.records)
    return {"sent": sent, "failed": failed, "capped": left_over, "records": week.records}


async def _claim(user_id: UUID, label: str) -> bool:
    async with session_scope() as db:
        got = await db.execute(
            text(f"UPDATE users SET digest_last_week = :w WHERE id = :u AND {_ON} "
                 "AND digest_last_week IS DISTINCT FROM :w RETURNING id"),
            {"w": label, "u": str(user_id)},
        )
        return got.scalar_one_or_none() is not None


async def _release(user_id: UUID, label: str, prev: str | None) -> None:
    async with session_scope() as db:
        await db.execute(
            text("UPDATE users SET digest_last_week = :p WHERE id = :u AND digest_last_week = :w"),
            {"p": prev, "u": str(user_id), "w": label},
        )
