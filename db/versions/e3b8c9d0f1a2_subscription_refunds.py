"""subscriptions: the paid period's start, a refund, a pause, a scheduled start

Revision ID: e3b8c9d0f1a2
Revises: d2a7b8c9e0f1
Create Date: 2026-09-21 09:00:00.000000

The Refund policy gives yearly and founding readers seven days from any charge
to take a full refund. The window is measured from `current_period_start`
(Razorpay's `current_start`, written by every path that applies a subscription),
so the plan card can offer the refund without a round trip to Razorpay; the
refund itself is recorded as `refund_id` (Razorpay's rfnd_…) so the button is
offered once and the "cancelled" email is not sent on top of the refund one.

Two more moments of a subscription's life that the cancel flow offers instead
of cancelling (DESIGN.md § Account): `paused_until` — Razorpay pauses at once
and the worker resumes it on this date, so a pause is a pause and not a
cancellation by another name; and `starts_at` — a yearly plan taken from the
cancel sheet begins when the paid month ends (Razorpay `start_at`), so nothing
is charged twice for the same days.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'e3b8c9d0f1a2'
down_revision: str | None = 'd2a7b8c9e0f1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("current_period_start", sa.DateTime(timezone=True)))
    op.add_column("subscriptions", sa.Column("refund_id", sa.Text()))
    op.add_column("subscriptions", sa.Column("paused_until", sa.DateTime(timezone=True)))
    op.add_column("subscriptions", sa.Column("starts_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("subscriptions", "starts_at")
    op.drop_column("subscriptions", "paused_until")
    op.drop_column("subscriptions", "refund_id")
    op.drop_column("subscriptions", "current_period_start")
