"""perf indexes: fk hot paths + pgvector hnsw

Revision ID: 51de411d824c
Revises: 8f3d21ab5e40
Create Date: 2026-07-19 20:20:37.335468

"""
from collections.abc import Sequence

from alembic import op

revision: str = '51de411d824c'
down_revision: str | None = '8f3d21ab5e40'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # These tables (events, perspectives, impacts, article_chunks) are written
    # continuously by the ingestion worker. A plain CREATE INDEX takes a lock
    # that fights those writes, so at production scale (25k+ article_chunks) the
    # index build stalls indefinitely — which stalls `alembic upgrade head` in
    # the deploy start command, so the API never boots and the healthcheck fails.
    # CONCURRENTLY builds without blocking writes; IF NOT EXISTS makes re-runs
    # (and pre-created indexes) idempotent. CONCURRENTLY can't run inside a
    # transaction, hence autocommit_block.
    #
    #  - events(sector, last_updated_at DESC): the feed candidate window
    #  - perspectives/impacts(event_id): event-detail joins (memberships/entities
    #    already lead a unique index)
    #  - article_chunks.embedding HNSW (vector_cosine_ops): agent RAG <=> retrieval
    with op.get_context().autocommit_block():
        # HNSW's PARALLEL build allocates a dynamic-shared-memory segment that
        # overflows the small /dev/shm on Railway's managed Postgres container
        # ("could not resize shared memory segment ... No space left on device"),
        # which aborts the migration and fails the deploy healthcheck. Building
        # single-threaded avoids the DSM allocation entirely and is fast at this
        # scale (~12s for 25k rows). Session-scoped SET applies to the CREATEs below.
        op.execute("SET max_parallel_maintenance_workers = 0")
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_events_sector_last_updated "
            "ON events (sector, last_updated_at DESC)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_perspectives_event_id "
            "ON perspectives (event_id)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_impacts_event_id "
            "ON impacts (event_id)"
        )
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_article_chunks_embedding_hnsw "
            "ON article_chunks USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_article_chunks_embedding_hnsw")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_impacts_event_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_perspectives_event_id")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_events_sector_last_updated")
