"""Poll the accounts' timelines into x_posts. Idempotent on post_id; each
account carries its since_id so a post is read (and billed) once."""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from sqlalchemy import text

from common.db import session_scope
from common.embeddings import embed_texts
from common.logging import get_logger
from common.text import detect_script
from correlation.clustering import EMBEDDING_TRUSTED_SCRIPTS
from xposts.accounts import ACCOUNTS
from xposts.client import XClient, post_text, post_urls

logger = get_logger(__name__)

READ_USD = 0.005  # X pay-per-use, per post read (2026-09)
_NOISE = re.compile(r"https?://\S+|@\w+|#")


def embed_text(raw: str) -> str:
    """What the embedding sees: the words, without links, handles and the hash
    sign (the tag's word stays). Pure; tested."""
    return " ".join(_NOISE.sub(" ", raw).split())


def newest_id(posts: list[dict], current: str | None) -> str | None:
    """since_id is a snowflake: numeric, monotonic. Pure; tested."""
    ids = [int(p["id"]) for p in posts if p.get("id")]
    if current:
        ids.append(int(current))
    return str(max(ids)) if ids else None


async def upsert_accounts(client: XClient) -> None:
    """The code's list is the registry: listed accounts are (re)enabled, the
    rest disabled, and an account without an X user id is resolved once."""
    async with session_scope() as s:
        for a in ACCOUNTS:
            await s.execute(text(
                "INSERT INTO x_accounts (handle, name, tier, language, enabled) VALUES (:h, :n, :t, :l, true) "
                "ON CONFLICT (handle) DO UPDATE SET name = EXCLUDED.name, tier = EXCLUDED.tier, language = EXCLUDED.language, enabled = true"
            ), {"h": a.handle, "n": a.name, "t": a.tier, "l": a.language})
        await s.execute(text("UPDATE x_accounts SET enabled = false WHERE handle <> ALL(:listed)"), {"listed": [a.handle for a in ACCOUNTS]})
        missing = [r[0] for r in (await s.execute(text("SELECT handle FROM x_accounts WHERE enabled AND user_id IS NULL"))).all()]
        if missing:
            found = await client.resolve(missing)
            for handle in missing:
                u = found.get(handle.casefold())
                if not u:
                    logger.warning("x_account_unresolved", handle=handle)
                    continue
                await s.execute(text(
                    "UPDATE x_accounts SET user_id = :id, profile_image_url = :img WHERE handle = :h"
                ), {"id": u["id"], "img": u.get("profile_image_url"), "h": handle})


async def poll_all(client: XClient) -> int:
    """One page per enabled account, newer than its watermark. Returns posts read."""
    async with session_scope() as s:
        accounts = (await s.execute(text(
            "SELECT handle, user_id, since_id FROM x_accounts WHERE enabled AND user_id IS NOT NULL ORDER BY handle"
        ))).mappings().all()
    read = 0
    for a in accounts:
        try:
            posts = await client.timeline(a["user_id"], a["since_id"])
        except Exception as exc:  # noqa: BLE001 — one account's failure must not stop the others
            logger.warning("x_poll_failed", handle=a["handle"], error=str(exc)[:200])
            continue
        read += len(posts)
        texts = [post_text(p) for p in posts]
        vecs = await embed_texts([embed_text(t) for t in texts]) if texts else []
        async with session_scope() as s:
            for p, t, v in zip(posts, texts, vecs, strict=True):
                trusted = detect_script(t) in EMBEDDING_TRUSTED_SCRIPTS
                await s.execute(text(
                    "INSERT INTO x_posts (post_id, handle, text, lang, created_at, urls, metrics, referenced, embedding) "
                    "VALUES (:id, :h, :t, :lang, :at, CAST(:urls AS jsonb), CAST(:m AS jsonb), CAST(:ref AS jsonb), CAST(:vec AS vector)) "
                    "ON CONFLICT (post_id) DO NOTHING"
                ), {
                    "id": p["id"], "h": a["handle"], "t": t, "lang": p.get("lang"),
                    "at": datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")),
                    "urls": json.dumps(post_urls(p)), "m": json.dumps(p.get("public_metrics") or {}),
                    "ref": json.dumps([r.get("id") for r in p.get("referenced_tweets") or []]),
                    "vec": str(v) if trusted else None,
                })
            await s.execute(text(
                "UPDATE x_accounts SET since_id = :since, last_polled_at = :now WHERE handle = :h"
            ), {"since": newest_id(posts, a["since_id"]), "now": datetime.now(UTC), "h": a["handle"]})
    logger.info("x_polled", accounts=len(accounts), posts=read, est_usd=round(read * READ_USD, 3))
    return read
