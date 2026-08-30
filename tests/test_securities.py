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

from tools.securities import parse_nse

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
