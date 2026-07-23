"""rename lens keys to single words in stored event projections

Revision ID: f3a1c8b920de
Revises: e7c94a2b1f08
Create Date: 2026-07-23 11:00:00.000000

Lens slugs became single words (cyber_grc->cyber, finance_trader->markets,
general->reader) so the same key refers to a lens on both the API and the
frontend. Events created before this carry the old keys in their served
`projection` JSONB; rewrite them so the renamed frontend finds the briefs
without waiting for re-ingestion.

Only the lens-keyed fields are remapped — lens_briefs / lens_points (object
keys) and available_lenses / role_interests (array values). The extraction
`lens_fields` key "cyber" and any "general"/"cyber" that appear inside brief
TEXT are deliberately untouched (Python key remap, not a blanket text replace).
"""
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f3a1c8b920de'
down_revision: str | None = 'e7c94a2b1f08'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OBJECT_FIELDS = ("lens_briefs", "lens_points")
_ARRAY_FIELDS = ("available_lenses", "role_interests")


def _remap(projection: dict, mapping: dict) -> bool:
    changed = False
    for field in _OBJECT_FIELDS:
        obj = projection.get(field)
        if isinstance(obj, dict):
            new = {mapping.get(k, k): v for k, v in obj.items()}
            if new != obj:
                projection[field] = new
                changed = True
    for field in _ARRAY_FIELDS:
        arr = projection.get(field)
        if isinstance(arr, list):
            new = [mapping.get(x, x) for x in arr]
            if new != arr:
                projection[field] = new
                changed = True
    return changed


def _apply(mapping: dict) -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, projection FROM events WHERE projection IS NOT NULL")
    ).fetchall()
    for eid, proj in rows:
        if isinstance(proj, str):
            proj = json.loads(proj)
        if not isinstance(proj, dict):
            continue
        if _remap(proj, mapping):
            conn.execute(
                sa.text("UPDATE events SET projection = CAST(:p AS jsonb) WHERE id = :i"),
                {"p": json.dumps(proj), "i": eid},
            )


def upgrade() -> None:
    _apply({"cyber_grc": "cyber", "finance_trader": "markets", "general": "reader"})


def downgrade() -> None:
    _apply({"cyber": "cyber_grc", "markets": "finance_trader", "reader": "general"})
