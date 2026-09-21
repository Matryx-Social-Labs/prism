"""The X API v2, pay-per-use: $0.005 a post READ, so every call here is shaped
to read a post once. Timelines are read with since_id (a request that returns
nothing costs nothing), the first read of an account starts at now − FIRST_LOOK
rather than its 3,200-post history, and no expansions are requested — the
quoted post is an id, never a second read. Verified 2026-09-21 against
docs.x.com/x-api/getting-started/pricing.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from common.logging import get_logger

logger = get_logger(__name__)

API = "https://api.x.com/2"
UA = "Prism/1.0 (+https://www.readprism.news)"
POST_FIELDS = "created_at,entities,public_metrics,lang,referenced_tweets,note_tweet"
USER_FIELDS = "name,username,profile_image_url"
FIRST_LOOK = timedelta(hours=6)
PAGE = 100  # the endpoint's maximum; one page per account per run


class XClient:
    def __init__(self, bearer_token: str):
        self._c = httpx.AsyncClient(
            base_url=API, timeout=30,
            headers={"Authorization": f"Bearer {bearer_token}", "User-Agent": UA},
        )

    async def aclose(self) -> None:
        await self._c.aclose()

    async def _get(self, path: str, params: dict) -> dict:
        r = await self._c.get(path, params=params)
        if r.status_code == 429:
            logger.warning("x_rate_limited", path=path, reset=r.headers.get("x-rate-limit-reset"))
            return {}
        r.raise_for_status()
        return r.json()

    async def resolve(self, handles: list[str]) -> dict[str, dict]:
        """handle (casefolded) → {id, name, username, profile_image_url}. One
        request per 100 handles, $0.01 a user, once per account ever."""
        out: dict[str, dict] = {}
        for i in range(0, len(handles), 100):
            body = await self._get("/users/by", {"usernames": ",".join(handles[i:i + 100]), "user.fields": USER_FIELDS})
            for u in body.get("data") or []:
                out[u["username"].casefold()] = u
        return out

    async def timeline(self, user_id: str, since_id: str | None) -> list[dict]:
        """The account's own posts newer than since_id — no reposts, no replies.
        Without a watermark, only the last FIRST_LOOK hours."""
        params: dict = {"max_results": PAGE, "exclude": "retweets,replies", "tweet.fields": POST_FIELDS}
        if since_id:
            params["since_id"] = since_id
        else:
            params["start_time"] = (datetime.now(UTC) - FIRST_LOOK).strftime("%Y-%m-%dT%H:%M:%SZ")
        body = await self._get(f"/users/{user_id}/tweets", params)
        return body.get("data") or []

    async def lookup(self, ids: list[str]) -> set[str] | None:
        """Which of these posts still exist. None when X could not answer — the
        caller must not read silence as deletion."""
        alive: set[str] = set()
        for i in range(0, len(ids), 100):
            try:
                body = await self._get("/tweets", {"ids": ",".join(ids[i:i + 100]), "tweet.fields": "created_at"})
            except httpx.HTTPError as exc:
                logger.warning("x_lookup_failed", error=str(exc)[:160])
                return None
            if not body:
                return None
            alive.update(p["id"] for p in body.get("data") or [])
        return alive


def post_text(post: dict) -> str:
    """The words as written. A long post (X Premium, >280 chars) arrives
    truncated in `text` and whole in `note_tweet`; the display rules and the
    product agree the text is never altered, so the whole one wins."""
    note = post.get("note_tweet") or {}
    return note.get("text") or post.get("text") or ""


def post_urls(post: dict) -> list[str]:
    """Links the post carries, unwound past t.co (which never canonicalises)."""
    seen: list[str] = []
    for holder in (post, post.get("note_tweet") or {}):
        for u in ((holder.get("entities") or {}).get("urls") or []):
            link = u.get("unwound_url") or u.get("expanded_url")
            if link and link not in seen and "x.com/" not in link and "twitter.com/" not in link:
                seen.append(link)
    return seen


def permalink(handle: str, post_id: str) -> str:
    return f"https://x.com/{handle}/status/{post_id}"
