"""labellers: a labeller is a Prism account that applied, and an admin approved

Revision ID: f8a3b6c21d47
Revises: c7e2a9f14d61
Create Date: 2026-09-23 00:00:00.000000

The labelling surface had no accounts on purpose (api/routes/label.py: "a signup
wall would cost more labels than it protects"). That held while two founders
labelled for a minute each. It stops holding once there is a guide to read, a
test to pass and a per-person accuracy record to keep — all three need an
identity that outlives one batch. Founder decision 2026-09-23: open application,
admin approval, language gating.

- `labellers` — one row per applicant, keyed on the Prism account. `status`
  starts `applied`; only an admin moves it to `active` (or `paused`).
  `languages_read` is what the labeller says they read WELL — the gate on which
  tasks they are served.
- `label_invites.user_id` — a signed-in labeller still answers through an
  invite, minted for them when they start a batch, so every response, status,
  agreement and compile path in tools/gold_candidates keeps working unchanged.
  At most one invite per (batch, account).
- `label_batches.listed` — shown on the labeller dashboard. Off by default:
  existing batches stay reachable only through their own links.
- `label_tasks.languages` — the languages a task needs its labeller to read.
  NULL means no gate, which is what every task written before this has.

All four tables are small (hundreds of rows), so nothing here contends with
the ingest path.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a3b6c21d47"
down_revision: str | None = "c7e2a9f14d61"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "labellers",
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("languages_read", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.Text(), nullable=False, server_default="applied"),
        # Why they want to label, in their words. Read by the admin who approves.
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("approved_by", sa.Text()),
        sa.CheckConstraint("status IN ('applied', 'active', 'paused')", name="ck_labellers_status"),
    )
    op.add_column("label_invites", sa.Column(
        "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")))
    op.create_index(
        "uq_label_invites_batch_user", "label_invites", ["batch_id", "user_id"],
        unique=True, postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.add_column("label_batches", sa.Column("listed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("label_tasks", sa.Column("languages", postgresql.ARRAY(sa.Text())))


def downgrade() -> None:
    op.drop_column("label_tasks", "languages")
    op.drop_column("label_batches", "listed")
    op.drop_index("uq_label_invites_batch_user", table_name="label_invites")
    op.drop_column("label_invites", "user_id")
    op.drop_table("labellers")
