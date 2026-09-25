"""trigram index on entities.name so search can match a record's cast

Revision ID: d4b7e2a9c1f3
Revises: f2b8d5a1c740
Create Date: 2026-09-25 00:00:00.000000

`/api/v1/search` now also matches the people and organisations named in a
record (`entities.name ILIKE '%q%'`), because the search page offers the names in
the news now and a name like "Nanavati Hospital" is in a record's cast without
being in its headline. Same reasoning as c8a3f5d21b74: a leading wildcard needs
trigrams, not a btree. 73,573 rows on production (2026-09-25), so a plain CREATE
INDEX finishes well within the deploy's healthcheck window.
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'd4b7e2a9c1f3'
down_revision: str | None = 'f2b8d5a1c740'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE INDEX IF NOT EXISTS ix_entities_name_trgm ON entities USING gin (name gin_trgm_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_entities_name_trgm")
