"""Load the exchange symbol master, and audit the tickers we already show.

    uv run python -m tools.securities --load          # refresh from NSE
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

ONLY NSE FOR NOW, and the audit says so rather than quietly passing US symbols.
BSE's equivalent download returns an HTML error page to a plain client, and the
corpus's US tickers (META, NVDA, GOOGL) have no Indian listing to validate against.
Refusing to vouch for what we cannot check is the point; adding a US master later
turns those from unverifiable into verified without changing any of this logic.
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

from common.securities import MIN_MASTER_ROWS, normalize

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
            "series": rec.get("SERIES") or None,
            "isin": rec.get("ISIN NUMBER") or None,
            "listed_on": listed,
        })
    return rows


async def load(url: str | None = None) -> None:
    """Refresh the master. Idempotent: re-running updates rather than duplicating.

    Securities that vanish from the published list are marked inactive, not
    deleted. A delisted company still appears in old coverage, and the honest
    answer to "what was this?" is the record plus its status.
    """
    import asyncpg

    from tools.snapshot_l2 import _prod_url

    rows = fetch_nse()
    c = await asyncpg.connect(url or _prod_url(), timeout=90)
    try:
        async with c.transaction():
            await c.executemany(
                """
                INSERT INTO securities
                  (id, isin, symbol, exchange, name, series, listed_on, active)
                VALUES ($1,$2,$3,'NSE',$4,$5,$6,true)
                ON CONFLICT (exchange, symbol) DO UPDATE
                  SET isin = EXCLUDED.isin, name = EXCLUDED.name,
                      series = EXCLUDED.series, listed_on = EXCLUDED.listed_on,
                      active = true
                """,
                [(uuid.uuid4(), r["isin"], r["symbol"], r["name"], r["series"], r["listed_on"])
                 for r in rows],
            )
            gone = await c.fetchval(
                "WITH d AS (UPDATE securities SET active = false "
                "WHERE exchange = 'NSE' AND active AND symbol <> ALL($1::text[]) "
                "RETURNING 1) SELECT count(*) FROM d",
                [r["symbol"] for r in rows],
            )
    finally:
        await c.close()
    with_isin = sum(1 for r in rows if r["isin"])
    print(f"  NSE: {len(rows)} securities, {with_isin} with an ISIN")
    if gone:
        print(f"  marked inactive (no longer listed): {gone}")


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
        known = {r["symbol"] for r in await c.fetch(
            "SELECT symbol FROM securities WHERE exchange = 'NSE'")}
        rows = await c.fetch(
            "SELECT jsonb_array_elements_text(projection->'finance'->'tickers') AS t "
            "FROM events WHERE jsonb_typeof(projection->'finance'->'tickers') = 'array'"
        )
    finally:
        await c.close()

    _require_loaded(known)

    counts = Counter(r["t"].strip().upper() for r in rows if r["t"].strip())
    valid = {t: n for t, n in counts.items() if t in known}
    unknown = {t: n for t, n in counts.items() if t not in known}
    print(f"  ticker mentions      : {sum(counts.values())}   distinct: {len(counts)}")
    print(f"  validated on NSE     : {len(valid)}  ({sum(valid.values())} mentions)")
    print(f"  NOT on NSE           : {len(unknown)}  ({sum(unknown.values())} mentions)")
    print("\n  unverified, most-shown first — each is either a foreign listing we")
    print("  cannot check yet, or a symbol that does not exist:")
    for t, n in sorted(unknown.items(), key=lambda kv: -kv[1])[:25]:
        print(f"    {t:16} {n}")


def _require_loaded(known: set[str]) -> None:
    """Refuse to judge anything against a master that never finished loading.

    A HALF-loaded master is worse than an empty one: it passes an is-it-empty
    check and then reports every genuine ticker it happens to be missing as a
    fabrication. Caught for real — a dry run of `--clean` against a master
    holding 2 rows proposed dropping NHPC, a real NSE listing.
    """
    if len(known) < MIN_MASTER_ROWS:
        raise SystemExit(
            f"the securities master holds {len(known)} rows, fewer than the "
            f"{MIN_MASTER_ROWS} a finished NSE load produces. Run --load first; "
            "judging tickers against a partial master would call real ones invented."
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
        known = {r["symbol"] for r in await c.fetch("SELECT symbol FROM securities")}
        _require_loaded(known)
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
    ap.add_argument("--db", metavar="URL", help="target database (default: production)")
    a = ap.parse_args()
    if a.load:
        asyncio.run(load(a.db))
    if a.audit:
        asyncio.run(audit(a.db))
    if a.clean:
        asyncio.run(clean(a.db, apply=a.apply))
    if not (a.load or a.audit or a.clean):
        ap.print_help()


if __name__ == "__main__":
    main()
