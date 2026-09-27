"""events.merged_into — a duplicate record points at the one it copies

Revision ID: f6b2d8e4a915
Revises: e5a9c3b7d2f1
Create Date: 2026-09-27 00:00:00.000000

In 33 hours of shadow the verified tier (correlation/verify.py) judged ~750
articles the same happening as an existing record at >= 0.85, and every one of
them founded its own record anyway. correlation/merge.py folds those copies into
the record they copy; this column is what the fold leaves behind. The absorbed
row is kept, not deleted — shared links, lens unlocks and the verdicts that
justified the merge all name it — and `merged_into` is its forwarding address:
the API answers its URL with a 308, and every list skips it.

Same shape as `entities.merged_into` and `stories.merged_into`. Always points at
a record that is not itself merged (the merge re-points anything aimed at the
record it absorbs), so a reader is one hop from the survivor. ON DELETE SET NULL:
deleting a survivor must not delete the copies' history with it.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f6b2d8e4a915'
down_revision: str | None = 'e5a9c3b7d2f1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("merged_into", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_events_merged_into", "events", "events",
        ["merged_into"], ["id"], ondelete="SET NULL",
    )
    # Partial: only absorbed rows carry a value — about one in ten.
    op.create_index(
        "ix_events_merged_into", "events", ["merged_into"],
        postgresql_where=sa.text("merged_into IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_events_merged_into", table_name="events")
    op.drop_constraint("fk_events_merged_into", "events", type_="foreignkey")
    op.drop_column("events", "merged_into")
