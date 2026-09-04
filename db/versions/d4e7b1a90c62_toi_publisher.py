"""regional editions fold into their masthead (toi_*, bbc_tamil, bbc_world)

Revision ID: d4e7b1a90c62
Revises: c5f9a71e3b48
Create Date: 2026-09-04 00:00:00.000000

`sources.publisher` exists so corroboration counts MASTHEADS, not feeds — the
comment on the column says so, and `COALESCE(s.publisher, s.slug)` in
correlation/trending.py and correlation/consumer.py is where it is read.

Four sources shipped without one and coalesced to their own slugs:
toi_delhi + toi_mumbai (The Times of India counted as THREE publishers), and
bbc_tamil + bbc_world, which predate the bbc_* family block in seed.py and never
picked up the publisher the other seven BBC feeds carry. Consequences, all user-facing:

  - `total_sources` on a trending story, shown to the reader as corroboration
  - `single_origin` (fires when exactly one publisher tells a story), which is
    the "only one newsroom is reporting this" signal
  - `source_count`, which `_root()` uses to pick a storyline's trunk

Measured on production: 800 URLs arrived under more than one source, and the
duplicated copies land in the SAME event, so each inflated that event's
publisher count by one.

ingestion/seed.py is `on_conflict_do_nothing`, so fixing the seed row does not
touch a database that already has these sources. This does.
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'd4e7b1a90c62'
down_revision: str | None = 'c5f9a71e3b48'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE sources SET publisher = 'timesofindia' "
        "WHERE slug IN ('toi_delhi', 'toi_mumbai')"
    )
    # bbc_world is not in ingestion/seed.py at all — it exists only in the
    # database — so the seed fix cannot reach it and this is its only repair.
    op.execute(
        "UPDATE sources SET publisher = 'bbc' "
        "WHERE slug IN ('bbc_tamil', 'bbc_world')"
    )


def downgrade() -> None:
    # Back to NULL, which is what they held: COALESCE then falls back to the slug
    # and each city edition counts as its own publisher again.
    op.execute(
        "UPDATE sources SET publisher = NULL "
        "WHERE slug IN ('toi_delhi', 'toi_mumbai', 'bbc_tamil', 'bbc_world')"
    )
