"""sources.publisher — count mastheads, not feeds

Revision ID: b7c2e91a4d33
Revises: d7f4a9c02b18
Create Date: 2026-07-29

The Hindu ships six RSS feeds — national plus Tamil Nadu, Kerala, Karnataka,
Andhra Pradesh and Telangana — and republishes the same article across them.
Measured on production 2026-07-28: 666 articles in that family share a
byte-identical body. Because corroboration counted `DISTINCT s.slug`, one
newsroom filing one story could report up to SIX independent sources.

That is the exact claim the product sells and the single-origin flag exists to
warn about, so it has to count publishers. `publisher` defaults to the slug, so
every unrelated source keeps counting for itself.
"""

import sqlalchemy as sa
from alembic import op

revision = "b7c2e91a4d33"
down_revision = "d7f4a9c02b18"
branch_labels = None
depends_on = None

# Feed slug -> masthead. Explicit rather than derived from the slug prefix:
# splitting on "_" would fold cisa_kev into cisa and is a silent trap for any
# future source whose slug happens to contain an underscore.
FAMILIES = {
    "thehindu_tamilnadu": "thehindu",
    "thehindu_kerala": "thehindu",
    "thehindu_karnataka": "thehindu",
    "thehindu_andhra": "thehindu",
    "thehindu_telangana": "thehindu",
}


def upgrade() -> None:
    op.add_column("sources", sa.Column("publisher", sa.Text(), nullable=True))
    op.execute("UPDATE sources SET publisher = slug WHERE publisher IS NULL")
    for feed, masthead in FAMILIES.items():
        op.execute(
            sa.text("UPDATE sources SET publisher = :m WHERE slug = :s").bindparams(
                m=masthead, s=feed
            )
        )


def downgrade() -> None:
    op.drop_column("sources", "publisher")
