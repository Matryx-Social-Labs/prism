"""trigram indexes so search stops scanning the whole events table

Revision ID: c8a3f5d21b74
Revises: b7f2c4a91e05
Create Date: 2026-08-29 00:00:00.000000

`/api/v1/search` runs `title ILIKE '%q%' OR summary ILIKE '%q%'`. Measured on
production (19,356 events): Seq Scan, ~100 ms per query for both a one-word and a
two-word term. That is survivable now and gets worse in a straight line — the
corpus is only frozen because ingestion is switched off.

A LEADING wildcard is the whole difficulty. A btree index cannot serve `%q%`, and
that is why the route carries a `ponytail:` note admitting the full scan. GIN over
trigrams can, which is what pg_trgm exists for, and the extension is already
installed here.

DELIBERATELY NOT tsvector, despite it being the more usual answer:

  * It would change what search MEANS. ILIKE is substring matching, so "modi"
    finds "Modinagar"; tsvector matches lexemes and would not. That is a product
    decision about behaviour, not an index, and not one to make silently inside a
    performance fix.
  * The corpus is multilingual across nine Indian languages. An 'english' text
    search config stems the wrong language for most of it, and 'simple' gives up
    stemming entirely — so a tsvector version needs a per-language column or a
    deliberate choice to do neither. Trigrams are script-agnostic and need no such
    decision.

So this is purely a speed change: identical results, no route change, no semantic
shift. If lexeme search is wanted later it can be added as its own feature with
its own gate.

CONCURRENTLY is not available inside Alembic's transaction, and at this table size
a plain CREATE INDEX finishes well within the deploy's healthcheck window.
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'c8a3f5d21b74'
down_revision: str | None = 'b7f2c4a91e05'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_events_title_trgm "
        "ON events USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_events_summary_trgm "
        "ON events USING gin (summary gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_events_summary_trgm")
    op.execute("DROP INDEX IF EXISTS ix_events_title_trgm")
    # pg_trgm is left installed: other things may rely on it, and dropping an
    # extension to undo an index would be the destructive reading of a rollback.
