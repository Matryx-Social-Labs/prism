"""user name + profession (signup profiling)

Revision ID: 9ddbcc3fd269
Revises: 149182e8b853
Create Date: 2026-07-20 19:56:10.693042

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '9ddbcc3fd269'
down_revision: str | None = '149182e8b853'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("profession", sa.Text(), nullable=True))
    op.add_column("auth_tokens", sa.Column("name", sa.Text(), nullable=True))
    op.add_column("auth_tokens", sa.Column("profession", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("auth_tokens", "profession")
    op.drop_column("auth_tokens", "name")
    op.drop_column("users", "profession")
    op.drop_column("users", "name")
