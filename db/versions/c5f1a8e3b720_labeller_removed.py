"""labellers.status may be 'removed'

Revision ID: c5f1a8e3b720
Revises: b2e7c4d91a36
Create Date: 2026-09-23 00:00:00.000000

Founder decision D5 (admin dashboard, 2026-09-23): removing a labeller keeps
their answers — they are the measurement every gate is judged on — and takes
away every qualification. `paused` could not say that: a paused labeller keeps
what they passed and comes back where they were.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c5f1a8e3b720"
down_revision: str | None = "b2e7c4d91a36"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_labellers_status", "labellers", type_="check")
    op.create_check_constraint("ck_labellers_status", "labellers", "status IN ('applied', 'active', 'paused', 'removed')")


def downgrade() -> None:
    # The old constraint has no 'removed'; the nearest state that still stops
    # every write is 'paused'.
    op.execute("UPDATE labellers SET status = 'paused' WHERE status = 'removed'")
    op.drop_constraint("ck_labellers_status", "labellers", type_="check")
    op.create_check_constraint("ck_labellers_status", "labellers", "status IN ('applied', 'active', 'paused')")
