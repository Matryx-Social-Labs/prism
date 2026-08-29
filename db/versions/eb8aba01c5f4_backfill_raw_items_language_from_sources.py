"""backfill raw_items.language from sources

Revision ID: eb8aba01c5f4
Revises: b17e4c9a2f31
Create Date: 2026-08-27 19:37:39.142632

"""
from collections.abc import Sequence

from alembic import op

revision: str = 'eb8aba01c5f4'
down_revision: str | None = 'b17e4c9a2f31'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Set raw_items.language from the source that produced it.

    ingestion/rss.py stamped language="en" on every envelope, including the
    Hindi, Tamil and Kannada feeds — so all 1,385 non-Latin production articles
    claimed to be English while sources.language held the right answer all along.

    Only rows that disagree with their source are touched, and only where the
    source actually declares a language, so this is a no-op on correct data and
    safe to re-run.
    """
    op.execute(
        """
        UPDATE raw_items ri
        SET language = s.language
        FROM sources s
        WHERE s.id = ri.source_id
          AND s.language IS NOT NULL
          AND s.language <> ''
          AND ri.language IS DISTINCT FROM s.language
        """
    )


def downgrade() -> None:
    """Irreversible by design: the previous values were wrong, and the correct
    ones are recoverable from sources at any time by re-running upgrade()."""
    pass
