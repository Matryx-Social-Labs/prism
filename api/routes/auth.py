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
from common.languages import DEFAULT_LANGUAGES, is_valid_language, offered
from common.professions import grouped, is_valid_profession

router = APIRouter()


class MagicLinkRequest(BaseModel):
    email: str  # email-only — the profile is collected after verify (see set_profile)


class VerifyRequest(BaseModel):
    token: str


class ProfileRequest(BaseModel):
    name: str
    profession: str  # slug from common.professions
    state: str | None = None  # ISO 3166-2, e.g. IN-KA
    languages: list[str] = []  # ordered by preference; languages[0] is primary
    consent: bool = False  # explicit terms/account consent (DPDP)


class SessionResponse(BaseModel):
    token: str
    user_id: str
    email: str
    needs_profile: bool  # true → route the reader to onboarding


class MeResponse(BaseModel):
    user_id: str
    email: str


@router.get("/api/v1/professions")
async def professions():
    """Sign-up dropdown vocabulary (grouped by domain)."""
    return {"groups": grouped()}


@router.get("/api/v1/languages")
async def languages():
    """Onboarding language picker vocabulary (native-script labels)."""
    return {"languages": offered(), "default": DEFAULT_LANGUAGES}


@router.post("/api/v1/auth/request")
async def request_link(body: MagicLinkRequest, db: AsyncSession = Depends(get_db)):
    if "@" not in body.email or len(body.email) > 320:
        raise HTTPException(status_code=422, detail="invalid email")
    settings = get_settings()
    try:
        raw = await auth.request_magic_link(db, body.email)
    except auth.RateLimited:
        # Same response as success — don't reveal that a request was just made
        # for this email (avoids an enumeration / timing side channel).
        return {"ok": True}
    link = f"{settings.prism_web_url}/auth/verify?token={raw}"
    text, html = magic_link_email(link=link, ttl_min=settings.prism_magic_token_ttl_min, to=body.email)
    await get_email_sender().send(
        to=body.email, subject="Your Parse sign-in link", body=text, html=html
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
    needs_profile = not await auth.profile_complete(db, user_id)
    return SessionResponse(
        token=token, user_id=str(user_id), email=email, needs_profile=needs_profile
    )


@router.post("/api/v1/auth/profile", response_model=MeResponse)
async def set_profile(
    body: ProfileRequest,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Complete onboarding for the signed-in reader: name, profession, location,
    languages, consent. Requires a valid session (the magic link was verified)."""
    name = (body.name or "").strip()
    if not name or len(name) > 120:
        raise HTTPException(status_code=422, detail="name required")
    if not is_valid_profession(body.profession):
        raise HTTPException(status_code=422, detail="valid profession required")
    langs = [c for c in body.languages if is_valid_language(c)]
    if not langs:
        raise HTTPException(status_code=422, detail="pick at least one language")
    if not body.consent:
        raise HTTPException(status_code=422, detail="consent required (DPDP)")
    await auth.set_profile(
        db, user_id, name=name, profession=body.profession, state=body.state, languages=langs
    )
    email = (
        await db.execute(text("SELECT email FROM users WHERE id = :i"), {"i": str(user_id)})
    ).scalar_one()
    return MeResponse(user_id=str(user_id), email=email)


@router.get("/api/v1/auth/me", response_model=MeResponse)
async def me(user_id: UUID = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    email = (
        await db.execute(text("SELECT email FROM users WHERE id = :i"), {"i": str(user_id)})
    ).scalar_one()
    return MeResponse(user_id=str(user_id), email=email)
