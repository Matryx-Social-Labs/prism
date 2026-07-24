"""storyline partition: versioned runs, event_story membership, veto cache

Revision ID: d7f4a9c02b18
Revises: c4e7a2f18b60
Create Date: 2026-07-24 17:20:00.000000

Wires the global storyline partitioner (correlation/partition.py) into durable
state. `partition_runs` is the immutable run ledger with an atomic 'current'
pointer (a partial-unique index guarantees exactly one live run); `event_story`
holds each event's story membership + L3 branch tree per run; `story_veto` caches
grounded-veto verdicts for reuse across runs. Also adds event_entities(entity_id):
the partition's global actor-graph self-join joins on entity_id, and the existing
composite unique (event_id, entity_id) can't serve an entity_id-first lookup.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7f4a9c02b18"
down_revision: str | None = "c4e7a2f18b60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = sa.dialects.postgresql.UUID
JSONB = sa.dialects.postgresql.JSONB


def upgrade() -> None:
    op.create_table(
        "partition_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("base_run_id", UUID(as_uuid=True), sa.ForeignKey("partition_runs.id")),  # NULL = base run
        sa.Column("status", sa.Text(), nullable=False, server_default="building"),  # building|current|superseded
        sa.Column("veto_state", sa.Text(), nullable=False, server_default="pending"),  # pending|applied
        sa.Column("resolution", sa.Float()),
        sa.Column("stats", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Atomic cutover invariant: at most one live run at a time (readers join to it).
    op.create_index(
        "uq_partition_runs_current", "partition_runs", ["status"],
        unique=True, postgresql_where=sa.text("status = 'current'"),
    )

    op.create_table(
        "event_story",
        sa.Column("run_id", UUID(as_uuid=True), sa.ForeignKey("partition_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("story_label", sa.Integer(), nullable=False),
        sa.Column("branch_parent_id", UUID(as_uuid=True)),
        sa.Column("off_spine", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("run_id", "event_id"),  # also serves the (run_id, event_id) read
    )
    # "all members of this story in this run" — the serving read shape.
    op.create_index("ix_event_story_run_label", "event_story", ["run_id", "story_label"])

    op.create_table(
        "story_veto",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("candidate_event_id", UUID(as_uuid=True), nullable=False),
        sa.Column("same_story", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("reason", sa.Text()),
        sa.Column("base_run_id", UUID(as_uuid=True), sa.ForeignKey("partition_runs.id", ondelete="SET NULL")),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Reuse key: a story's versioned identity + the candidate it judged.
    op.create_index("uq_story_veto_sig_candidate", "story_veto", ["signature", "candidate_event_id"], unique=True)

    op.create_index("ix_event_entities_entity", "event_entities", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_event_entities_entity", table_name="event_entities")
    op.drop_index("uq_story_veto_sig_candidate", table_name="story_veto")
    op.drop_table("story_veto")
    op.drop_index("ix_event_story_run_label", table_name="event_story")
    op.drop_table("event_story")
    op.drop_index("uq_partition_runs_current", table_name="partition_runs")
    op.drop_table("partition_runs")
