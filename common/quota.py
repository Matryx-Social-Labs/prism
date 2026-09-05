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
