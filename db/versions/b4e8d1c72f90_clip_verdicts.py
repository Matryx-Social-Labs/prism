"""clip verdicts: a model's reading of whether a passage is about THIS story

Revision ID: b4e8d1c72f90
Revises: a7c2e9d41b06
Create Date: 2026-09-20 12:00:00.000000

The embedding-plus-cast candidate stage cannot tell "about this story" from
"about this topic" on real transcripts: labelled precision was 0.29–0.47 on
2026-09-20 (a conference with ten sub-stories, a story layer that splits one
saga into four). The one instrument that reads both texts is a model. Its
verdict per (event, window) is cached here so the hourly recompute never pays
for the same pair twice; only `event` verdicts become clips.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'b4e8d1c72f90'
down_revision: str | None = 'a7c2e9d41b06'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "clip_verdicts",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("window_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("podcast_windows.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("verdict", sa.Text(), nullable=False),  # event | topic | unrelated
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("clip_verdicts")
