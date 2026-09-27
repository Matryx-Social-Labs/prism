"""Browser cache headers for the API's public reads.

Audit, 2026-09-27: 15 of 17 public GETs sent no Cache-Control, so a reader's
browser asked the API in Singapore again for the same feed, digest or taxonomy
on every visit (Railway's edge caches nothing). A read listed here is the same
for every reader — the URL is the whole key — and tests/test_api_cache_headers.py
fails if a listed route ever reads the session or the raw request.

Only a successful GET is marked, and a route that sets its own policy
(subject.py) keeps it. Everything unlisted is left as it was: uncached.
"""

from __future__ import annotations

import re

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Seconds a browser may reuse a response; it may serve one twice that old while
# it re-asks. Short where the answer moves (the feed), long for the vocabularies.
_PUBLIC: list[tuple[re.Pattern[str], int]] = [
    (re.compile(p), s)
    for p, s in (
        (r"^/api/v1/feed$", 30),
        (r"^/api/v1/search$", 60),
        (r"^/api/v1/trending$", 60),
        (r"^/api/v1/trending/[^/]+$", 60),
        (r"^/api/v1/entity/[^/]+$", 300),
        (r"^/api/v1/events/[^/]+/versions$", 300),
        (r"^/api/v1/corrections$", 300),
        (r"^/api/v1/digest/markets$", 300),
        (r"^/api/v1/sources$", 300),
        (r"^/api/v1/billing/plans$", 300),
        (r"^/api/v1/(lenses|regions|taxonomy|professions|languages)$", 3600),
    )
]


def cache_control_for(path: str) -> str | None:
    for pattern, seconds in _PUBLIC:
        if pattern.match(path):
            return f"public, max-age={seconds}, stale-while-revalidate={seconds * 2}"
    return None


class PublicCacheHeaders:
    """Pure ASGI, so the Ask stream passes through untouched."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        value = cache_control_for(scope["path"]) if scope["type"] == "http" and scope["method"] == "GET" else None
        if value is None:
            await self.app(scope, receive, send)
            return

        async def send_marked(message: Message) -> None:
            if message["type"] == "http.response.start" and message["status"] == 200:
                headers = MutableHeaders(scope=message)
                if "cache-control" not in headers:
                    headers["Cache-Control"] = value
            await send(message)

        await self.app(scope, receive, send_marked)
