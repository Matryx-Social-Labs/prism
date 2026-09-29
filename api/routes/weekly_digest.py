"""The week's record by email: the account toggle and the one-click unsubscribe.

The toggle is the consent (common/weekly_digest.set_digest); the unsubscribe is
the same withdrawal from the email itself, with no sign-in: an HMAC-signed link
(GET, from the footer) or RFC 8058's one-click POST (List-Unsubscribe-Post,
from the mail client). Both answer the same way for every valid token.
"""

import html
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, StrictBool
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from common import weekly_digest
from common.config import get_settings
from common.db import get_db

router = APIRouter()


class DigestState(BaseModel):
    # Strict: consent is an explicit true, never "1" or "yes" coerced into one.
    on: StrictBool


@router.get("/api/v1/me/digest", response_model=DigestState)
async def get_digest(user_id: UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return DigestState(on=await weekly_digest.digest_on(db, user_id))


@router.put("/api/v1/me/digest", response_model=DigestState)
async def put_digest(body: DigestState, user_id: UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return DigestState(on=await weekly_digest.set_digest(db, user_id, body.on))


def _page(title: str, line: str, status: int, confirm: str | None = None) -> HTMLResponse:
    """A plain page in the record's words: no script; the only thing from the
    request ever printed is a VERIFIED token, escaped, in the confirm form."""
    account = f"{get_settings().prism_web_url.rstrip('/')}/account#digest"
    button = (
        f'<form method="post" action="/api/v1/digest/unsubscribe?t={html.escape(confirm, quote=True)}">'
        '<button type="submit" style="font:bold 16px/1 Arial,Helvetica,sans-serif;padding:14px 18px;border-radius:8px;'
        'border:0;background:#0B57D0;color:#fff;cursor:pointer">Stop the week\'s record</button></form>'
        if confirm else ""
    )
    return HTMLResponse(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>{title} · Prism</title></head>
<body style="margin:0;background:#F7F6F2;color:#111317;font:16px/1.55 Arial,Helvetica,sans-serif">
<main style="max-width:520px;margin:48px auto;padding:0 20px"><p style="font:12px/18px Menlo,Consolas,monospace;color:#5B6069">READPRISM.NEWS</p>
<h1 style="font:bold 28px/34px Georgia,serif;margin:8px 0 12px">{title}</h1><p>{line}</p>{button}
<p><a href="{account}" style="color:#0B57D0">Your account</a></p></main></body></html>""",
        status_code=status,
        headers={"Cache-Control": "no-store"},
    )


async def _unsubscribe(t: str, db: AsyncSession) -> HTMLResponse:
    user_id = weekly_digest.verify_unsubscribe_token(t)
    if user_id is None:
        return _page("This link is not valid", "Nothing was changed. You can turn the week's record off in your account.", 400)
    await weekly_digest.unsubscribe(db, user_id)
    return _page("You are unsubscribed", "The week's record will not be sent to you again unless you turn it back on in your account.", 200)


# The link in the email only ASKS: mail scanners (Outlook Safe Links and the like)
# open every link in a message, so a GET that withdrew consent would unsubscribe
# readers who never clicked. The button POSTs; so does a mail client's one-click
# (RFC 8058, List-Unsubscribe-Post), which never sees this page.
@router.get("/api/v1/digest/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_link(t: str = ""):
    if weekly_digest.verify_unsubscribe_token(t) is None:
        return _page("This link is not valid", "Nothing was changed. You can turn the week's record off in your account.", 400)
    return _page("Stop the week's record?", "One press and it stops. You can turn it back on in your account.", 200, confirm=t)


@router.post("/api/v1/digest/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_one_click(t: str = "", db: AsyncSession = Depends(get_db)):
    return await _unsubscribe(t, db)
