"""label_responses.skipped: "I cannot read this", which is not "I cannot decide"

Revision ID: a1c4e8b90d23
Revises: f3c8d2e51a09
Create Date: 2026-09-01 00:00:00.000000

72 of the 123 tasks in the first batch carry a non-Latin headline — 46 Devanagari,
40 Kannada, 6 Tamil. A labeller who does not read Kannada has no honest answer for
those, and the only exits available were to guess or to tick `unsure`.

BOTH OF THOSE CORRUPT THE MEASUREMENT, in different ways. A guess puts noise into
the set that later reads as human judgement. `unsure` is worse than it looks: it
is a claim ABOUT THE STORY — "I read these and cannot decide" — and it is used to
find genuinely ambiguous boundaries. A skip is a claim about the LABELLER. Fold
them together and "this pair is ambiguous" becomes indistinguishable from "we
asked the wrong person", which is exactly the signal you need to route the task
to someone who can read it.

Both are excluded from the vote, so this changes no verdict. What it changes is
whether you can SEE why an answer is missing.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a1c4e8b90d23'
down_revision: str | None = 'f3c8d2e51a09'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing rows backfill to false, which is the truthful default: every
    # response recorded before this column existed was a real judgement.
    op.add_column(
        "label_responses",
        sa.Column("skipped", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    # Dropping the column collapses skips back into ordinary empty answers, which
    # would read as "none of these belong" — a verdict nobody gave. The rows are
    # left in place rather than reinterpreted; re-running upgrade restores the
    # distinction only for responses recorded after it.
    op.drop_column("label_responses", "skipped")
