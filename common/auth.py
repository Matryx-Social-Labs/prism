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


async def request_magic_link(
    session: AsyncSession,
    email: str,
    name: str | None = None,
    profession: str | None = None,
) -> str:
    """Create a single-use magic token for `email`; return the RAW token (the
    caller emails it). name/profession (sign-up profile) ride on the token and
    are applied only when it creates a brand-new user. Raises RateLimited if one
    was requested too recently."""
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
            "INSERT INTO auth_tokens (id, email, token_hash, expires_at, name, profession) "
            "VALUES (gen_random_uuid(), :e, :h, :exp, :n, :p)"
        ),
        {"e": email, "h": _hash(raw), "exp": expires, "n": name, "p": profession},
    )
    return raw


async def verify_and_consume(session: AsyncSession, raw_token: str) -> UUID | None:
    """Consume a magic token (single-use) and return the authenticated user id,
    creating the user + granting free Markets samples on first sign-in. Returns
    None if the token is unknown, expired, or already consumed.

    The UPDATE ... WHERE consumed_at IS NULL ... RETURNING makes consumption
    atomic — a token replayed concurrently is spent exactly once.
    """
    row = (
        await session.execute(
            text(
                "UPDATE auth_tokens SET consumed_at = now() "
                "WHERE token_hash = :h AND consumed_at IS NULL AND expires_at > now() "
                "RETURNING email, name, profession"
            ),
            {"h": _hash(raw_token)},
        )
    ).mappings().first()
    if row is None:
        return None
    email = row["email"]
    # Upsert the user; a returned id means this is a brand-new account. On first
    # creation, stamp the sign-up profile carried on the token.
    user_id = (
        await session.execute(
            text(
                "INSERT INTO users (id, email, name, profession) "
                "VALUES (gen_random_uuid(), :e, :n, :p) "
                "ON CONFLICT (email) DO NOTHING RETURNING id"
            ),
            {"e": email, "n": row["name"], "p": row["profession"]},
        )
    ).scalar_one_or_none()
    if user_id is None:  # existing user
        user_id = (
            await session.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email})
        ).scalar_one()
    else:  # new user — grant the free Markets samples once
        await grant_samples(session, user_id, get_settings().prism_free_markets_samples)
    return user_id


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
