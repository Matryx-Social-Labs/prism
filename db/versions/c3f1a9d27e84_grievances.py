"""grievances: the complaint queue the IT Rules' Grievance Officer answers from

Revision ID: c3f1a9d27e84
Revises: a7d4e2c19b60
Create Date: 2026-09-29 00:00:00.000000

IT Rules 2021 Part III (R10, R11(2)) apply to a news aggregator and are not
stayed: anyone may complain about published content; the publisher acknowledges
within 24 hours, decides within 15 days, and publishes the officer's name and
contact, plus a monthly count of grievances received and decided (R18(3), R19).
docs/COMPLIANCE-INDIA.md N1–N3. Until now "Something wrong?" opened a mailto and
nothing was counted, so none of those clocks could be shown to have been kept.

One row per complaint. `ref` is what the complainant quotes back; `status`
moves open → resolved | rejected, only by an admin, with an `outcome` in words.
`acknowledged_at` is set when the acknowledgement (with a copy of the complaint
as recorded) is sent. No IP or user agent is stored.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'c3f1a9d27e84'
down_revision: str | None = 'a7d4e2c19b60'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "grievances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ref", sa.Text(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.Text()),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("subject_url", sa.Text()),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("outcome", sa.Text()),
        sa.CheckConstraint("status IN ('open', 'resolved', 'rejected')", name="ck_grievances_status"),
    )
    op.create_index("ix_grievances_created_at", "grievances", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_grievances_created_at", table_name="grievances")
    op.drop_table("grievances")
