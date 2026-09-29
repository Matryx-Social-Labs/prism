"""verify every attach: a follow-up answer per verdict, and which links it wrote

Revision ID: b3e7f1c2a9d4
Revises: 0fe2072138b1
Create Date: 2026-09-29 00:00:00.000000

With PRISM_EVENT_VERIFY=confirm the title, embedding and entity tiers only
propose; Jev decides each attach and also answers whether the article is a later
development of the event (correlation/verify.SAME_STORY). That answer is kept
beside the same-happening one (`story_noul`), and a follow-up link the verifier
wrote is marked on event_links (`method = 'verified'`) so the record page can
show only those, apart from the LLM thread-linker's ('thread').

A proposed candidate may have no gist distance (the article or the event's
members carry no gist), so `gist_distance` may now be empty.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3e7f1c2a9d4"
down_revision: str | None = "0fe2072138b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Metadata-only changes (a constant default, DROP NOT NULL), but each ALTER
    # waits for ACCESS EXCLUSIVE behind open transactions on the table: fail
    # fast rather than queue every reader behind it.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column("event_match_verdicts", sa.Column("story_noul", sa.Float(), nullable=True))
    op.alter_column("event_match_verdicts", "gist_distance", nullable=True)
    op.add_column("event_links", sa.Column("method", sa.Text(), nullable=False, server_default="thread"))


def downgrade() -> None:
    op.drop_column("event_links", "method")
    op.execute("UPDATE event_match_verdicts SET gist_distance = 1.0 WHERE gist_distance IS NULL")
    op.alter_column("event_match_verdicts", "gist_distance", nullable=False)
    op.drop_column("event_match_verdicts", "story_noul")
