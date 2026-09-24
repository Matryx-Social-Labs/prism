"""Shared FastAPI dependencies for the serving layer."""

import hmac
import re
from typing import Any
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, Response
from sqlalchemy import text
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


def admin_emails() -> frozenset[str]:
    return frozenset(e.strip().lower() for e in get_settings().prism_admin_emails.split(",") if e.strip())


# The browser writes that may carry the session cookie. A cookie is sent by the
# browser on its own, so a write it authenticates must come from one of our
# pages: SameSite=Lax already stops another site's form, and this stops anything
# SameSite does not (audit C5, defence in depth). A request with no Origin is
# not a browser page and carries no ambient cookie of ours unless it copied one.
_SAFE = frozenset({"GET", "HEAD", "OPTIONS"})
_PREVIEW = re.compile(r"https://prism-[a-z0-9-]+-matrixsociallabs-projects\.vercel\.app")


def _origin_ok(request: Request) -> bool:
    if request.method in _SAFE:
        return True
    origin = request.headers.get("origin")
    return origin is None or origin in get_settings().cors_origin_list or bool(_PREVIEW.fullmatch(origin))


def session_token(request: Request, authorization: str) -> str | None:
    """The presented session: the Authorization header (tools, tests, and pages
    signed in before the cookie, until they migrate), else the HttpOnly cookie,
    which only counts on a write from one of our own pages."""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        return token
    cookie = request.cookies.get(get_settings().prism_session_cookie)
    return cookie if cookie and _origin_ok(request) else None


def set_session_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        s.prism_session_cookie, token, max_age=s.prism_session_ttl_days * 86400, path="/",
        domain=s.prism_cookie_domain or None, secure=s.prism_cookie_secure, httponly=True, samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(s.prism_session_cookie, path="/", domain=s.prism_cookie_domain or None,
                           secure=s.prism_cookie_secure, httponly=True, samesite="lax")


async def get_current_user(
    request: Request,
    authorization: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """Resolve the `Authorization: Bearer <token>` header to a user id, else 401.

    Used by the read-time paywall gate, the watchlist, and the personalized brief.
    """
    user_id = await get_current_user_optional(request, authorization, db)
    if user_id is None:
        # ONE message, not two. The previous version distinguished "missing
        # bearer token" from "invalid or expired session", which is a small
        # information leak: it tells an unauthenticated caller whether a token
        # exists. It also duplicated the parse, which is the actual reason this
        # delegates now.
        raise HTTPException(status_code=401, detail="missing or invalid session")
    return user_id


async def get_current_user_optional(
    request: Request,
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
    token = session_token(request, authorization)
    return await auth.resolve_session(db, token) if token else None


async def require_admin_user(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> str:
    """The signed-in founder's email, when it is on PRISM_ADMIN_EMAILS; else 403.

    The /admin dashboard's guard (founder decision D1). An account, not the
    shared token: every change it makes is recorded against a person
    (common/admin_audit), and a founder who leaves is removed by editing one
    variable rather than rotating a secret everyone holds."""
    email = (await db.execute(text("SELECT lower(email) FROM users WHERE id = :u"), {"u": user_id})).scalar()
    if not email or email not in admin_emails():
        raise HTTPException(status_code=403, detail="not an admin")
    return email
