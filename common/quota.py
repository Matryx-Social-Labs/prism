"""Per-account pro-lens sample quota (freemium D4/D13).

The cost model rests on this: a free user gets a small, fixed number of
Markets-lens samples. If the cap could be bypassed or double-spent, on-demand
LLM generation goes unbounded again — the exact hole the paywall exists to close.

So the decrement is ONE atomic statement — ``UPDATE ... WHERE remaining > 0
RETURNING`` — not a read-then-write. Two concurrent viewers of the same
event+lens (two tabs, two replicas) race on the same row; Postgres serializes
the row-level UPDATEs, so at most `remaining` of them succeed. No app-side lock,
no read-modify-write window.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def try_consume_sample(session: AsyncSession, user_id: UUID) -> bool:
    """Atomically consume one sample.

    Returns True if a sample was available and consumed, False if the cap is
    exhausted (or the user has no quota row). Never raises on exhaustion — the
    caller shows the unlock screen on False.
    """
    remaining = (
        await session.execute(
            text(
                "UPDATE usage_quota "
                "SET remaining = remaining - 1, updated_at = now() "
                "WHERE user_id = :uid AND remaining > 0 "
                "RETURNING remaining"
            ),
            {"uid": str(user_id)},
        )
    ).scalar_one_or_none()
    return remaining is not None


async def grant_samples(session: AsyncSession, user_id: UUID, count: int) -> None:
    """Create or top up a user's sample allowance (idempotent upsert on user_id)."""
    await session.execute(
        text(
            "INSERT INTO usage_quota (id, user_id, remaining) "
            "VALUES (gen_random_uuid(), :uid, :n) "
            "ON CONFLICT (user_id) "
            "DO UPDATE SET remaining = usage_quota.remaining + :n, updated_at = now()"
        ),
        {"uid": str(user_id), "n": count},
    )


async def remaining_samples(session: AsyncSession, user_id: UUID) -> int | None:
    """Current sample count for display (the meter). None when there is NO ROW.

    None is not zero. A user with no quota row has never been granted samples —
    which is a different fact from having spent them all, and the 402 body says
    so rather than telling a never-granted account it is out. Absence of
    evidence must not read as evidence, which is the rule this repo keeps
    relearning (see content_similarity, backlog(), verify_claims).
    """
    return (
        await session.execute(
            text("SELECT remaining FROM usage_quota WHERE user_id = :uid"),
            {"uid": str(user_id)},
        )
    ).scalar_one_or_none()


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

    Claim BEFORE debiting, so the debit can be tied to the winner: the pair
    (claim, debit) is then at-most-once per reader per lens even under
    concurrency, without an application lock.
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
    """Undo a claim that never delivered a brief.

    Generation returns 200 with an EMPTY brief when the model is unavailable
    (api/routes/events.py — "never a 500"). A reader must not lose a sample for
    a panel that renders nothing, so the claim is rolled back and no debit
    happens. Without this the claim would persist and permanently mark an
    unlock the reader never received.
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


def _ip_key(ip: str) -> str:
    import hashlib

    return hashlib.sha256(ip.encode()).hexdigest()[:24]


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
            ip_key = f"prism:ask:ip:{_ip_key(ip)}:{day}"
            m = await r.incr(ip_key)
            if m == 1:
                await r.expire(ip_key, 60 * 60 * 26)
            if m > ANON_ASK_PER_IP_PER_DAY:
                return "ip"
        spent = float(await r.get(f"prism:ask:spend:{day}") or 0.0)
        if spent >= ASK_DAILY_CEILING_USD or (anonymous and spent >= 0.8 * ASK_DAILY_CEILING_USD):
            return "ceiling"
    except Exception:  # noqa: BLE001 — a limiter that is down must not take Ask down with it
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
    except Exception:  # noqa: BLE001
        return None
