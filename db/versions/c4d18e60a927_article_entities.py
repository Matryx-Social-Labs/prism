"""article_entities — an event's cast comes from the articles it holds

Revision ID: c4d18e60a927
Revises: b7c2e91a4d33
Create Date: 2026-07-29

event_entities links a cast member to an EVENT and nothing else, so once an
article is wrongly absorbed its actors belong to the event permanently — even
after the article leaves. That is the feedback loop behind every over-merge in
this dataset: an event that absorbs one article about Narendra Modi becomes
matchable by every future article about Narendra Modi, so each bad merge widens
the opening for the next. One event reached 978 actors that way.

Linking entities to the ARTICLE lets the matcher ask a different question — not
"has this event ever touched this actor" but "how many of this event's articles
name it" — so an actor inherited from a single mistaken member carries no weight.

Backfilled from enrichments.shared_fields, which has held per-article entities
all along; nothing needs re-extracting and no LLM credits are spent.
"""

import sqlalchemy as sa
from alembic import op

revision = "c4d18e60a927"
down_revision = "b7c2e91a4d33"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "article_entities",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("article_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="affected"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("article_id", "entity_id", name="uq_article_entities"),
    )
    op.create_index("ix_article_entities_article", "article_entities", ["article_id"])
    op.create_index("ix_article_entities_entity", "article_entities", ["entity_id"])

    # Backfill from the extractions we already hold. Matching on entities.name is
    # what correlation/consumer.py itself does when it upserts, so this reproduces
    # the same links rather than inventing a second rule.
    op.execute(
        """
        INSERT INTO article_entities (id, article_id, entity_id, role)
        SELECT DISTINCT ON (e.article_id, ent.id)
               gen_random_uuid(), e.article_id, ent.id,
               coalesce(x->>'role', 'affected')
        FROM enrichments e
        CROSS JOIN LATERAL jsonb_array_elements(e.shared_fields->'entities') x
        JOIN entities ent ON ent.name = x->>'name'
        WHERE jsonb_typeof(e.shared_fields->'entities') = 'array'
        ON CONFLICT (article_id, entity_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("article_entities")
