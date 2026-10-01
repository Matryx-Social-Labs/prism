"""events.first_published_at: when a record was first reported, not first processed

Revision ID: c7d4e9a2b815
Revises: b3e7f1c2a9d4
Create Date: 2026-10-01 00:00:00.000000

`first_seen_at` is when Prism ingested the founding article. After a backlog
that is processing order: the Flydubai cockpit-attack story (190 articles
published 2026-09-30 07:30 to 10-01 12:10 UTC, 70 records) showed every record
between 10-01 08:18 and 12:14, and its timelines read in that order. The new
column holds the earliest member article's own publication time, within a
week before first_seen_at and an hour after (an RSS date can be months old or
in the future), else first_seen_at. correlation/chronology.place_in_time keeps
it on every projection rebuild; tools/backfill_first_published.py fills the
rows that existed before it.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7d4e9a2b815"
down_revision: str | None = "b3e7f1c2a9d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A nullable column with no default is metadata-only, but ALTER waits for
    # ACCESS EXCLUSIVE behind open transactions on events: fail fast rather
    # than queue every reader behind it.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column("events", sa.Column("first_published_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "first_published_at")
