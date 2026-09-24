"""event_revisions: every published version of a record, kept

Revision ID: e7a4c2b9f613
Revises: d8b3f6a2c914
Create Date: 2026-09-24 00:00:00.000000

A record's headline, summary and briefs were overwritten in place, so what a
reader saw yesterday could not be shown again: not to a reader asking what
changed, not to a complaint, not to a regulator. The IT Rules digital-media code
asks a news publisher to preserve what it published for at least 60 days
(Rule 19(3), not stayed; docs/COMPLIANCE-INDIA.md), and a machine-written
headline is Prism's own publication if it is ever disputed.

A trigger rather than application code: `events` has several writers (the
correlation rebuild through the ORM, persist_briefs and the API in raw SQL), and
a trigger is the one place none of them can skip. It stores the version being
REPLACED, stamped with when it was replaced; the current version is the row in
`events`. Counts and coverage changing on every new report are not a new
version; only what a reader reads is. A deleted record keeps its last version.

No foreign key on purpose: the revision must outlive the event row.
ponytail: kept forever for now; prune past a year if the table ever matters.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7a4c2b9f613"
down_revision: str | None = "d8b3f6a2c914"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_revisions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("replaced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("op", sa.Text(), nullable=False),  # update | delete
        sa.Column("title", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("lens_briefs", postgresql.JSONB()),
        sa.Column("lens_points", postgresql.JSONB()),
    )
    op.create_index("ix_event_revisions_event", "event_revisions", ["event_id", "replaced_at"])
    op.execute(
        """
        CREATE FUNCTION record_event_revision() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE'
             OR OLD.title IS DISTINCT FROM NEW.title
             OR OLD.summary IS DISTINCT FROM NEW.summary
             OR OLD.projection -> 'lens_briefs' IS DISTINCT FROM NEW.projection -> 'lens_briefs'
             OR OLD.projection -> 'lens_points' IS DISTINCT FROM NEW.projection -> 'lens_points' THEN
            INSERT INTO event_revisions (event_id, op, title, summary, lens_briefs, lens_points)
            VALUES (OLD.id, lower(TG_OP), OLD.title, OLD.summary,
                    OLD.projection -> 'lens_briefs', OLD.projection -> 'lens_points');
          END IF;
          RETURN NULL;
        END
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER events_revision AFTER UPDATE OF title, summary, projection OR DELETE ON events "
        "FOR EACH ROW EXECUTE FUNCTION record_event_revision()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS events_revision ON events")
    op.execute("DROP FUNCTION IF EXISTS record_event_revision()")
    op.drop_index("ix_event_revisions_event", table_name="event_revisions")
    op.drop_table("event_revisions")
