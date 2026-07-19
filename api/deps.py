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
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing bearer token")
    user_id = await auth.resolve_session(db, token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="invalid or expired session")
    return user_id
