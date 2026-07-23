"""persistent trending stories

Revision ID: c4e7a2f18b60
Revises: b2d5e1f4a093
Create Date: 2026-07-23 14:00:00.000000

A trending story is a community of events promoted to a durable, shareable
identity. The reconciliation pass (correlation/trending.py) detects trending
communities and matches them to existing stories by member/cast overlap, so the
`slug` (and thus the /trending/<slug> share URL) survives coverage growth. Merges
keep the oldest story and point the younger at it via `merged_into` (its URL 301s);
stories that stop trending go `dormant` (not deleted) so shared links never 404.
The slug is frozen at creation.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c4e7a2f18b60'
down_revision: str | None = 'b2d5e1f4a093'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stories",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("cast", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("member_event_ids", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("hero_event_id", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.Column("sector", sa.Text()),
        sa.Column("regions", sa.dialects.postgresql.ARRAY(sa.Text())),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("velocity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),  # active|dormant
        sa.Column("merged_into", sa.dialects.postgresql.UUID(as_uuid=True)),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Serving query: active stories, ranked by velocity/sources.
    op.create_index("ix_stories_status_velocity", "stories", ["status", "velocity"])


def downgrade() -> None:
    op.drop_index("ix_stories_status_velocity", table_name="stories")
    op.drop_table("stories")
