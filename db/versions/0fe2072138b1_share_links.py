"""share_links: founder links to a Prism page, tagged for one platform

Revision ID: 0fe2072138b1
Revises: d7e2b4c81f05
Create Date: 2026-09-29 00:00:00.000000

A founder makes a link on /admin/marketing (common/share_links.py): a
6-character code, the page it opens, the platform, the medium and the
campaign. The code is its utm_content and its short address (/go/<code>);
the visits it brings are counted in usage_daily under that code, never who.
A link is archived, never deleted: a posted link keeps working, and its
counts keep their label.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0fe2072138b1'
down_revision: str | None = 'd7e2b4c81f05'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "share_links",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("medium", sa.Text(), nullable=False),
        sa.Column("campaign", sa.Text(), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("code ~ '^[2-9a-hjkmnp-z]{6}$'", name="ck_share_links_code"),
    )


def downgrade() -> None:
    op.drop_table("share_links")
