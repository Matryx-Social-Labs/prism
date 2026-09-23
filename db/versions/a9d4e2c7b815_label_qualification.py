"""label qualification: practise a task, pass its test, then label it

Revision ID: a9d4e2c7b815
Revises: f8a3b6c21d47
Create Date: 2026-09-23 00:00:00.000000

Phase 3 of the labeller workspace plan. The first labelling round came back with
its two labellers disagreeing in opposite systematic ways, "because nothing made
them" read the guidance. Founder decision 2026-09-23: a 90% test per task kind,
passed before any work batch of that kind is offered.

Practice and qualification are BATCHES, so the task page and the next/answer
protocol serve them unchanged:

- `label_batches.purpose` — `work` (everything that exists), `practice` (answer,
  then see the expected answer and why) or `qualify` (a scored attempt).
- `label_tasks.expected` / `.explanation` — the agreed answer and the reason.
  Only practice and qualify tasks carry them, and they are never serialised to
  the client before the answer (practice) or the end of the attempt (qualify).
- `label_invites.attempt` — each qualification attempt is its own invite, so
  its answers never mix with an earlier attempt's. The one-invite-per-account
  index from f8a3b6c21d47 becomes one per (batch, account, attempt); work
  batches only ever use attempt 0.
- `label_invites.task_ids` — the random draw for one attempt (NULL = the whole
  batch), `finished_at` / `score` — the attempt's result, written once.
- `labeller_qualifications` — per account and kind: passed or not, best score,
  how many attempts, when the last one ended (the retake cooldown), and
  `granted_by` when an admin qualified someone by hand.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a9d4e2c7b815"
down_revision: str | None = "f8a3b6c21d47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("label_batches", sa.Column("purpose", sa.Text(), nullable=False, server_default="work"))
    op.create_check_constraint(
        "ck_label_batches_purpose", "label_batches", "purpose IN ('work', 'practice', 'qualify')")
    op.add_column("label_tasks", sa.Column("expected", postgresql.JSONB()))
    op.add_column("label_tasks", sa.Column("explanation", sa.Text()))

    op.add_column("label_invites", sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("label_invites", sa.Column("task_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True))))
    op.add_column("label_invites", sa.Column("finished_at", sa.DateTime(timezone=True)))
    op.add_column("label_invites", sa.Column("score", sa.Float()))
    op.drop_index("uq_label_invites_batch_user", table_name="label_invites")
    op.create_index(
        "uq_label_invites_batch_user_attempt", "label_invites", ["batch_id", "user_id", "attempt"],
        unique=True, postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    op.create_table(
        "labeller_qualifications",
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("kind", sa.Text(), primary_key=True),
        sa.Column("passed_at", sa.DateTime(timezone=True)),
        sa.Column("best_score", sa.Float()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("granted_by", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("labeller_qualifications")
    op.drop_index("uq_label_invites_batch_user_attempt", table_name="label_invites")
    op.create_index(
        "uq_label_invites_batch_user", "label_invites", ["batch_id", "user_id"],
        unique=True, postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    for col in ("score", "finished_at", "task_ids", "attempt"):
        op.drop_column("label_invites", col)
    op.drop_column("label_tasks", "explanation")
    op.drop_column("label_tasks", "expected")
    op.drop_constraint("ck_label_batches_purpose", "label_batches", type_="check")
    op.drop_column("label_batches", "purpose")
