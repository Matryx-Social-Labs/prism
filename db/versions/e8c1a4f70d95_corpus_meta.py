"""corpus_meta: which embedding model wrote the vectors in this database

Revision ID: e8c1a4f70d95
Revises: d4e7b1a90c62
Create Date: 2026-09-05 00:00:00.000000

Cosine distance is not comparable across embedding models and the failure is
silent — vectors still come out, neighbours are still returned, the feed just
starts fusing unrelated stories. Measured when mE5 was first run against mpnet's
thresholds: 76 false merges against 3, a 25x increase, nothing logged.

Nothing recorded which model produced a stored vector, so a config change and a
re-embed could drift apart with no way to notice. One row, written by the
re-embed, checked before any stage that writes more vectors.

Seeded from the CURRENT configured model, because that is what the existing
corpus was in fact embedded with. Seeding it empty would make the guard fire on
every deployment until someone re-embedded, which trains people to ignore it.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'e8c1a4f70d95'
down_revision: str | None = 'd4e7b1a90c62'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "corpus_meta",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("embed_model", sa.Text(), nullable=False),
        sa.Column("embed_dim", sa.Integer(), nullable=False),
        sa.Column("embed_prefix", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("id = 1", name="ck_corpus_meta_singleton"),
    )
    # Seed from settings rather than a literal: this migration runs against
    # databases embedded with whatever model was live for them, and hardcoding one
    # would assert something false about the other.
    from common.config import get_settings
    from common.embeddings import DOC_PREFIX, _needs_prefix

    s = get_settings()
    # The PREFIX is seeded as well, not left NULL. Recording the model name alone
    # would be a half-truth the guard reads as a mismatch on first boot — same
    # name, different prefix — and a guard that fires on a correct deployment is
    # one people switch off.
    prefix = DOC_PREFIX if _needs_prefix(s.prism_embed_model) else None
    op.execute(
        sa.text(
            "INSERT INTO corpus_meta (id, embed_model, embed_dim, embed_prefix) "
            "VALUES (1, :m, :d, :p)"
        ).bindparams(m=s.prism_embed_model, d=s.prism_embed_dim, p=prefix)
    )


def downgrade() -> None:
    op.drop_table("corpus_meta")
