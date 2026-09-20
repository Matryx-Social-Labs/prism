"""Prism serving layer — /api/v1 REST + SSE (docs: api/README.md).

Shared by the Next.js web app now and the React Native app later.
Route handlers live in api/routes/*; this module only wires the app,
middleware, and routers. Response models live in api/schemas.py.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import (
    admin,
    auth,
    billing,
    digest,
    events,
    feed,
    label,
    meta,
    search,
    trending,
    watchlist,
)
from common.config import get_settings
from common.logging import setup_logging

setup_logging()

app = FastAPI(
    title="Prism API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# One router per concern. Paths are absolute in each router, so the app's
# route set is identical to the pre-split single-file version.
app.include_router(meta.router)
app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(feed.router)
app.include_router(search.router)
app.include_router(digest.router)
app.include_router(events.router)
app.include_router(trending.router)
app.include_router(watchlist.router)
app.include_router(label.router)
app.include_router(admin.router)
