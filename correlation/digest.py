"""Market Pulse — the day's ticker board (founder decision 1, 2026-09-27).

Which listed companies and market-wide forces did the last 24 hours of
business and finance reporting name, what happened, and why would a markets
reader notice? Rows are counted and sourced: a company from the tickers the
record carries (common/securities.py decides those), what happened from the
record's Prism headline and catalyst, "Prism's reading" and "why notice" from
the impact the analysis wrote for THAT company, else the record's own. No
prices exist anywhere in Prism, so none are shown.

It replaced an essay the model wrote over the 12 most recently touched business
events, with no time window; on the day it was audited it named one ticker.
The model now writes at most three lines, from the rows alone, and a line with
a number the rows do not print is dropped.

Built at most once per TTL and cached in Redis (single-flight across replicas):
a stale board is served at once while one refresh runs behind the reader.
"""

import asyncio
import contextlib
import json
import re
import time
from datetime import UTC, datetime, timedelta

from pydantic import AliasChoices, BaseModel, Field, field_validator
from sqlalchemy import text

from common import outlets
from common.config import get_settings
from common.db import session_scope
from common.llm import REASONING_OFF, structured_chat
from common.locks import single_flight
from common.logging import get_logger
from common.observability import fetch_prompt
from common.securities import Master, company_key, fold, master, names_company
from common.stream import get_redis

logger = get_logger(__name__)

# A new key: the old one holds an essay, which is not a board.
CACHE_KEY = "digest:markets:board"
CACHE_TTL = 30 * 60  # a board of the last 24 hours, not a daily edition
# Kept this long after it goes stale, so the reader who arrives after expiry gets
# the last board at once while one refresh runs behind them. Regenerating the
# essay inside that reader's request took 27 s (2026-09-27).
STALE_TTL = 24 * 60 * 60
_refreshing: set[asyncio.Task] = set()  # held so a running refresh is not garbage-collected

WINDOW = timedelta(hours=24)
MARKET_SECTORS = ("business", "finance")
MARKET_WIDE_ROWS = 12
READ_LINES = 3
READ_LINE_CHARS = 240

# A record with no company is market-wide when its catalyst is a rule or a rate,
# or its headline names a force that moves every listed company: the central
# bank and the regulators, tax and duty, a strike, the rupee, the indices.
# Headlines are Prism's own, in English.
MARKET_WIDE_CATALYSTS = frozenset({"regulatory_action", "rate_decision"})
_MARKET_WIDE = re.compile(
    r"\b(?:RBI|repo|MPC|SEBI|IRDAI|GST|tax (?:cuts?|hikes?|rates?|slabs?|regime|reforms?|rules?)|"
    r"(?:import|export|customs|excise) dut(?:y|ies)|tariffs?|strike|UPI|MDR|forex|"
    r"rupee (?:falls|rises|slips|gains|weakens|strengthens|hits|ends|closes|opens|recovers)|"
    r"inflation|Sensex|Nifty|crude|bond yields?|FPIs?|FIIs?|fiscal|budget|monetary|interest rates?)\b",
    re.IGNORECASE,
)
# Beyond this many companies a record is about a sector or the market — the
# strike story that lists 22 banks, the export story that lists four scooter
# makers. Only the companies its headline names keep a row from it; with none,
# the record is market-wide. Measured on the first day's board: one record was
# 22 of 76 company rows.
MAX_COMPANIES = 3
# The extractor's labels are snake_case and lowercase; these read as words.
_ACRONYMS = frozenset({"upi", "mdr", "rbi", "sebi", "gst", "ipo", "ev", "ai", "us", "eu", "psu", "fdi", "fpi", "dgca", "faa", "nclt", "lpg", "cng"})
_READING = {"up": "positive", "positive": "positive", "down": "negative", "negative": "negative", "mixed": "mixed"}


def words(label: str | None) -> str | None:
    """'regulatory_action' → 'Regulatory action'; 'upi_mdr_boycott' → 'UPI MDR boycott'.
    'other' says nothing, so it is nothing."""
    first = (label or "").split(",")[0].strip().lower()
    if not first or first == "other":
        return None
    out = " ".join(w.upper() if w in _ACRONYMS else w for w in first.replace("_", " ").split())
    return out[:1].upper() + out[1:]


def display_name(name: str) -> str:
    """The listed name without its share class or legal form, in the exchange's
    own spelling: 'JP Morgan Chase & Co. Common Stock' → 'JP Morgan Chase'."""
    key_words = company_key(name).split()
    kept: list[str] = []
    for token in re.sub(r"\(the\)|^the\s+", "", name, flags=re.IGNORECASE).split():
        if len(fold(" ".join(kept + [token])).split()) > len(key_words):
            break
        kept.append(token)
    return " ".join(kept).rstrip(",.- ") or name


