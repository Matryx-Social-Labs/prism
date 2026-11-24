"""How long the pipeline's slow parts take, per UTC day — what /admin/pipeline reads.

The API and the worker are separate services sharing Redis, so the store is
Redis, shaped like common/spend: one hash per UTC day, `timings:<day>`. A
duration is counted into a fixed bucket (field `<name>|<upper bound ms>`, or
`|inf` past the last bound) and added to `<name>|sum`, so a mean is exact; a
counter is field `#<name>`. Fixed buckets keep a day's record a few dozen
integers whatever the traffic, at the price of exact quantiles: a p50 or p95
read back is the bucket's upper bound.

Recording never fails a call: a Redis error is logged and the call proceeds.
A day with no hash is `recorded: False`, never zero.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import math
import time
from bisect import bisect_left
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.logging import get_logger
from common.stream import get_redis

logger = get_logger(__name__)

KEEP_DAYS = 30
# The client has a connect timeout but no read timeout, and a write can run under
# the match lock: a stalled Redis must cost at most this, then be dropped.
WRITE_TIMEOUT_S = 1.0
# The admin page's read: a stalled Redis fails it (the endpoint shows `days: null`).
READ_TIMEOUT_S = 3.0
# Upper bounds in ms, roughly 1.5x apart: 1 ms to a day.
BUCKETS_MS = (
    1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500, 700, 1000, 1500, 2000, 3000, 5000, 7000,
    10000, 15000, 30000, 60000, 120000, 300000, 600000, 1800000, 3600000, 14400000, 86400000,
)
OVERFLOW = "inf"
SUM = "sum"
COUNTER = "#"


def _key(day: dt.date) -> str:
    return f"timings:{day.isoformat()}"


def _today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


def bucket(ms: float) -> str:
    """The smallest bound at or above `ms`, or the overflow bucket."""
    i = bisect_left(BUCKETS_MS, ms)
    return str(BUCKETS_MS[i]) if i < len(BUCKETS_MS) else OVERFLOW


def quantile(counts: dict[str, int], q: float) -> int | None:
    """The upper bound of the bucket holding quantile q: the true value is at most
    this and more than the bound below it. None when it falls in the overflow
    bucket (unknown, not large) or nothing was observed."""
    total = sum(counts.values())
    if not total:
        return None
    rank = max(1, math.ceil(q * total - 1e-9))
    seen = 0
    for bound in sorted(counts, key=lambda b: math.inf if b == OVERFLOW else int(b)):
        seen += counts[bound]
        if seen >= rank:
            return None if bound == OVERFLOW else int(bound)
    return None


async def _incr(field: str, n: int, total: tuple[str, float] | None = None) -> None:
    try:
        key = _key(_today())
        pipe = get_redis().pipeline(transaction=False)
        pipe.hincrby(key, field, n)
        if total is not None:
            pipe.hincrbyfloat(key, *total)
        pipe.expire(key, KEEP_DAYS * 86400)
        await asyncio.wait_for(pipe.execute(), WRITE_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 — observability never costs a call
        logger.warning("timing_record_failed", field=field, error=str(exc)[:160])


async def observe(name: str, ms: float) -> None:
    await _incr(f"{name}|{bucket(ms)}", 1, (f"{name}|{SUM}", ms))


async def count(name: str, n: int = 1) -> None:
    await _incr(COUNTER + name, n)


async def seen_before(key: str, ttl_s: int) -> bool:
    """Mark `key` seen for ttl_s and say whether it already was. Never raises:
    when Redis cannot answer, False (unknown is not a repeat)."""
    try:
        created = await asyncio.wait_for(get_redis().set(key, 1, nx=True, ex=ttl_s), WRITE_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 — observability never costs a call
        logger.warning("seen_before_failed", key=key, error=str(exc)[:160])
        return False
    return not created


@asynccontextmanager
async def timed(name: str) -> AsyncIterator[None]:
    """Observe the block's wall time under `name` however it ends; a TimeoutError
    also counts `<name>.timeout`, any other exception `<name>.error`. Exceptions
    pass through unchanged."""
    start = time.perf_counter()
    try:
        yield
    except TimeoutError:
        await count(f"{name}.timeout")
        raise
    except Exception:
        await count(f"{name}.error")
        raise
    finally:
        ms = (time.perf_counter() - start) * 1000
        logger.info("timed", name=name, ms=round(ms, 1))
        await observe(name, ms)


def _row(name: str, counts: dict[str, int], total: float | None) -> dict:
    """A timing's day. mean_ms is None for a day recorded before sums were."""
    n = sum(counts.values())
    return {"name": name, "n": n, "p50_ms": quantile(counts, 0.5), "p95_ms": quantile(counts, 0.95),
            "mean_ms": round(total / n, 1) if total is not None and n else None}


def _day(day: dt.date, h: dict[str, str]) -> dict:
    buckets: dict[str, dict[str, int]] = {}
    sums: dict[str, float] = {}
    counters = []
    for field, value in h.items():
        if field.startswith(COUNTER):
            counters.append({"name": field[len(COUNTER):], "n": int(value)})
            continue
        name, bound = field.rsplit("|", 1)
        if bound == SUM:
            sums[name] = float(value)
        else:
            buckets.setdefault(name, {})[bound] = int(value)
    rows = [_row(name, c, sums.get(name)) for name, c in buckets.items()]
    return {"day": day.isoformat(), "recorded": bool(h), "timings": sorted(rows, key=lambda r: r["name"]),
            "counters": sorted(counters, key=lambda r: r["name"])}


async def days(n: int, today: dt.date | None = None) -> list[dict]:
    """The last n UTC days, newest first: {day, recorded, timings, counters}.
    p50_ms/p95_ms are bucket upper bounds (see quantile); mean_ms is exact.
    Raises on any Redis error, a stall past READ_TIMEOUT_S included."""
    today = today or _today()
    wanted = [today - dt.timedelta(days=i) for i in range(n)]
    pipe = get_redis().pipeline(transaction=False)
    for d in wanted:
        pipe.hgetall(_key(d))
    raw = await asyncio.wait_for(pipe.execute(), READ_TIMEOUT_S)
    return [_day(d, h or {}) for d, h in zip(wanted, raw, strict=True)]
