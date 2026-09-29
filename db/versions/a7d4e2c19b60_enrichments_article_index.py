"""index enrichments by article so a record's enrichments are not a full scan

Revision ID: a7d4e2c19b60
Revises: f6b2d8e4a915
Create Date: 2026-09-29 00:00:00.000000

The story page (and, since 2026-09-29, an actor's "What <name> said") reads a
record's enrichments by `article_id`. No index covered it. Measured on
production (38,197 rows, 112 MB): `WHERE article_id = ANY(<12 ids>)` is a Seq
Scan, 21 ms and 7,634 buffers per lookup, and it grows in a straight line with
the corpus. A btree makes it an index lookup.

CONCURRENTLY is not available inside Alembic's transaction; at this size a plain
CREATE INDEX finishes well within the deploy's healthcheck window (as
c8a3f5d21b74 did for search).
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'a7d4e2c19b60'
down_revision: str | None = 'f6b2d8e4a915'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_enrichments_article_id ON enrichments (article_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_enrichments_article_id")
