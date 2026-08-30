"""per-labeller invites: identity becomes a credential, not a typed name

Revision ID: e2b6f014c9a7
Revises: d9e4c1a70f38
Create Date: 2026-08-29 00:00:00.000000

FIXING A REAL BUG, not hardening a hypothetical. `label_responses` was keyed on
(task_id, labeller) where `labeller` is a name the person types, and the insert is
ON CONFLICT DO UPDATE. So a second labeller typing "Ana" silently OVERWRITES the
first Ana's answers.

That is the worst available failure for this feature. The entire reason responses
are per-person is to capture disagreement — two opinions on one task is how a hard
call is told apart from a careless one. A name collision quietly collapses two
opinions into one, and the resulting gold set looks completely normal. Among a
handful of Indian labellers, colliding first names are likely rather than
hypothetical.

Identity is therefore a server-issued token, and a name is only a display label.
Two people called Ana are now two labellers who happen to share a caption.

WHY A TOKEN TABLE AND NOT SIGNED LINKS. An HMAC needs no table, but revoking one
careless labeller means rotating the key and invalidating everyone. A row can be
revoked on its own, carries `last_seen_at` for spotting a link that spread further
than intended, and involves no crypto to get wrong.

WHY THE TOKEN IS NOT IN THE URL. The page mints one on first visit and keeps it in
localStorage, sending it in the request body. A credential in a path leaks through
browser history, Referer headers, server logs and any shared screenshot; the batch
key in the URL stays a join capability only, which is a far weaker thing to leak.

What this deliberately does NOT prevent: someone clearing storage to join twice.
That is a nuisance rather than a compromise — the content is public headlines, the
damage is a duplicate opinion, and `ms_spent` plus per-invite counts make it
visible afterwards. Closing the batch is the answer if it ever matters.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'e2b6f014c9a7'
down_revision: str | None = 'd9e4c1a70f38'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "label_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # The write credential. Unique and indexed: every answer looks up by it.
        sa.Column("token", sa.Text(), nullable=False, unique=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("label_batches.id", ondelete="CASCADE"), nullable=False),
        # Display only. Collisions here are harmless now, which is the whole point.
        sa.Column("name", sa.Text()),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        # Spot a link that travelled further than intended: many invites minted
        # minutes apart, or one still active long after the session it was for.
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_label_invites_batch", "label_invites", ["batch_id"])

    # Re-key responses onto the invite. The live batch holds zero responses, so
    # nothing is migrated and nothing is lost; a backfill would mean inventing an
    # identity for answers that never had one.
    op.execute("DELETE FROM label_responses")
    op.drop_constraint("uq_label_response_once", "label_responses", type_="unique")
    op.add_column(
        "label_responses",
        sa.Column("invite_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("label_invites.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_label_response_once", "label_responses", ["task_id", "invite_id"]
    )
    op.create_index("ix_label_responses_invite", "label_responses", ["invite_id"])

    # Whether a batch hands out invites to anyone holding its link. Off means the
    # only way in is an invite someone minted for you by name.
    op.add_column(
        "label_batches",
        sa.Column("self_join", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    # Responses are cleared going back, and that is not laziness — the old schema
    # CANNOT represent the new data. Its unique constraint is (task_id, labeller),
    # so two people who both answered under the name "Ana" have no legal
    # representation there and the index creation fails outright. Downgrading is
    # therefore lossy by nature, and doing it loudly here beats a migration that
    # errors halfway with the table already altered.
    op.execute("DELETE FROM label_responses")
    op.drop_column("label_batches", "self_join")
    op.drop_index("ix_label_responses_invite", table_name="label_responses")
    op.drop_constraint("uq_label_response_once", "label_responses", type_="unique")
    op.drop_column("label_responses", "invite_id")
    op.create_unique_constraint(
        "uq_label_response_once", "label_responses", ["task_id", "labeller"]
    )
    op.drop_index("ix_label_invites_batch", table_name="label_invites")
    op.drop_table("label_invites")
