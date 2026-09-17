"""persist first story visibility on events

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-09-17 00:00:00.000000

The current partition is stamped at migration time as an instrumentation
baseline. That is explicitly not a reconstruction of its historical publish
time. Future rows are stamped atomically when a partition becomes current.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("story_visible_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE events e
        SET story_visible_at = now()
        FROM event_story es
        JOIN partition_runs pr ON pr.id = es.run_id AND pr.status = 'current'
        WHERE e.id = es.event_id
        """
    )


def downgrade() -> None:
    op.drop_column("events", "story_visible_at", if_exists=True)
