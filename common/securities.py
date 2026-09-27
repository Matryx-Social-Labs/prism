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
import time
import unicodedata
from dataclasses import dataclass

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

# What articles call a company that its listed name does not say → the listed
# name, both as `company_key` writes them. Hand-listed from the organisations
# production articles name, like common/entity_aliases.py and for the same
# reason: an initialism is ambiguous, and a wrong link puts a company on a
# story it is not in. Add one only after seeing it name that company in real
# coverage.
ALIASES: dict[str, str] = {
    "airtel": "bharti airtel",
    "amazon": "amazon com",
    "amazon web services": "amazon com",
    "amd": "advanced micro devices",
    "apollo hospitals": "apollo hospitals enterprise",
    "aws": "amazon com",
    "bel": "bharat electronics",
    "bhel": "bharat heavy electricals",
    "bpcl": "bharat petroleum",
    "citi": "citigroup",
    "dr reddy s": "dr reddy s laboratories",
    "goldman sachs": "goldman sachs group",
    "google": "alphabet",
    "hal": "hindustan aeronautics",
    "hcl tech": "hcl technologies",
    "hcltech": "hcl technologies",
    "hdfc life": "hdfc life insurance",
    "hpcl": "hindustan petroleum",
    "hsbc": "hsbc holdings",
    "hul": "hindustan unilever",
    "ibm": "international business machines",
    "indianoil": "indian oil",
    "indigo": "interglobe aviation",
    "jpmorgan": "jp morgan chase",
    "kalyan jewellers": "kalyan jewellers india",
    "klarna": "klarna group",
    "l and t": "larsen and toubro",
    "lenskart": "lenskart solutions",
    "lic": "life insurance corporation of india",
    "m and m": "mahindra and mahindra",
    "maruti": "maruti suzuki india",
    "maruti suzuki": "maruti suzuki india",
    "meta": "meta platforms",
    "nykaa": "fsn e commerce ventures",
    "ola electric": "ola electric mobility",
    "ongc": "oil and natural gas",
    "paytm": "one 97 communications",
    "policybazaar": "pb fintech",
    "sail": "steel authority of india",
    "sbi": "state bank of india",
    "sun pharma": "sun pharmaceutical industries",
    "tcs": "tata consultancy services",
    "turtlemint": "turtlemint fintech solutions",
    "uber": "uber technologies",
    "united airlines": "united airlines holdings",
    "warner bros": "warner bros discovery",
    "youtube": "alphabet",
    "zomato": "eternal",
}
# Listed names the linker must never read as the company, because in the news
# they are something else first: the venue a share trades on (BSE, NSE, MCX,
# Nasdaq), the agency whose rating or index is quoted (Moody's, CRISIL), a
# group rather than its listing ("Reliance" is Reliance, Inc. on NYSE; "Fortis"
# is a Canadian utility; "Tata Motors" is two listings since the demerger), a
# namesake ("EQT" the Swedish investor is not EQT Corporation; "Dow" is the
# index), or a plain word ("People", "Urban"). All seen linked wrongly on
# production.
AMBIGUOUS = frozenset({
    "bse", "nse", "national stock exchange of india", "multi commodity exchange of india", "nasdaq", "cme group",
    "intercontinental exchange", "indian energy exchange", "moody s", "s and p global",
    "msci", "crisil", "icra", "reliance", "fortis", "tata motors", "people", "urban", "ats",
    "dow", "eqt",
})


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


# ── Does the article name the company? ───────────────────────────────────────
# A symbol existing is not a symbol belonging: F (Ford) was stored on a US–China
# summit and TSM on a Japanese earthquake. So a ticker is kept only when the
# article names its company, and a company a business article names exactly
# gets its ticker even when the extractor gave none (the linker) — the
# extractor gave one on 13.7% of business and finance events.
#
# WHAT THIS DOES NOT FIX. The audit's other examples (2026-09-27) ARE named in
# their articles: CVX as the sponsor of a student water project, JPM and GS
# through their CEOs at a dinner, PFE as a counterfeited brand. Whether a
# named company is what a story is about is a judgement no name rule makes.

# What a listing's name carries that an article's never does: the share class
# ("Class A Common Stock", "American Depositary Shares", all after " - ") and
# the legal form ("Limited", "Inc.", "Corporation", "(The)").
_SHARE_CLASS = re.compile(
    r"\s+-\s.*$|\s+(?:class\s+[a-z]\s+)?(?:new\s+)?"
    r"(?:common stock|common shares|capital stock|ordinary shares?|american depositary shares?)\b.*$",
    re.IGNORECASE,
)
# "and" only ever trails from "& Co." ("JP Morgan Chase & Co.").
_LEGAL_FORM = frozenset({"limited", "ltd", "inc", "incorporated", "corporation", "corp", "company", "co", "plc", "llc", "the", "and"})
# Words an article drops from a listed name ("Uber" for Uber Technologies,
# "Goldman Sachs" for Goldman Sachs Group). The name check only; the linker
# matches the whole name.
_DESCRIPTOR = frozenset({"industries", "technologies", "technology", "platforms", "holdings", "group", "enterprises", "international"})
# The exchanges a ticker is shown on, India first (BSE is not loaded yet).
EXCHANGE_ORDER = ("NSE", "BSE", "NASDAQ", "NYSE")


