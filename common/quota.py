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


async def remaining_samples(session: AsyncSession, user_id: UUID) -> int:
    """Current sample count for display (the meter). 0 if no row."""
    value = (
        await session.execute(
            text("SELECT remaining FROM usage_quota WHERE user_id = :uid"),
            {"uid": str(user_id)},
        )
    ).scalar_one_or_none()
    return value or 0
