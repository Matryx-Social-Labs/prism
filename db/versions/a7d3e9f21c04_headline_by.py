"""headline_by: whose words the event's title is

Revision ID: a7d3e9f21c04
Revises: f2a9c7e18b40
Create Date: 2026-09-17 00:00:00.000000

Founder decision 1(b), 2026-09-17: the canonical title is a Prism-written
headline from the reports, labelled as ours. `events.title` stays the one
field every surface reads (chart row, ticket, route, search, watchlist,
share card), so the rule holds everywhere by construction; `headline_by`
records whose words it holds — NULL means the first report's own headline,
'prism' means the extractor or the backfill wrote it. Each outlet's own
headline lives on its raw item and prints under Sources, so nothing is lost
when the title is rewritten.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a7d3e9f21c04'
down_revision: str | None = 'f2a9c7e18b40'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("headline_by", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "headline_by")
