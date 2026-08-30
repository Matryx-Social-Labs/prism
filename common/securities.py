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

US SYMBOLS DROP TOO, for now. META, NVDA and GOOGL are real, and the master is
NSE-only, so they cannot be checked here and are therefore not shown. That is the
intended behaviour of a check we can defend — "we cannot verify this" and "this
is fake" get the same treatment until a US master exists, at which point they
turn into ordinary passes with no change to this logic.
"""

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from common.logging import get_logger

logger = get_logger(__name__)

# Yahoo Finance writes NSE symbols as "UPL.NS", and the extractor reproduces its
# data provider's formatting. The security underneath is real, so the suffix is
# stripped before matching — membership is still required afterwards, so this
# repairs a spelling and never admits a symbol on its own.
_NSE_SUFFIX = ".NS"

# NSE lists ~2,559 equities. A master holding fewer rows than this is a load that
# failed or never finished — not a small exchange. The distinction matters because
# a HALF-loaded master is more dangerous than an empty one: it passes an
# is-it-empty check, then silently reports every genuine ticker it happens to be
# missing as a fabrication. That is not hypothetical — a dry run of
# `tools.securities --clean` against a master holding 2 rows proposed dropping
# NHPC, which is a real NSE listing.
MIN_MASTER_ROWS = 1000


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

    AN UNLOADED MASTER MEANS WE CANNOT CHECK, NOT THAT EVERYTHING IS FAKE. If the
    table has never been loaded — or was loaded half way — every ticker would
    silently disappear and the markets lens would go blank with nothing in the
    logs to explain it: a configuration mistake wearing the costume of a clean
    result. So a master below `MIN_MASTER_ROWS` passes the tickers through
    unchanged and says so loudly.
    """
    wanted = {n for n in (normalize(t) for t in tickers) if n}
    if not wanted:
        return []

    # Asked BEFORE the membership query, not only when nothing matched. Checking
    # it afterwards leaves a hole with a quiet failure in it: a half-loaded master
    # that happens to carry one of the article's tickers answers non-empty, the
    # guard never fires, and every other real symbol in the same article is
    # dropped as invented. A count on a ~2.5k-row table is not worth that.
    held = (await session.execute(sa_text("SELECT count(*) FROM securities"))).scalar_one()
    if held < MIN_MASTER_ROWS:
        logger.error(
            "securities master holds %d rows — ticker validation is NOT running. "
            "Load it with `python -m tools.securities --load`.",
            held,
            extra={"tickers": sorted(wanted)},
        )
        return sorted(wanted)

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
