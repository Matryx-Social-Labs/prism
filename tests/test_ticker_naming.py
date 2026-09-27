"""A ticker must belong to its story, and a named company must get its ticker.

`validated()` only asks whether a listing carries the symbol. On production
that let F (Ford) sit on a US–China summit and TSM on a Japanese earthquake:
real listings, named nowhere in their articles. `choose_tickers` keeps a
ticker only when the article's headline, opening or organisations name its
company, and links the companies a business article's organisations name
exactly — the extractor gave a ticker on 13.7% of business and finance events.

The linker's precision gate is 0.95 (measured 147 of 150 on held-out articles),
so what it must never do is pinned here: a group, a venue, a plain word.
"""

from common.securities import build_master, choose_tickers, company_key

# Real names as the exchanges publish them, padded past the per-market floor.
ROWS = [
    ("HINDUNILVR", "NSE", "Hindustan Unilever Limited"),
    ("SUNPHARMA", "NSE", "Sun Pharmaceutical Industries Limited"),
    ("SBIN", "NSE", "State Bank of India"),
    ("RELIANCE", "NSE", "Reliance Industries Limited"),
    ("BSE", "NSE", "BSE Limited"),
    ("HDFCBANK", "NSE", "HDFC Bank Limited"),
    ("HAL", "NSE", "Hindustan Aeronautics Limited"),
    ("ADANIPORTS", "NSE", "Adani Ports and Special Economic Zone Limited"),
    ("BPCL", "NSE", "Bharat Petroleum Corporation Limited"),
    ("DLF", "NSE", "DLF Limited"),
    ("CESC", "NSE", "CESC Limited"),
    ("TPG", "NASDAQ", "TPG Inc. - Class A Common Stock"),
    ("CHSCL", "NASDAQ", "CHS Inc - Class B Cumulative Redeemable Preferred Stock, Series 4"),
    ("MBNKO", "NASDAQ", "Medallion Bank - Fixed-Rate Reset Non-Cumulative Perpetual Preferred Stock, Series F"),
    ("PFBC", "NASDAQ", "Preferred Bank - Common Stock"),
    ("F", "NYSE", "Ford Motor Company Common Stock"),
    ("HDB", "NYSE", "HDFC Bank Limited Common Stock"),
    ("HAL", "NYSE", "Halliburton Company Common Stock"),
    ("RS", "NYSE", "Reliance, Inc. Common Stock"),
    ("GOOG", "NASDAQ", "Alphabet Inc. - Class C Capital Stock"),
    ("GOOGL", "NASDAQ", "Alphabet Inc. - Class A Common Stock"),
    ("GOOGM", "NASDAQ", "Alphabet Inc. - Depositary Shares representing a 1/20th Interest"),
    ("BA", "NYSE", "Boeing Company (The) Common Stock"),
    ("BA$A", "NYSE", "Boeing Company (The) Depositary Shares"),
] + [(f"{m}{n}", m, f"Padding {m} {n} Limited") for m in ("NSE", "NASDAQ", "NYSE") for n in range(1000)]
LISTED = build_master(ROWS)


def org(name: str, role: str = "affected", kind: str = "company") -> dict:
    return {"name": name, "type": kind, "role": role}


def test_listed_names_fold_to_how_articles_write_them():
    assert company_key("Sun Pharmaceutical Industries Limited") == "sun pharmaceutical industries"
    assert company_key("Boeing Company (The) Common Stock") == "boeing"
    assert company_key("JP Morgan Chase & Co. Common Stock") == "jp morgan chase"
    assert company_key("Alphabet Inc. - Class A Common Stock") == "alphabet"
    assert company_key("GAIL (India) Limited") == "gail"
    assert company_key("Nestlé India Ltd.") == "nestle india"


def test_a_real_listing_the_article_never_names_is_dropped():
    """F on the US–China summit: Ford is a listing, and not in the story."""
    got = choose_tickers(LISTED, ["F"], "US and China fail to reach strategic stability at state summit",
                         "Leaders met in Beijing on Saturday.", [org("White House", kind="government")], "politics")
    assert got == []


def test_a_company_the_headline_names_keeps_its_ticker():
    got = choose_tickers(LISTED, ["SUNPHARMA"], "TNPCB tells NGT no expansion at Sun Pharmaceutical unit", "", [], "business")
    assert got == ["SUNPHARMA"]


def test_a_company_named_only_deep_in_the_body_does_not():
    """Six banks' economists quoted in an RBI preview are named, but the preview
    is not about them."""
    body = "Economists expect a 25 basis point hike. " * 40 + "State Bank of India economists agreed."
    assert choose_tickers(LISTED, ["SBIN"], "Most economists see RBI raising rates", body, [], "finance") == []


def test_a_quoted_source_is_not_the_company():
    body = "Economists expect a hike. " * 40
    ents = [org("State Bank of India", role="source_cited")]
    assert choose_tickers(LISTED, ["SBIN"], "Most economists see RBI raising rates", body, ents, "finance") == []


