"""Auth routes: request a magic link, verify it for a bearer session, whoami.

The email delivery backend is pluggable (common/email.py) and defaults to a
console sender, so the flow works end-to-end in dev with no provider configured.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from common import auth
from common.config import get_settings
from common.db import get_db
from common.email import get_email_sender
from common.email_templates import magic_link_email
from common.professions import grouped, is_valid_profession

router = APIRouter()


class MagicLinkRequest(BaseModel):
    email: str
    consent: bool = False  # DPDP: explicit consent to create an account (D12)
    name: str | None = None  # required for new sign-ups (see request_link)
    profession: str | None = None  # slug from common.professions


class VerifyRequest(BaseModel):
    token: str


class SessionResponse(BaseModel):
    token: str
    user_id: str
    email: str


class MeResponse(BaseModel):
    user_id: str
    email: str


@router.get("/api/v1/professions")
async def professions():
    """Sign-up dropdown vocabulary (grouped by domain)."""
    return {"groups": grouped()}


@router.post("/api/v1/auth/request")
async def request_link(body: MagicLinkRequest, db: AsyncSession = Depends(get_db)):
    if "@" not in body.email or len(body.email) > 320:
        raise HTTPException(status_code=422, detail="invalid email")
    if not body.consent:
        raise HTTPException(status_code=422, detail="consent required (DPDP)")
    # Sign-up profile is mandatory (applied only if this creates a new account).
    name = (body.name or "").strip()
    if not name or len(name) > 120:
        raise HTTPException(status_code=422, detail="name required")
    if not body.profession or not is_valid_profession(body.profession):
        raise HTTPException(status_code=422, detail="valid profession required")
    settings = get_settings()
    try:
        raw = await auth.request_magic_link(db, body.email, name=name, profession=body.profession)
    except auth.RateLimited:
        # Same response as success — don't reveal that a request was just made
        # for this email (avoids an enumeration / timing side channel).
        return {"ok": True}
    link = f"{settings.prism_web_url}/auth/verify?token={raw}"
    text, html = magic_link_email(link=link, ttl_min=settings.prism_magic_token_ttl_min, to=body.email)
    await get_email_sender().send(
        to=body.email, subject="Your Prism sign-in link", body=text, html=html
    )
    return {"ok": True}


@router.post("/api/v1/auth/verify", response_model=SessionResponse)
async def verify(body: VerifyRequest, db: AsyncSession = Depends(get_db)):
    user_id = await auth.verify_and_consume(db, body.token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    token = await auth.create_session(db, user_id)
    email = (
        await db.execute(text("SELECT email FROM users WHERE id = :i"), {"i": str(user_id)})
    ).scalar_one()
    return SessionResponse(token=token, user_id=str(user_id), email=email)


@router.get("/api/v1/auth/me", response_model=MeResponse)
async def me(user_id: UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    email = (
        await db.execute(text("SELECT email FROM users WHERE id = :i"), {"i": str(user_id)})
    ).scalar_one()
    return MeResponse(user_id=str(user_id), email=email)
