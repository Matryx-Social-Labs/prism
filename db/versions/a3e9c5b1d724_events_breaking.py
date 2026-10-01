"""events.breaking_*: when a record crossed the breaking bar, and on what count

Revision ID: a3e9c5b1d724
Revises: f7d3b9c2e481
Create Date: 2026-10-01 00:00:00.000000

correlation/heat.mark_breaking sets these once, when a record first reported in
the last three hours reaches >= 6 outlets within two hours of its first report,
in >= 2 languages, and was not anticipated (its story already had coverage).
The counts are what the front page prints ("6 outlets · 3 languages in 2 h").
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3e9c5b1d724"
down_revision: str | None = "f7d3b9c2e481"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("breaking_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("breaking_outlets", sa.Integer(), nullable=True))
    op.add_column("events", sa.Column("breaking_languages", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "breaking_languages")
    op.drop_column("events", "breaking_outlets")
    op.drop_column("events", "breaking_at")
