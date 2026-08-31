"""A fabricated ticker must not reach the database at all.

`tools/securities.py` measured the damage on production: of 128 distinct ticker
strings the extractor emitted, 82 are not listed on NSE — 138 of 201 mentions.
`HUL` is the sharpest case. Hindustan Unilever trades as HINDUNILVR; "HUL" is
what people call the company, and NSE's own equity list confirms it is absent.
It renders as an ordinary ticker chip, reaches nothing when followed, and never
matches a watchlist. Nothing in the product can notice that from the inside.

So the check belongs at the write, not at each of the five places a ticker is
later read. These tests pin the write path — including the reused-extraction
branch, which skips the model and would happily skip the check with it.
"""

import json
import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_engine, session_scope
from common.securities import EXPECTED_MARKETS, normalize, validated

pytestmark = pytest.mark.asyncio(loop_scope="session")

# Real listings, one per covered market. HUL is deliberately NOT among them —
# that is the fact under test, and it is NSE's own list that says so, with
# Nasdaq's and NYSE's agreeing.
SEED = [
    ("HINDUNILVR", "NSE", "INE030A01027", "Hindustan Unilever Limited"),
    ("UPL", "NSE", "INE628A01036", "UPL Limited"),
    ("META", "NASDAQ", None, "Meta Platforms, Inc. - Class A Common Stock"),
    ("A", "NYSE", None, "Agilent Technologies, Inc. Common Stock"),
]


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


@asynccontextmanager
async def master(markets: tuple[str, ...] = tuple(EXPECTED_MARKETS)):
    """A securities master that exists only for the duration of one test.

    Built inside a transaction that is ALWAYS rolled back, so the real master is
    never touched — it is reference data loaded from the exchange, not something
    a test may leave rows in.

    `markets` names which markets are padded to a plausible size, because SIZE
    PER MARKET is itself part of the contract: a market short of its floor is
    treated as unloaded and validation steps aside for everything. Pass a subset
    to get the half-loaded case, or `()` for the never-loaded one.
    """
    async with get_engine().connect() as conn:
        trans = await conn.begin()
        s = AsyncSession(bind=conn)
        await s.execute(text("DELETE FROM securities"))
        for market in markets:
            await s.execute(
                text("INSERT INTO securities (id, symbol, exchange, name) "
                     "SELECT gen_random_uuid(), :m || g, :m, 'padding' "
                     "FROM generate_series(1, :n) g"),
                {"m": market, "n": EXPECTED_MARKETS[market]},
            )
        for symbol, exchange, isin, name in SEED:
            await s.execute(
                text("INSERT INTO securities (id, isin, symbol, exchange, name, active) "
                     "VALUES (:i, :isin, :sym, :ex, :n, true)"),
                {"i": str(uuid.uuid4()), "isin": isin, "sym": symbol,
                 "ex": exchange, "n": name},
            )
        try:
            yield s
        finally:
            await trans.rollback()


# --- the invented symbol ------------------------------------------------------


async def test_a_symbol_no_security_carries_is_refused():
    """HUL is the measured case: the company is real, the ticker is not."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with master() as s:
        assert await validated(s, ["HUL"]) == []


async def test_the_real_symbol_beside_it_survives():
    """The failure runs both ways. Dropping HINDUNILVR to be safe would empty the
    markets lens of exactly the tickers that are worth showing."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with master() as s:
        assert await validated(s, ["HUL", "HINDUNILVR"]) == ["HINDUNILVR"]


async def test_an_index_is_not_a_security():
    """`^NSENIFTY` and `^BSESENSEX` came out of the extractor as tickers. They are
    indices — nothing to follow, nothing to hold, and not in an equity master."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with master() as s:
        assert await validated(s, ["^NSENIFTY", "^BSESENSEX"]) == []


async def test_the_yahoo_suffix_is_a_spelling_not_a_different_security():
    """`UPL.NS` is Yahoo Finance's notation for an NSE listing — the extractor
    reproduced its data provider's formatting. The security underneath is real,
    so refusing it would report a genuine listing as invented."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with master() as s:
        assert await validated(s, ["UPL.NS"]) == ["UPL"]


async def test_case_and_spacing_do_not_decide_whether_a_ticker_is_real():
    if not await _db_reachable():
        pytest.skip("no database")
    async with master() as s:
        assert await validated(s, ["  hindunilvr "]) == ["HINDUNILVR"]


