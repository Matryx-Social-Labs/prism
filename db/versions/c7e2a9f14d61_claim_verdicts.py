"""claim verdicts: which quotes on a speaker card are one statement, which a translation

Revision ID: c7e2a9f14d61
Revises: b4d18e7c3f20
Create Date: 2026-09-23 00:00:00.000000

Verbatim is checked against the ARTICLE, not the speaker, so an outlet's own
translation passes it; the extractor canonicalises speaker names to English,
which puts that translation on the same card as the original
(enrichment/renderings.py). One Jev call per speaker card asks, for every quote,
"spoken in the language printed?" and, for every cross-language pair, "same
statement?". The answers are cached here as raw probabilities with a hash of the
quotes they were asked about, so the sweep re-asks only when a new report
changes the card and the crossing points can be set from labels without asking
again.

Keyed per (event, speaker) like clip_verdicts and x_post_verdicts are keyed per
(event, item), with the same ON DELETE CASCADE: a merged-away event takes its
verdicts with it. The table is new and empty, so the FK's validation is instant.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c7e2a9f14d61"
down_revision: str | None = "b4d18e7c3f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claim_verdicts",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        # api.routes.events._speaker_key: punctuation and case folded, tokens kept.
        sa.Column("speaker_key", sa.Text(), primary_key=True),
        sa.Column("card_hash", sa.Text(), nullable=False),
        sa.Column("verdicts", postgresql.JSONB(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("claim_verdicts")
