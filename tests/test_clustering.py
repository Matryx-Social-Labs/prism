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
# distance 0.4 (inside the 0.45 entity band, outside the 0.12 near-dup band).
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


async def test_entity_overlap_excludes_ubiquitous_actors():
    """A shared UBIQUITOUS actor (in > MAX_DF distinct events, e.g. a national
    politician) must not count toward the merge — otherwise unrelated political
    stories snowball into one blob. Only distinctive (low-df) actors count."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    e1, e2, target = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    modi = (uuid.uuid4(), f"modi-{tag}", "person")       # will sit in 3 events → df=3 > MAX_DF
    local = (uuid.uuid4(), f"local-{tag}", "person")     # only in target → df=1, distinctive
    local2 = (uuid.uuid4(), f"local2-{tag}", "person")   # only in target → df=1, distinctive
    try:
        async with session_scope() as s:
            # e1/e2 have NULL embedding so they only inflate modi's df, never match.
            for eid in (e1, e2):
                await s.execute(
                    text("INSERT INTO events (id, title, sector, last_updated_at) VALUES (:i,:t,'politics',now())"),
                    {"i": str(eid), "t": f"filler {eid}"},
                )
            await s.execute(
                text("INSERT INTO events (id, title, sector, last_updated_at, embedding) "
                     "VALUES (:i,:t,'politics',now(),CAST(:v AS vector))"),
                {"i": str(target), "t": "target event", "v": _vec(V)},
            )
            for ent_id, slug, etype in (modi, local, local2):
                await s.execute(
                    text("INSERT INTO entities (id, slug, name, entity_type) VALUES (:i,:s,:n,:et)"),
                    {"i": str(ent_id), "s": slug, "n": slug, "et": etype},
                )
            links = [(e1, modi), (e2, modi), (target, modi), (target, local), (target, local2)]
            for eid, ent in links:
                await s.execute(
                    text("INSERT INTO event_entities (id, event_id, entity_id, role) VALUES (:i,:e,:en,'subject')"),
                    {"i": str(uuid.uuid4()), "e": str(eid), "en": str(ent[0])},
                )

        # Incoming shares the ubiquitous actor + ONE distinctive → only 1 counts → no match.
        async with session_scope() as s:
            m = await find_event(
                s, cve_ids=[], url=None, title="unrelated protest", published_at=None,
                embedding=V_MODERATE, entity_slugs=[modi[1], local[1]],
            )
        assert m is None

        # Incoming shares TWO distinctive actors → matches.
        async with session_scope() as s:
            m2 = await find_event(
                s, cve_ids=[], url=None, title="unrelated protest", published_at=None,
                embedding=V_MODERATE, entity_slugs=[local[1], local2[1]],
            )
        assert m2 is not None and m2.match_type == "entity_overlap"
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_entities WHERE event_id = ANY(:e)"),
                            {"e": [str(e1), str(e2), str(target)]})
            await s.execute(text("DELETE FROM entities WHERE id = ANY(:i)"),
                            {"i": [str(modi[0]), str(local[0]), str(local2[0])]})
            await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"),
                            {"e": [str(e1), str(e2), str(target)]})


async def test_related_developments_shares_actor():
    """Story branches: events sharing a person/org actor are surfaced; a shared
    place is not enough."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    e_anchor, e_branch, e_weak = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    p1 = (uuid.uuid4(), f"wangchuk-{tag}", "person")
    p2 = (uuid.uuid4(), f"cjp-{tag}", "organization")
    place = (uuid.uuid4(), f"delhi-{tag}", "place")
    try:
        async with session_scope() as s:
            for eid in (e_anchor, e_branch, e_weak):
                await s.execute(
                    text("INSERT INTO events (id, title, sector, last_updated_at) VALUES (:i, :t, 'politics', now())"),
                    {"i": str(eid), "t": f"dev {eid}"},
                )
            for ent_id, slug, etype in (p1, p2, place):
                await s.execute(
                    text("INSERT INTO entities (id, slug, name, entity_type) VALUES (:i,:s,:n,:et)"),
                    {"i": str(ent_id), "s": slug, "n": slug, "et": etype},
                )
            # anchor+branch share TWO actors; anchor+weak share only one actor + a place
            links = [(e_anchor, p1), (e_anchor, p2), (e_anchor, place),
                     (e_branch, p1), (e_branch, p2),
                     (e_weak, p1), (e_weak, place)]
            for eid, ent in links:
                await s.execute(
                    text("INSERT INTO event_entities (id, event_id, entity_id, role) VALUES (:i,:e,:en,'subject')"),
                    {"i": str(uuid.uuid4()), "e": str(eid), "en": str(ent[0])},
                )
        from correlation.threads import related_developments

        rel = {r["id"] for r in await related_developments(e_anchor)}
        assert str(e_branch) in rel  # shares 2 actors
        assert str(e_weak) not in rel  # shares only 1 actor (+ a place) → below threshold
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_entities WHERE event_id = ANY(:e)"),
                            {"e": [str(e_anchor), str(e_branch), str(e_weak)]})
            await s.execute(text("DELETE FROM entities WHERE id = ANY(:i)"),
                            {"i": [str(p1[0]), str(p2[0]), str(place[0])]})
            await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"),
                            {"e": [str(e_anchor), str(e_branch), str(e_weak)]})
