"""record the classification stage clock

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-09-17 00:00:00.000000

Existing rows deliberately remain NULL. Their ``updated_at`` values may have
been changed by enrichment, so backfilling them would manufacture false latency
measurements. New classifications get an exact timestamp in the consumer.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "raw_items",
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("raw_items", "classified_at", if_exists=True)
