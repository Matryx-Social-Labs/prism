"""Suggested questions must not answer the paid question.

`/questions` returns four static template strings per lens — product copy, not
paid content, and showing "Which tickers does this move?" to a free reader is
the pitch rather than a leak. Exactly one question is derived from story data:
question 1 of the cyber lens becomes "How is this being exploited in the wild?"
when `projection.cyber.exploitation.kev_listed` is set.

That one line was an oracle. `GET /events/{id}` filters `projection` to the
lenses a reader has unlocked; this route read the same field unfiltered, so
looping every event id with `?lens=cyber` and string-matching question 1 read
off the KEV set with no account at all.

Deliberately NOT gated, and worth stating so nobody "fixes" it later: the lens
fallback in `suggested_questions` reveals whether a story carries cyber or
finance fields. `EventDetail.available_lenses` already publishes exactly that,
computed from the UNFILTERED projection, because the locked lens still flips —
seeing what you are missing is the upgrade moment, not a leak.
"""

import inspect
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from agent.questions import suggested_questions

KEV = {"cyber": {"exploitation": {"kev_listed": True}}}
EXPLOITED = "How is this being exploited in the wild?"


def test_kev_question_is_withheld_from_a_reader_who_has_not_unlocked_cyber():
    assert EXPLOITED not in suggested_questions(KEV, "cyber")


def test_kev_question_is_served_to_a_reader_who_has():
    assert EXPLOITED in suggested_questions(KEV, "cyber", unlocked=True)


def test_the_default_fails_closed_and_cannot_be_passed_by_accident():
    """A caller that forgets the argument must leak nothing.

    The gate is worth little if omitting it is the insecure default — that is
    how the browser-only paywall happened. Keyword-only so a third positional
    argument can never drift into it.
    """
    param = inspect.signature(suggested_questions).parameters["unlocked"]
    assert param.default is False
    assert param.kind is inspect.Parameter.KEYWORD_ONLY


def test_a_non_kev_story_never_shows_it_either_way():
    plain = {"cyber": {"exploitation": {"kev_listed": False}}}
    assert EXPLOITED not in suggested_questions(plain, "cyber", unlocked=True)


@pytest.mark.asyncio(loop_scope="session")
async def test_THE_ROUTE_gates_it(monkeypatch):
    """The wiring, not the parts.

    Every assertion above passes with the route still calling
    `suggested_questions(projection, lens)` and ignoring the new argument
    entirely — the function would be correct and nothing would use it. Three
    tests in this repo have already shipped in exactly that shape, so this
    drives the real endpoint over HTTP.
    """
    import api.routes.events as events
    from api.main import app
    from common import auth

    uid = uuid.uuid4()
    eid = uuid.uuid4()

    async def resolve(db, token):
        return uid if token == "good" else None

    monkeypatch.setattr(auth, "resolve_session", resolve)

    class _R:
        def mappings(self):
            return self

        def first(self):
            return {"projection": KEV}

        def scalar_one_or_none(self):
            # has_unlocked: this reader HAS paid for cyber on this story.
            return 1

    class _S:
        async def execute(self, *a, **kw):
            return _R()

    async def fake_db():
        yield _S()

    app.dependency_overrides[events.get_db] = fake_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            anon = await c.get(f"/api/v1/events/{eid}/questions?lens=cyber")
            assert anon.status_code == 200
            assert EXPLOITED not in anon.json()["questions"], (
                "an anonymous caller read KEV status off the suggested questions; "
                "the projection is gated on /events/{id} and must be here too"
            )

            paid = await c.get(
                f"/api/v1/events/{eid}/questions?lens=cyber",
                headers={"Authorization": "Bearer good"},
            )
            assert paid.status_code == 200
            assert EXPLOITED in paid.json()["questions"], (
                "the reader who unlocked cyber lost the question they paid for"
            )
    finally:
        app.dependency_overrides.pop(events.get_db, None)