async def fetch_window(since: datetime) -> tuple[list, list, dict[str, str], Master]:
    """The rows the board is built from: business and finance records reported
    since `since`, the impacts on them, who publishes each feed, and the master."""
    async with session_scope() as s:
        events = (
            await s.execute(
                text(
                    """
                    SELECT e.id, e.title, e.sector, e.projection, e.last_updated_at
                    FROM events e
                    WHERE e.sector IN ('business', 'finance')
                      AND e.merged_into IS NULL
                      AND e.last_updated_at >= :since
                      AND COALESCE((e.projection ->> 'latest_published_at')::timestamptz, e.last_updated_at) >= :since
                    """
                ),
                {"since": since},
            )
        ).mappings().all()
        impacts = (
            await s.execute(
                text(
                    """
                    SELECT i.event_id, COALESCE(en.name, i.provenance ->> 'entity_name') AS entity,
                           i.effect, i.direction, i.confidence
                    FROM impacts i LEFT JOIN entities en ON en.id = i.entity_id
                    WHERE i.event_id = ANY(CAST(:ids AS uuid[]))
                    """
                ),
                {"ids": [str(e["id"]) for e in events]},
            )
        ).mappings().all()
        publishers = {slug: o.publisher for slug, o in (await outlets.registry(s)).items()}
        listed = await master(s)
    return list(events), list(impacts), publishers, listed


def _record(e, publishers: dict[str, str]) -> dict:
    p = e["projection"] or {}
    fin = p.get("finance") or {}
    pubs = {publishers.get(s, s) for s in p.get("source_slugs") or [] if s not in outlets.RAW_RECORD_FEEDS}
    return {
        "id": str(e["id"]),
        "headline": e["title"],
        "catalyst": words(fin.get("catalyst")),
        "outlets": len(pubs) or 1,
        "single_source": len(pubs) <= 1,
        "published_at": p.get("latest_published_at") or e["last_updated_at"].isoformat(),
        "_publishers": pubs,
        "_point": next(iter((p.get("lens_points") or {}).get("reader") or []), None),
    }


def _reading(direction: str | None, confidence: float | None) -> dict:
    reading = _READING.get((direction or "").lower())
    return {"reading": reading, "confidence": round(confidence, 2) if reading and confidence is not None else None}


def _order(row: dict) -> tuple:
    # Most-corroborated first (outlets, by masthead), then the newest report.
    return (-row["outlets"], -datetime.fromisoformat(row["published_at"]).timestamp())


def assemble(events, impacts, publishers: dict[str, str], listed: Master, since: datetime, now: datetime) -> dict:
    """The board, from the window's rows. Pure, so every rule is testable."""
    impacts_of: dict[str, list] = {}
    for i in impacts:
        impacts_of.setdefault(str(i["event_id"]), []).append(i)
    best: dict[str, dict] = {}  # one row per company: its most-corroborated record
    market_wide: list[dict] = []
    for e in events:
        rec = _record(e, publishers)
        fin = (e["projection"] or {}).get("finance") or {}
        price = fin.get("price_impact") or {}
        on_record = impacts_of.get(rec["id"], [])
        named = [(t, listed.by_symbol[t][0]) for t in fin.get("tickers") or [] if t in listed.by_symbol]
        shown = named
        if len(named) > MAX_COMPANIES:
            headline = fold(rec["headline"] or "")
            shown = [(t, i) for t, i in named if names_company(t, i.name, headline, [])]
        for symbol, listing in shown:
            mine = [
                i for i in on_record
                if i["entity"] and names_company(symbol, listing.name, fold(i["entity"]), [company_key(i["entity"])])
            ]
            impact = max(mine, key=lambda i: i["confidence"] or 0, default=None)
            only = len(named) == 1  # the record's own read and point speak for its only company
            if impact:
                reading, why = _reading(impact["direction"], impact["confidence"]), words(impact["effect"])
            elif only:
                reading, why = _reading(price.get("direction"), price.get("confidence")), rec["_point"]
            else:
                reading, why = _reading(None, None), None
            row = {**rec, "symbol": symbol, "exchange": listing.exchange, "company": display_name(listing.name),
                   **reading, "why": why}
            key = company_key(listing.name)
            if key not in best or _order(row) < _order(best[key]):
                best[key] = row
        wide = len(named) > MAX_COMPANIES or fin.get("catalyst") in MARKET_WIDE_CATALYSTS or _MARKET_WIDE.search(rec["headline"] or "")
        if not shown and wide:
            top = max(on_record, key=lambda i: i["confidence"] or 0, default=None)
            market_wide.append({**rec, **_reading(price.get("direction"), price.get("confidence")),
                                "why": words(top["effect"]) if top else rec["_point"]})
    companies = sorted(best.values(), key=_order)
    market_wide = sorted(market_wide, key=_order)[:MARKET_WIDE_ROWS]
    on_board = {r["id"]: r["_publishers"] for r in companies + market_wide}
    return {
        "window": {"start": since.isoformat(), "end": now.isoformat()},
        "counts": {
            "companies": len(companies),
            "stories": len(on_board),
            "outlets": len(set().union(*on_board.values())),
        },
        "companies": [{k: v for k, v in r.items() if not k.startswith("_")} for r in companies],
        "market_wide": [{k: v for k, v in r.items() if not k.startswith("_")} for r in market_wide],
    }


