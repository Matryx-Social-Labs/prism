"""POST /api/v1/beacon — count one page view or action (admin dashboard, phase 3).

The web's `track()` and page-view hook post here. Anonymous by design: it takes
an event name and one word, and keeps only a daily count (common/usage.py says
exactly what is and is not kept, and the privacy policy says the same).

Always 204, whatever happened, so a script learns nothing from the answer. What
is dropped: bots by user agent; anything whose word is not on the list; a
visitor past the day's cap; and everything while Redis is away — the cap and
the visitor count both live there, and an uncapped counter would let one
script write the numbers investors are shown. An outage undercounts; it never
overcounts.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import client_ip, get_current_user_optional
from common import usage
from common.db import get_db
from common.logging import get_logger
from common.stream import get_redis

router = APIRouter()
logger = get_logger(__name__)


class Beacon(BaseModel):
    e: Literal["view", "arrival", "share", "ask", "lens", "subscribe", "signin"]
    d: Annotated[str, Field(max_length=48)] = ""
    # An arrival's referrer HOST (never the path) and its ?s= share marker.
    ref: Annotated[str, Field(max_length=253)] = ""
    s: Annotated[str, Field(max_length=16)] = ""


@router.post("/api/v1/beacon", status_code=204)
async def beacon(
    body: Beacon,
    request: Request,
    user_id: uuid.UUID | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> Response:
    ua = request.headers.get("user-agent", "")
    dim = usage.dimension(body.e, body.d, body.ref, body.s)
    if dim is None or usage.is_bot(ua):
        return Response(status_code=204)
    day = usage.today()
    try:
        r = get_redis()
        v = usage.visitor(await usage.day_salt(r, day.isoformat()), client_ip(request) or "", ua)
        n_key = f"prism:usage:n:{day.isoformat()}:{v}"
        n = await r.incr(n_key)
        if n == 1:
            await r.expire(n_key, usage.TWO_DAYS_S)
        if n > usage.EVENTS_PER_VISITOR_PER_DAY:
            return Response(status_code=204)
        new_visitor = False
        if body.e == "view":
            v_key = f"prism:usage:v:{day.isoformat()}"
            new_visitor = await r.sadd(v_key, v) == 1
            await r.expire(v_key, usage.TWO_DAYS_S)
    except Exception as exc:  # noqa: BLE001 — fail closed: see the module docstring
        logger.warning("beacon_redis_unavailable", error_type=type(exc).__name__)
        return Response(status_code=204)
    await usage.bump(db, body.e, dim, day)
    if new_visitor:
        await usage.bump(db, "visitors", "", day)
    if user_id is not None:
        await usage.active(db, user_id, day)
    return Response(status_code=204)
