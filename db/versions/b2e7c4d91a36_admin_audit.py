"""admin_audit: who changed what from the /admin dashboard

Revision ID: b2e7c4d91a36
Revises: a9d4e2c7b815
Create Date: 2026-09-23 00:00:00.000000

The dashboard lets a founder approve and pause labellers, publish tests and
list batches on production (founder decision D1, 2026-09-23). Each of those is
written here in the same transaction as the change, keyed on the founder's
email — so "who paused this person, and when" always has an answer.
Append-only; tiny.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2e7c4d91a36"
down_revision: str | None = "a9d4e2c7b815"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_audit",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("admin_audit")
