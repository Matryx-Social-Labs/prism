"""IndexNow: tell Bing (and so Copilot / ChatGPT search, which read Bing's
index), Yandex and Naver about records the moment they change, instead of
waiting for a crawl. Google does not take IndexNow; the sitemaps carry it.

The key is public by design — the protocol proves ownership by serving the key
back at https://<host>/<key>.txt (web/public/<key>.txt) — so it lives in code,
not in an environment variable. One POST per hour with every URL that changed;
never a failure that reaches the worker's other jobs.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from sqlalchemy import text

from common.config import get_settings
from common.logging import get_logger

logger = get_logger(__name__)

# The feed's own rule (api/routes/feed.py): a record whose only sources are the
# CVE feeds is not journalism and is not served — so not pinged either.
CVE_ONLY_JSON = json.dumps(sorted({"nvd", "cisa_kev"}))

KEY = "f03e0a4bf99412be88776a3ae743d5fd"
ENDPOINT = "https://api.indexnow.org/indexnow"
BATCH = 10_000  # the protocol's cap per submission


def _host() -> str:
    return get_settings().prism_web_url.rstrip("/").split("://", 1)[-1]


async def changed_urls(db, *, since_minutes: int = 70) -> list[str]:
    """Records and stories that moved in the window: the same rows the feed and
    Stories serve (CVE-only records excluded, merged stories excluded)."""
    web = get_settings().prism_web_url.rstrip("/")
    events = (
        await db.execute(
            text(
                """
                SELECT e.id FROM events e
                WHERE e.last_updated_at >= now() - make_interval(mins => :m)
                  AND NOT (
                      COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) > 0
                      AND (e.projection->'source_slugs') <@ CAST(:cve_only AS jsonb)
                  )
                ORDER BY e.last_updated_at DESC LIMIT 2000
                """
            ),
            {"m": since_minutes, "cve_only": CVE_ONLY_JSON},
        )
    ).scalars().all()
    stories = (
        await db.execute(
            text(
                "SELECT slug FROM stories WHERE status = 'active' AND merged_into IS NULL "
                "AND last_updated_at >= now() - make_interval(mins => :m) ORDER BY last_updated_at DESC LIMIT 500"
            ),
            {"m": since_minutes},
        )
    ).scalars().all()
    urls = [f"{web}/story/{i}" for i in events] + [f"{web}/trending/{s}" for s in stories]
    if urls:
        urls += [f"{web}/feed", f"{web}/trending"]
    return urls


async def submit(urls: list[str], client: httpx.AsyncClient | None = None) -> int:
    """POST the batch; returns how many URLs were accepted (0 on any failure)."""
    if not urls:
        return 0
    host = _host()
    if host.startswith("localhost") or host.startswith("127."):
        return 0  # a dev machine never pings the index
    own = client is None
    client = client or httpx.AsyncClient(timeout=20)
    try:
        body: dict[str, Any] = {"host": host, "key": KEY, "keyLocation": f"https://{host}/{KEY}.txt", "urlList": urls[:BATCH]}
        r = await client.post(ENDPOINT, json=body, headers={"Content-Type": "application/json; charset=utf-8"})
        # 200 OK · 202 Accepted (key not yet verified) — both mean received.
        if r.status_code in (200, 202):
            logger.info("indexnow_submitted", urls=len(body["urlList"]), status=r.status_code)
            return len(body["urlList"])
        logger.warning("indexnow_refused", status=r.status_code, body=r.text[:160])
        return 0
    except Exception:
        logger.exception("indexnow_failed")
        return 0
    finally:
        if own:
            await client.aclose()


async def ping_changed(db) -> int:
    return await submit(await changed_urls(db))
