"""Ask is the only endpoint whose cost scales with USERS, and it had no limit.

A lens brief is generated once and cached for every reader. A question runs
retrieval plus generation, every time, for whoever asks. It was unlimited and
unauthenticated — one script overnight is the entire remaining budget.

The cap must not become a login wall. Anonymous reading is the product's funnel,
so anonymous gets a small per-session allowance and hitting it prompts sign-in.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text

from common.db import session_scope
from common.quota import (
    ANON_ASK_PER_SESSION,
    USER_ASK_PER_DAY,
    ask_allowance,
    ask_questions_used,
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


async def _session_with(s, user_ref, n_user_msgs, n_assistant_msgs=0):
    eid = uuid.uuid4()
    await s.execute(
        text("INSERT INTO events (id,title,summary,last_updated_at) VALUES (:i,'t','s',now())"),
        {"i": str(eid)},
    )
    sid = uuid.uuid4()
    await s.execute(
        text("INSERT INTO agent_sessions (id, event_id, user_ref) VALUES (:i,:e,:u)"),
        {"i": str(sid), "e": str(eid), "u": user_ref},
    )
    for role, n in (("user", n_user_msgs), ("assistant", n_assistant_msgs)):
        for _ in range(n):
            await s.execute(
                text(
                    "INSERT INTO agent_messages (id, session_id, role, content) "
                    "VALUES (gen_random_uuid(), :s, :r, 'x')"
                ),
                {"s": str(sid), "r": role},
            )
    return sid


async def test_assistant_replies_do_not_count_against_the_cap():
    """A completed turn writes TWO rows. Counting both halves every cap and makes
    the model's own replies look like user activity."""
    if not await _db():
        pytest.skip("no database")
    async with session_scope() as s:
        sid = await _session_with(s, None, n_user_msgs=2, n_assistant_msgs=2)
        assert await ask_questions_used(s, None, sid) == 2


async def test_an_anonymous_session_is_capped_but_not_walled():
    if not await _db():
        pytest.skip("no database")
    async with session_scope() as s:
        sid = await _session_with(s, None, n_user_msgs=ANON_ASK_PER_SESSION - 1)
        allowed, used, cap = await ask_allowance(s, None, sid)
        assert allowed is True and cap == ANON_ASK_PER_SESSION

        sid2 = await _session_with(s, None, n_user_msgs=ANON_ASK_PER_SESSION)
        allowed, used, cap = await ask_allowance(s, None, sid2)
        assert allowed is False and used == ANON_ASK_PER_SESSION


async def test_a_signed_in_reader_gets_the_larger_daily_window():
    if not await _db():
        pytest.skip("no database")
    async with session_scope() as s:
        ref = str(uuid.uuid4())
        await _session_with(s, ref, n_user_msgs=ANON_ASK_PER_SESSION + 1)
        sid = await _session_with(s, ref, n_user_msgs=0)
        allowed, used, cap = await ask_allowance(s, ref, sid)
        # Counted ACROSS the account's sessions, not per session.
        assert cap == USER_ASK_PER_DAY
        assert used == ANON_ASK_PER_SESSION + 1
        assert allowed is True


async def test_an_accounts_questions_are_counted_across_its_sessions():
    """Otherwise a new session per question resets the allowance, which is the
    same bypass the anonymous cap accepts and a signed-in cap must not."""
    if not await _db():
        pytest.skip("no database")
    async with session_scope() as s:
        ref = str(uuid.uuid4())
        for _ in range(3):
            await _session_with(s, ref, n_user_msgs=2)
        sid = await _session_with(s, ref, n_user_msgs=0)
        assert await ask_questions_used(s, ref, sid) == 6


async def test_one_readers_questions_never_count_against_another():
    if not await _db():
        pytest.skip("no database")
    async with session_scope() as s:
        a, b = str(uuid.uuid4()), str(uuid.uuid4())
        await _session_with(s, a, n_user_msgs=5)
        sid_b = await _session_with(s, b, n_user_msgs=0)
        assert await ask_questions_used(s, b, sid_b) == 0


async def test_signing_in_mid_conversation_adopts_the_anonymous_session():
    """REGRESSION (quota bypass): ensure_session resumed on (session_id, event_id)
    with no ownership check, so a reader who signed in kept writing into a
    NULL-user_ref session and their questions stayed uncounted against the
    account. Triggering it required no effort — just signing in mid-chat.
    """
    if not await _db():
        pytest.skip("no database")
    from agent.rag import ensure_session

    async with session_scope() as s:
        sid = await _session_with(s, None, n_user_msgs=2)
        eid = (
            await s.execute(
                text("SELECT event_id FROM agent_sessions WHERE id = :i"), {"i": str(sid)}
            )
        ).scalar_one()

    ref = str(uuid.uuid4())
    await ensure_session(eid, sid, user_ref=ref)

    async with session_scope() as s:
        owner = (
            await s.execute(
                text("SELECT user_ref FROM agent_sessions WHERE id = :i"), {"i": str(sid)}
            )
        ).scalar_one()
        assert owner == ref, "the session stayed anonymous after sign-in"
        # And the questions asked while anonymous now count against the account.
        assert await ask_questions_used(s, ref, sid) == 2


async def test_a_session_already_owned_is_never_reassigned():
    """Adoption claims an UNOWNED session once. Transferring one that already has
    an owner would let a second reader inherit someone else's conversation."""
    if not await _db():
        pytest.skip("no database")
    from agent.rag import ensure_session

    first = str(uuid.uuid4())
    async with session_scope() as s:
        sid = await _session_with(s, first, n_user_msgs=1)
        eid = (
            await s.execute(
                text("SELECT event_id FROM agent_sessions WHERE id = :i"), {"i": str(sid)}
            )
        ).scalar_one()

    await ensure_session(eid, sid, user_ref=str(uuid.uuid4()))

    async with session_scope() as s:
        owner = (
            await s.execute(
                text("SELECT user_ref FROM agent_sessions WHERE id = :i"), {"i": str(sid)}
            )
        ).scalar_one()
        assert owner == first, "an owned session was transferred to another reader"
