"""personalization: subsector, image_url, event_links

Revision ID: 8f3d21ab5e40
Revises: c0bcace5aca1
Create Date: 2026-07-15

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8f3d21ab5e40"
down_revision: str | None = "c0bcace5aca1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("subsector", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("raw_items", sa.Column("image_url", sa.Text(), nullable=True))
    op.create_table(
        "event_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("from_event_id", sa.UUID(), nullable=False),
        sa.Column("to_event_id", sa.UUID(), nullable=False),
        # leads_to | related | none — 'none' persists LLM rejections so a
        # candidate pair is never re-asked (idempotent, quota-safe).
        sa.Column("relation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["from_event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["to_event_id"], ["events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_event_id", "to_event_id", name="uq_event_links_pair"),
    )
    op.create_index("ix_event_links_from", "event_links", ["from_event_id"])
    op.create_index("ix_event_links_to", "event_links", ["to_event_id"])


def downgrade() -> None:
    op.drop_index("ix_event_links_to", table_name="event_links")
    op.drop_index("ix_event_links_from", table_name="event_links")
    op.drop_table("event_links")
    op.drop_column("raw_items", "image_url")
    op.drop_column("events", "image_url")
    op.drop_column("events", "subsector")
