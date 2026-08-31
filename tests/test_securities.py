"""Parsing the exchange symbol master — the set every ticker is checked against.

A security missing from this master is a ticker the audit will wrongly call
fabricated, and a malformed row that silently drops takes a real company with it.
So the parser has to degrade rather than disappear: keep the security, lose only
the field that failed.

Measured motivation, on production: of 128 distinct ticker strings the LLM emitted,
46 exist on NSE and 82 do not — including `HUL` (Hindustan Unilever trades as
HINDUNILVR), `ECB`, and the Yahoo-style `UPL.NS`, `^BSESENSEX` and `^NSENIFTY`.
"""

from datetime import date

from tools.securities import parse_nasdaq, parse_nse, parse_otherlisted

HEADER = (
    "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, "
    "MARKET LOT, ISIN NUMBER, FACE VALUE"
)


def rows(*lines: str):
    return parse_nse("\n".join([HEADER, *lines]))


def test_a_normal_row_parses_every_field():
    (r,) = rows("HINDUNILVR,Hindustan Unilever Limited,EQ,29-JUN-1995,1,1,INE030A01027,1")
    assert r["symbol"] == "HINDUNILVR"
    assert r["name"] == "Hindustan Unilever Limited"
    assert r["series"] == "EQ"
    assert r["isin"] == "INE030A01027"
    assert r["listed_on"] == date(1995, 6, 29)


def test_the_headers_stray_spaces_do_not_lose_columns():
    """NSE publishes " SERIES" and " ISIN NUMBER" with leading spaces. Indexing by
    the exact spelling would silently yield None for both, and every security would
    then arrive with no ISIN — the identifier this whole design is keyed on."""
    (r,) = rows("INFY,Infosys Limited,EQ,08-FEB-1995,5,1,INE009A01021,5")
    assert r["isin"] == "INE009A01021" and r["series"] == "EQ"


def test_an_unparseable_date_keeps_the_security():
    """Losing the row would remove a real company from the master, which turns a
    valid ticker into a reported fabrication. Lose the date, keep the security."""
    (r,) = rows("ODDDATE,Odd Date Ltd,EQ,not-a-date,10,1,INE111A01011,10")
    assert r["symbol"] == "ODDDATE" and r["listed_on"] is None


def test_a_missing_isin_keeps_the_security():
    """A handful of listed instruments genuinely have no ISIN in the file. They are
    still tradeable symbols and still validate a ticker."""
    (r,) = rows("NOISIN,No Isin Ltd,EQ,01-JAN-2020,10,1,,10")
    assert r["symbol"] == "NOISIN" and r["isin"] is None


def test_a_row_with_no_symbol_is_dropped():
    """The symbol is the thing being validated against. A row without one cannot
    take part, and admitting it would put an empty string into the known set —
    which would then validate an empty ticker."""
    assert rows(",Blank Symbol Ltd,EQ,01-JAN-2020,10,1,INE222A01011,10") == []


def test_values_are_stripped():
    (r,) = rows("  TCS , Tata Consultancy Services Limited , EQ , 25-AUG-2004 ,1,1, INE467B01029 ,1")
    assert r["symbol"] == "TCS" and r["isin"] == "INE467B01029"


def test_a_header_only_file_yields_nothing_rather_than_raising():
    """A fetch returning only a header — or an error page — should not explode in
    the parser; `load` is where emptiness gets challenged."""
    assert parse_nse(HEADER) == []


# --- the US master ------------------------------------------------------------
# Added because NSE alone was not enough to judge by. The six most-shown
# unverified symbols in production — META, NVDA, GOOGL, MSFT, AAPL, AMZN — are
# all genuine Nasdaq listings, so a backfill run against NSE alone would have
# deleted 41 correct ticker mentions as fabrications.

NASDAQ_HEADER = (
    "Symbol|Security Name|Market Category|Test Issue|Financial Status|"
    "Round Lot Size|ETF|NextShares"
)
OTHER_HEADER = (
    "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|"
    "Test Issue|NASDAQ Symbol"
)
# Verbatim from the published files on 2026-08-31, footer included.
FOOTER_NASDAQ = "File Creation Time: 0831202607:00|||||||"
FOOTER_OTHER = "File Creation Time: 0831202607:00||||||"


def nasdaq(*lines: str):
    return parse_nasdaq("\n".join([NASDAQ_HEADER, *lines, FOOTER_NASDAQ]))


def other(*lines: str):
    return parse_otherlisted("\n".join([OTHER_HEADER, *lines, FOOTER_OTHER]))


def test_a_nasdaq_listing_parses():
    (r,) = nasdaq("META|Meta Platforms, Inc. - Class A Common Stock|Q|N|N|100|N|N")
    assert r["symbol"] == "META" and r["exchange"] == "NASDAQ"
    assert r["name"].startswith("Meta Platforms")


def test_the_file_creation_footer_is_not_a_security():
    """Both files end with `File Creation Time: ...`, which parses as a perfectly
    ordinary row carrying a symbol. Admitted, it would validate a ticker made of
    a timestamp."""
    assert nasdaq() == [] and other() == []


def test_a_test_issue_is_not_a_security():
    """`MTEST` and the three IEX test symbols are venue plumbing. They are real
    rows in the real file, and a reader cannot hold any of them."""
    assert other("MTEST|NYSE Texas, Inc. TEST Common Stock|M|MTEST|N|100|Y|MTEST") == []
    assert nasdaq("ZAZZT|Nasdaq TEST Stock|G|Y|N|100|N|N") == []


def test_the_exchange_letter_becomes_a_market_name():
    (r,) = other("A|Agilent Technologies, Inc. Common Stock|N|A|N|100|N|A")
    assert r["exchange"] == "NYSE"


def test_the_act_symbol_is_stored_not_the_nasdaq_one():
    """otherlisted carries the same security under two spellings: `BRK.A` in the
    ACT column and `BRK-A` in the NASDAQ one. The dotted form is how the class is
    written in prose, so it is the one an extractor emits and the one to store.

    Storing the wrong column is invisible in most rows — for the large majority
    the two are identical — which is why this test picks one where they differ.
    A ticker stored as `BRK-A` would match nothing a reader ever writes.
    """
    (r,) = other("BRK.A|Berkshire Hathaway Inc. Class A|N|BRK.A|N|10|N|BRK-A")
    assert r["symbol"] == "BRK.A"


def test_an_unmapped_exchange_letter_keeps_the_security():
    """If Nasdaq adds a venue, its listings must still validate a ticker. Dropping
    them would turn every symbol on that venue into a reported fabrication —
    the same degrade-rather-than-disappear rule the NSE parser follows."""
    (r,) = other("NEWCO|New Venue Corp Common Stock|X|NEWCO|N|100|N|NEWCO")
    assert r["symbol"] == "NEWCO" and r["exchange"] == "US-X"


def test_a_us_security_carries_no_isin_and_that_is_allowed():
    """The US files publish none — (exchange, symbol) identifies the security
    there. `securities.isin` is nullable for exactly this."""
    (r,) = nasdaq("NVDA|NVIDIA Corporation - Common Stock|Q|N|N|100|N|N")
    assert r["isin"] is None and r["listed_on"] is None
