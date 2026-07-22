"""dedupe event_entities to one row per (event_id, entity_id)

Revision ID: e7c94a2b1f08
Revises: 5493a4141cbb
Create Date: 2026-07-23 09:30:00.000000

The (event_id, entity_id, role) unique key let the SAME entity attach to one event
multiple times under different roles (subject/mentioned/affected) as its member
articles merged. The IDF-weighted actor-graph queries (clustering match + story
timeline edges) sum 1/df over those role-rows and multiply seed-rows x neighbour-rows,
so a duplicated actor inflated an edge N-fold — over-weighting the very bridges that
community detection then failed to cut, leaking unrelated stories into a trending
story's timeline (e.g. Sikkim tunnel / Bengal meters into the CJP protest arc).

Collapse to one row per (event_id, entity_id), preferring the 'affected' role so the
cast ordering (api/routes/events.py orders affected-first) is preserved.
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'e7c94a2b1f08'
down_revision: str | None = '5493a4141cbb'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM event_entities WHERE id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (
                    PARTITION BY event_id, entity_id
                    ORDER BY (role = 'affected') DESC, created_at, id
                ) AS rn
                FROM event_entities
            ) t WHERE rn > 1
        )
        """
    )
    op.drop_constraint("uq_event_entities_event_entity_role", "event_entities", type_="unique")
    op.create_unique_constraint(
        "uq_event_entities_event_entity", "event_entities", ["event_id", "entity_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_event_entities_event_entity", "event_entities", type_="unique")
    op.create_unique_constraint(
        "uq_event_entities_event_entity_role", "event_entities", ["event_id", "entity_id", "role"]
    )
