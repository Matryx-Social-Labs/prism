"""canonical entity identity: qid on entities + a local Wikidata alias index

Revision ID: a4d1e9c7b330
Revises: eb8aba01c5f4
Create Date: 2026-08-28 00:00:00.000000

Entity identity is currently the slug, and a slug folds strings: every
romanisation of a party is a separate row until a human notices and adds a line
to common/entity_aliases.py. 39 production slugs hold what is really one entity,
and because every clustering site weights actors by 1/df, a split halves the
document frequency on each side and makes a national fixture look twice as
distinctive as it is — measured up to 372x distortion for split magnets.

`qid` is the real identity: Q10230 is the BJP whether the article wrote "BJP",
"Bharatiya Janta Party" or "भारतीय जनता पार्टी".

`resolution` records HOW the link was made, never just that it was. A wrong fold
is unrecoverable once mentions are repointed, so "which of these came from an
exact index hit and which from a tie-break" has to be answerable later without
re-deriving it. NULL means unlinked, which is a normal outcome and not an error:
measured coverage is 72% among entities that can form an edge at all, and the
remainder stay on their slug.

`entity_alias` is the local index — every surface form Wikidata knows for a
candidate item, normalised with the same function our entity slugs use. Kept as a
table rather than a cache file because it is queried at link time and is the audit
trail for why a fold happened.

No column is dropped and nothing is repointed here. This migration only makes the
identity RECORDABLE; deciding and applying folds is a separate, reversible pass.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a4d1e9c7b330'
down_revision: str | None = 'eb8aba01c5f4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("entities", sa.Column("qid", sa.Text(), nullable=True))
    op.add_column("entities", sa.Column("resolution", sa.Text(), nullable=True))
    # Not unique: several rows legitimately share a qid until the fold is applied,
    # and that shared state is exactly what the fold pass reads.
    op.create_index("ix_entities_qid", "entities", ["qid"])

    op.create_table(
        "entity_alias",
        # The normalised surface form — slugify(canonical_entity_name(name)), the
        # same key an entity slug is built with, so a slug looks itself up with no
        # second convention to keep in sync.
        sa.Column("alias_norm", sa.Text(), nullable=False),
        sa.Column("qid", sa.Text(), nullable=False),
        sa.Column("lang", sa.Text(), nullable=True),
        # label | sitelink | alias — WHICH surface form matched, not just that one
        # did. Load-bearing for disambiguation: Wikidata alias sets are not
        # identity-preserving (Q234277, CPI(M), lists plain "Communist Party of
        # India" — a different, still-existing party) whereas a label or wiki title
        # is the item's canonical name. Label beats alias when they disagree.
        sa.Column("kind", sa.Text(), nullable=True),
        # Sitelink count: a weak prominence proxy, used only to break a tie when
        # one surface form points at two items.
        sa.Column("prior", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("surface", sa.Text(), nullable=True),  # the unnormalised form, for audit
        sa.PrimaryKeyConstraint("alias_norm", "qid"),
    )
    op.create_index("ix_entity_alias_qid", "entity_alias", ["qid"])


def downgrade() -> None:
    op.drop_index("ix_entity_alias_qid", table_name="entity_alias")
    op.drop_table("entity_alias")
    op.drop_index("ix_entities_qid", table_name="entities")
    op.drop_column("entities", "resolution")
    op.drop_column("entities", "qid")
