"""multilingual embeddings 384->768 + events hnsw

Revision ID: 5493a4141cbb
Revises: 9ddbcc3fd269
Create Date: 2026-07-20 23:23:09.035589

Switch to a 768-dim multilingual embedding model (paraphrase-multilingual-mpnet-
base-v2) so cross-language coverage clusters into one story. Existing 384-dim
vectors are invalid under the new model, so they're cleared and re-embedded on
the next ingest. Also adds the missing HNSW index on events.embedding (clustering
+ thread candidate retrieval were doing a sequential cosine scan).
"""
from collections.abc import Sequence

from alembic import op

revision: str = '5493a4141cbb'
down_revision: str | None = '9ddbcc3fd269'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_article_chunks_embedding_hnsw", table_name="article_chunks", if_exists=True)
    # Old-dim vectors can't be cast to the new dim — clear them (re-embedded on ingest).
    op.execute("UPDATE article_chunks SET embedding = NULL")
    op.execute("UPDATE events SET embedding = NULL")
    op.execute("ALTER TABLE article_chunks ALTER COLUMN embedding TYPE vector(768)")
    op.execute("ALTER TABLE events ALTER COLUMN embedding TYPE vector(768)")
    # Rebuild the chunk HNSW + add the missing events HNSW (single-threaded to
    # avoid the /dev/shm overflow that failed the first HNSW deploy).
    with op.get_context().autocommit_block():
        op.execute("SET max_parallel_maintenance_workers = 0")
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_article_chunks_embedding_hnsw "
            "ON article_chunks USING hnsw (embedding vector_cosine_ops)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_events_embedding_hnsw "
            "ON events USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    op.drop_index("ix_events_embedding_hnsw", table_name="events", if_exists=True)
    op.drop_index("ix_article_chunks_embedding_hnsw", table_name="article_chunks", if_exists=True)
    op.execute("UPDATE article_chunks SET embedding = NULL")
    op.execute("UPDATE events SET embedding = NULL")
    op.execute("ALTER TABLE article_chunks ALTER COLUMN embedding TYPE vector(384)")
    op.execute("ALTER TABLE events ALTER COLUMN embedding TYPE vector(384)")
    with op.get_context().autocommit_block():
        op.execute("SET max_parallel_maintenance_workers = 0")
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_article_chunks_embedding_hnsw "
            "ON article_chunks USING hnsw (embedding vector_cosine_ops)"
        )
