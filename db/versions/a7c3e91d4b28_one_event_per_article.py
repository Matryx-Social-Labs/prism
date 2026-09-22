"""one event per article: the invariant correlation relied on a comment for

Revision ID: a7c3e91d4b28
Revises: f1c4a7d92e35
Create Date: 2026-09-22 00:00:00.000000

`event_memberships` was unique on (event_id, article_id): an article could not
join the same event twice, but nothing stopped it joining two events. That never
happened in production (0 of 20,127 memberships on 2026-09-22) only because the
correlation consumer runs as exactly one process and its "concurrency 1" lives
in two comments (worker/__main__.py, common/stream.py). A second replica, or
XAUTOCLAIM handing a slow message to a second consumer, would run match-or-create
twice for one article and seed two events for one story.

The constraint makes the bad state unrepresentable; the consumer now also takes
an advisory lock around match-or-create so two processes serialise on the
database rather than on a deployment rule (docs/AUDIT-2026-09.md C3).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a7c3e91d4b28"
down_revision: str | None = "f1c4a7d92e35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Keep the earliest membership if a duplicate ever slipped in (none had).
    op.execute(
        """
        DELETE FROM event_memberships m USING event_memberships k
        WHERE m.article_id = k.article_id AND m.id <> k.id AND m.created_at > k.created_at
        """
    )
    op.create_unique_constraint("uq_event_memberships_article", "event_memberships", ["article_id"])


def downgrade() -> None:
    op.drop_constraint("uq_event_memberships_article", "event_memberships", type_="unique")
