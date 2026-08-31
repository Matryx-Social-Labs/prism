"""Load the exchange symbol master, and audit the tickers we already show.

    uv run python -m tools.securities --load          # refresh NSE + US masters
    uv run python -m tools.securities --audit         # check stored tickers, READ-ONLY
    uv run python -m tools.securities --clean         # strip the invented ones (dry-run)

WHY THIS EXISTS. `FinanceLens.tickers` is a list of strings an LLM emitted with
nothing checking them, and they flow into the watchlist join. Measured on
production: 201 mentions across 103 events, 128 distinct symbols.

The symbols look right, which is exactly the danger. INFY, TCS, SBIN, HDFCBANK,
PERSISTENT and BEL are genuine NSE codes. `HUL` is not — Hindustan Unilever trades
as HINDUNILVR, and "HUL" is only what people call the company. A reader following
that ticker reaches nothing and a watchlist keyed on it silently never matches, so
the failure is invisible from the inside.

THE SOURCE IS THE EXCHANGE'S OWN LIST, not a vendor feed or a scrape: NSE publishes
EQUITY_L.csv with symbol, company name, series and ISIN for every listed equity.
That makes validation a set membership test rather than a judgement, which is the
only kind of check worth putting in front of an LLM's output.

TWO MARKETS, EACH FROM ITS OWN EXCHANGE. NSE publishes EQUITY_L.csv (symbol,
company, series, ISIN); Nasdaq publishes nasdaqlisted.txt and otherlisted.txt,
which between them cover every US venue. Both are free and official.

The US master was not optional. On NSE alone, the six most-shown unverified
symbols in production — META, NVDA, GOOGL, MSFT, AAPL, AMZN — are all real
Nasdaq listings, so cleaning against NSE alone would have deleted 41 correct
ticker mentions. `ECB` and `HUL` appear in NEITHER list, which is exactly the
distinction worth having: a fabrication, not a gap in our coverage.

STILL NOT COVERED: BSE (its download returns an HTML error page to a plain
client) and every non-US, non-Indian venue. The audit reports those as "on NO
exchange" alongside genuine fabrications, and says so, because from here the two
are indistinguishable.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import urllib.request
import uuid
from collections import Counter
from datetime import datetime

from common.securities import EXPECTED_MARKETS, normalize

NSE_EQUITY_L = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
# NSE serves the archive only to something that looks like a browser.
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def fetch_nse() -> list[dict]:
    req = urllib.request.Request(NSE_EQUITY_L, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return parse_nse(r.read().decode("utf-8", errors="replace"))


def parse_nse(body: str) -> list[dict]:
    """Split from the fetch so the parsing rules are testable without the network.

    They are worth testing: the published header carries stray spaces, the listing
    date is DD-MON-YYYY, and a row that fails to parse must degrade rather than
    disappear — a security missing from the master is a ticker we would wrongly
    call fabricated.
    """
    rows = []
    for raw in csv.DictReader(io.StringIO(body)):
        # The published header carries stray spaces (" SERIES", " ISIN NUMBER"), so
        # keys are normalised rather than indexed by their exact spelling.
        rec = {k.strip().upper(): (v or "").strip() for k, v in raw.items() if k}
        if not rec.get("SYMBOL"):
            continue
        listed = None
        if rec.get("DATE OF LISTING"):
            try:
                listed = datetime.strptime(rec["DATE OF LISTING"], "%d-%b-%Y").date()
            except ValueError:
                listed = None      # an unparseable date must not drop the security
        rows.append({
            "symbol": rec["SYMBOL"],
            "name": rec.get("NAME OF COMPANY") or rec["SYMBOL"],
            "exchange": "NSE",
            "series": rec.get("SERIES") or None,
            "isin": rec.get("ISIN NUMBER") or None,
            "listed_on": listed,
        })
    return rows


NASDAQ_LISTED = "https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt"
OTHER_LISTED = "https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt"

# otherlisted.txt names the venue with a single letter. Anything not listed here
# is kept under its raw code rather than dropped — see `_parse_us`.
US_EXCHANGES = {"N": "NYSE", "P": "NYSEARCA", "Z": "CBOE", "A": "NYSEAMERICAN",
                "V": "IEX", "M": "NYSETEXAS"}


def fetch_us() -> list[dict]:
    """Nasdaq's own symbol directory, which covers every US venue, not just Nasdaq.

    Free, public, and published by the exchange — the same standard the NSE
    source is held to. No ISIN in these files, which is why `securities.isin` is
    nullable: a US security is identified here by (exchange, symbol) alone.
    """
    return parse_nasdaq(_get(NASDAQ_LISTED)) + parse_otherlisted(_get(OTHER_LISTED))


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_nasdaq(body: str) -> list[dict]:
    return _parse_us(body, "Symbol", lambda _r: "NASDAQ")


def parse_otherlisted(body: str) -> list[dict]:
    return _parse_us(body, "ACT Symbol", lambda r: _us_exchange(r.get("Exchange", "")))


def _us_exchange(code: str) -> str | None:
    # An unmapped code keeps the security under its raw letter instead of losing
    # it. If Nasdaq adds a venue, its listings should still validate a ticker —
    # a security missing from the master is a real symbol we call fabricated.
    return US_EXCHANGES.get(code) or (f"US-{code}" if code else None)


def _parse_us(body: str, symbol_col: str, exchange) -> list[dict]:
    """Both files are pipe-delimited with the same two traps.

    They end with a `File Creation Time: ...` line that parses as a perfectly
    ordinary row carrying a symbol, and they carry TEST ISSUES — `MTEST`, and
    three IEX test symbols — which are venue plumbing, not companies. Admitting
    either would validate a ticker a reader cannot hold.
    """
    rows = []
    for raw in csv.DictReader(io.StringIO(body), delimiter="|"):
        rec = {(k or "").strip(): (v or "").strip() for k, v in raw.items() if k}
        sym = rec.get(symbol_col, "")
        if not sym or sym.startswith("File Creation Time"):
            continue
        if rec.get("Test Issue") == "Y":
            continue
        ex = exchange(rec)
        if not ex:
            continue
        rows.append({
            "symbol": sym,
            "name": rec.get("Security Name") or sym,
            "exchange": ex,
            "series": None,
            "isin": None,       # the US files publish none; (exchange, symbol) identifies
            "listed_on": None,
        })
    return rows


async def _upsert(c, rows: list[dict]) -> None:
    """Write one batch, then retire what each market no longer lists.

    The retirement sweep is per market and REFUSES to run on a short batch. A
    truncated download would otherwise mark an entire exchange inactive, which is
    the same half-loaded failure the read side guards against — arriving here as
    a write instead.
    """
    by_exchange: dict[str, list[str]] = {}
    for r in rows:
        by_exchange.setdefault(r["exchange"], []).append(r["symbol"])

    async with c.transaction():
        await c.executemany(
            """
            INSERT INTO securities
              (id, isin, symbol, exchange, name, series, listed_on, active)
            VALUES ($1,$2,$3,$4,$5,$6,$7,true)
            ON CONFLICT (exchange, symbol) DO UPDATE
              SET isin = EXCLUDED.isin, name = EXCLUDED.name,
                  series = EXCLUDED.series, listed_on = EXCLUDED.listed_on,
                  active = true
            """,
            [(uuid.uuid4(), r["isin"], r["symbol"], r["exchange"], r["name"],
              r["series"], r["listed_on"]) for r in rows],
        )
        for ex, symbols in sorted(by_exchange.items()):
            floor = EXPECTED_MARKETS.get(ex, 1)
            if len(symbols) < floor:
                print(f"  {ex}: {len(symbols)} rows is short of the {floor} a finished "
                      "load produces — inserted, but retiring nothing")
                continue
            gone = await c.fetchval(
                "WITH d AS (UPDATE securities SET active = false "
                "WHERE exchange = $1 AND active AND symbol <> ALL($2::text[]) "
                "RETURNING 1) SELECT count(*) FROM d",
                ex, symbols,
            )
            if gone:
                print(f"  {ex}: marked {gone} inactive (no longer listed)")

    for ex, symbols in sorted(by_exchange.items()):
        print(f"  {ex}: {len(symbols)} securities")


async def load(url: str | None = None, market: str = "all") -> None:
    """Refresh the master. Idempotent: re-running updates rather than duplicating.

    Securities that vanish from a published list are marked inactive, not
    deleted. A delisted company still appears in old coverage, and the honest
    answer to "what was this?" is the record plus its status.
    """
    import asyncpg

    from tools.snapshot_l2 import _prod_url

    rows: list[dict] = []
    if market in ("all", "nse"):
        rows += fetch_nse()
    if market in ("all", "us"):
        rows += fetch_us()
    if not rows:
        raise SystemExit(f"no securities fetched for market={market!r} — refusing to write")

    c = await asyncpg.connect(url or _prod_url(), timeout=120)
    try:
        await _upsert(c, rows)
    finally:
        await c.close()
    print(f"  total: {len(rows)} securities, {sum(1 for r in rows if r['isin'])} with an ISIN")


async def audit(url: str | None = None) -> None:
    """Check every ticker already stored against the master. READ-ONLY.

    Reports three buckets, and the third is the one that matters: a symbol neither
    listed here nor plausibly foreign is a fabrication we are currently rendering
    to readers.
    """
    import asyncpg

    from tools.snapshot_l2 import _prod_url

    c = await asyncpg.connect(url or _prod_url(), timeout=90)
    try:
        await c.execute("SET default_transaction_read_only = on")
        await _require_loaded(c)
        listed: dict[str, set[str]] = {}
        for r in await c.fetch("SELECT symbol, exchange FROM securities"):
            listed.setdefault(r["symbol"], set()).add(r["exchange"])
        rows = await c.fetch(
            "SELECT jsonb_array_elements_text(projection->'finance'->'tickers') AS t "
            "FROM events WHERE jsonb_typeof(projection->'finance'->'tickers') = 'array'"
        )
    finally:
        await c.close()

    counts = Counter(normalize(r["t"]) for r in rows if r["t"].strip())
    counts.pop("", None)
    by_market: Counter = Counter()
    unknown = {}
    for t, n in counts.items():
        where = listed.get(t)
        if where:
            by_market[min(where)] += n
        else:
            unknown[t] = n
    print(f"  ticker mentions      : {sum(counts.values())}   distinct: {len(counts)}")
    for market, n in sorted(by_market.items()):
        held = sum(1 for t in counts if market in listed.get(t, ()))
        print(f"  validated on {market:<8}: {held}  ({n} mentions)")
    print(f"  on NO exchange       : {len(unknown)}  ({sum(unknown.values())} mentions)")
    if unknown:
        print("\n  These name no security on any exchange we load. A symbol here is")
        print("  either invented or belongs to a market we do not cover:")
        for t, n in sorted(unknown.items(), key=lambda kv: -kv[1])[:25]:
            print(f"    {t:16} {n}")


async def _require_loaded(c) -> None:
    """Refuse to judge anything against a master that never finished loading.

    PER MARKET, not on the total. A US-only load holds ~11,000 rows and would
    clear any total floor, then report every genuine NSE ticker as invented
    because none of them are there. Caught for real in the other direction: a dry
    run of `--clean` against a master holding 2 rows proposed dropping NHPC, a
    real NSE listing.
    """
    held = {r["exchange"]: r["n"] for r in
            await c.fetch("SELECT exchange, count(*) AS n FROM securities GROUP BY exchange")}
    short = {m: held.get(m, 0) for m, floor in EXPECTED_MARKETS.items() if held.get(m, 0) < floor}
    if short:
        raise SystemExit(
            "the securities master is short on "
            + ", ".join(f"{m} ({n} rows, expected >= {EXPECTED_MARKETS[m]})"
                        for m, n in sorted(short.items()))
            + ".\nRun --load first; judging tickers against a partial master would "
              "call real ones invented."
        )


async def clean(url: str | None = None, apply: bool = False) -> None:
    """Remove already-stored tickers that no security carries. DRY-RUN by default.

    `common/securities.py` stops new ones at the write. It cannot touch what is
    already there — 138 mentions across 103 events, extracted before the master
    existed — and those are what a reader sees today.

    Only the ticker LIST is rewritten. `raw_model_output` keeps the extractor's
    verbatim output, so this narrows what we display without destroying the record
    of what was claimed.
    """
    import asyncpg

    from tools.snapshot_l2 import _prod_url

    c = await asyncpg.connect(url or _prod_url(), timeout=90)
    try:
        await _require_loaded(c)
        known = {r["symbol"] for r in await c.fetch("SELECT symbol FROM securities")}
        for table, col in (("enrichments", "lens_fields"), ("events", "projection")):
            rows = await c.fetch(
                f"SELECT id, {col} AS doc FROM {table} "
                f"WHERE jsonb_typeof({col} -> 'finance' -> 'tickers') = 'array'"
            )
            changed = dropped = 0
            for r in rows:
                doc = json.loads(r["doc"]) if isinstance(r["doc"], str) else dict(r["doc"])
                had = doc["finance"]["tickers"]
                kept: list[str] = []
                for t in had:
                    n = normalize(t)
                    if n in known and n not in kept:
                        kept.append(n)
                if kept == had:
                    continue
                changed += 1
                dropped += len(had) - len(kept)
                if apply:
                    await c.execute(
                        f"UPDATE {table} SET {col} = "
                        f"jsonb_set({col}, '{{finance,tickers}}', $1::jsonb) WHERE id = $2",
                        json.dumps(kept), r["id"],
                    )
            verb = "rewrote" if apply else "would rewrite"
            print(f"  {table}.{col}: {verb} {changed} of {len(rows)} rows, "
                  f"dropping {dropped} unverified mentions")
    finally:
        await c.close()
    if not apply:
        print("\n  DRY RUN — nothing was written. Re-run with --apply.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", action="store_true")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--clean", action="store_true",
                    help="strip unverified tickers from stored rows (dry-run)")
    ap.add_argument("--apply", action="store_true", help="let --clean actually write")
    ap.add_argument("--market", choices=("all", "nse", "us"), default="all",
                    help="which symbol master to load (default: all)")
    ap.add_argument("--db", metavar="URL", help="target database (default: production)")
    a = ap.parse_args()
    if a.load:
        asyncio.run(load(a.db, a.market))
    if a.audit:
        asyncio.run(audit(a.db))
    if a.clean:
        asyncio.run(clean(a.db, apply=a.apply))
    if not (a.load or a.audit or a.clean):
        ap.print_help()


if __name__ == "__main__":
    main()
