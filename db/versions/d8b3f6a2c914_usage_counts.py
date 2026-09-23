"""usage_daily + user_days: how Prism is used, counted without knowing who

Revision ID: d8b3f6a2c914
Revises: c5f1a8e3b720
Create Date: 2026-09-23 00:00:00.000000

Founder decisions D2/D3 (admin dashboard, 2026-09-23). Nothing about a reader
was being counted: Plausible was wired in and never switched on.

- `usage_daily` — one row per (IST day, event, dimension) with a count: page
  views by kind of page, arrivals by where they came from, shares by surface,
  lens opens, Ask by entry point, the steps of subscribing. Totals only; no
  id, no address, no story, no question. `visitors` is a row here too: the
  day's distinct visitors, counted in Redis against a daily-rotating salt that
  is deleted within two days, so no hash ever reaches this table.
- `user_days` — the IST days a SIGNED-IN account used Prism. A date and
  nothing about what was read; it is what retention is measured on, and the
  privacy policy says so.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d8b3f6a2c914"
down_revision: str | None = "c5f1a8e3b720"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_daily",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("event", sa.Text(), primary_key=True),
        sa.Column("dim", sa.Text(), primary_key=True, server_default=""),
        sa.Column("count", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_table(
        "user_days",
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
    )
    op.create_index("ix_user_days_day", "user_days", ["day"])


def downgrade() -> None:
    op.drop_index("ix_user_days_day", table_name="user_days")
    op.drop_table("user_days")
    op.drop_table("usage_daily")