def fold(text: str) -> str:
    """Lowercase words, accents off ('Nestlé'), '&' as 'and', punctuation as
    space: how names are compared."""
    text = unicodedata.normalize("NFKD", (text or "").lower().replace("&", " and "))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def company_key(name: str) -> str:
    """A listed name as an article writes it: 'Sun Pharmaceutical Industries
    Limited' → 'sun pharmaceutical industries'; 'Boeing Company (The) Common
    Stock' → 'boeing'; 'GAIL (India) Limited' → 'gail'."""
    words = fold(_SHARE_CLASS.sub("", name or "").replace("(India)", "")).split()
    while words and words[-1] in _LEGAL_FORM:
        words.pop()
    while words and words[0] == "the":
        words.pop(0)
    return " ".join(words)


def _short_key(key: str) -> str:
    words = key.split()
    while len(words) > 1 and words[-1] in _DESCRIPTOR:
        words.pop()
    return " ".join(words)


def _has_words(needle: str, hay: str) -> bool:
    return bool(needle) and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", hay) is not None


def names_company(symbol: str, name: str, text: str, entity_keys: list[str]) -> bool:
    """Does an article (its `fold`ed headline and opening, and the `company_key`s
    of the organisations extracted from it) name this listing?

    Three ways, each measured on the production tickers it must keep:
    - the name, less its legal form and descriptor words, in the text ("Uber");
    - an organisation that IS the name, its start ("Adani Ports" for Adani
      Ports and Special Economic Zone; "Sun Pharma" for Sun Pharmaceutical
      Industries, compared without spaces from six letters up, so "Tata" is never
      Tata Motors) or a unit of it ("Bharat Petroleum Corporation Limited-Kochi
      Refinery"), or the symbol itself ("TCS", "ONGC");
    - a curated alias (ALIASES), in the text or as an organisation.
    Indian-language articles are covered by the organisations, which the
    extractor writes in English.
    """
    key = company_key(name)
    if _has_words(_short_key(key), text):
        return True
    squashed = key.replace(" ", "")
    for ek in entity_keys:
        e = ek.replace(" ", "")
        if ek == key or key.startswith(ek + " ") or ek.startswith(key + " ") or e == symbol.lower() or (len(e) >= 6 and squashed.startswith(e)):
            return True
    return any(_has_words(a, text) or a in entity_keys for a, k in ALIASES.items() if k == key)


# The organisations the linker reads: companies and organisations, never a
# source the article quotes ("Goldman Sachs analysts said") — named, but not
# what the story is about. 1,444 of 10,711 in three weeks of business news.
_LINKABLE = frozenset({"company", "organization"})


def link_keys(entities: list[dict]) -> list[str]:
    """The listed names an article's organisations ARE, exactly, aliases resolved.
    Exact on purpose: the linker's precision gate is 0.95, and "Sun", "India",
    "State Bank" and "Reliance" name no listing exactly."""
    out: list[str] = []
    for e in entities:
        if e.get("type") not in _LINKABLE or e.get("role") == "source_cited":
            continue
        k = company_key(e.get("name") or "")
        k = ALIASES.get(k, k)
        if k and k not in AMBIGUOUS and k not in out:
            out.append(k)
    return out


@dataclass(frozen=True)
class Listing:
    symbol: str
    exchange: str
    name: str


@dataclass(frozen=True)
class Master:
    by_symbol: dict[str, list[Listing]]  # every listing, India first
    by_key: dict[str, Listing]  # the one listing a name links to
    short: bool  # a market below its floor: nothing can be judged


_master: tuple[float, Master] | None = None
MASTER_TTL_S = 3600  # the master changes when someone runs `tools.securities --load`
# Lines a name never links to: preference shares, notes, warrants, units,
# rights, funds. A company listed only through one (Medallion Bank's
# preferreds) is not a listed company to a reader. Worded as the share class,
# not the company: Preferred Bank's common stock is a company.
_NOT_SHARES = re.compile(
    r"preferred (?:stock|shares?|securities)|\bwarrants?\b|\bunits?\b|\brights?\b|\bnotes? due\b|debenture|\betf\b|closed end fund|%",
    re.IGNORECASE,
)


