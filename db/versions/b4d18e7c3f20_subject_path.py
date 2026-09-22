"""subject_path: what a story is about, as a path instead of two flat columns

Revision ID: b4d18e7c3f20
Revises: a7c3e91d4b28
Create Date: 2026-09-22 00:00:00.000000

`sector` and `subsector` stay and keep their meaning — every reader, URL and
API response still works, and `common.subjects.legacy_for()` derives them from
the path. What they cannot do is carry depth: a reader cannot follow cricket,
only sports, and 22 % of production sits in `other` because crime, accidents
and community life have nowhere else to go.

The path is a dotted string (`civic.crime.violent`) rather than a foreign key
into a subjects table. The tree lives in `common/subjects.py`, in git, because
changing it changes URLs and navigation and should be reviewed like code, not
edited live. A text path also makes the query that matters trivial — every
story under a branch is `subject_path LIKE 'civic.crime%'` — which is what the
node pages and every subject-scoped analysis are built on.

The index is text_pattern_ops: a btree on the default collation cannot serve a
prefix LIKE, and prefix LIKE is the only query this column exists for.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4d18e7c3f20"
down_revision: str | None = "a7c3e91d4b28"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("subject_path", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("subject_confidence", sa.Float(), nullable=True))
    op.execute(
        "CREATE INDEX ix_events_subject_path ON events (subject_path text_pattern_ops)"
    )
    # The feed and every node page read "this branch, newest first".
    op.execute(
        "CREATE INDEX ix_events_subject_path_updated ON events "
        "(subject_path text_pattern_ops, last_updated_at DESC)"
    )


def downgrade() -> None:
    op.drop_index("ix_events_subject_path_updated", table_name="events")
    op.drop_index("ix_events_subject_path", table_name="events")
    op.drop_column("events", "subject_confidence")
    op.drop_column("events", "subject_path")
