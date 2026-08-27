"""Load the offline fixture corpus into the LOCAL database.

    make seed          # or: uv run python -m tools.load_fixtures

A fresh clone used to serve an empty feed until you enabled ingestion and
started paying for LLM calls. This loads a real slice of production — the events
named in the gold sets plus everything needed to reconstruct them — so the whole
correlation and scoring loop runs with no API key and no spend.

WHAT THIS CORPUS CAN AND CANNOT MEASURE — read before trusting a number from it.

  L1 (article -> event) reproduces production EXACTLY. Verified: B3 precision
  0.8341, recall 0.6451, macro purity 0.9347, 77 predicted vs 56 gold clusters —
  identical to the same scorer run against production. That layer is pairwise and
  local, so a subset behaves like the whole.

  L2 (event -> story) DOES NOT, and must not be tuned here. The partition weights
  edges by 1/df where df is the actor's document frequency IN THE WINDOW. With 152
  events instead of 19,337, df collapses, 1/df explodes, and far more edges clear
  the floor: the same code scores P 0.1749 / fp 250 on the fixture against
  P 0.4344 / fp 69 in production. Nothing is broken — the corpus is simply too
  small for a global, corpus-relative statistic.

  For L2 use the full-corpus snapshot instead:
      uv run python -m tools.sweep_partition --snapshot   # read-only from prod
      uv run python -m tools.sweep_partition --cv

REFUSES TO RUN AGAINST ANYTHING BUT A LOCAL DATABASE. It writes, and the same
reasoning as tests/conftest.py applies: this repo genuinely reaches production
over the Railway proxy for admin queries, so a leftover exported DATABASE_URL is
a live path to writing fixture rows into real data.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "corpus.json.gz"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db", "postgres"}

# Order matters: FK parents first.
TABLES = [
    ("sources", ("id", "slug", "name", "source_type", "publisher", "country", "language")),
    # `raw` is NOT NULL but holds the original feed payload — bulky and useless
    # downstream, so it is defaulted rather than exported. DEFAULTS covers it.
    ("raw_items", ("id", "source_id", "external_id", "url", "title", "body", "language",
                   "published_at", "image_url", "relevance", "classification")),
    ("articles", ("id", "raw_item_id", "clean_text", "retrieval_tier", "word_count")),
    ("enrichments", ("id", "article_id", "event_type", "summary", "occurred_at", "sentiment",
                     "shared_fields", "lens_fields", "model")),
    ("events", ("id", "title", "summary", "sector", "subsector", "regions", "image_url",
                "occurred_at", "first_seen_at", "last_updated_at", "projection", "embedding")),
    ("event_memberships", ("event_id", "article_id", "match_type", "match_score", "is_survivor")),
    ("entities", ("id", "slug", "name", "entity_type")),
    ("event_entities", ("event_id", "entity_id", "role")),
]
JSONB = {"classification", "shared_fields", "lens_fields", "projection"}
VECTOR = {"embedding"}
# NOT NULL columns the fixture deliberately does not carry, with a literal to use.
# The ORM supplies uuid4 defaults in Python; a raw INSERT does not, and these
# tables have no server-side default. Postgres generates them instead.
DEFAULTS = {
    "raw_items": {"raw": "'{}'::jsonb"},
    "event_memberships": {"id": "gen_random_uuid()"},
    "event_entities": {"id": "gen_random_uuid()"},
}
TIMESTAMPS = {"published_at", "occurred_at", "first_seen_at", "last_updated_at"}


def _refuse_non_local() -> None:
    raw = re.sub(r"^postgresql\+asyncpg://", "postgresql://", get_settings().database_url)
    host = urlparse(raw).hostname or ""
    name = (urlparse(raw).path or "").lstrip("/")
    if host in LOCAL_HOSTS or name.endswith("_test"):
        return
    raise SystemExit(
        f"refusing to load fixtures into a non-local database (host={host!r} db={name!r}).\n"
        "This command WRITES. Point DATABASE_URL at localhost or a *_test database."
    )


def _time_shift(data: dict) -> timedelta:
    """How far forward to move the whole corpus so its newest event is ~now.

    Without this the fixture rots. correlation/partition.py only considers events
    with `last_updated_at > now() - 30 days`, so a corpus captured in August is
    partly invisible by September and entirely invisible by October — and the
    failure is quiet: the partition just sees fewer events and the scores drift,
    which looks like a code regression. Measured on the first attempt: 32 of 86
    gold events had already aged out.

    The shift is a single offset applied to every timestamp, so RELATIVE timing —
    which the spine, the branch tree and any time-decay term all depend on — is
    preserved exactly. Only the absolute epoch moves.
    """
    newest = max(
        (datetime.fromisoformat(e["last_updated_at"]) for e in data["events"] if e.get("last_updated_at")),
        default=None,
    )
    if newest is None:
        return timedelta(0)
    # Land the newest event a few hours back, not exactly now: several queries
    # use `now() - interval` windows and an event stamped in the future would be
    # excluded by the ones that also bound the upper edge.
    target = datetime.now(UTC) - timedelta(hours=6)
    return max(target - newest, timedelta(0))


async def load() -> None:
    _refuse_non_local()
    if not FIXTURE.exists():
        raise SystemExit(f"no fixture at {FIXTURE} — run `uv run python -m tools.export_fixtures`")
    with gzip.open(FIXTURE, "rt", encoding="utf-8") as fh:
        data = json.load(fh)

    shift = _time_shift(data)
    print(f"  shifting corpus forward by {shift.days} days so it stays inside the window")

    async with session_scope() as s:
        for table, cols in TABLES:
            rows = data.get(table) or []
            if not rows:
                continue
            placeholders = ", ".join(f":{c}" for c in cols)
            casts = ", ".join(
                f"CAST(:{c} AS vector)" if c in VECTOR
                else f"CAST(:{c} AS jsonb)" if c in JSONB
                else f"CAST(:{c} AS timestamptz)" if c in TIMESTAMPS
                else f":{c}"
                for c in cols
            )
            del placeholders
            extra = DEFAULTS.get(table, {})
            all_cols = list(cols) + list(extra)
            all_vals = casts + ("".join(f", {v}" for v in extra.values()))
            sql = text(
                f"INSERT INTO {table} ({', '.join(all_cols)}) VALUES ({all_vals}) "
                f"ON CONFLICT DO NOTHING"
            )
            payload = []
            for r in rows:
                item = {}
                for c in cols:
                    v = r.get(c)
                    if c in JSONB and v is not None:
                        v = json.dumps(v)
                    elif c in TIMESTAMPS and isinstance(v, str) and v:
                        # asyncpg type-checks the bind parameter BEFORE the SQL
                        # cast runs, so a CAST(:x AS timestamptz) does not save a
                        # string here — it has to arrive as a datetime.
                        v = datetime.fromisoformat(v) + shift
                    item[c] = v
                payload.append(item)
            await s.execute(sql, payload)
            print(f"  {table:20} {len(payload):5} rows")
    print("\nfixtures loaded. try:  make score")


if __name__ == "__main__":
    asyncio.run(load())
