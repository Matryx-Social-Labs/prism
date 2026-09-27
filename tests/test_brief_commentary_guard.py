"""A brief that talks about its input is dropped, never stored or served.

Production 2026-09-27: the Markets brief of "Journalist Biography Profile" read
"…no listed-company or policy announcement in the provided text", and a Reader
brief opened "The provided article text describes the professional background of
a journalist". A brief naming what the reports leave open ("the reports do not
yet say whether…") is the product working and must survive.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import correlation.briefs as briefs
from common.db import session_scope
from correlation.schemas import LensBriefs

pytestmark = pytest.mark.asyncio(loop_scope="session")

META = ("These stories carry no direct market catalyst: they are regional law-and-order items with no "
        "listed-company or policy announcement in the provided text.")
NEWS = ("An avalanche struck the base camp of Himlung Himal in Nepal, leaving ten people missing. "
        "The reports do not yet say whether search operations are under way.")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _event() -> uuid.UUID:
    eid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO events (id,title,summary,sector,last_updated_at,projection) "
                             "VALUES (:i,'Avalanche at Himlung base camp','Ten missing.','world',now(),'{}'::jsonb)"),
                        {"i": str(eid)})
    return eid


async def _stored(eid) -> dict:
    async with session_scope() as s:
        proj = (await s.execute(text("SELECT projection FROM events WHERE id = :i"), {"i": str(eid)})).scalar_one()
    return proj.get("lens_briefs") or {}


async def _drop(eid):
    async with session_scope() as s:
        await s.execute(text("DELETE FROM events WHERE id = :i"), {"i": str(eid)})


async def test_persist_drops_a_commentary_brief_and_keeps_the_news():
    if not await _db_reachable():
        pytest.skip("no database")
    eid = await _event()
    try:
        await briefs.persist_briefs(eid, {"markets": {"text": META, "points": ["x"]},
                                          "reader": {"text": NEWS, "points": []}})
        assert await _stored(eid) == {"reader": NEWS}
    finally:
        await _drop(eid)


async def test_a_generated_commentary_brief_is_never_returned(monkeypatch):
    """The API serves what generate_briefs returns before persisting it, so the
    drop has to happen here too, not only at the store."""
    if not await _db_reachable():
        pytest.skip("no database")
    eid = await _event()

    async def _chat(**kw):
        return LensBriefs.model_validate({"reader": {"text": NEWS}, "markets": {"text": META}})

    monkeypatch.setattr(briefs, "structured_chat", _chat)
    try:
        out = await briefs.generate_briefs(eid, ["reader", "markets"])
        assert set(out) == {"reader"}
    finally:
        await _drop(eid)
