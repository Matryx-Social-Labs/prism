# api/

The FastAPI app (`api/main.py`) — served at `https://api.readprism.news` on Railway.

- `routes/` — one router per concern; every path is written in full (`/api/v1/...`), and
  each module is registered by hand in `main.py`
- `schemas.py` — response models shared by more than one route (pure Pydantic)
- `deps.py` — the auth tiers: account session (HttpOnly cookie or Bearer), static admin
  token, admin-by-account (`PRISM_ADMIN_EMAILS`); labelling uses its own invite token
- `routes/serialization.py` — `build_feed_item`, the one serialiser for a story row

The route surface is locked by `tests/test_api_routes.py`: add a route there in the same
change. Every endpoint: [docs/API.md](../docs/API.md).