async def test_one_security_named_twice_is_stored_once():
    """`UPL` and `UPL.NS` in one extraction are one company. Two entries would
    double it in the watchlist join and in the digest's mover count."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with master() as s:
        assert await validated(s, ["UPL", "UPL.NS", "upl"]) == ["UPL"]


async def test_normalize_leaves_an_ordinary_symbol_alone():
    assert normalize("INFY") == "INFY" and normalize("") == ""


# --- the configuration mistake that would look like a clean result ------------


async def test_an_unloaded_master_passes_tickers_through_instead_of_blanking_them():
    """Absence of evidence must not trigger an action — the rule this repo has
    been burned by four times.

    If `securities` has never been loaded, every ticker fails membership and the
    markets lens goes silently empty while the pipeline reports success. That
    reads as "the extractor found no tickers", which is the one conclusion the
    data cannot support. An unloaded master means we cannot check.
    """
    if not await _db_reachable():
        pytest.skip("no database")
    async with master(markets=()) as s:
        await s.execute(text("DELETE FROM securities"))
        assert await validated(s, ["HUL", "HINDUNILVR"]) == ["HINDUNILVR", "HUL"]


async def test_a_half_loaded_master_is_not_treated_as_an_answer():
    """The dangerous middle. A partial master passes an is-it-empty check and then
    reports every genuine ticker it is missing as invented.

    Not hypothetical: a dry run of `tools.securities --clean` against a master
    holding 2 rows proposed dropping NHPC, a real NSE listing. Note that
    HINDUNILVR IS present here — so a size check made only after an empty result
    would never fire, and HUL beside it would look adjudicated rather than
    unchecked.
    """
    if not await _db_reachable():
        pytest.skip("no database")
    async with master(markets=()) as s:
        assert await validated(s, ["HUL", "HINDUNILVR"]) == ["HINDUNILVR", "HUL"]


async def test_one_market_missing_stops_the_whole_check():
    """The failure the US master introduced. A US-only load holds ~11,000 rows and
    clears any TOTAL floor — and then reports every genuine NSE ticker as invented,
    because none of them are there. HINDUNILVR is real; with NSE unloaded the only
    honest answer is that we cannot say."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with master(markets=("NASDAQ", "NYSE")) as s:
        # HUL is in NO master and META is in one that IS loaded. Judging would
        # return just META; the honest answer with NSE missing is that we cannot
        # judge at all, so both come back. Asserting on a pair where one symbol
        # is absent is what makes the two outcomes distinguishable — an earlier
        # version of this test used two symbols that were both present, so a
        # total-row floor passed it while leaving the bug in place.
        assert await validated(s, ["HUL", "META"]) == ["HUL", "META"]


