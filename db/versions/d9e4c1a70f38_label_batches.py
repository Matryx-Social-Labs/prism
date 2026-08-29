"""labelling batches, tasks and responses — gold sets as a recurring job

Revision ID: d9e4c1a70f38
Revises: c8a3f5d21b74
Create Date: 2026-08-29 00:00:00.000000

The gold set is the measurement everything else is judged against, and it was a
one-off: 45 stories hand-written into a Python literal. That is why the story layer
cannot currently be decided — the set is too small and drawn from one topic, and
there was no path to a bigger one that did not involve someone editing source code.

So labelling becomes a job the product supports rather than a thing done once:
batches of tasks, answered by people who are not developers, stored server-side.

THREE TABLES, AND THE THIRD IS THE POINT.

`label_responses` is keyed on (task, labeller) rather than on task alone, so two
people may answer the same task and disagree. That is deliberate. A gold set with
one opinion per item cannot tell a hard call from a careless one, and the existing
set already had to hand-maintain an AMBIGUOUS list for exactly the pairs where a
person could reasonably go either way. With repeated answers that list becomes
measurable — agreement is data, not an annotation someone remembers to add.

`unsure` is a first-class answer, not an empty selection. "These might be the same
story" and "none of these are" are different judgements, and collapsing them would
put coin-flips into the gold set as confident negatives. The existing set's own
docstring makes the same argument: ambiguous pairs are excluded from scoring so a
correct algorithm is not punished for a coin flip.

`labeller` is a free-text key the person types once, not an account. The audience is
non-technical and the task is short; requiring a signup would cost more labels than
it protects. Access is gated by an unguessable batch key instead, which is the
proportionate control for an endpoint that reads nothing sensitive and only appends.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'd9e4c1a70f38'
down_revision: str | None = 'c8a3f5d21b74'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "label_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # The unguessable half of the share link, and the lookup key for every
        # request a labeller makes.
        sa.Column("key", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False, server_default="story_boundary"),
        sa.Column("notes", sa.Text()),
        sa.Column("open", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "label_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("label_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("seed_event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        # Candidate event ids WITH the signal that proposed each, carried forward so
        # a finished set can be checked for correlation with one proposer.
        sa.Column("candidates", postgresql.JSONB(), nullable=False),
        sa.Column("sector", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("batch_id", "position", name="uq_label_tasks_position"),
    )
    op.create_index("ix_label_tasks_batch", "label_tasks", ["batch_id", "position"])

    op.create_table(
        "label_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("label_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("labeller", sa.Text(), nullable=False),
        sa.Column("selected", postgresql.JSONB(), nullable=False),
        sa.Column("unsure", sa.Boolean(), nullable=False, server_default=sa.false()),
        # How long the person looked at it. A three-second answer to a ten-candidate
        # screen is not a judgement, and without this there is no way to find that
        # out afterwards.
        sa.Column("ms_spent", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        # One answer per person per task; re-answering UPDATES rather than appends,
        # so someone can correct themselves without inflating agreement.
        sa.UniqueConstraint("task_id", "labeller", name="uq_label_response_once"),
    )
    op.create_index("ix_label_responses_task", "label_responses", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_label_responses_task", table_name="label_responses")
    op.drop_table("label_responses")
    op.drop_index("ix_label_tasks_batch", table_name="label_tasks")
    op.drop_table("label_tasks")
    op.drop_table("label_batches")
