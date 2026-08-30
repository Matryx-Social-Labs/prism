"""securities: a symbol master, so a ticker has to exist before we show it

Revision ID: f3c8d2e51a09
Revises: e2b6f014c9a7
Create Date: 2026-08-29 00:00:00.000000

`FinanceLens.tickers` is a list of strings an LLM emitted, validated against
nothing, and it flows into the watchlist join. Measured on production: 201 ticker
mentions across 103 events, 128 distinct symbols.

They look right, which is the problem. INFY, TCS, SBIN, HDFCBANK, PERSISTENT and
BEL are all genuine NSE symbols. `HUL` is not — Hindustan Unilever trades as
HINDUNILVR, and "HUL" is merely what people call the company. Confirmed against
NSE's own equity list: HUL absent, HINDUNILVR present. A reader following that
ticker reaches nothing, and a watchlist keyed on it silently never matches.

KEYED ON ISIN, not on the symbol. A symbol is unique only within an exchange and
gets reassigned; an ISIN identifies the security itself and is the one identifier
NSE and BSE agree on. That is also what makes the QID path work later — Wikidata
records ISIN (P946) on company items, so an entity already linked to a QID can
reach its security without an LLM guessing in between.

`active` rather than deletion: a delisted security still appears in old coverage,
and the honest answer to "what was this?" is the record plus its status, not a
missing row.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'f3c8d2e51a09'
down_revision: str | None = 'e2b6f014c9a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "securities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # Nullable: a few listed instruments genuinely lack one in the source file,
        # and refusing to record them would leave the master quietly incomplete —
        # which is the failure this table exists to prevent.
        sa.Column("isin", sa.Text()),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("series", sa.Text()),
        sa.Column("listed_on", sa.Date()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        # A symbol is unique per exchange, never globally: NSE and BSE both list the
        # same company under different codes.
        sa.UniqueConstraint("exchange", "symbol", name="uq_securities_exchange_symbol"),
    )
    op.create_index("ix_securities_symbol", "securities", ["symbol"])
    op.create_index("ix_securities_isin", "securities", ["isin"])


def downgrade() -> None:
    op.drop_index("ix_securities_isin", table_name="securities")
    op.drop_index("ix_securities_symbol", table_name="securities")
    op.drop_table("securities")
