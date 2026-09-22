"""Shared FastAPI dependencies for the serving layer."""

import hmac
from typing import Any
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from common import auth
from common.config import Settings, get_settings
from common.db import get_db

ADMIN_TOKEN_PLACEHOLDER = "change-me"


def assert_admin_token_configured(settings: Settings) -> None:
    """Refuse to serve outside a laptop with the placeholder admin token.

    The default exists so `make up` works with no secrets; a deploy that forgot
    PRISM_ADMIN_TOKEN would otherwise accept the string from .env.example on
    /admin/pipeline/run and the gold-set export."""
    local = "localhost" in settings.prism_web_url or "127.0.0.1" in settings.prism_web_url
    if settings.prism_admin_token == ADMIN_TOKEN_PLACEHOLDER and not local:
        raise RuntimeError("PRISM_ADMIN_TOKEN is the placeholder; set it before serving")


def client_ip(request: Any) -> str | None:
    """The caller's address, as far as a trusted proxy vouches for it.

    `X-Forwarded-For` reads client, proxy1, proxy2…: everything to the LEFT of
    the hops our own proxies appended is whatever the caller chose to send. The
    anonymous Ask cap is keyed on this, so taking the first entry (as this did)
    meant one script with a rotating header had an unlimited number of
    identities and could exhaust the day's spend ceiling for every reader
    (audit H2).
    """
    hops = get_settings().prism_trusted_proxy_hops
    socket_ip = request.client.host if request.client else None
    if hops <= 0:
        return socket_ip
    chain = [p.strip() for p in (request.headers.get("x-forwarded-for") or "").split(",") if p.strip()]
    if not chain:
        return socket_ip
    # The proxy nearest us appended the last entry; step back over the hops we
    # trust. A chain shorter than that is a direct or misconfigured call — take
    # its leftmost entry rather than inventing one.
    return chain[-hops] if len(chain) >= hops else chain[0]


async def require_admin(x_admin_token: str = Header(default="")) -> None:
    """The operator's token, compared in constant time. One dependency for the
    three admin surfaces, so the header name and the 403 live in one place."""
    if not hmac.compare_digest(x_admin_token.encode(), get_settings().prism_admin_token.encode()):
        raise HTTPException(status_code=403, detail="admin token required")


async def get_current_user(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """Resolve the `Authorization: Bearer <token>` header to a user id, else 401.

    Used by the read-time paywall gate, the watchlist, and the personalized brief.
    """
    user_id = await get_current_user_optional(authorization, db)
    if user_id is None:
        # ONE message, not two. The previous version distinguished "missing
        # bearer token" from "invalid or expired session", which is a small
        # information leak: it tells an unauthenticated caller whether a token
        # exists. It also duplicated the parse, which is the actual reason this
        # delegates now.
        raise HTTPException(status_code=401, detail="missing or invalid session")
    return user_id


async def get_current_user_optional(
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> UUID | None:
    """The same resolution, but None instead of 401 when there is no valid session.

    Ask is deliberately open to anonymous readers — the free tier is the top of
    the funnel and a login wall there would cost the audience the product is
    built to gather. So identity has to be OPTIONAL: signed-in usage gets
    attributed, anonymous usage still works.

    A bad or expired token is treated as anonymous rather than rejected, for the
    same reason: someone whose session lapsed mid-read should get an answer, not
    an error they cannot act on.
    """
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return await auth.resolve_session(db, token)
