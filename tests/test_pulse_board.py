"""Market Pulse is a ticker board (founder decision 1, 2026-09-27).

The job: which listed companies and market-wide forces did the last 24 hours
of business reporting name, what happened, and why would a markets reader
notice. It replaced an LLM essay over the 12 most recently touched business
events — no time window, one ticker on the day it was audited. Rows are
counted and sourced; the model may only add three lines read from them.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from common.db import session_scope
from common.securities import build_master
from correlation import digest

NOW = datetime(2026, 9, 27, 17, 30, tzinfo=UTC)
SINCE = NOW - digest.WINDOW
LISTED = build_master([
    ("SUNPHARMA", "NSE", "Sun Pharmaceutical Industries Limited"),
    ("SBIN", "NSE", "State Bank of India"),
    ("BA", "NYSE", "Boeing Company (The) Common Stock"),
    ("INDIGO", "NSE", "InterGlobe Aviation Limited"),
    ("JPM", "NYSE", "JP Morgan Chase & Co. Common Stock"),
])
PUBLISHERS = {"thehindu": "thehindu", "thehindu_tamilnadu": "thehindu", "livemint": "livemint", "ndtv": "ndtv", "economictimes": "economictimes"}


def event(title, *, tickers=(), slugs=("ndtv",), catalyst=None, price=None, reader=None, sector="business", hours_ago=2):
    finance = {"tickers": list(tickers)}
    if catalyst:
        finance["catalyst"] = catalyst
    if price:
        finance["price_impact"] = price
    published = NOW - timedelta(hours=hours_ago)
    return {
        "id": uuid.uuid4(),
        "title": title,
        "sector": sector,
        "last_updated_at": published,
        "projection": {
            "finance": finance,
            "source_slugs": list(slugs),
            "latest_published_at": published.isoformat(),
            "lens_points": {"reader": reader} if reader else {},
        },
    }


def board(events, impacts=()):
    return digest.assemble(events, list(impacts), PUBLISHERS, LISTED, SINCE, NOW)


def test_a_company_the_days_business_reporting_names_is_a_row():
    ev = event("TNPCB tells NGT no expansion at Sun Pharma unit", tickers=["SUNPHARMA"],
               slugs=["thehindu_tamilnadu"], catalyst="regulatory_action")
    (row,) = board([ev])["companies"]
    assert row["symbol"] == "SUNPHARMA" and row["exchange"] == "NSE"
    assert row["company"] == "Sun Pharmaceutical Industries"
    assert row["id"] == str(ev["id"]) and row["headline"] == ev["title"]
    assert row["catalyst"] == "Regulatory action", "human words, not snake_case"
    assert row["outlets"] == 1 and row["single_source"] is True
    assert row["published_at"] == ev["projection"]["latest_published_at"]


def test_labels_read_as_words():
    """The extractor's catalysts and effects are snake_case; 'other' says nothing."""
    assert digest.words("upi_mdr_boycott") == "UPI MDR boycott"
    assert digest.words("earnings_beat,commodity_inflation") == "Earnings beat"
    assert digest.words("other") is None and digest.words(None) is None


def test_the_company_is_named_as_listed_without_its_share_class():
    assert digest.display_name("JP Morgan Chase & Co. Common Stock") == "JP Morgan Chase"
    assert digest.display_name("Boeing Company (The) Common Stock") == "Boeing"
    assert digest.display_name("Amazon.com, Inc. - Common Stock") == "Amazon.com"
    assert digest.display_name("Mahindra & Mahindra Limited") == "Mahindra & Mahindra"


def test_outlets_are_counted_by_masthead():
    """The Hindu's state feeds are one newsroom; two of them are one outlet."""
    ev = event("SBI raises ATM charges", tickers=["SBIN"], slugs=["thehindu", "thehindu_tamilnadu"])
    (row,) = board([ev])["companies"]
    assert row["outlets"] == 1 and row["single_source"] is True


def test_the_most_corroborated_company_leads_and_uses_its_best_record():
    thin = event("SBI branch opens", tickers=["SBIN"], slugs=["ndtv"])
    thick = event("Bank strike deferred", tickers=["SBIN"], slugs=["ndtv", "livemint", "economictimes"], hours_ago=5)
    boeing = event("Boeing flags 737 MAX glitch", tickers=["BA"], slugs=["ndtv", "livemint"])
    rows = board([boeing, thin, thick])["companies"]
    assert [r["symbol"] for r in rows] == ["SBIN", "BA"]
    assert rows[0]["id"] == str(thick["id"]) and rows[0]["outlets"] == 3


