"""entities.merged_into — so a fold holds instead of decaying

Revision ID: b7f2c4a91e05
Revises: a4d1e9c7b330
Create Date: 2026-08-28 00:00:00.000000

Folding variant entity rows onto a canonical one fixes the corpus as it stands and
nothing after it. `_resolve_entity` maps a slug to a row, the variant rows survive
the fold by design, and so the very next article naming "BJP" lands back on the
`bjp` row and the split reopens. The fold would look like it worked and quietly
come undone — worse than not running it, because the measurement gets taken once,
believed, and never revisited.

`merged_into` is the redirect that closes that loop, and it is not a new idea here:
`stories.merged_into` already does exactly this so an old share link keeps
resolving, and `api/routes/trending.py` already walks that chain with a hop bound
and a cycle check. Same shape, same reasons, one level down.

Nullable and self-referential; NULL means "this row is canonical", which is almost
every row. ON DELETE SET NULL rather than CASCADE: losing a canonical entity must
orphan its variants, not delete them — they still hold a name real articles used,
and removing mentions to tidy up a dangling pointer is the destructive reading of
an ambiguous situation.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b7f2c4a91e05'
down_revision: str | None = 'a4d1e9c7b330'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("entities", sa.Column("merged_into", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_entities_merged_into", "entities", "entities",
        ["merged_into"], ["id"], ondelete="SET NULL",
    )
    # Partial: only folded rows carry a value, and they are a small minority.
    op.create_index(
        "ix_entities_merged_into", "entities", ["merged_into"],
        postgresql_where=sa.text("merged_into IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_entities_merged_into", table_name="entities")
    op.drop_constraint("fk_entities_merged_into", "entities", type_="foreignkey")
    op.drop_column("entities", "merged_into")
