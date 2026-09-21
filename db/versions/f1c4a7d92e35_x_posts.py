"""x posts: what the official accounts said on X about a story, as written

Revision ID: f1c4a7d92e35
Revises: e3b8c9d0f1a2
Create Date: 2026-09-21 12:00:00.000000

Four tables, one per fact, the shape of the podcast layer (a7c2e9d41b06):

- x_accounts        the allowlist (xposts/accounts.py seeds it): which official
                    account, its X user id, the avatar the display rules require,
                    and the since_id watermark. `enabled` rather than deletion.
- x_posts           one row per post, the text as written (never altered — the
                    display rules and the product's verbatim rule agree), the
                    same mE5 embedding the events carry, and the compliance
                    columns: last_seen_at (re-hydrated weekly while attached),
                    deleted_at (gone on X → gone here within the day).
- event_x_posts     the match: this post is about this event, by which method
                    (url = it links an article we hold; judge = a model read
                    both), with the cosine and the rank. NEVER a membership: a
                    post is signal, not coverage — it counts toward nothing.
- x_post_verdicts   the judge's cached reading per (event, post), so the
                    ten-minute rematch never pays for the same pair twice.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from common.config import get_settings

revision: str = 'f1c4a7d92e35'
down_revision: str | None = 'e3b8c9d0f1a2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "x_accounts",
        sa.Column("handle", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text()),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("tier", sa.Text(), nullable=False),  # official | wire | journalist
        sa.Column("profile_image_url", sa.Text()),
        sa.Column("language", sa.Text(), nullable=False, server_default="en"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("since_id", sa.Text()),
        sa.Column("last_polled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "x_posts",
        sa.Column("post_id", sa.Text(), primary_key=True),
        sa.Column("handle", sa.Text(), sa.ForeignKey("x_accounts.handle", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("lang", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("urls", postgresql.JSONB()),  # unwound/expanded links in the post
        sa.Column("metrics", postgresql.JSONB()),  # public_metrics at fetch; never shown as a count
        sa.Column("referenced", postgresql.JSONB()),  # referenced_tweets ids; the quoted post is never fetched
        sa.Column("embedding", Vector(get_settings().prism_embed_dim)),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_x_posts_created", "x_posts", ["created_at"])
    op.create_table(
        "event_x_posts",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("post_id", sa.Text(), sa.ForeignKey("x_posts.post_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("method", sa.Text(), nullable=False),  # url | judge
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_event_x_posts_post", "event_x_posts", ["post_id"])
    op.create_table(
        "x_post_verdicts",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("post_id", sa.Text(), sa.ForeignKey("x_posts.post_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("verdict", sa.Text(), nullable=False),  # event | topic | unrelated
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("x_post_verdicts")
    op.drop_index("ix_event_x_posts_post", table_name="event_x_posts")
    op.drop_table("event_x_posts")
    op.drop_index("ix_x_posts_created", table_name="x_posts")
    op.drop_table("x_posts")
    op.drop_table("x_accounts")
