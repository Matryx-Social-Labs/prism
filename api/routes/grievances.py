"""The grievance mechanism: IT Rules 2021 Part III (R10, R11(2), R18(3), R19),
Consumer Protection (E-Commerce) Rules R4, DPDP Act s.8(9) — docs/COMPLIANCE-INDIA.md
rows 1, 3, 14 and N1–N3.

POST  /api/v1/grievances              — anyone: file a complaint; acknowledged by email at once
GET   /api/v1/grievances/report       — public monthly counts, September 2026 to this month, zeros printed
GET   /api/v1/admin/grievances        — founders: the queue, optionally one status
PATCH /api/v1/admin/grievances/{ref}  — founders: resolve or reject with the outcome in words (audited, emailed)

A complaint is committed before any email is attempted, so a failed send never
loses it, and `acknowledged_at` is set only when the acknowledgement went out:
the 24-hour clock is shown kept or not, never assumed. No IP address is stored
anywhere: the per-address limit counts a hash salted daily (common/usage.day_salt)
in Redis, and the key expires with the salt.
"""

from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, StringConstraints, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import client_ip, require_admin_user
from common import usage
from common.admin_audit import audit
from common.config import get_settings
from common.db import get_db
from common.email import get_email_sender
from common.email_templates import ENTITY, IST, render
from common.logging import get_logger
from common.stream import get_redis

router = APIRouter()
logger = get_logger(__name__)
PRIVATE = {"Cache-Control": "no-store"}

# Founder, 2026-09-29. The web prints the same from web/src/lib/legal.ts;
# tests/test_grievances.py fails if the two ever disagree.
OFFICER_NAME = "Tejas ShylaShashidhara"
OFFICER_TITLE = "Grievance Officer (Chief Executive Officer)"
GRIEVANCE_EMAIL = "grievance@readprism.news"
DECIDE_WITHIN_DAYS = 15  # IT Rules R11(2)(c); the strictest clock, so one covers every regime (N2)
REPORT_FROM = date(2026, 9, 1)  # the month the mechanism opened
PER_ADDRESS_PER_DAY = 10  # far above any person's complaints; carrier NAT shares addresses
ACKS_PER_RECIPIENT_PER_DAY = 3  # one address, a few honest complaints a day; the rest are saved unacknowledged
SITE = "https://www.readprism.news"

KINDS = (
    "A fact is wrong",
    "A quote is not in the article",
    "An outlet says something different",
    "An outlet that covered this is missing",
    "Privacy or my data",
    "Payments or my plan",
    "Something else",
)
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"  # one @, a dotted domain, no whitespace (no header injection)
_REF_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # no 0/O, 1/I: read aloud over a phone

def subject_path(raw: str) -> str | None:
    """A page on Prism, stored as its path; anything else is refused.

    A same-site path (`/story/…`) or a https://www.readprism.news link, which
    is stored without its host. `//host/…` is another site, and whitespace or a
    backslash is not a path we print."""
    s = raw.strip()
    if not s:
        return None
    if s == SITE or s.startswith(f"{SITE}/"):
        s = s[len(SITE):] or "/"
    if not s.startswith("/") or s.startswith("//") or "\\" in s or any(c.isspace() or ord(c) < 32 for c in s):
        raise ValueError("a page on readprism.news: a path such as /story/… or a https://www.readprism.news link")
    return urlsplit(s).path or "/"


class GrievanceIn(BaseModel):
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=254, pattern=EMAIL_PATTERN)]
    category: Literal[KINDS]
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=5000)]
    name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] = ""
    subject_url: Annotated[str, StringConstraints(max_length=500)] = ""
    # The honeypot: hidden from people, filled in by form-filling scripts.
    website: Annotated[str, StringConstraints(max_length=500)] = ""

    @field_validator("subject_url")
    @classmethod
    def _same_site(cls, v: str) -> str:
        return subject_path(v) or ""


class Decision(BaseModel):
    status: Literal["resolved", "rejected"]
    outcome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=5000)]


def new_ref(now: datetime) -> str:
    """PG-20260929-7K3Q: the IST day it arrived and four random characters."""
    return f"PG-{now.astimezone(IST):%Y%m%d}-{''.join(secrets.choice(_REF_ALPHABET) for _ in range(4))}"