def test_an_indian_language_article_is_named_by_its_english_organisations():
    """The extractor writes organisations in English; the Kannada text never says
    'Sun Pharma' in Latin letters."""
    got = choose_tickers(LISTED, ["SUNPHARMA"], "ಷೇರುಪೇಟೆ ಸೂಚ್ಯಂಕ", "ಸನ್ ಫಾರ್ಮಾ ಷೇರು ಮೌಲ್ಯ ಕುಸಿದಿದೆ", [org("Sun Pharma")], "business")
    assert got == ["SUNPHARMA"]


def test_a_unit_of_the_company_names_it():
    """The Kochi refinery IS Bharat Petroleum; the land story names only the unit."""
    ents = [org("Bharat Petroleum Corporation Limited-Kochi Refinery")]
    assert choose_tickers(LISTED, ["BPCL"], "LSGD allocates ₹16 crore for land acquisition", "", ents, "politics") == ["BPCL"]


def test_what_articles_call_a_company_counts_as_naming_it():
    assert choose_tickers(LISTED, ["SBIN"], "SBI raises ATM charges from October 1", "", [], "finance") == ["SBIN"]
    assert choose_tickers(LISTED, ["GOOGL"], "EU fines Google 403 million euros", "", [], "technology") == ["GOOGL"]


def test_the_indian_listing_stands_for_the_company():
    """HDB is HDFC Bank's NYSE receipt; the linker gives HDFCBANK, so the two must
    not become two rows for one bank."""
    assert choose_tickers(LISTED, ["HDB"], "HDFC Bank Q1 profit rises", "", [], "business") == ["HDFCBANK"]


# --- the linker --------------------------------------------------------------


def test_a_business_article_naming_a_listed_company_gets_its_ticker():
    ents = [org("Hindustan Unilever"), org("Adani Ports and Special Economic Zone Ltd")]
    assert choose_tickers(LISTED, [], "FMCG makers raise prices", "", ents, "business") == ["HINDUNILVR", "ADANIPORTS"]


def test_the_linker_reads_business_and_finance_only():
    assert choose_tickers(LISTED, [], "Heatwave", "", [org("Hindustan Unilever")], "politics") == []


def test_a_group_a_venue_or_a_fragment_is_never_linked():
    """"Reliance" is Reliance, Inc. on NYSE by exact name; "BSE" is where a share
    lists, not the story; "Sun" and "State Bank" name no listing exactly."""
    ents = [org("Reliance"), org("BSE", kind="organization"), org("Sun"), org("State Bank"), org("India", kind="organization")]
    assert choose_tickers(LISTED, [], "Stock to list today on BSE", "", ents, "business") == []


def test_a_quoted_source_is_never_linked():
    assert choose_tickers(LISTED, [], "Gold outlook", "", [org("State Bank of India", role="source_cited")], "finance") == []


def test_a_us_listing_that_shares_an_indian_symbol_is_not_linked():
    """HAL is Hindustan Aeronautics on NSE and Halliburton on NYSE; linked, the
    oil-services story would be shown as the Indian aircraft maker."""
    assert choose_tickers(LISTED, [], "Oilfield services slow", "", [org("Halliburton")], "business") == []
    assert choose_tickers(LISTED, [], "Engines for Tejas", "", [org("Hindustan Aeronautics Limited")], "business") == ["HAL"]


def test_a_three_letter_name_links_only_an_indian_listing():
    """DLF is the developer; in Indian news "TPG" and "CHS" are as often someone
    else (CHS was a Sharjah dairy's partner, linked to a US co-op's preferreds)."""
    ents = [org("DLF"), org("TPG"), org("CHS", kind="organization")]
    assert choose_tickers(LISTED, [], "Realty deal", "", ents, "business") == ["DLF"]


def test_a_company_listed_only_through_preference_shares_is_never_linked():
    """A reader cannot follow Medallion Bank's common stock: there is none. The
    rule reads the share class, so Preferred Bank's common stock still links."""
    ents = [org("Medallion Bank"), org("Preferred Bank")]
    assert choose_tickers(LISTED, [], "US lenders report", "", ents, "business") == ["PFBC"]


def test_a_company_links_to_its_common_share():
    """Not the preference line (BA$A), a depositary note (GOOGM) or the shorter
    non-voting class (GOOG): one company, the ticker readers follow."""
    ents = [org("Boeing"), org("Google")]
    assert choose_tickers(LISTED, [], "Boeing and Google sign a deal", "", ents, "business") == ["BA", "GOOGL"]


def test_a_name_two_indian_companies_share_is_never_linked():
    """"CESC" is CESC Limited, Kolkata's listed utility, and also Chamundeshwari
    Electricity Supply Corporation, Mysuru's state-owned discom, which Kannada
    papers name as CESC every week. The first prod revalidation linked the
    Mysuru one's grievance meetings to the Kolkata listing (2026-09-27)."""
    ents = [org("CESC", kind="organization")]
    assert choose_tickers(LISTED, [], "ವಿದ್ಯುತ್ ಗ್ರಾಹಕರ ಕುಂದುಕೊರತೆ: CESC ಸಭೆ", "", ents, "business") == []

