"""user language preferences: languages, state, consented_at

Revision ID: b2d5e1f4a093
Revises: f3a1c8b920de
Create Date: 2026-07-23 12:00:00.000000

Phase 1 onboarding collects, server-side, the reader's languages (ordered by
preference — first is primary), their state (ISO 3166-2, e.g. IN-KA), and a
consent timestamp captured at the profile step (after magic-link verify). All
nullable and default-safe: pre-existing rows and the pre-profile window read as
NULL, and the feed falls back to its language-agnostic behaviour when unset.
Small table (users), so this is safe to run inline on startup.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b2d5e1f4a093'
down_revision: str | None = 'f3a1c8b920de'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("languages", sa.ARRAY(sa.Text()), nullable=True))
    op.add_column("users", sa.Column("state", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "consented_at")
    op.drop_column("users", "state")
    op.drop_column("users", "languages")
