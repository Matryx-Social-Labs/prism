"""Every change made from /admin, recorded against the founder who made it.

Written in the SAME transaction as the change, so a change without its record
(or a record of a change that rolled back) cannot exist. Read back on the
dashboard's audit page; never edited or deleted by the app.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession


async def audit(db: AsyncSession | AsyncConnection, actor: str, action: str, target: str,
                detail: dict[str, Any] | None = None) -> None:
    await db.execute(
        text("INSERT INTO admin_audit (actor, action, target, detail) VALUES (:a, :x, :t, CAST(:d AS jsonb))"),
        {"a": actor, "x": action, "t": target, "d": json.dumps(detail or {})},
    )


async def recent(db: AsyncSession, limit: int) -> list[dict[str, Any]]:
    rows = (await db.execute(
        text("SELECT actor, action, target, detail, created_at FROM admin_audit ORDER BY id DESC LIMIT :n"),
        {"n": limit},
    )).mappings().all()
    return [dict(r) for r in rows]