# ── The read: at most three lines, from the rows alone ─────────────────────────


class MarketReadLLM(BaseModel):
    lines: list[str] = Field(default_factory=list, validation_alias=AliasChoices("lines", "read", "points"))

    @field_validator("lines", mode="before")
    @classmethod
    def _one_string_is_lines(cls, v):
        return [ln for ln in v.splitlines() if ln.strip()] if isinstance(v, str) else v


def _rows_text(board: dict) -> str:
    lines = [
        " · ".join(str(x) for x in (r["symbol"], r["company"], r["headline"], r["catalyst"], r["reading"],
                                     f"{r['outlets']} outlets") if x)
        for r in board["companies"]
    ]
    lines += [
        " · ".join(str(x) for x in ("market-wide", r["headline"], r["catalyst"], f"{r['outlets']} outlets") if x)
        for r in board["market_wide"]
    ]
    return "\n".join(lines)


def grounded(lines: list[str], rows: str) -> list[str]:
    """At most three lines, and none with a number the rows do not print: the
    model may not invent a figure, and a reader cannot tell one that it did."""
    def numbers(s: str) -> set[str]:
        return {n.rstrip(".,") for n in re.findall(r"\d[\d.,]*", s)}

    held = numbers(rows)
    kept = [ln.strip() for ln in lines if ln.strip() and len(ln.strip()) <= READ_LINE_CHARS and numbers(ln) <= held]
    return kept[:READ_LINES]


async def _read(board: dict) -> list[str]:
    if not board["companies"] and not board["market_wide"]:
        return []  # an empty day is said plainly on the page; nothing to read
    rows = _rows_text(board)
    prompt = fetch_prompt("market-read")
    try:
        result = await structured_chat(
            model=get_settings().prism_model_correlate,
            messages=prompt.compile(rows=rows),
            output_model=MarketReadLLM,
            trace_name="market-read",
            max_tokens=400,
            reasoning=REASONING_OFF,
            metadata={"stage": "market-read", "rows": rows.count("\n") + 1},
            langfuse_prompt=prompt if prompt.version else None,
        )
    except Exception:
        # The read is optional; the board is the record. A failed call leaves
        # the board without it until the next refresh.
        logger.warning("market_read_unavailable", exc_info=True)
        return []
    kept = grounded(result.lines, rows)
    logger.info("market_read_generated", lines=len(kept), dropped=len(result.lines) - len(kept))
    return kept


async def _generate() -> dict:
    now = datetime.now(UTC)
    since = now - WINDOW
    board = assemble(*await fetch_window(since), since, now)
    return {**board, "read": await _read(board), "generated_at": now.isoformat()}


async def _store(redis, digest: dict) -> None:
    entry = {"digest": digest, "fresh_until": time.time() + CACHE_TTL}
    await redis.set(CACHE_KEY, json.dumps(entry), ex=STALE_TTL)


def _cached(raw: str) -> tuple[dict, float]:
    """(board, fresh_until)."""
    entry = json.loads(raw)
    return entry["digest"], entry["fresh_until"]


async def _refresh() -> None:
    """One refresh across requests and replicas. Never raises: it runs detached,
    and any failure (the database, or Redis on the lock) leaves the stale board."""
    lock = f"refresh:{CACHE_KEY}"
    try:
        redis = get_redis()
        if not await redis.set(lock, "1", nx=True, ex=120):
            return
    except Exception as exc:  # noqa: BLE001 — a background refresh must never surface
        logger.warning("digest_refresh_failed", stage="lock", error=str(exc)[:160])
        return
    try:
        digest = await _generate()
        if digest is not None:
            await _store(redis, digest)
    except Exception as exc:  # noqa: BLE001 — a background refresh must never surface; the stale board stands
        logger.warning("digest_refresh_failed", stage="generate", error=str(exc)[:160])
    finally:
        with contextlib.suppress(Exception):  # the lock's TTL reaps it, as in common/locks.single_flight
            await redis.delete(lock)


async def get_market_digest() -> dict | None:
    """Cached board. Stale is served at once and refreshed behind the reader;
    only an empty cache builds in the request, single-flighted across replicas."""
    redis = get_redis()
    cached = await redis.get(CACHE_KEY)
    if cached:
        digest, fresh_until = _cached(cached)
        if fresh_until < time.time():
            task = asyncio.create_task(_refresh())
            _refreshing.add(task)
            task.add_done_callback(_refreshing.discard)
        return digest

    async with single_flight(CACHE_KEY, ttl=60, wait_timeout=45.0) as leader:
        if not leader:
            cached = await redis.get(CACHE_KEY)
            if cached:
                return _cached(cached)[0]
        digest = await _generate()
        if digest is None:
            return None
        await _store(redis, digest)
        return digest
