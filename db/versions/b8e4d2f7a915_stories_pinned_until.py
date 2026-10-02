"""stories.pinned_until: a founder's pin on /trending, until when

Revision ID: b8e4d2f7a915
Revises: a3e9c5b1d724
Create Date: 2026-10-02 00:00:00.000000

A pinned story leads /trending, ahead of the running stories, and stays listed
while the pin holds even if it has gone quiet. Set and cleared from /admin/stories
(api/routes/admin_stories.py), each change in admin_audit.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8e4d2f7a915"
down_revision: str | None = "a3e9c5b1d724"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("stories", sa.Column("pinned_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("stories", "pinned_until")
