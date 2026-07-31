"""index event_memberships(article_id) — the missing leading-column index

Revision ID: b17e4c9a2f31
Revises: c4d18e60a927
Create Date: 2026-07-31 09:40:00.000000

event_memberships carries UNIQUE(event_id, article_id), so nothing leads with
article_id. Every lookup "which event holds this article?" is therefore a
sequential scan of the whole table, and two hot paths do exactly that on every
article ingested:

  - correlation/clustering.py::_match_by_url resolves a duplicate URL to its event
  - correlation/clustering.py::_match_by_entities joins article_entities to
    event_memberships on article_id to find candidate events

18,632 rows today and it only grows. The composite unique index cannot serve
these because a b-tree is only useful from its leading column.

"""
from collections.abc import Sequence

from alembic import op

revision: str = "b17e4c9a2f31"
down_revision: str | None = "c4d18e60a927"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # CONCURRENTLY + IF NOT EXISTS + autocommit_block, per 51de411d824c: the
    # worker writes this table continuously, `alembic upgrade head` runs inside
    # the deploy start command, and a lock fight there means the API never boots
    # and the healthcheck fails.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_event_memberships_article "
            "ON event_memberships (article_id)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_event_memberships_article")
