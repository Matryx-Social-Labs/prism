"""A symbol becomes a ticker only if a listed security actually carries it.

This is the enforcement half of `tools/securities.py`, which builds the master.
The measurement that motivated it, taken on production: of 128 distinct ticker
strings the extractor emitted, 46 exist on NSE and 82 do not — 138 of 201
mentions. `HUL` is the clearest case: Hindustan Unilever trades as HINDUNILVR,
and "HUL" is only what people call the company. It renders as an ordinary ticker
chip, reaches nothing when followed, and never matches a watchlist. The failure
is invisible from the inside, which is why it needs a check rather than a review.

WHAT IS LOST BY DROPPING ONE. Nothing: `enrichments.raw_model_output` stores the
extractor's verbatim output, so a dropped symbol is still recoverable and still
auditable. What changes is only what we are willing to SHOW as a ticker.

TWO MARKETS, AND THE SECOND ONE CHANGED THE ANSWERS. When only NSE was loaded,
META, NVDA, GOOGL, MSFT, AAPL and AMZN — the six most-shown unverified symbols in
production — were dropped as unverifiable. All six are genuine Nasdaq listings.
`ECB` and `HUL` are absent from BOTH lists, which is what separates a fabrication
from a gap in our coverage, and it is a distinction we could not draw before.
"""

import re

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from common.logging import get_logger

logger = get_logger(__name__)

# Yahoo Finance writes NSE symbols as "UPL.NS", and the extractor reproduces its
# data provider's formatting. The security underneath is real, so the suffix is
# stripped before matching — membership is still required afterwards, so this
# repairs a spelling and never admits a symbol on its own.
_NSE_SUFFIX = ".NS"

# Each market we CLAIM to cover, and the row count a finished load produces
# (NSE ~2,559, NASDAQ ~5,580, NYSE ~2,930). A master short of one of these is a
# load that failed or never finished, not a small exchange.
#
# CHECKED PER MARKET, NOT AS A TOTAL, and that is the whole point of the shape.
# A US-only load holds ~11,000 rows and sails past any total floor — then reports
# every genuine NSE ticker as invented, because none of them are there. The
# half-loaded master is more dangerous than the empty one precisely because it
# answers confidently. Not hypothetical: a dry run of `tools.securities --clean`
# against a master holding 2 rows proposed dropping NHPC, a real NSE listing.
#
# The other US venues a load brings in (NYSEARCA, CBOE, NYSEAMERICAN) are
# coverage, not a promise — they are mostly ETFs, and no corpus ticker depends
# on them, so their absence should not stop us judging the rest.
EXPECTED_MARKETS = {"NSE": 1000, "NASDAQ": 1000, "NYSE": 1000}


# MEASURED, not chosen, from the 15,701 symbols in the loaded master: the longest
# is 10 characters (WOCKPHARMA, ZODIACLOTH), and the only non-alphanumeric
# characters any real symbol uses are & - . $ (M&M, BAJAJ-AUTO, BRK.A, AGM$A).
# Nothing lowercase, no underscore, no slash, no space, no caret.
#
# This is a cheap shape test, and it is LOSSLESS against the master by
# construction — a string it rejects cannot be a row in the table. Its whole
# value is on the path where the master cannot be consulted, which would
# otherwise hand `N/A` and whole refusal sentences straight to the reader.
_SYMBOL = re.compile(r"^[A-Z0-9.&$-]{1,10}$")

# The extractor's own vocabulary, which it emits into `tickers` when it has
# nothing to say: FinanceLens's field names, and the values belonging to its
# neighbouring fields. Found in production — `PRICE_IMPACT`, `SECTOR`,
# `CATALYST`, `CONFIDENCE`, `DIRECTION`, `MAGNITUDE`, `MIXED`, `MINOR` and `0.5`
# were all stored as ticker symbols and rendered to readers as chips.
#
# ONLY CONSULTED WHEN THE MASTER CANNOT BE, because it is a guess about intent
# rather than a fact about listings, and the two do collide: `UP` is a
# `direction` value AND a real NYSE symbol (Wheels Up Experience). With a
# healthy master, membership decides and Wheels Up keeps its ticker.
_SCHEMA_WORDS = frozenset({
    "TICKERS", "SECTOR", "CATALYST", "PRICE", "IMPACT", "DIRECTION", "MAGNITUDE",
    "CONFIDENCE", "UP", "DOWN", "MIXED", "MINOR", "MODERATE", "MAJOR",
    "NONE", "NULL", "OTHER", "STRING", "ARRAY",
})


def looks_like_symbol(ticker: str) -> bool:
    # A letter is required because `0.5` — a `confidence` value — was stored as a
    # ticker and clears the character test on its own. Lossless: all 15,701 loaded
    # symbols contain a letter. Nine of them START with a digit, so a leading
    # letter must NOT be required.
    return bool(_SYMBOL.match(ticker)) and any(c.isalpha() for c in ticker)


def normalize(ticker: str) -> str:
    t = (ticker or "").strip().upper()
    if t.endswith(_NSE_SUFFIX):
        t = t[: -len(_NSE_SUFFIX)]
    return t


async def validated(session: AsyncSession, tickers: list[str]) -> list[str]:
    """Keep only the symbols the master knows, normalised, in the order given.

    Delisted securities still match. The question asked here is "did this symbol
    ever identify something real", not "can you trade it today" — a company
    delisted last month still appears in this month's coverage, and refusing its
    ticker would call a genuine symbol a fabrication.

    AN UNLOADED MARKET MEANS WE CANNOT CHECK, NOT THAT EVERYTHING IS FAKE. If a
    market in `EXPECTED_MARKETS` is missing or half loaded, every ticker from it
    would silently disappear and the markets lens would go blank with nothing in
    the logs to explain it: a configuration mistake wearing the costume of a
    clean result. So a short master passes the tickers through unchanged and
    says so loudly.
    """
    wanted = {n for n in (normalize(t) for t in tickers) if n and looks_like_symbol(n)}
    if not wanted:
        return []

    # Asked BEFORE the membership query, not only when nothing matched. Checking
    # it afterwards leaves a hole with a quiet failure in it: a half-loaded master
    # that happens to carry one of the article's tickers answers non-empty, the
    # guard never fires, and every other real symbol in the same article is
    # dropped as invented.
    held = {
        r[0]: r[1]
        for r in await session.execute(
            sa_text("SELECT exchange, count(*) FROM securities GROUP BY exchange")
        )
    }
    short = {m: held.get(m, 0) for m, floor in EXPECTED_MARKETS.items() if held.get(m, 0) < floor}
    if short:
        logger.error(
            "securities master is short on %s — ticker validation is NOT running. "
            "Load it with `python -m tools.securities --load`.",
            ", ".join(f"{m} ({n} rows)" for m, n in sorted(short.items())),
            extra={"tickers": sorted(wanted)},
        )
        # Degraded, not credulous. Without a master we cannot say whether a
        # symbol is listed, but we can still say that the lens's own field names
        # are not tickers — and shipping those to a reader is not the honest
        # half of "we could not check".
        return sorted(t for t in wanted if t not in _SCHEMA_WORDS)

    rows = await session.execute(
        sa_text("SELECT symbol FROM securities WHERE symbol = ANY(:s)"),
        {"s": sorted(wanted)},
    )
    known = {r[0] for r in rows}

    out: list[str] = []
    for t in tickers:
        n = normalize(t)
        if n in known and n not in out:
            out.append(n)
    return out
