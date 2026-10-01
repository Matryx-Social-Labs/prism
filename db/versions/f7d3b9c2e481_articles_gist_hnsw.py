"""articles.gist_embedding: the HNSW index the matching actually needs

Revision ID: f7d3b9c2e481
Revises: e2b7c4d9a613
Create Date: 2026-10-01 00:00:00.000000

The verifier's gist candidates and the story layer search articles by their
English gist, and nothing indexed it: HNSW sat on events.embedding and
article_chunks.embedding (the raw-text vectors), so every incoming article
seq-scanned ~34k gists — 1.02 s, under the match-or-create lock (measured on
prod 2026-10-01). CONCURRENTLY so enrichment keeps writing during the build.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "f7d3b9c2e481"
down_revision: str | None = "e2b7c4d9a613"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        # A parallel HNSW build needs shared memory, and Railway's Postgres
        # container has Docker's 64 MB /dev/shm: in prod the parallel build failed
        # ("could not resize shared memory segment") and left an INVALID index that
        # IF NOT EXISTS then skipped on the next boot. Serial build: 31 s for 34k gists.
        op.execute("SET max_parallel_maintenance_workers = 0")
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_articles_gist_embedding_hnsw "
            "ON articles USING hnsw (gist_embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_articles_gist_embedding_hnsw")
