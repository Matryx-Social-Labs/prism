"""story_events: a record joins one story at birth

Revision ID: e2b7c4d9a613
Revises: d1a6f3e8b402
Create Date: 2026-10-01 00:00:00.000000

The story layer was recomputed from scratch every 15 minutes (Leiden over a
similarity graph) and only kept while a story trended: the Iran war's 360
records sat in 198 groups and never held a story for more than a day. A story
now persists from its first record (`anchor_event_id`); every later record joins
exactly one story on the judge's word (correlation/stories.py), with the kind of
development it is (`facet`). `story_verdicts` keeps every answer, the replay
cache and the merge pass's evidence. A running story (a war, a tournament) is
judged against a founder-written `scope` instead of its founding report.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e2b7c4d9a613"
down_revision: str | None = "d1a6f3e8b402"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("stories", sa.Column("anchor_event_id", postgresql.UUID(as_uuid=True),
                                       sa.ForeignKey("events.id"), nullable=True))
    op.add_column("stories", sa.Column("scope", sa.Text(), nullable=True))
    op.create_table(
        "story_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stories.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("noul", sa.Float(), nullable=True),  # the judge's part-of-story answer; NULL for the anchor
        sa.Column("facet", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_story_events_story", "story_events", ["story_id"])
    op.create_table(
        "story_verdicts",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stories.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("noul", sa.Float(), nullable=False),
        sa.Column("facet", sa.Text(), nullable=True),
        sa.Column("distance", sa.Float(), nullable=True),  # nearest member's gist; NULL when a follow-up link proposed it
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("story_verdicts")
    op.drop_index("ix_story_events_story", table_name="story_events")
    op.drop_table("story_events")
    op.drop_column("stories", "scope")
    op.drop_column("stories", "anchor_event_id")
