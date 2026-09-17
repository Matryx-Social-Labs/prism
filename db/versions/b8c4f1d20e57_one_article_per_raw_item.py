"""one article per raw item

Revision ID: b8c4f1d20e57
Revises: a7d3e9f21c04
Create Date: 2026-09-17 00:00:00.000000

Two consumers can hold the same raw item at once: a message that stalls
inside an LLM cooldown is reclaimed by a second worker while the first is
still finishing, and both insert an article. The idempotency check on the
way in then meets two rows where it expects one and the handler fails for
good. Six raw items on 2026-09-17, twelve membership rows, every duplicate
in the same event as its twin. Remove the later twins and their dependants,
then make the state unrepresentable.
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'b8c4f1d20e57'
down_revision: str | None = 'a7d3e9f21c04'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DUPES = """
    CREATE TEMP TABLE dupe_articles AS
    SELECT id FROM (
        SELECT id, row_number() OVER (PARTITION BY raw_item_id ORDER BY created_at, id) AS rn
        FROM articles
    ) t WHERE rn > 1
"""


def upgrade() -> None:
    op.execute(DUPES)
    op.execute("DELETE FROM field_provenance WHERE enrichment_id IN (SELECT id FROM enrichments WHERE article_id IN (SELECT id FROM dupe_articles))")
    op.execute("DELETE FROM enrichments WHERE article_id IN (SELECT id FROM dupe_articles)")
    op.execute("DELETE FROM event_memberships WHERE article_id IN (SELECT id FROM dupe_articles)")
    op.execute("DELETE FROM article_chunks WHERE article_id IN (SELECT id FROM dupe_articles)")
    op.execute("DELETE FROM articles WHERE id IN (SELECT id FROM dupe_articles)")
    op.execute("DROP TABLE dupe_articles")
    op.create_index("uq_articles_raw_item", "articles", ["raw_item_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_articles_raw_item", table_name="articles")
