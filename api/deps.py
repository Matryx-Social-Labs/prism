"""Shared FastAPI dependencies for the serving layer."""

from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from common import auth
from common.db import get_db


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
