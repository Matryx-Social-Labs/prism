"""perf indexes: fk hot paths + pgvector hnsw

Revision ID: 51de411d824c
Revises: 8f3d21ab5e40
Create Date: 2026-07-19 20:20:37.335468

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '51de411d824c'
down_revision: str | None = '8f3d21ab5e40'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Feed candidate window: WHERE sector = ANY(...) + per-sector ORDER BY
    # last_updated_at DESC (api/routes/feed.py). A single composite btree covers
    # both the filter and the window.
    op.create_index(
        "ix_events_sector_last_updated",
        "events",
        ["sector", sa.text("last_updated_at DESC")],
    )
    # Event-detail joins by event_id. event_memberships / event_entities already
    # have event_id as the leading column of a unique index, so only these two
    # (whose only index is the PK) actually need one.
    op.create_index("ix_perspectives_event_id", "perspectives", ["event_id"])
    op.create_index("ix_impacts_event_id", "impacts", ["event_id"])
    # Agent RAG retrieval orders article_chunks.embedding <=> query (cosine).
    # Without an ANN index that is a full scan on every question — worse once
    # paid "unlimited Ask" ships. HNSW (pgvector pg16) matches the <=> operator
    # via vector_cosine_ops.
    op.execute(
        "CREATE INDEX ix_article_chunks_embedding_hnsw "
        "ON article_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_article_chunks_embedding_hnsw")
    op.drop_index("ix_impacts_event_id", table_name="impacts")
    op.drop_index("ix_perspectives_event_id", table_name="perspectives")
    op.drop_index("ix_events_sector_last_updated", table_name="events")
