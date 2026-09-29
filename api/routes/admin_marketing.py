"""/admin/marketing: founder links to Prism pages, and what the visits they
brought did (common/share_links.py says what is counted and what is not).

GET   /api/v1/admin/links          — every link, newest first, with its counts for a period
POST  /api/v1/admin/links          — make one (audited)
PATCH /api/v1/admin/links/{code}   — archive or restore one (audited); a posted link keeps working
GET   /api/v1/links/{code}         — public: where a short link goes (the web's /go/<code>)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_admin_user
from common import metrics, share_links
from common.admin_audit import audit
from common.config import get_settings
from common.db import get_db
from common.usage import IST

router = APIRouter()
PRIVATE = {"Cache-Control": "no-store"}
_COLUMNS = "code, path, kind, title, platform, medium, campaign, note, created_by, created_at, archived_at"
LIST_LIMIT = 1000


class LinkIn(BaseModel):
    target: Annotated[str, Field(max_length=500)]
    platform: str
    medium: str | None = None
    campaign: Annotated[str, Field(max_length=share_links.CAMPAIGN_MAX)] = ""
    # What the founder saw when they made it (a headline, a name): the list's label.
    title: Annotated[str, Field(max_length=300)] = ""
    note: Annotated[str, Field(max_length=200)] = ""


class LinkState(BaseModel):
    archived: bool


def _out(row: Any, web_url: str) -> dict[str, Any]:
    r = dict(row)
    return {**r, "url": share_links.long_url(web_url, r), "short_url": share_links.short_url(web_url, r["code"])}


def _series(by_day: dict[date, int], days: list[date], created: datetime) -> list[int | None]:
    """Visits per day; None before the link existed (not counted, not zero)."""
    made = created.astimezone(IST).date()
    return [None if d < made else by_day.get(d, 0) for d in days]


@router.get("/api/v1/admin/links")
async def list_links(
    response: Response,
    days: Annotated[int, Query(ge=1, le=365)] = 28,
    _: str = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    response.headers.update(PRIVATE)
    w = metrics.window(days)
    rows = (await db.execute(text(f"SELECT {_COLUMNS} FROM share_links ORDER BY created_at DESC LIMIT :n"),
                             {"n": LIST_LIMIT})).mappings().all()
    perf = await share_links.performance(db, w["start"], w["end"])
    span = [w["start"] + timedelta(days=i) for i in range(days)]
    web_url = get_settings().prism_web_url
    empty = {"visits": 0, "by_day": {}, "goals": dict.fromkeys(sorted(share_links.GOALS), 0)}
    links = []
    for row in rows:
        p = perf.get(row["code"], empty)
        links.append({**_out(row, web_url), "visits": p["visits"], "goals": p["goals"],
                      "series": _series(p["by_day"], span, row["created_at"])})
    return {
        "range": {"days": days, "start": w["start"].isoformat(), "end": w["end"].isoformat(), "tz": "Asia/Kolkata"},
        "platforms": share_links.PLATFORMS, "media": sorted(share_links.MEDIA),
        "campaigns": sorted({r["campaign"] for r in rows if r["campaign"]}),
        "links": links,
    }


def _check(body: LinkIn, web_url: str) -> tuple[str, str]:
    """The page's path and the medium, or a 422 saying what is wrong, in words."""
    path = share_links.target_path(body.target, web_url)
    if path is None:
        raise HTTPException(status_code=422, detail="That is not a public Prism page. Paste a readprism.news address or a path such as /story/…")
    if body.platform not in share_links.PLATFORMS:
        raise HTTPException(status_code=422, detail="Pick a platform from the list")
    medium = body.medium or share_links.PLATFORMS[body.platform]
    if medium not in share_links.MEDIA:
        raise HTTPException(status_code=422, detail="Pick a medium from the list")
    if body.campaign and not share_links.CAMPAIGN.fullmatch(body.campaign):
        raise HTTPException(status_code=422, detail="A campaign is lowercase letters, digits and hyphens, such as launch-week")
    return path, medium


@router.post("/api/v1/admin/links", status_code=201)
async def make_link(body: LinkIn, actor: str = Depends(require_admin_user), db: AsyncSession = Depends(get_db)):
    web_url = get_settings().prism_web_url
    path, medium = _check(body, web_url)
    params = {"path": path, "kind": share_links.kind(path), "title": body.title.strip(), "platform": body.platform,
              "medium": medium, "campaign": body.campaign, "note": body.note.strip(), "by": actor}
    row = None
    for _ in range(5):  # 31^6 codes: a collision is rare; retry rather than fail
        row = (await db.execute(text(
            f"INSERT INTO share_links (code, path, kind, title, platform, medium, campaign, note, created_by) "
            f"VALUES (:code, :path, :kind, :title, :platform, :medium, :campaign, :note, :by) "
            f"ON CONFLICT (code) DO NOTHING RETURNING {_COLUMNS}"),
            {**params, "code": share_links.new_code()})).mappings().first()
        if row:
            break
    if row is None:
        raise HTTPException(status_code=503, detail="No code was free; try again")
    await audit(db, actor, "link.create", row["code"], {"path": path, "platform": body.platform, "campaign": body.campaign})
    await db.commit()
    share_links.forget()
    return _out(row, web_url)


@router.patch("/api/v1/admin/links/{code}")
async def set_link_state(code: str, body: LinkState, actor: str = Depends(require_admin_user),
                         db: AsyncSession = Depends(get_db)):
    row = (await db.execute(text(
        f"UPDATE share_links SET archived_at = CASE WHEN :a THEN coalesce(archived_at, now()) END "
        f"WHERE code = :c RETURNING {_COLUMNS}"), {"a": body.archived, "c": code})).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="No link with that code")
    await audit(db, actor, "link.archive" if body.archived else "link.restore", code)
    await db.commit()
    return _out(row, get_settings().prism_web_url)


@router.get("/api/v1/links/{code}")
async def resolve(code: str, response: Response, db: AsyncSession = Depends(get_db)):
    """Where /go/<code> sends a reader: the page and its tags. An archived link
    still resolves; a posted link must keep working."""
    if not share_links.CODE.fullmatch(code):
        raise HTTPException(status_code=404, detail="No such link")
    row = (await db.execute(text(f"SELECT {_COLUMNS} FROM share_links WHERE code = :c"), {"c": code})).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="No such link")
    # A link's page and tags never change once it is made.
    response.headers["Cache-Control"] = "public, max-age=3600"
    return {"path": row["path"], "tags": share_links.tags(dict(row))}
