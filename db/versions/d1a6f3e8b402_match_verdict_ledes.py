"""event_match_verdicts: the second reading on opening texts

Revision ID: d1a6f3e8b402
Revises: c8e1f4a7b2d6
Create Date: 2026-10-01 00:00:00.000000

In the 0.65-0.85 band the first reading (headline, summary, nearest members)
refused paraphrases of one happening: ~14% of new records were duplicates. The
best refused candidate is read again on both reports' opening text
(correlation/verify.judge_ledes); its two answers are kept beside the first so
the band can be audited and re-thresholded without asking again.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1a6f3e8b402"
down_revision: str | None = "c8e1f4a7b2d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("event_match_verdicts", sa.Column("lede_noul", sa.Float(), nullable=True))
    op.add_column("event_match_verdicts", sa.Column("lede_story_noul", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("event_match_verdicts", "lede_story_noul")
    op.drop_column("event_match_verdicts", "lede_noul")
