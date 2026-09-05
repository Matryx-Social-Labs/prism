"""lens_unlocks: what a reader has paid to open, and the Ask meter's indexes

Revision ID: f2a9c7e18b40
Revises: e8c1a4f70d95
Create Date: 2026-09-05 00:00:00.000000

Two things, both load-bearing for the paywall.

1. `lens_unlocks` makes the unit of payment an unlocked lens on a story rather
   than an HTTP request, so a refresh costs nothing and a failed generation
   charges nothing.

2. Indexes for the Ask meter. `agent_messages` had ONLY a primary key and its
   `session_id` foreign key was unindexed — Postgres does not index FKs
   automatically — so counting a user's recent questions sequentially scanned
   both tables on every question. The FK index is worth having regardless:
   deleting an agent_session currently scans all of agent_messages.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f2a9c7e18b40'
down_revision: str | None = 'e8c1a4f70d95'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lens_unlocks",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_id", sa.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("lens", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "event_id", "lens", name="uq_lens_unlock"),
    )
    # The read on the hot path: "has this user unlocked this lens on this event?"
    # The unique constraint already indexes the triple, so no second index.
    op.create_index("ix_agent_sessions_user_ref", "agent_sessions", ["user_ref"])
    op.create_index(
        "ix_agent_messages_session_created", "agent_messages", ["session_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_agent_messages_session_created", table_name="agent_messages")
    op.drop_index("ix_agent_sessions_user_ref", table_name="agent_sessions")
    op.drop_table("lens_unlocks")
