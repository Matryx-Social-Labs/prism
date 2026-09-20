"""raw_items.image_phash: a perceptual fingerprint of the report's photo

Revision ID: c9f1a2b3d4e5
Revises: b4e8d1c72f90
Create Date: 2026-09-20 16:00:00.000000

Two uploads of one photograph (BBC's language editions) read as one picture
in a story's rail. 64-bit dHash as 16 hex chars; NULL = not hashed (no image,
or the fetch failed). common/imagehash.py.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c9f1a2b3d4e5'
down_revision: str | None = 'b4e8d1c72f90'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("raw_items", sa.Column("image_phash", sa.Text()))


def downgrade() -> None:
    op.drop_column("raw_items", "image_phash")
