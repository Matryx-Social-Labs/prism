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
# cos 0.8 → distance 0.2: outside the 0.12 near-dup tier but inside the 0.25
# near-dup entity band (where ONE strong actor is enough).
V_NEAR = [0.8, 0.6] + [0.0] * 766


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


async def test_entity_overlap_idf_weighting():
    """IDF-weighting, not a df cutoff. A shared magnet (high df) is down-weighted to
    near-zero, so two events sharing ONLY magnets don't merge — but a magnet PLUS one
    specific actor does (the specific actor carries it). The old cutoff deleted the
    magnet entirely; for a trending story whose own core is high-df, that dropped the
    very actors binding its same-development retellings and fragmented the story."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    m1 = (uuid.uuid4(), f"cjp-{tag}", "organization")       # magnet → 14 events, 1/14 ≈ 0.07
    m2 = (uuid.uuid4(), f"pradhan-{tag}", "person")          # magnet → 14 events
    specific = (uuid.uuid4(), f"metro-{tag}", "organization")  # df 1 → the carrier
    fillers = [uuid.uuid4() for _ in range(13)]
    target = uuid.uuid4()
    all_ev = [str(x) for x in fillers] + [str(target)]
    try:
        async with session_scope() as s:
            for ent_id, slug, etype in (m1, m2, specific):
                await s.execute(text("INSERT INTO entities (id,slug,name,entity_type) VALUES (:i,:s,:n,:et)"),
                                {"i": str(ent_id), "s": slug, "n": slug, "et": etype})
            # 13 fillers (NULL embedding, never candidates) carry both magnets → df 14 each.
            for fe in fillers:
                await s.execute(text("INSERT INTO events (id,title,sector,last_updated_at) VALUES (:i,:t,'politics',now())"),
                                {"i": str(fe), "t": f"filler {fe}"})
                for ent_id, *_ in (m1, m2):
                    await s.execute(text("INSERT INTO event_entities (id,event_id,entity_id,role) VALUES (:i,:e,:en,'subject')"),
                                    {"i": str(uuid.uuid4()), "e": str(fe), "en": str(ent_id)})
            await s.execute(text("INSERT INTO events (id,title,sector,last_updated_at,embedding) "
                                 "VALUES (:i,:t,'politics',now(),CAST(:v AS vector))"),
                            {"i": str(target), "t": "metro shut (English)", "v": _vec(V)})
            for ent_id, *_ in (m1, m2, specific):
                await s.execute(text("INSERT INTO event_entities (id,event_id,entity_id,role) VALUES (:i,:e,:en,'subject')"),
                                {"i": str(uuid.uuid4()), "e": str(target), "en": str(ent_id)})

        # magnet + specific → IDF carried by the specific actor → merges (the fix; the old
        # df<=2 cutoff dropped the magnet, leaving only 1 shared → no match).
        async with session_scope() as s:
            hit = await find_event(s, cve_ids=[], url=None, title="मेट्रो बंद", published_at=None,
                                   embedding=V_MODERATE, entity_slugs=[m1[1], specific[1]])
        assert hit is not None and hit.match_type == "entity_overlap"

        # two magnets only → IDF ≈ 0.14 < threshold → no merge (guard against blobbing).
        async with session_scope() as s:
            miss = await find_event(s, cve_ids=[], url=None, title="unrelated protest", published_at=None,
                                    embedding=V_MODERATE, entity_slugs=[m1[1], m2[1]])
        assert miss is None
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_entities WHERE event_id = ANY(:e)"), {"e": all_ev})
            await s.execute(text("DELETE FROM entities WHERE id = ANY(:i)"),
                            {"i": [str(m1[0]), str(m2[0]), str(specific[0])]})
            await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"), {"e": all_ev})


async def test_entity_overlap_near_dup_single_actor():
    """In the near-dup embedding band (<=0.25) ONE IDF-strong shared actor is enough
    — two Hindi retellings of "16 metro stations shut" sit at ~0.20 and share only
    "Delhi Metro". In the looser band (0.25-0.45) that single actor is NOT enough."""
    if not await _db_reachable():
        pytest.skip("no database")
    eid = uuid.uuid4()
    tag = uuid.uuid4().hex[:6]
    actor = (uuid.uuid4(), f"delhi-metro-{tag}", "organization")  # df 1 → IDF 1.0
    try:
        async with session_scope() as s:
            await s.execute(
                text("INSERT INTO events (id, title, sector, last_updated_at, embedding) "
                     "VALUES (:i,:t,'politics',now(),CAST(:v AS vector))"),
                {"i": str(eid), "t": "16 metro stations shut (English)", "v": _vec(V)},
            )
            await s.execute(
                text("INSERT INTO entities (id, slug, name, entity_type) VALUES (:i,:s,:n,:et)"),
                {"i": str(actor[0]), "s": actor[1], "n": actor[1], "et": actor[2]},
            )
            await s.execute(
                text("INSERT INTO event_entities (id, event_id, entity_id, role) VALUES (:i,:e,:en,'subject')"),
                {"i": str(uuid.uuid4()), "e": str(eid), "en": str(actor[0])},
            )

        # near-dup (dist 0.2) + the single strong actor → merges.
        async with session_scope() as s:
            hit = await find_event(s, cve_ids=[], url=None, title="मेट्रो बंद", published_at=None,
                                   embedding=V_NEAR, entity_slugs=[actor[1]])
        assert hit is not None and hit.match_type == "entity_overlap"

        # looser band (dist 0.4) + a single actor → below MIN_SHARED → no merge.
        async with session_scope() as s:
            miss = await find_event(s, cve_ids=[], url=None, title="मेट्रो बंद", published_at=None,
                                    embedding=V_MODERATE, entity_slugs=[actor[1]])
        assert miss is None
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_entities WHERE event_id = :e"), {"e": str(eid)})
            await s.execute(text("DELETE FROM entities WHERE id = :i"), {"i": str(actor[0])})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})


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


# ── Collapsed-script guard ──────────────────────────────────────────────────
# One production event absorbed 139 unrelated Kannada articles: garbage-dumping
# FIRs, exam-fraud legislation, a Blinkit fine, dam politics, CWG weightlifting,
# all under a headline about protecting a bird. 120 of them arrived on the
# embedding path and 18 more on the single-actor entity shortcut.
#
# The cause is not a loose threshold. Measured on production, a Kannada article
# has 228 unrelated same-script neighbours inside 0.12 and 36 inside 0.04, and
# the ROC against distance is the diagonal (AUC ~0.5) — no cut separates true
# duplicates from unrelated pairs. So the guard is on the PATH, not the number,
# and these tests pin exactly that: distance is inadmissible on its own for a
# collapsed script, however small it gets.

KANNADA = "ಹೊಸಪೇಟೆ | ಎರೆಬೂತ ಸಂರಕ್ಷಣೆಗೆ ಅರಣ್ಯ ಇಲಾಖೆ ಬದ್ಧ"
TAMIL = "சிக்கல் தீர்ந்தது என்று அமைச்சர் தெரிவித்தார்"


async def _seed_event(s, eid, title, vec=V):
    await s.execute(
        text("INSERT INTO events (id,title,sector,last_updated_at,embedding) "
             "VALUES (:i,:t,'politics',now(),CAST(:v AS vector))"),
        {"i": str(eid), "t": title, "v": _vec(vec)},
    )


async def _seed_actor(s, eid, slug):
    ent = uuid.uuid4()
    await s.execute(text("INSERT INTO entities (id,slug,name,entity_type) VALUES (:i,:s,:n,'person')"),
                    {"i": str(ent), "s": slug, "n": slug})
    await s.execute(text("INSERT INTO event_entities (id,event_id,entity_id,role) VALUES (:i,:e,:en,'subject')"),
                    {"i": str(uuid.uuid4()), "e": str(eid), "en": str(ent)})
    return ent


async def _cleanup(eids, ents):
    async with session_scope() as s:
        await s.execute(text("DELETE FROM event_entities WHERE event_id = ANY(:e)"), {"e": [str(x) for x in eids]})
        if ents:
            await s.execute(text("DELETE FROM entities WHERE id = ANY(:i)"), {"i": [str(x) for x in ents]})
        await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"), {"e": [str(x) for x in eids]})


@pytest.mark.parametrize("title", [KANNADA, TAMIL], ids=["kannada", "tamil"])
async def test_collapsed_script_never_merges_on_distance_alone(title):
    """An IDENTICAL embedding is still not enough. This is the 120-article path."""
    if not await _db_reachable():
        pytest.skip("no database")
    eid = uuid.uuid4()
    try:
        async with session_scope() as s:
            await _seed_event(s, eid, "an unrelated story")
        async with session_scope() as s:
            miss = await find_event(s, cve_ids=[], url=None, title=title, published_at=None,
                                    embedding=V, entity_slugs=None)
        assert miss is None, "distance alone merged a collapsed-script article"
    finally:
        await _cleanup([eid], [])


async def test_collapsed_script_rejects_the_single_actor_shortcut():
    """The other 18 articles: one shared actor inside the 0.25 near band. That band
    spans 54% of all unrelated Kannada pairs, so it cannot be evidence here."""
    if not await _db_reachable():
        pytest.skip("no database")
    eid, tag = uuid.uuid4(), uuid.uuid4().hex[:6]
    ents = []
    try:
        async with session_scope() as s:
            await _seed_event(s, eid, "an unrelated story")
            ents.append(await _seed_actor(s, eid, f"solo-actor-{tag}"))
        async with session_scope() as s:
            miss = await find_event(s, cve_ids=[], url=None, title=KANNADA, published_at=None,
                                    embedding=V_NEAR, entity_slugs=[f"solo-actor-{tag}"])
        assert miss is None
    finally:
        await _cleanup([eid], ents)


async def test_collapsed_script_still_merges_on_two_shared_actors():
    """The guard must not orphan Kannada entirely — two shared actors is the
    measured-good gate (0.65 recall at 0.008 false-positive rate)."""
    if not await _db_reachable():
        pytest.skip("no database")
    eid, tag = uuid.uuid4(), uuid.uuid4().hex[:6]
    ents = []
    try:
        async with session_scope() as s:
            await _seed_event(s, eid, "the same story, in English")
            ents.append(await _seed_actor(s, eid, f"actor-one-{tag}"))
            ents.append(await _seed_actor(s, eid, f"actor-two-{tag}"))
        async with session_scope() as s:
            hit = await find_event(s, cve_ids=[], url=None, title=KANNADA, published_at=None,
                                   embedding=V_MODERATE,
                                   entity_slugs=[f"actor-one-{tag}", f"actor-two-{tag}"])
        assert hit is not None and hit.match_type == "entity_overlap"
    finally:
        await _cleanup([eid], ents)


@pytest.mark.parametrize(
    "title", ["Supreme Court refuses urgent hearing", "मेट्रो बंद"], ids=["latin", "devanagari"]
)
async def test_trusted_scripts_keep_the_embedding_path(title):
    """Devanagari is measured SEPARABLE (69% recall at zero false positives), so the
    guard must not touch it. Gating on 'not English' would have cost 689 articles."""
    if not await _db_reachable():
        pytest.skip("no database")
    eid = uuid.uuid4()
    try:
        async with session_scope() as s:
            await _seed_event(s, eid, "the same story")
        async with session_scope() as s:
            hit = await find_event(s, cve_ids=[], url=None, title=title, published_at=None,
                                   embedding=V, entity_slugs=None)
        assert hit is not None and hit.match_type == "embedding"
    finally:
        await _cleanup([eid], [])
