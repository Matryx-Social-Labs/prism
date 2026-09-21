"""What the X developer policy asks of stored posts: keep them current, and a
post gone on X is gone here. Attached posts (the only ones a reader sees) are
looked up again weekly ($0.005 each); one that no longer exists is marked
deleted and leaves the API at once. Posts that never attached are purged after
PURGE_AFTER days — nothing shows them, so nothing needs them.

A deletion request from X or the account owner is one statement:
  UPDATE x_posts SET deleted_at = now() WHERE post_id = '…';
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from common.db import session_scope
from common.logging import get_logger
from xposts.client import XClient

logger = get_logger(__name__)

RECHECK_AFTER = timedelta(days=7)
PURGE_AFTER = timedelta(days=14)


async def rehydrate(client: XClient) -> int:
    """Re-look-up attached posts not seen for RECHECK_AFTER; returns how many
    were found deleted. Silence from X marks nothing."""
    async with session_scope() as s:
        due = [r[0] for r in (await s.execute(text(
            "SELECT DISTINCT p.post_id FROM x_posts p JOIN event_x_posts ep ON ep.post_id = p.post_id "
            "WHERE p.deleted_at IS NULL AND p.last_seen_at < :before"
        ), {"before": datetime.now(UTC) - RECHECK_AFTER})).all()]
    if not due:
        return 0
    alive = await client.lookup(due)
    if alive is None:
        return 0
    gone = [p for p in due if p not in alive]
    async with session_scope() as s:
        await s.execute(text("UPDATE x_posts SET last_seen_at = now() WHERE post_id = ANY(:ids)"), {"ids": list(alive)})
        if gone:
            await s.execute(text("UPDATE x_posts SET deleted_at = now() WHERE post_id = ANY(:ids)"), {"ids": gone})
        await s.execute(text(
            "DELETE FROM x_posts WHERE fetched_at < :before "
            "AND post_id NOT IN (SELECT post_id FROM event_x_posts)"
        ), {"before": datetime.now(UTC) - PURGE_AFTER})
    logger.info("x_rehydrated", checked=len(due), deleted=len(gone))
    return len(gone)