def _when(d: datetime) -> str:
    return d.astimezone(IST).strftime("%-d %B %Y, %H:%M IST")


def _day(d: datetime) -> str:
    return d.astimezone(IST).strftime("%-d %B %Y")


def _copy(g: dict) -> list[tuple[str, str]]:
    """The complaint as recorded, field by field — what the complainant is sent (N2)."""
    rows = [
        ("Reference", g["ref"]),
        ("Received", _when(g["created_at"])),
        ("About", g["category"]),
        ("Page", f"{SITE}{g['subject_url']}" if g["subject_url"] else ""),
        ("Your name", g["name"] or ""),
        ("Your email", g["email"]),
        ("Your complaint", g["body"]),
    ]
    return [(k, v) for k, v in rows if v]


def acknowledgement(g: dict) -> tuple[str, str, str]:
    """(subject, text, html) of the acknowledgement: a copy of the complaint,
    who decides it, and both clocks."""
    subject = f"We received your complaint · {g['ref']}"
    by = _day(g["created_at"] + timedelta(days=DECIDE_WITHIN_DAYS))
    text_body, html = render(
        subject=subject,
        title="We received your complaint",
        meta=f"Grievance · {g['ref']}",
        paragraphs=[
            f"This acknowledges your complaint to {ENTITY}. A copy of it, as we recorded it, is below.",
            f"Our Grievance Officer, {OFFICER_NAME}, will decide it within {DECIDE_WITHIN_DAYS} days, by {by}, "
            f"and write to you at this address with the outcome.",
        ],
        facts=[
            *_copy(g),
            ("Acknowledged", _when(g["created_at"])),
            ("Decision", f"Within {DECIDE_WITHIN_DAYS} days · by {by}"),
            ("Grievance Officer", f"{OFFICER_NAME} · {OFFICER_TITLE}"),
            ("Write to", GRIEVANCE_EMAIL),
        ],
        cta=None,
        note=f"To add to it, reply to this email or write to {GRIEVANCE_EMAIL}, quoting {g['ref']}.",
        because=f"a complaint was filed with Prism from {g['email']}.",
        preheader=f"Reference {g['ref']}. A decision within {DECIDE_WITHIN_DAYS} days, by {by}.",
    )
    return subject, text_body, html


def notification(g: dict, acknowledged: bool) -> tuple[str, str, str]:
    """(subject, text, html) for the officer's inbox; replying answers the complainant."""
    subject = f"Complaint {g['ref']} · {g['category']}"
    by = _day(g["created_at"] + timedelta(days=DECIDE_WITHIN_DAYS))
    text_body, html = render(
        subject=subject,
        title=f"A complaint to decide by {by}",
        meta=f"Grievance · {g['ref']}",
        paragraphs=[
            "Reply to this email to write to the complainant. Record the decision on the admin's Grievances page, "
            "which emails them the outcome and counts it in the monthly report.",
            "The acknowledgement was emailed to them."
            if acknowledged
            else "The acknowledgement could NOT be emailed to them. Acknowledge it by hand within 24 hours.",
        ],
        facts=_copy(g),
        cta=("Open the grievances", f"{get_settings().prism_web_url.rstrip('/')}/admin/grievances"),
        because=f"{GRIEVANCE_EMAIL} receives every complaint filed at {SITE}/grievance.",
    )
    return subject, text_body, html


def outcome_email(g: dict) -> tuple[str, str, str]:
    """(subject, text, html) telling the complainant what was decided."""
    resolved = g["status"] == "resolved"
    subject = f"{'Your complaint is resolved' if resolved else 'A decision on your complaint'} · {g['ref']}"
    text_body, html = render(
        subject=subject,
        title="Your complaint is resolved" if resolved else "Your complaint was not upheld",
        meta=f"Grievance · {g['ref']} · {'Resolved' if resolved else 'Rejected'}",
        paragraphs=[g["outcome"], "If you are not satisfied with this decision, reply to this email and say why."],
        facts=[
            ("Decided", _when(g["resolved_at"])),
            ("Grievance Officer", f"{OFFICER_NAME} · {OFFICER_TITLE}"),
            *_copy(g),
        ],
        cta=None,
        because=f"you filed complaint {g['ref']} with Prism from {g['email']}.",
    )
    return subject, text_body, html


