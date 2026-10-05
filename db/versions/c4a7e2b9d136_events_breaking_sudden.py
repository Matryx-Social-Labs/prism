"""events.breaking_sudden: the judge's reading of a breaking candidate

Revision ID: c4a7e2b9d136
Revises: b8e4d2f7a915
Create Date: 2026-10-05 00:00:00.000000

A record that crosses the breaking counts (correlation/heat.py) is asked once
whether it reports a sudden happening rather than a statement or announcement;
the answer is kept, so a candidate is judged once and the bar can be read back.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4a7e2b9d136"
down_revision: str | None = "b8e4d2f7a915"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("breaking_sudden", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "breaking_sudden")
