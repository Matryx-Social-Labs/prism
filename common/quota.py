"""What a reader may spend: professional lens reads and Ask questions.

Lens reads are metered like Ask (founder decision, 2026-09-27): a read is one
professional lens opened on one story, and once opened it stays open for that
reader on that story, so a refresh or a second tab costs nothing. An account's
meter is COUNTED from its own lens_unlocks rows (a rolling day), the way Ask
counts agent_messages, so it cannot drift from the record of what was opened
and giving a read back is deleting the row. It replaced a lifetime counter of
three samples (usage_quota), which is no longer read or written.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.logging import get_logger

logger = get_logger(__name__)

READER_LENS = "reader"


async def has_unlocked(session: AsyncSession, user_id: UUID, event_id: UUID, lens: str) -> bool:
    """Whether this reader has already paid to open this lens on this story."""
    return (
        await session.execute(
            text(
                "SELECT 1 FROM lens_unlocks "
                "WHERE user_id = :uid AND event_id = :eid AND lens = :lens"
            ),
            {"uid": str(user_id), "eid": str(event_id), "lens": lens},
        )
    ).scalar_one_or_none() is not None


async def record_unlock(session: AsyncSession, user_id: UUID, event_id: UUID, lens: str) -> bool:
    """Claim the unlock. True if THIS caller claimed it, False if it already existed.

    ON CONFLICT DO NOTHING, and the return value is the whole point: two tabs
    unlocking the same lens race on the unique constraint, and exactly one of
    them gets True. The loser reads as "already unlocked" rather than as an
    integrity error surfacing to a reader as a 500.

    The claim IS the read: the meter counts these rows, so a claim that lost
    the race spends nothing.
    """
    return (
        await session.execute(
            text(
                "INSERT INTO lens_unlocks (id, user_id, event_id, lens) "
                "VALUES (gen_random_uuid(), :uid, :eid, :lens) "
                "ON CONFLICT (user_id, event_id, lens) DO NOTHING "
                "RETURNING id"
            ),
            {"uid": str(user_id), "eid": str(event_id), "lens": lens},
        )
    ).scalar_one_or_none() is not None


async def release_unlock(session: AsyncSession, user_id: UUID, event_id: UUID, lens: str) -> None:
    """Give back a read that never delivered a brief.

    Generation returns 200 with an EMPTY brief when the model is unavailable or
    writes nothing (api/routes/events.py — "never a 500"). A reader must not
    lose a read for a panel that renders nothing, and the meter counts these
    rows, so deleting the claim is the refund. Idempotent: two tabs failing on
    the same lens give back one read, not two.
    """
    await session.execute(
        text(
            "DELETE FROM lens_unlocks "
            "WHERE user_id = :uid AND event_id = :eid AND lens = :lens"
        ),
        {"uid": str(user_id), "eid": str(event_id), "lens": lens},
    )


async def unlocked_lenses(session: AsyncSession, user_id: UUID, event_id: UUID) -> set[str]:
    """Every lens this reader has opened on this story.

    One query for the whole event rather than one per lens: the event payload
    filters all lenses at once, and N round trips on the most-viewed route to
    answer a set-membership question is the shape of a needless N+1.
    """
    rows = (
        await session.execute(
            text("SELECT lens FROM lens_unlocks WHERE user_id = :uid AND event_id = :eid"),
            {"uid": str(user_id), "eid": str(event_id)},
        )
    ).scalars().all()
    return set(rows)


# Lens reads. Anonymous readers get a few per browser session (a random id the
# page keeps in sessionStorage) with a per-address ceiling only a script
# reaches, as Ask does; a free account gets USER_LENS_PER_DAY in any rolling
# day; Plus reads every lens (api/routes/events._on_plus). Most reads are cache
# hits (the worker writes every lens a story offers), so this meter is the
# product's line between free and Plus, not a cost brake.
ANON_LENS_PER_SESSION = 3
USER_LENS_PER_DAY = 10
ANON_LENS_PER_IP_PER_DAY = 60
ANON_LENS_TTL_S = 60 * 60 * 24  # an idle anonymous session's reads are forgotten after a day


# ponytail: count-after-claim, so N simultaneous first opens of N different
# stories by one account can pass the cap by N-1. Only a script does that;
# serialise per account (an advisory lock) if it ever shows up.
async def lens_reads_today(session: AsyncSession, user_id: UUID) -> int:
    """Lenses this account opened in the last day, counted from its unlocks."""
    return (
        await session.execute(
            text(
                "SELECT count(*) FROM lens_unlocks "
                "WHERE user_id = :uid AND created_at > now() - interval '1 day'"
            ),
            {"uid": str(user_id)},
        )
    ).scalar_one()


async def _anon_keys(r, reader: str, ip: str | None) -> tuple[str, str | None]:
    from datetime import UTC, datetime

    from common.usage import day_salt

    day = datetime.now(UTC).strftime("%Y%m%d")
    ip_key = f"prism:lens:ip:{_ip_key(ip, await day_salt(r, f'ask-{day}'))}:{day}" if ip else None
    return f"prism:lens:anon:{reader}", ip_key


async def anon_lens_open(reader: str, ip: str | None, event_id: UUID, lens: str) -> tuple[bool, int]:
    """Open a lens on a story for an anonymous browser session: (allowed, reads
    this session has used). Add first, then count, so a re-open is free and two
    tabs racing for the last read cannot both have it. The address set holds
    stories, not sessions: a fresh session id per request still meets it.
    Redis unreachable → allowed, as Ask; the read is a cached brief."""
    from common.stream import get_redis

    member = f"{event_id}:{lens}"
    try:
        r = get_redis()
        key, ip_key = await _anon_keys(r, reader, ip)
        if not await r.sadd(key, member):
            return True, await r.scard(key)
        await r.expire(key, ANON_LENS_TTL_S)
        used = await r.scard(key)
        over = used > ANON_LENS_PER_SESSION
        if not over and ip_key:
            await r.sadd(ip_key, member)
            await r.expire(ip_key, 60 * 60 * 26)
            over = await r.scard(ip_key) > ANON_LENS_PER_IP_PER_DAY
            if over:
                await r.srem(ip_key, member)
        if over:
            await r.srem(key, member)
            return False, used - 1
        return True, used
    except Exception as exc:  # noqa: BLE001 — a meter that is down must not take the lens down with it
        logger.warning("lens_meter_check_failed", error_type=type(exc).__name__, error=str(exc)[:200])
        return True, 0


async def anon_lens_release(reader: str, ip: str | None, event_id: UUID, lens: str) -> None:
    """Give an anonymous read back (the brief came out empty)."""
    from common.stream import get_redis

    try:
        r = get_redis()
        key, ip_key = await _anon_keys(r, reader, ip)
        await r.srem(key, f"{event_id}:{lens}")
        if ip_key:
            await r.srem(ip_key, f"{event_id}:{lens}")
    except Exception as exc:  # noqa: BLE001 — the read stays spent; say so
        logger.warning("lens_meter_release_failed", error_type=type(exc).__name__, error=str(exc)[:200])


# Ask spend guardrails.
#
# Ask is the only endpoint whose cost scales with USERS rather than with corpus
# size: a lens brief is generated once and cached for everyone, but every
# question runs retrieval plus generation. It was unlimited and unauthenticated.
#
# ANONYMOUS ASK STAYS OPEN. A login wall on the most engaging thing the product
# does would cost the free funnel, so anonymous readers get a small per-session
# allowance and hitting it prompts sign-in — which converts rather than blocks.
# Not an IP cap: carrier-grade NAT in India puts thousands of real readers behind
# one address, so an IP limit throttles exactly the audience we want.
ANON_ASK_PER_SESSION = 3
USER_ASK_PER_DAY = 10  # free account; Plus gets PLUS_ASK_PER_DAY (BUSINESS-MODEL.md §3)
PLUS_ASK_PER_DAY = 100
# A per-address ceiling only a script reaches. Carrier-grade NAT can put a
# building behind one address, so this is deliberately far above what any
# group of humans asks anonymously in a day — it exists because an anonymous
# session costs nothing to mint, so the session cap alone is no cap.
ANON_ASK_PER_IP_PER_DAY = 60
# Burst: questions per minute for one identity (account, or anonymous session).
ASK_PER_MINUTE = 6
# Estimated cost of one answer, by the model the plan gets (common/billing);
# summed per day in Redis against the global ceiling below.
ASK_COST_USD = {"free": 0.0005, "plus": 0.003}
ASK_DAILY_CEILING_USD = 25.0  # at 80% anonymous Ask closes; at 100% free too; Plus continues


async def ask_questions_used(
    session: AsyncSession, user_ref: str | None, session_id: UUID
) -> int:
    """Questions already asked — by this account today, or by this anonymous session.

    Counted from `agent_messages` rather than a counter table, so the meter is
    derived from the record of the questions themselves and cannot drift from
    it. `role = 'user'` is load-bearing: a completed turn writes two rows, so
    counting all of them would halve every cap.

    KNOWN LIMIT, worth stating rather than hiding: messages persist only after a
    turn completes or is refused, so a failed or aborted generation spends money
    and leaves nothing to count. This is an accurate USAGE meter and an
    under-counting SPEND meter. Bounding actual spend needs the provider's own
    accounting, not ours.
    """
    if user_ref:
        sql = (
            "SELECT count(*) FROM agent_messages m "
            "JOIN agent_sessions s ON s.id = m.session_id "
            "WHERE s.user_ref = :ref AND m.role = 'user' "
            "AND m.created_at > now() - interval '1 day'"
        )
        params = {"ref": user_ref}
    else:
        # Anonymous: scoped to the one session, which is all the identity there
        # is. Clearing cookies resets it — accepted, since the alternative is an
        # IP cap that punishes shared connections.
        sql = (
            "SELECT count(*) FROM agent_messages "
            "WHERE session_id = :sid AND role = 'user'"
        )
        params = {"sid": str(session_id)}
    return (await session.execute(text(sql), params)).scalar_one() or 0


async def ask_allowance(
    session: AsyncSession, user_ref: str | None, session_id: UUID, plan: str = "free"
) -> tuple[bool, int, int]:
    """(allowed, used, cap) for the next question, by plan."""
    cap = (PLUS_ASK_PER_DAY if plan == "plus" else USER_ASK_PER_DAY) if user_ref else ANON_ASK_PER_SESSION
    used = await ask_questions_used(session, user_ref, session_id)
    return used < cap, used, cap


def _ip_key(ip: str, salt: str) -> str:
    """The address, hashed with a salt that changes daily and is deleted within
    two days (common/usage.day_salt). Unsalted, sha256 of an IPv4 address is
    reversible by trying all four billion — which made the privacy policy's
    "cannot be turned back into your address" untrue (admin dashboard review,
    2026-09-23)."""
    import hashlib

    return hashlib.sha256(f"{salt}|{ip}".encode()).hexdigest()[:24]


async def ask_burst_ok(identity: str, ip: str | None, anonymous: bool) -> str | None:
    """The Redis-side checks before a question runs. Returns None when the
    question may proceed, else a short reason: 'burst' (too many this minute),
    'ip' (anonymous per-address ceiling), 'ceiling' (the day's spend ceiling).
    Redis unreachable → allow: the account/session caps above still hold."""
    from datetime import UTC, datetime

    from common.stream import get_redis

    try:
        r = get_redis()
        day = datetime.now(UTC).strftime("%Y%m%d")
        minute = datetime.now(UTC).strftime("%Y%m%d%H%M")
        burst_key = f"prism:ask:burst:{identity}:{minute}"
        n = await r.incr(burst_key)
        if n == 1:
            await r.expire(burst_key, 120)
        if n > ASK_PER_MINUTE:
            return "burst"
        if anonymous and ip:
            from common.usage import day_salt

            ip_key = f"prism:ask:ip:{_ip_key(ip, await day_salt(r, f'ask-{day}'))}:{day}"
            m = await r.incr(ip_key)
            if m == 1:
                await r.expire(ip_key, 60 * 60 * 26)
            if m > ANON_ASK_PER_IP_PER_DAY:
                return "ip"
        spent = float(await r.get(f"prism:ask:spend:{day}") or 0.0)
        if spent >= ASK_DAILY_CEILING_USD or (anonymous and spent >= 0.8 * ASK_DAILY_CEILING_USD):
            return "ceiling"
    except Exception as exc:  # noqa: BLE001 — a limiter that is down must not take Ask down with it
        logger.warning("ask_throttle_check_failed", error_type=type(exc).__name__, error=str(exc)[:200])
        return None
    return None


async def ask_record_spend(plan: str) -> None:
    """Add one answer's estimated cost to today's total (see ASK_COST_USD)."""
    from datetime import UTC, datetime

    from common.stream import get_redis

    try:
        r = get_redis()
        day = datetime.now(UTC).strftime("%Y%m%d")
        key = f"prism:ask:spend:{day}"
        await r.incrbyfloat(key, ASK_COST_USD.get(plan, ASK_COST_USD["plus"]))
        await r.expire(key, 60 * 60 * 26)
    except Exception as exc:  # noqa: BLE001 — spend goes unrecorded, not Ask undelivered; but say so
        logger.warning("ask_spend_record_failed", error_type=type(exc).__name__, error=str(exc)[:200])
        return None
