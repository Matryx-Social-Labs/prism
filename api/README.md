# api/

The serving layer (FastAPI). Exposes the personalized feed, the story view (both sides, impact and
control mapping, sources), user profile and onboarding, alerts and subscriptions, and the per-story
agent endpoints. Real-time push (the feed and the Phase 2 trader fast-lane) is served over
websockets or SSE.

See [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).
