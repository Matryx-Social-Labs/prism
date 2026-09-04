"""label_tasks.payload: a task shape that is not a story boundary

Revision ID: c5f9a71e3b48
Revises: a1c4e8b90d23
Create Date: 2026-09-04 00:00:00.000000

`label_batches.kind` has existed since the table was created and only ever held
`story_boundary`. The second kind is here: claim attribution — given a quote and
the speaker the extractor assigned to it, did the article really attribute it to
that person?

A story task is (seed, candidates). A claim task is a quote, its surrounding
context and a claimed speaker, and none of that fits `candidates` without
pretending a quote is an event. `payload` carries it instead, so the two kinds
share the machinery that matters — invites, per-person progress, skip, revoke,
agreement — and differ only in what a task IS.

Nullable, and `candidates` is left NOT NULL with `[]` written for claim rows: the
existing story tasks are untouched and every existing query keeps working.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'c5f9a71e3b48'
down_revision: str | None = 'a1c4e8b90d23'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("label_tasks", sa.Column("payload", postgresql.JSONB()))
    # A story task's seed IS an event. A claim task's subject is an ARTICLE, and
    # an article need not belong to an event, so the FK cannot stay required for
    # the new kind without inventing an event to point at.
    op.alter_column("label_tasks", "seed_event_id", nullable=True)


def downgrade() -> None:
    # Claim tasks have no seed event, so restoring NOT NULL would fail while any
    # exist. They are deleted rather than given a fabricated one: a made-up event
    # id is silently wrong data, which is worse than an absent row.
    op.execute("DELETE FROM label_tasks WHERE seed_event_id IS NULL")
    op.alter_column("label_tasks", "seed_event_id", nullable=False)
    op.drop_column("label_tasks", "payload")
