"""entity_variant_verdicts: one name, one entity

Revision ID: c8e1f4a7b2d6
Revises: c7d4e9a2b815
Create Date: 2026-10-01 00:00:00.000000

Indian-language articles transliterate a name differently, and identity is a
slug, so one person becomes many entities (the Flydubai pilot was fifteen). Two
spellings with the same consonant skeleton, seen together in one record, a
verified follow-up or one story, are asked of Jev; its answer is kept here, and
a "same" answer folds the variant into the spelling with the most mentions
(correlation/variants.py).

The table is the decision record, the replay cache (a pair is asked once, a
"different" answer included) and the undo: `journal` holds every row the fold
moved, whole, so `tools/entity_variants.py --unfold` can put them back, and
`reverted_at` keeps an undone pair from folding again.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8e1f4a7b2d6"
down_revision: str | None = "c7d4e9a2b815"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "entity_variant_verdicts",
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("survivor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("noul", sa.Float(), nullable=False),  # Jev's probability that both name one entity
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("via", sa.Text(), nullable=False),  # attach | backfill
        sa.Column("evidence", sa.Text(), nullable=False),  # record | verified_link | story
        sa.Column("journal", postgresql.JSONB(), nullable=True),  # set when folded
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("entity_variant_verdicts")