def test_prisms_reading_is_the_companys_own_impact_when_there_is_one():
    ev = event("Airbus coating issue; Boeing software fix", tickers=["INDIGO", "BA"], slugs=["ndtv", "livemint"],
               price={"direction": "up", "confidence": 0.4})
    impacts = [{"event_id": ev["id"], "entity": "IndiGo", "effect": "a321neo_repainting_costs", "direction": "negative", "confidence": 0.7}]
    rows = {r["symbol"]: r for r in board([ev], impacts)["companies"]}
    assert (rows["INDIGO"]["reading"], rows["INDIGO"]["confidence"]) == ("negative", 0.7)
    assert rows["INDIGO"]["why"] == "A321neo repainting costs"
    # The record's one price read is not Boeing's: two companies share it.
    assert rows["BA"]["reading"] is None and rows["BA"]["confidence"] is None


def test_a_records_price_read_speaks_for_its_only_company():
    ev = event("Sun Pharma recalls a batch in the US", tickers=["SUNPHARMA"], price={"direction": "down", "confidence": 0.6},
               reader=["Watch for a formal announcement"])
    (row,) = board([ev])["companies"]
    assert (row["reading"], row["confidence"]) == ("negative", 0.6)
    assert row["why"] == "Watch for a formal announcement", "no impact names it: the record's own point"


def test_market_wide_forces_are_their_own_rows():
    rbi = event("RBI seen raising repo rate by 25 basis points", slugs=["ndtv", "livemint"])
    upi = event("Mobile retailers warn proposed payment charges could squeeze margins", catalyst="regulatory_action",
                slugs=["ndtv", "livemint", "economictimes"])
    plain = event("Chennai home buyers prefer 3-BHK homes", catalyst="other")
    out = board([rbi, upi, plain])
    assert [r["id"] for r in out["market_wide"]] == [str(upi["id"]), str(rbi["id"])]
    assert "symbol" not in out["market_wide"][0]


def test_the_counts_are_the_boards_own():
    a = event("Sun Pharma unit", tickers=["SUNPHARMA", "SBIN"], slugs=["ndtv", "thehindu"])
    b = event("RBI policy preview", slugs=["livemint", "ndtv"])
    assert board([a, b])["counts"] == {"companies": 2, "stories": 2, "outlets": 3}, "an outlet on two rows is one outlet"


def test_an_empty_day_says_so_with_zeros_not_a_failure():
    out = board([])
    assert out["counts"] == {"companies": 0, "stories": 0, "outlets": 0}
    assert out["companies"] == [] and out["market_wide"] == []
    assert out["window"] == {"start": SINCE.isoformat(), "end": NOW.isoformat()}


# --- the read: at most three lines, and only from the rows ---------------------


def test_the_read_keeps_three_lines_and_no_number_the_rows_do_not_hold():
    rows = "SBIN · State Bank of India · Bank strike deferred · 3 outlets"
    lines = [
        "The bank strike was deferred.",
        "Bank shares rose 4% on the news.",  # 4 is in no row: invented
        "Three outlets carried it.",
        "State Bank of India leads.",
        "A fifth line.",
    ]
    assert digest.grounded(lines, rows) == ["The bank strike was deferred.", "Three outlets carried it.", "State Bank of India leads."]


pytestmark_db = pytest.mark.asyncio(loop_scope="session")


@pytestmark_db
async def test_the_board_reads_the_window_from_the_database(monkeypatch):
    """The SQL half: business and finance only, and only what was reported in
    the window. Asserted on this test's own rows — other tests share the table."""
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    fresh, stale, rebuilt, off = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    now = datetime.now(UTC)
    hour, day_ago = now - timedelta(hours=1), now - timedelta(hours=30)
    rows = [  # id, sector, last_updated_at (the projection's clock), latest_published_at (the news's)
        (fresh, "business", hour, hour),
        (stale, "finance", day_ago, day_ago),
        (rebuilt, "business", hour, day_ago),  # re-projected today; reported yesterday
        (off, "politics", hour, hour),
    ]
    async with session_scope() as s:
        for eid, sector, touched, published in rows:
            await s.execute(
                text("INSERT INTO events (id, title, sector, last_updated_at, projection) "
                     "VALUES (:i, :t, :s, :at, CAST(:p AS jsonb))"),
                {"i": str(eid), "t": f"{tag} {sector}", "s": sector, "at": touched,
                 "p": f'{{"latest_published_at": "{published.isoformat()}", "source_slugs": ["ndtv"]}}'},
            )
    try:
        got = await digest.fetch_window(now - digest.WINDOW)
        ids = {str(e["id"]) for e in got[0]}
        assert str(fresh) in ids
        assert str(stale) not in ids and str(rebuilt) not in ids and str(off) not in ids
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:i AS uuid[]))"),
                            {"i": [str(r[0]) for r in rows]})