async def test_a_us_listing_validates_once_its_market_is_loaded():
    """META, NVDA, GOOGL, MSFT, AAPL and AMZN were the six most-shown unverified
    symbols in production. All six are genuine Nasdaq listings, so cleaning
    against NSE alone would have deleted 41 correct mentions."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with master() as s:
        assert await validated(s, ["META", "HUL", "A"]) == ["META", "A"]


# --- the whole write path, including the branch that skips the model ----------


async def test_a_fabricated_ticker_never_lands_in_lens_fields(monkeypatch):
    """End to end through `handle_classified_item`, on the REUSED-extraction path.

    That branch exists to avoid paying for the same URL twice, and it hands back a
    stored extraction without calling the model. A check wired into the model call
    would be skipped here entirely — and this is the path 534 production URL
    groups take.
    """
    if not await _db_reachable():
        pytest.skip("no database")

    import common.securities as cs
    import enrichment.consumer as ec

    # This test is about the WIRING — that the consumer routes tickers through the
    # check at all. The per-market floor has its own tests above, and the real
    # master lives in the committed database this consumer opens its own sessions
    # against, so it cannot be staged in a rolled-back transaction here. Claiming
    # no markets makes the floor vacuously satisfied without weakening it.
    monkeypatch.setattr(cs, "EXPECTED_MARKETS", {})

    async def _no_embeddings(chunks):
        return [[0.0] * 768 for _ in chunks]

    async def _no_publish(*_a, **_k):
        return None

    monkeypatch.setattr(ec, "embed_texts", _no_embeddings)
    monkeypatch.setattr(ec.stream, "publish", _no_publish)

    tag = uuid.uuid4().hex[:8]
    url = f"https://example.test/{tag}/markets"
    extraction = {
        "shared": {"event_type": "other", "headline_summary": "A markets story."},
        "finance": {"tickers": ["HUL", "HINDUNILVR", "^NSENIFTY"], "sector": "fmcg"},
    }
    made: list[tuple] = []
    try:
        async with session_scope() as s:
            made.append(await _seed_prior_enrichment(s, url, extraction))
            await _seed_security(s, "HINDUNILVR")
            second = await _seed_raw_item(s, url)
        made.append(second)

        await ec.handle_classified_item({"raw_item_id": str(second[1])})

        async with session_scope() as s:
            row = (
                await s.execute(
                    text(
                        "SELECT e.lens_fields, e.raw_model_output FROM enrichments e "
                        "JOIN articles a ON a.id = e.article_id WHERE a.raw_item_id = :r"
                    ),
                    {"r": str(second[1])},
                )
            ).mappings().one()

        stored = row["lens_fields"]["finance"]["tickers"]
        assert stored == ["HINDUNILVR"], f"an unvalidated ticker was stored: {stored}"
        assert row["lens_fields"]["finance"]["sector"] == "fmcg", "the rest of the lens is intact"
        # Provenance: what the model actually said is still on the row, so a
        # dropped symbol stays auditable rather than being erased from history.
        assert "HUL" in row["raw_model_output"]["finance"]["tickers"]
    finally:
        await _cleanup(made)


async def _seed_security(s, symbol: str) -> None:
    """Committed, because the consumer opens its own session. Reference data: a
    real NSE listing, so leaving it is correct and re-running is a no-op."""
    await s.execute(
        text("INSERT INTO securities (id, symbol, exchange, name, series, active) "
             "VALUES (:i, :sym, 'NSE', :sym, 'EQ', true) "
             "ON CONFLICT (exchange, symbol) DO NOTHING"),
        {"i": str(uuid.uuid4()), "sym": symbol},
    )


async def _seed_prior_enrichment(s, url: str, extraction: dict) -> tuple:
    sid, rid, aid, eid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await s.execute(
        text("INSERT INTO sources (id,slug,name,source_type) VALUES (:i,:s,:s,'rss')"),
        {"i": str(sid), "s": f"tick-{sid.hex[:6]}"},
    )
    await s.execute(
        text("INSERT INTO raw_items (id,source_id,external_id,url,title,raw,relevance) "
             "VALUES (:i,:s,:e,:u,'t','{}'::jsonb,'relevant')"),
        {"i": str(rid), "s": str(sid), "e": f"ext-{rid.hex[:8]}", "u": url},
    )
    await s.execute(
        text("INSERT INTO articles (id,raw_item_id,clean_text,retrieval_tier,word_count) "
             "VALUES (:i,:r,'the body','body',2)"),
        {"i": str(aid), "r": str(rid)},
    )
    await s.execute(
        text("INSERT INTO enrichments (id,article_id,model,raw_model_output) "
             "VALUES (:i,:a,'ollama:test',CAST(:p AS jsonb))"),
        {"i": str(eid), "a": str(aid), "p": json.dumps(extraction)},
    )
    return sid, rid, aid, eid


async def _seed_raw_item(s, url: str) -> tuple:
    """A second feed carrying the same URL — the reuse path's entry condition."""
    sid, rid = uuid.uuid4(), uuid.uuid4()
    await s.execute(
        text("INSERT INTO sources (id,slug,name,source_type) VALUES (:i,:s,:s,'rss')"),
        {"i": str(sid), "s": f"tick2-{sid.hex[:6]}"},
    )
    await s.execute(
        text(
            "INSERT INTO raw_items "
            "  (id,source_id,external_id,url,title,raw,relevance,classification) "
            "VALUES (:i,:s,:e,:u,'t','{}'::jsonb,'relevant',CAST(:c AS jsonb))"
        ),
        {"i": str(rid), "s": str(sid), "e": f"ext-{rid.hex[:8]}", "u": url,
         "c": json.dumps({"sector": "finance"})},
    )
    return sid, rid, None, None


async def _cleanup(made) -> None:
    async with session_scope() as s:
        for sid, rid, _aid, _eid in made:
            await s.execute(
                text("DELETE FROM field_provenance WHERE enrichment_id IN "
                     "(SELECT e.id FROM enrichments e JOIN articles a ON a.id = e.article_id "
                     " WHERE a.raw_item_id = :r)"),
                {"r": str(rid)},
            )
            await s.execute(
                text("DELETE FROM article_chunks WHERE article_id IN "
                     "(SELECT id FROM articles WHERE raw_item_id = :r)"),
                {"r": str(rid)},
            )
            await s.execute(
                text("DELETE FROM enrichments WHERE article_id IN "
                     "(SELECT id FROM articles WHERE raw_item_id = :r)"),
                {"r": str(rid)},
            )
            await s.execute(text("DELETE FROM articles WHERE raw_item_id = :r"), {"r": str(rid)})
            await s.execute(text("DELETE FROM raw_items WHERE id = :i"), {"i": str(rid)})
            await s.execute(text("DELETE FROM sources WHERE id = :i"), {"i": str(sid)})
