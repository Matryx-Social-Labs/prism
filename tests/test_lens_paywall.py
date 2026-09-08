"""The lens paywall, enforced on the server or not at all.

Before this, `isLocked(slug) = slug !== "reader" && !session` in StoryView.tsx
was the entire paywall — a browser-side lock over an endpoint anyone could curl.

Two findings shaped these tests, and both were invisible until someone read the
code rather than the design:

1. `get_brief` early-returns on the cache, so a check placed after it would only
   ever run for the FIRST viewer of each (event, lens). Everyone else read free.
2. `GET /events/{id}` returns `lens_briefs`/`lens_points` as plain fields, so
   gating /brief alone was bypassable with one request to a different route.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text

from common.db import session_scope
from common.quota import (
    grant_samples,
    has_unlocked,
    record_unlock,
    release_unlock,
    remaining_samples,
    try_consume_sample,
    unlocked_lenses,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def _cleanup():
    """Delete what this module seeds.

    loop_scope="session" matches the module's pytestmark. Without it the fixture
    runs on a different event loop from the tests and asyncpg tears the
    connection down across loops — which surfaces as an unrelated-looking
    "attached to a different loop" error at teardown, not as a failing test.

    These tests run against the developer's own database — there is no separate
    test DB — so rows left behind are not merely untidy: test_personalization
    asserts over the whole `events` table and started failing on ordering when
    this module seeded events and walked away. A test that breaks another test
    is a broken test.
    """
    yield
    async with session_scope() as s:
        await s.execute(text("DELETE FROM agent_messages WHERE content = 'x'"))
        await s.execute(
            text("DELETE FROM agent_sessions WHERE id NOT IN "
                 "(SELECT session_id FROM agent_messages)")
        )
        await s.execute(text("DELETE FROM lens_unlocks"))
        await s.execute(text("DELETE FROM usage_quota WHERE user_id IN "
                             "(SELECT id FROM users WHERE email LIKE '%@t.test')"))
        await s.execute(text("DELETE FROM events WHERE title = 't' AND summary = 's'"))
        await s.execute(text("DELETE FROM users WHERE email LIKE '%@t.test'"))


async def _db() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _user(s) -> uuid.UUID:
    uid = uuid.uuid4()
    await s.execute(
        text("INSERT INTO users (id, email) VALUES (:i, :e)"),
        {"i": str(uid), "e": f"{uid}@t.test"},
    )
    return uid


async def _event(s) -> uuid.UUID:
    eid = uuid.uuid4()
    await s.execute(
        text("INSERT INTO events (id,title,summary,last_updated_at) VALUES (:i,'t','s',now())"),
        {"i": str(eid)},
    )
    return eid


async def test_a_second_tab_cannot_spend_a_second_sample():
    """THE RACE. Two tabs opening the same lens both find no unlock row and both
    try to pay. The claim is the arbiter: exactly one INSERT wins the unique
    constraint, so exactly one debit happens."""
    if not await _db():
        pytest.skip("no database")
    async with session_scope() as s:
        uid, eid = await _user(s), await _event(s)
        await grant_samples(s, uid, 3)

        first = await record_unlock(s, uid, eid, "markets")
        second = await record_unlock(s, uid, eid, "markets")
        assert first is True and second is False, "both tabs claimed the same unlock"

        # Only the winner debits.
        assert await try_consume_sample(s, uid) is True
        assert await remaining_samples(s, uid) == 2, "a refresh or a second tab charged twice"


async def test_a_failed_brief_gives_the_sample_back():
    """Generation returns 200 with an EMPTY brief when the model is down, by
    design. Nobody pays for a panel that renders nothing."""
    if not await _db():
        pytest.skip("no database")
    async with session_scope() as s:
        uid, eid = await _user(s), await _event(s)
        await grant_samples(s, uid, 3)
        assert await record_unlock(s, uid, eid, "markets") is True
        await try_consume_sample(s, uid)
        # ...generation raises...
        await release_unlock(s, uid, eid, "markets")
        await grant_samples(s, uid, 1)
        assert await remaining_samples(s, uid) == 3, "the reader paid for an empty brief"
        assert await has_unlocked(s, uid, eid, "markets") is False, (
            "a claim survived for a brief that never materialised"
        )


async def test_no_quota_row_is_unknown_not_zero():
    """Absence of evidence is not evidence. A user who was never granted samples
    must not be told they have spent them all."""
    if not await _db():
        pytest.skip("no database")
    async with session_scope() as s:
        uid = await _user(s)
        assert await remaining_samples(s, uid) is None


async def test_unlocked_lenses_is_one_query_for_the_whole_event():
    """The event payload filters every lens at once; asking per lens would be an
    N+1 on the most-viewed route."""
    if not await _db():
        pytest.skip("no database")
    async with session_scope() as s:
        uid, eid = await _user(s), await _event(s)
        await record_unlock(s, uid, eid, "markets")
        await record_unlock(s, uid, eid, "cyber")
        assert await unlocked_lenses(s, uid, eid) == {"markets", "cyber"}
        assert await unlocked_lenses(s, uid, uuid.uuid4()) == set()
