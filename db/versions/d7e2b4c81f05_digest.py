"""digest: the week's record by email, opt-in, with its consent record

Revision ID: d7e2b4c81f05
Revises: c3f1a9d27e84
Create Date: 2026-09-29 00:00:00.000000

A weekly email of the week's counted records (common/weekly_digest.py), sent
only to an account that turned it on (DPDP s.6: explicit, never pre-ticked,
withdrawable as easily as given). The two timestamps are the consent record:
when it was turned on and, once turned off (the account toggle or the
one-click unsubscribe), when. `digest_last_week` is the ISO week last sent
("2026-W40"), so a rerun of Sunday's job never sends a second copy.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'd7e2b4c81f05'
down_revision: str | None = 'c3f1a9d27e84'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("digest_opted_in_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("digest_unsubscribed_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("digest_last_week", sa.Text()))


def downgrade() -> None:
    op.drop_column("users", "digest_last_week")
    op.drop_column("users", "digest_unsubscribed_at")
    op.drop_column("users", "digest_opted_in_at")
