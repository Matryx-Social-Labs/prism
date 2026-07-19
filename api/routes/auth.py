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

router = APIRouter()


class MagicLinkRequest(BaseModel):
    email: str
    consent: bool = False  # DPDP: explicit consent to create an account (D12)


class VerifyRequest(BaseModel):
    token: str


class SessionResponse(BaseModel):
    token: str
    user_id: str
    email: str


class MeResponse(BaseModel):
    user_id: str
    email: str


@router.post("/api/v1/auth/request")
async def request_link(body: MagicLinkRequest, db: AsyncSession = Depends(get_db)):
    if "@" not in body.email or len(body.email) > 320:
        raise HTTPException(status_code=422, detail="invalid email")
    if not body.consent:
        raise HTTPException(status_code=422, detail="consent required (DPDP)")
    settings = get_settings()
    try:
        raw = await auth.request_magic_link(db, body.email)
    except auth.RateLimited:
        # Same response as success — don't reveal that a request was just made
        # for this email (avoids an enumeration / timing side channel).
        return {"ok": True}
    link = f"{settings.prism_web_url}/auth/verify?token={raw}"
    await get_email_sender().send(
        to=body.email,
        subject="Your Prism sign-in link",
        body=(
            f"Sign in to Prism: {link}\n\n"
            f"This link expires in {settings.prism_magic_token_ttl_min} minutes and can be used once."
        ),
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