def _link_rank(item: Listing) -> tuple:
    # India first; then the common share over a preference line (BA$A), a
    # depositary note (GOOGM) or a non-voting class (GOOG); then the shortest.
    plain = item.exchange == "NSE" or re.search(r"common|ordinary", item.name, re.IGNORECASE)
    return (EXCHANGE_ORDER.index(item.exchange), not plain, len(item.symbol), item.symbol)


async def master(session: AsyncSession) -> Master:
    """The shown exchanges' listings, indexed by symbol and by name. One query an
    hour: 11k rows, and the names are folded once rather than per article."""
    global _master
    now = time.monotonic()
    if _master and now - _master[0] < MASTER_TTL_S:
        return _master[1]
    rows = await session.execute(sa_text("SELECT symbol, exchange, name FROM securities"))
    _master = (now, build_master(rows))
    return _master[1]


def build_master(rows) -> Master:
    """(symbol, exchange, name) rows → the two indexes. Split from `master` so the
    linker's evaluation can run on an exported master. Only the exchanges a
    ticker is shown on: an ETF on NYSE Arca names no company."""
    by_symbol: dict[str, list[Listing]] = {}
    by_key: dict[str, list[Listing]] = {}
    held: dict[str, int] = {}
    for symbol, exchange, name in rows:
        held[exchange] = held.get(exchange, 0) + 1
        if exchange not in EXCHANGE_ORDER:
            continue
        item = Listing(symbol, exchange, name)
        by_symbol.setdefault(symbol, []).append(item)
        if not _NOT_SHARES.search(name):
            by_key.setdefault(company_key(name), []).append(item)
    for items in by_symbol.values():
        items.sort(key=lambda i: EXCHANGE_ORDER.index(i.exchange))
    short = any(held.get(m, 0) < floor for m, floor in EXPECTED_MARKETS.items())
    return Master(by_symbol, {k: min(v, key=_link_rank) for k, v in by_key.items() if k}, short)


def reset_master() -> None:
    """Tests seed the master mid-run; the process cache would pin the old one."""
    global _master
    _master = None


async def article_tickers(
    session: AsyncSession, tickers: list[str], title: str, text: str, entities: list[dict], sector: str | None
) -> list[str]:
    """The tickers an article carries: the extractor's, if listed AND named by
    the article; then, for business and finance, every listed company its
    organisations name exactly (`link_keys`)."""
    kept = await validated(session, tickers)
    listed = await master(session)
    if listed.short:
        return kept  # validated() has said why, loudly; nothing here can be judged
    return choose_tickers(listed, kept, title, text, entities, sector)


# "Named" means in the headline or the opening (about two paragraphs), or as an
# organisation the article is about. Deeper in, a listing is mostly incidental:
# the six banks whose economists an RBI preview quotes, the Tata companies a
# Tata Sons explainer lists. Measured on 1,437 stored ticker mentions, reading
# the whole text kept 39 more, almost all of that kind.
LEDE_CHARS = 600


def choose_tickers(
    listed: Master, tickers: list[str], title: str, text: str, entities: list[dict], sector: str | None
) -> list[str]:
    lede = fold(f"{title} {(text or '')[:LEDE_CHARS]}")
    keys = [
        company_key(e.get("name") or "")
        for e in entities
        if e.get("type") not in ("person", "place") and e.get("role") != "source_cited"
    ]
    out: list[str] = []
    for t in tickers:
        named = next((i for i in listed.by_symbol.get(t, []) if names_company(t, i.name, lede, keys)), None)
        if named:
            # One company, one ticker, India's listing first — the one the linker
            # would give: HDB (the NYSE receipt) is HDFCBANK, and the "Pfizer Ltd"
            # of a Karnataka licence story is PFIZER, not PFE.
            symbol = listed.by_key.get(company_key(named.name), named).symbol
            if symbol not in out:
                out.append(symbol)
    if sector in ("business", "finance"):
        out += [s for s in linked(listed, entities) if s not in out]
    return out


def linked(listed: Master, entities: list[dict]) -> list[str]:
    out: list[str] = []
    for k in link_keys(entities):
        item = listed.by_key.get(k)
        if not item or item.symbol in out:
            continue
        # A US listing whose symbol an Indian one also uses (HAL is Hindustan
        # Aeronautics on NSE, Halliburton on NYSE) would be shown as the Indian
        # company, so it is not linked.
        if listed.by_symbol[item.symbol][0] != item:
            continue
        # Three letters name an Indian company in Indian news (DLF, UPL, ITC);
        # abroad they were EQT the Swedish investor and CHS in Sharjah. US
        # initialisms link through ALIASES ("ibm") or not at all.
        if len(k) <= 3 and item.exchange != "NSE":
            continue
        out.append(item.symbol)
    return out
