"""Magic-link auth logic (N3-compliant), independent of FastAPI so it can be
unit-tested directly.

Discipline (eng-review N3):
- Tokens are random (`secrets.token_urlsafe`) and stored only as SHA-256 hashes —
  the raw value lives only in the emailed link and the client's Authorization header.
- Magic tokens are single-use (`consumed_at`) and time-limited.
- Requests are rate-limited per email.
- Sessions are bearer tokens (no cookie → no CSRF surface), revocable by row delete.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.quota import grant_samples


class RateLimited(Exception):
    """A magic link was requested for this email inside the cooldown window."""


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def request_magic_link(session: AsyncSession, email: str) -> str:
    """Create a single-use magic token for `email`; return the RAW token (the
    caller emails it). Email-only: the sign-up profile (name/profession/languages)
    is collected AFTER the link is verified (see set_profile), so this transactional
    link needs nothing but an email and creates no account. Raises RateLimited if
    one was requested too recently."""
    settings = get_settings()
    email = email.strip().lower()
    recent = (
        await session.execute(
            text(
                "SELECT 1 FROM auth_tokens WHERE email = :e "
                "AND created_at > now() - make_interval(secs => :cd) LIMIT 1"
            ),
            {"e": email, "cd": settings.prism_magic_request_cooldown_s},
        )
    ).scalar_one_or_none()
    if recent is not None:
        raise RateLimited(email)
    raw = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(minutes=settings.prism_magic_token_ttl_min)
    await session.execute(
        text(
            "INSERT INTO auth_tokens (id, email, token_hash, expires_at) "
            "VALUES (gen_random_uuid(), :e, :h, :exp)"
        ),
        {"e": email, "h": _hash(raw), "exp": expires},
    )
    return raw


async def verify_and_consume(session: AsyncSession, raw_token: str) -> UUID | None:
    """Consume a magic token (single-use) and return the authenticated user id,
    creating the user + granting free Markets samples on first sign-in. Returns
    None if the token is unknown, expired, or already consumed.

    The UPDATE ... WHERE consumed_at IS NULL ... RETURNING makes consumption
    atomic — a token replayed concurrently is spent exactly once.
    """
    email = (
        await session.execute(
            text(
                "UPDATE auth_tokens SET consumed_at = now() "
                "WHERE token_hash = :h AND consumed_at IS NULL AND expires_at > now() "
                "RETURNING email"
            ),
            {"h": _hash(raw_token)},
        )
    ).scalar_one_or_none()
    if email is None:
        return None
    return await user_for_verified_email(session, email)


async def user_for_verified_email(session: AsyncSession, email: str) -> UUID:
    """The account for an email some identity provider has VERIFIED — a consumed
    magic link, or a Google ID token with email_verified. Creates it on first
    sign-in (no unverified/junk rows) and grants the free Markets samples once;
    a Google sign-in on an address that already has a magic-link account lands
    in the same account, since the verified email is the identity."""
    email = email.strip().lower()
    user_id = (
        await session.execute(
            text(
                "INSERT INTO users (id, email) VALUES (gen_random_uuid(), :e) "
                "ON CONFLICT (email) DO NOTHING RETURNING id"
            ),
            {"e": email},
        )
    ).scalar_one_or_none()
    if user_id is None:  # existing user
        user_id = (
            await session.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email})
        ).scalar_one()
    else:  # new user — grant the free Markets samples once
        await grant_samples(session, user_id, get_settings().prism_free_markets_samples)
    return user_id


GOOGLE_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleTokenInvalid(ValueError):
    pass


async def verify_google_id_token(credential: str) -> str:
    """Google Identity Services hands the browser a signed ID token; the browser
    hands it to us. Google's tokeninfo endpoint checks the signature and expiry
    (no JWKS/crypto dependency here — sign-ins are rare); we check it was minted
    for OUR client id, by Google, for a verified email. Returns the email."""
    import httpx

    client_id = get_settings().google_client_id
    if not client_id:
        raise GoogleTokenInvalid("google sign-in is not configured")
    async with httpx.AsyncClient(timeout=8.0) as http:
        r = await http.get(GOOGLE_TOKENINFO, params={"id_token": credential})
    if r.status_code != 200:
        raise GoogleTokenInvalid("token rejected by google")
    claims = r.json()
    if claims.get("aud") != client_id:
        raise GoogleTokenInvalid("token was not issued for this app")
    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise GoogleTokenInvalid("unexpected issuer")
    if str(claims.get("email_verified")).lower() != "true" or not claims.get("email"):
        raise GoogleTokenInvalid("email not verified")
    return str(claims["email"])


async def profile_complete(session: AsyncSession, user_id: UUID) -> bool:
    """A profile is complete once the reader has picked a profession (the gate the
    onboarding step fills). Drives the `needs_profile` flag returned on verify."""
    profession = (
        await session.execute(
            text("SELECT profession FROM users WHERE id = :i"), {"i": str(user_id)}
        )
    ).scalar_one_or_none()
    return profession is not None


async def set_profile(
    session: AsyncSession,
    user_id: UUID,
    *,
    name: str,
    profession: str,
    state: str | None,
    languages: list[str],
) -> None:
    """Persist the onboarding profile + stamp consent. Consent is recorded here
    (not at the email step) because that's where the reader agrees to the terms."""
    await session.execute(
        text(
            "UPDATE users SET name = :n, profession = :p, state = :s, "
            "languages = CAST(:langs AS text[]), consented_at = now() WHERE id = :i"
        ),
        {"n": name, "p": profession, "s": state, "langs": languages, "i": str(user_id)},
    )


async def create_session(session: AsyncSession, user_id: UUID) -> str:
    """Issue a bearer session token; store only its hash. Returns the raw token."""
    raw = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(days=get_settings().prism_session_ttl_days)
    await session.execute(
        text(
            "INSERT INTO sessions (id, user_id, token_hash, expires_at) "
            "VALUES (gen_random_uuid(), :uid, :h, :exp)"
        ),
        {"uid": str(user_id), "h": _hash(raw), "exp": expires},
    )
    return raw


async def resolve_session(session: AsyncSession, bearer: str) -> UUID | None:
    """Return the user id for a valid, unexpired bearer token, else None."""
    return (
        await session.execute(
            text("SELECT user_id FROM sessions WHERE token_hash = :h AND expires_at > now()"),
            {"h": _hash(bearer)},
        )
    ).scalar_one_or_none()
