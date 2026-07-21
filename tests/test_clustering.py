"""Cross-language clustering: the entity-overlap + looser-embedding match tier.

A translated retelling shares the key actors and is moderately (not near-dup)
similar. Verifies it matches on >=2 shared entities within the looser band, and
does NOT match on a single shared entity.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from correlation.clustering import find_event

pytestmark = pytest.mark.asyncio(loop_scope="session")

# 768-dim vectors with a controlled cosine: V=[1,0,...], V'=[0.6,0.8,...] → cos 0.6,
# distance 0.4 (inside the 0.55 entity band, outside the 0.12 near-dup band).
V = [1.0, 0.0] + [0.0] * 766
V_MODERATE = [0.6, 0.8] + [0.0] * 766


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


def _vec(v: list[float]) -> str:
    return "[" + ",".join(str(x) for x in v) + "]"


async def test_entity_overlap_matches_cross_language():
    if not await _db_reachable():
        pytest.skip("no database")
    eid = uuid.uuid4()
    tag = uuid.uuid4().hex[:6]
    ents = [(uuid.uuid4(), f"wangchuk-{tag}"), (uuid.uuid4(), f"pradhan-{tag}")]
    try:
        async with session_scope() as s:
            await s.execute(
                text(
                    "INSERT INTO events (id, title, sector, regions, last_updated_at, embedding) "
                    "VALUES (:i, :t, 'politics', CAST(:r AS text[]), now(), CAST(:v AS vector))"
                ),
                {"i": str(eid), "t": "CJP march English coverage", "r": ["IN"], "v": _vec(V)},
            )
            for ent_id, slug in ents:
                await s.execute(
                    text("INSERT INTO entities (id, slug, name, entity_type) VALUES (:i, :s, :n, 'person')"),
                    {"i": str(ent_id), "s": slug, "n": slug},
                )
                await s.execute(
                    text("INSERT INTO event_entities (id, event_id, entity_id, role) VALUES (:i, :e, :en, 'subject')"),
                    {"i": str(uuid.uuid4()), "e": str(eid), "en": str(ent_id)},
                )

        # A Hindi retelling: same two actors, moderately similar (not near-dup), distinct title.
        async with session_scope() as s:
            m = await find_event(
                s, cve_ids=[], url=None, title="बिलकुल अलग शीर्षक", published_at=None,
                embedding=V_MODERATE, entity_slugs=[e[1] for e in ents],
            )
        assert m is not None and m.match_type == "entity_overlap"

        # Only one shared entity → below MIN_SHARED → no match.
        async with session_scope() as s:
            m2 = await find_event(
                s, cve_ids=[], url=None, title="बिलकुल अलग शीर्षक", published_at=None,
                embedding=V_MODERATE, entity_slugs=[ents[0][1]],
            )
        assert m2 is None
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_entities WHERE event_id = :e"), {"e": str(eid)})
            await s.execute(text("DELETE FROM entities WHERE id = ANY(:ids)"), {"ids": [str(e[0]) for e in ents]})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})


async def test_related_developments_shares_actor():
    """Story branches: events sharing a person/org actor are surfaced; a shared
    place is not enough."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    e_anchor, e_branch, e_place = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    person = (uuid.uuid4(), f"wangchuk-{tag}", "person")
    place = (uuid.uuid4(), f"delhi-{tag}", "place")
    try:
        async with session_scope() as s:
            for eid in (e_anchor, e_branch, e_place):
                await s.execute(
                    text("INSERT INTO events (id, title, sector, last_updated_at) VALUES (:i, :t, 'politics', now())"),
                    {"i": str(eid), "t": f"dev {eid}"},
                )
            for ent_id, slug, etype in (person, place):
                await s.execute(
                    text("INSERT INTO entities (id, slug, name, entity_type) VALUES (:i,:s,:n,:et)"),
                    {"i": str(ent_id), "s": slug, "n": slug, "et": etype},
                )
            # anchor + branch share the person; anchor + place-event share only a place
            for eid, ent in ((e_anchor, person), (e_branch, person), (e_anchor, place), (e_place, place)):
                await s.execute(
                    text("INSERT INTO event_entities (id, event_id, entity_id, role) VALUES (:i,:e,:en,'subject')"),
                    {"i": str(uuid.uuid4()), "e": str(eid), "en": str(ent[0])},
                )
        from correlation.threads import related_developments

        rel = {r["id"] for r in await related_developments(e_anchor)}
        assert str(e_branch) in rel  # shares the person actor
        assert str(e_place) not in rel  # only a shared place → excluded
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_entities WHERE event_id = ANY(:e)"),
                            {"e": [str(e_anchor), str(e_branch), str(e_place)]})
            await s.execute(text("DELETE FROM entities WHERE id = ANY(:i)"), {"i": [str(person[0]), str(place[0])]})
            await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"),
                            {"e": [str(e_anchor), str(e_branch), str(e_place)]})
