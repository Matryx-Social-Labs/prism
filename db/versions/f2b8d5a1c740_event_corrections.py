"""event_corrections: the public corrections log

Revision ID: f2b8d5a1c740
Revises: e7a4c2b9f613
Create Date: 2026-09-24 00:00:00.000000

Every published version of a record is already kept (event_revisions); what a
version cannot say is WHY it changed. A correction is an editorial act: a
founder records that the record was wrong and why, and the record says so in
public with the date, the reason and a note (the strategy report's corrections
log; /about promised it). Two reasons, because only two are editorial:
`source_correction` (the outlet corrected its own report) and `prism_error`
(Prism got it wrong). New reporting changes a record every day and is shown
by the versions, not called a correction.

Append-only and no foreign key, like event_revisions: a correction outlives
the record it corrects.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2b8d5a1c740"
down_revision: str | None = "e7a4c2b9f613"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_corrections",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.CheckConstraint("reason IN ('source_correction', 'prism_error')", name="ck_event_corrections_reason"),
        sa.CheckConstraint("char_length(note) BETWEEN 10 AND 600", name="ck_event_corrections_note"),
    )
    op.create_index("ix_event_corrections_event", "event_corrections", ["event_id", "created_at"])
    op.create_index("ix_event_corrections_created", "event_corrections", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_event_corrections_created", table_name="event_corrections")
    op.drop_index("ix_event_corrections_event", table_name="event_corrections")
    op.drop_table("event_corrections")