async def _send(to: str, mail: tuple[str, str, str], ref: str, what: str, reply_to: str) -> bool:
    """True when the provider took it. A failure is logged (never the complaint's
    words or address) and returned, never raised: the complaint is already saved."""
    subject, body, html = mail
    try:
        await get_email_sender().send(to=to, subject=subject, body=body, html=html, reply_to=reply_to)
        return True
    except Exception as exc:  # noqa: BLE001 — any provider failure is the same fact: not sent
        logger.warning("grievance_email_failed", ref=ref, email_kind=what, error_type=type(exc).__name__, error=str(exc)[:200])
        return False


async def _may_email(address: str) -> bool:
    """Whether this address may get another acknowledgement today. The
    acknowledgement carries the complainant's own words to the address they
    typed, which nobody has confirmed, so an unchecked form would let anyone
    make readprism.news mail any text to anyone (review 2026-09-29). Capped per
    recipient; Redis away → no email (the complaint is still saved and shows
    "not acknowledged by email" in the queue, for the officer to acknowledge)."""
    try:
        r = get_redis()
        day = usage.today().isoformat()
        key = f"prism:grievance:to:{day}:{usage.visitor(await usage.day_salt(r, day), address.strip().lower(), '')}"
        n = await r.incr(key)
        if n == 1:
            await r.expire(key, usage.TWO_DAYS_S)
        return n <= ACKS_PER_RECIPIENT_PER_DAY
    except Exception as exc:  # noqa: BLE001 — see the docstring
        logger.warning("grievance_ack_limit_unavailable", error_type=type(exc).__name__)
        return False


async def _over_limit(ip: str | None) -> bool:
    """Count one complaint against this address today. Redis away → allowed:
    a complaint the law obliges us to take is never refused for an outage."""
    if not ip:
        return False
    try:
        r = get_redis()
        day = usage.today().isoformat()
        key = f"prism:grievance:ip:{day}:{usage.visitor(await usage.day_salt(r, day), ip, '')}"
        n = await r.incr(key)
        if n == 1:
            await r.expire(key, usage.TWO_DAYS_S)
        return n > PER_ADDRESS_PER_DAY
    except Exception as exc:  # noqa: BLE001 — see the docstring
        logger.warning("grievance_limit_unavailable", error_type=type(exc).__name__)
        return False


_COLUMNS = "ref, created_at, name, email, category, subject_url, body, status, acknowledged_at, resolved_at, outcome"


@router.post("/api/v1/grievances", status_code=201)
async def file_grievance(body: GrievanceIn, request: Request, db: AsyncSession = Depends(get_db)):
    refused = f"This complaint could not be sent from here. Write to {GRIEVANCE_EMAIL} instead."
    if body.website:
        raise HTTPException(status_code=400, detail=refused)
    if await _over_limit(client_ip(request)):
        raise HTTPException(status_code=429, detail=f"Too many complaints from this connection today. Write to {GRIEVANCE_EMAIL} instead.")
    params = {"name": body.name or None, "email": body.email, "category": body.category,
              "subject_url": body.subject_url or None, "body": body.body}
    g = None
    for _ in range(5):  # a collision is one in a million a day; retry rather than fail
        g = (await db.execute(text(
            f"INSERT INTO grievances (ref, name, email, category, subject_url, body) "
            f"VALUES (:ref, :name, :email, :category, :subject_url, :body) "
            f"ON CONFLICT (ref) DO NOTHING RETURNING {_COLUMNS}"),
            {**params, "ref": new_ref(datetime.now(IST))})).mappings().first()
        if g:
            break
    if g is None:
        raise HTTPException(status_code=503, detail=refused)
    g = dict(g)
    await db.commit()  # saved before any email: a failed send never loses it

    acknowledged = await _may_email(g["email"]) and await _send(g["email"], acknowledgement(g), g["ref"], "acknowledgement", GRIEVANCE_EMAIL)
    if acknowledged:
        await db.execute(text("UPDATE grievances SET acknowledged_at = now() WHERE ref = :r"), {"r": g["ref"]})
        await db.commit()
    await _send(GRIEVANCE_EMAIL, notification(g, acknowledged), g["ref"], "notification", g["email"])
    return {"ref": g["ref"], "acknowledged": acknowledged, "decide_by": (g["created_at"] + timedelta(days=DECIDE_WITHIN_DAYS)).isoformat()}


