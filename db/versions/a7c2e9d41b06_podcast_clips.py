"""podcast clips: what the news podcasts said about a story, in their own words

Revision ID: a7c2e9d41b06
Revises: e3f4a5b6c7d8
Create Date: 2026-09-20 00:00:00.000000

Four tables, one per fact:

- podcast_shows      the registry (podcasts/shows.py seeds it): whose show, which
                     feed, which language. `enabled` rather than deletion, like
                     securities.active — an old clip still names its show.
- podcast_episodes   one row per feed item. `audio_duration_s` and `audio_bytes`
                     are what WE transcribed: hosts stitch ads in per request
                     (Spreaker served 2.57 MB and 2.12 MB of the same episode to
                     two user agents on 2026-09-20), so the player compares the
                     file it loaded against these and shifts the seek.
- podcast_windows    30–60 s of transcript with word timestamps and the same mE5
                     embedding the events carry, so a window→event match is one
                     index scan on events.embedding.
- event_clips        the match: this window is about this event, with the
                     cosine that said so and the rank it earned. Nothing here is
                     shown below the gold_clips precision gate (0.9).

Audio is never stored. The enclosure is fetched once, transcribed, discarded.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from common.config import get_settings

revision: str = 'a7c2e9d41b06'
down_revision: str | None = 'e3f4a5b6c7d8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "podcast_shows",
        sa.Column("slug", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("publisher", sa.Text(), nullable=False),
        sa.Column("feed_url", sa.Text(), nullable=False),
        sa.Column("site_url", sa.Text()),
        sa.Column("art_url", sa.Text()),
        sa.Column("language", sa.Text(), nullable=False, server_default="en"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_polled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "podcast_episodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("show_slug", sa.Text(), sa.ForeignKey("podcast_shows.slug", ondelete="CASCADE"), nullable=False),
        sa.Column("guid", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("episode_url", sa.Text()),
        sa.Column("audio_url", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feed_duration_s", sa.Integer()),
        sa.Column("audio_duration_s", sa.Float()),
        sa.Column("audio_bytes", sa.BigInteger()),
        sa.Column("language", sa.Text()),
        # pending → done | failed | skipped (too old to pay for)
        sa.Column("transcript_status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("transcribed_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("show_slug", "guid", name="uq_podcast_episodes_show_guid"),
    )
    op.create_index("ix_podcast_episodes_published", "podcast_episodes", ["published_at"])
    op.create_index("ix_podcast_episodes_status", "podcast_episodes", ["transcript_status"])
    op.create_table(
        "podcast_windows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("podcast_episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("start_s", sa.Float(), nullable=False),
        sa.Column("end_s", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("words", postgresql.JSONB()),  # [[word, start, end], …]
        sa.Column("embedding", Vector(get_settings().prism_embed_dim)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("episode_id", "seq", name="uq_podcast_windows_episode_seq"),
    )
    op.create_table(
        "event_clips",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("window_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("podcast_windows.id", ondelete="CASCADE"), primary_key=True),
        # The clip may span several windows merged; these are its real bounds.
        sa.Column("start_s", sa.Float(), nullable=False),
        sa.Column("end_s", sa.Float(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("entity_hits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_event_clips_window", "event_clips", ["window_id"])


def downgrade() -> None:
    op.drop_index("ix_event_clips_window", table_name="event_clips")
    op.drop_table("event_clips")
    op.drop_table("podcast_windows")
    op.drop_index("ix_podcast_episodes_status", table_name="podcast_episodes")
    op.drop_index("ix_podcast_episodes_published", table_name="podcast_episodes")
    op.drop_table("podcast_episodes")
    op.drop_table("podcast_shows")
