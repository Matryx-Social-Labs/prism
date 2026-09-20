"""subscriptions: who is on which plan, from which provider

Revision ID: d2a7b8c9e0f1
Revises: c9f1a2b3d4e5
Create Date: 2026-09-20 18:00:00.000000

The plug-in point for Razorpay (BUSINESS-MODEL.md §8) built before the account
exists: entitlement is read from here today (provider 'manual' lets the founder
grant Plus to testers and founding members by hand), and the Razorpay webhook
writes the same rows when it arrives. `status` follows the provider's words —
active | past_due | cancelled | halted | expired — and entitlement is a function
of status and current_period_end (common/billing.py), never a boolean column
that can go stale.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'd2a7b8c9e0f1'
down_revision: str | None = 'c9f1a2b3d4e5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),  # manual | razorpay
        sa.Column("provider_sub_id", sa.Text()),
        sa.Column("plan", sa.Text(), nullable=False),  # plus_monthly | plus_yearly | founding
        sa.Column("status", sa.Text(), nullable=False),  # active | past_due | cancelled | halted | expired
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
        sa.Column("cancel_at", sa.DateTime(timezone=True)),
        sa.Column("price_paise", sa.Integer()),  # what this subscriber pays, locked at purchase (offer price)
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "provider_sub_id", name="uq_subscriptions_provider_sub"),
    )
    op.create_index("ix_subscriptions_user", "subscriptions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_subscriptions_user", table_name="subscriptions")
    op.drop_table("subscriptions")