def months(start: date, today: date) -> list[str]:
    """Every month from `start` to `today`'s, as YYYY-MM, oldest first."""
    out, y, m = [], start.year, start.month
    while (y, m) <= (today.year, today.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def monthly(counted: dict[str, dict], today: date) -> list[dict]:
    """The report's rows, newest month first; a month with no complaints prints zeros."""
    zero = {"received": 0, "resolved": 0, "rejected": 0, "open": 0, "median_days": None}
    return [{"month": m, **counted.get(m, zero)} for m in reversed(months(REPORT_FROM, today))]


@router.get("/api/v1/grievances/report")
async def report(db: AsyncSession = Depends(get_db)):
    """Counts only, by the IST month a complaint was received: how many, how
    many resolved, rejected and still open, and the median days to a decision
    (null until one is decided). IT Rules R18(3), R19; N3."""
    rows = (await db.execute(text(
        """
        SELECT to_char(created_at AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM') AS month,
               count(*) AS received,
               count(*) FILTER (WHERE status = 'resolved') AS resolved,
               count(*) FILTER (WHERE status = 'rejected') AS rejected,
               count(*) FILTER (WHERE status = 'open') AS open,
               percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM resolved_at - created_at) / 86400) AS median_days
        FROM grievances GROUP BY 1
        """))).mappings().all()
    counted = {r["month"]: {**{k: r[k] for k in ("received", "resolved", "rejected", "open")},
                            "median_days": None if r["median_days"] is None else round(float(r["median_days"]), 1)}
               for r in rows}
    return {"since": REPORT_FROM.isoformat(), "decide_within_days": DECIDE_WITHIN_DAYS, "months": monthly(counted, usage.today())}


@router.get("/api/v1/admin/grievances")
async def queue(
    response: Response,
    status: Literal["open", "resolved", "rejected"] | None = None,
    _: str = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    response.headers.update(PRIVATE)
    where = "WHERE status = :s" if status else ""
    # Open first and oldest first — the ones nearest their 15-day deadline can
    # never fall off the end of the page; decided ones after, newest first.
    order = "ORDER BY (status = 'open') DESC, CASE WHEN status = 'open' THEN created_at END ASC, created_at DESC"
    rows = (await db.execute(text(f"SELECT {_COLUMNS} FROM grievances {where} {order} LIMIT 500"),
                             {"s": status} if status else {})).mappings().all()
    return {"decide_within_days": DECIDE_WITHIN_DAYS, "grievances": [
        {**r, "decide_by": r["created_at"] + timedelta(days=DECIDE_WITHIN_DAYS)} for r in rows]}


@router.patch("/api/v1/admin/grievances/{ref}")
async def decide(ref: str, body: Decision, actor: str = Depends(require_admin_user), db: AsyncSession = Depends(get_db)):
    """Open → resolved | rejected, once. Recorded against the founder in the
    same transaction, committed, and only then emailed to the complainant."""
    g = (await db.execute(text(
        f"UPDATE grievances SET status = :s, outcome = :o, resolved_at = now() "
        f"WHERE ref = :r AND status = 'open' RETURNING {_COLUMNS}"),
        {"s": body.status, "o": body.outcome, "r": ref})).mappings().first()
    if g is None:
        was = (await db.execute(text("SELECT status FROM grievances WHERE ref = :r"), {"r": ref})).scalar()
        raise HTTPException(status_code=404 if was is None else 409,
                            detail="No complaint with that reference" if was is None else f"Already {was}")
    await audit(db, actor, "grievance.decide", ref, {"status": body.status})
    await db.commit()
    g = dict(g)
    emailed = await _send(g["email"], outcome_email(g), ref, "outcome", GRIEVANCE_EMAIL)
    return {"ref": ref, "status": body.status, "emailed": emailed}
