"""article gist embedding + event_match_verdicts: the verified matching tier

Revision ID: e5a9c3b7d2f1
Revises: d4b7e2a9c1f3
Create Date: 2026-09-25 00:00:00.000000

Measured 2026-09-25 (docs/CANONICALIZATION.md): an event is matched on its
founding article's first 1200 raw characters, which separates same-happening
pairs at AUC 0.46 on hard same-language pairs — worse than chance — because
Prajavani's lead is 19% site furniture and templated local news reads alike. The
extractor's ENGLISH headline + one-line summary, embedded, separates them at
0.91–0.99 on all three labelled sets. That vector is `articles.gist_embedding`.

It finds candidates; it never merges on its own (no threshold is safe: false
merges persist at cosine 0.97). Jev reads the candidates and its answer is kept
in `event_match_verdicts` — the audit trail and the replay cache, like
clip_verdicts.

`ix_events_last_updated` serves the tier's in-window scan; the other tiers
filter on the same column through the (sector, last_updated_at) index, which a
sector-free filter cannot use.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from common.config import get_settings

revision: str = 'e5a9c3b7d2f1'
down_revision: str | None = 'd4b7e2a9c1f3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("gist_embedding", Vector(get_settings().prism_embed_dim)))
    op.create_index("ix_events_last_updated", "events", ["last_updated_at"])
    op.create_table(
        "event_match_verdicts",
        sa.Column("article_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("noul", sa.Float(), nullable=False),  # Jev's probability that both report the same happening
        sa.Column("gist_distance", sa.Float(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False),  # shadow | live, when it was asked
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("event_match_verdicts")
    op.drop_index("ix_events_last_updated", table_name="events")
    op.drop_column("articles", "gist_embedding")
