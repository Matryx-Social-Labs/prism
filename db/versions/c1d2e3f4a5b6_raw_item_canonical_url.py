"""raw item canonical URL comparison key

Revision ID: c1d2e3f4a5b6
Revises: b8c4f1d20e57
Create Date: 2026-09-17 00:00:00.000000

``raw_items.url`` remains the publisher observation and is never rewritten.
``url_canonical`` is a versioned comparison key used to reuse extraction and
match repeat observations to the same event despite tracking parameters.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b8c4f1d20e57"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("raw_items", sa.Column("url_canonical", sa.Text(), nullable=True))
    op.add_column("raw_items", sa.Column("url_canonical_version", sa.SmallInteger(), nullable=True))
    op.create_index(
        "ix_raw_items_url_canonical", "raw_items", ["url_canonical"],
        postgresql_where=sa.text("url_canonical IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_raw_items_url_canonical", table_name="raw_items")
    op.drop_column("raw_items", "url_canonical_version", if_exists=True)
    op.drop_column("raw_items", "url_canonical", if_exists=True)
