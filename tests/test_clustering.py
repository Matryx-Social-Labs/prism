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


async def _purge_events(s, ids):
    """Tear down an event and everything _attach_article hung off it.

    Takes the CALLER's session rather than opening its own: the teardowns already
    hold one and have already deleted rows these statements touch, so a second
    session blocks on the first's uncommitted locks while the first waits for it —
    the tests hung rather than failed.
    """
    ids = [str(i) for i in ids]
    arts = [str(a) for a in (await s.execute(
        text("SELECT article_id FROM event_memberships WHERE event_id = ANY(:e)"), {"e": ids}
    )).scalars().all()]
    await s.execute(text("DELETE FROM event_memberships WHERE event_id = ANY(:e)"), {"e": ids})
    await s.execute(text("DELETE FROM event_entities WHERE event_id = ANY(:e)"), {"e": ids})
    if arts:
        await s.execute(text("DELETE FROM article_entities WHERE article_id = ANY(:a)"), {"a": arts})
        raws = [str(r) for r in (await s.execute(
            text("SELECT raw_item_id FROM articles WHERE id = ANY(:a)"), {"a": arts})).scalars().all()]
        await s.execute(text("DELETE FROM articles WHERE id = ANY(:a)"), {"a": arts})
        if raws:
            srcs = [str(x) for x in (await s.execute(
                text("SELECT source_id FROM raw_items WHERE id = ANY(:r)"), {"r": raws})).scalars().all()]
            await s.execute(text("DELETE FROM raw_items WHERE id = ANY(:r)"), {"r": raws})
            if srcs:
                await s.execute(text("DELETE FROM sources WHERE id = ANY(:s)"), {"s": srcs})


async def _attach_article(s, event_id, entity_ids):
    """Give an event one real article that names `entity_ids`.

    Required since article_entities: an event's cast is now derived from the
    articles it holds, so seeding event_entities alone leaves an event with no
    countable actors. One article naming all of them is also the honest shape —
    a single-article event's sole article is where its cast comes from.
    """
    sid, rid, aid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    tag = uuid.uuid4().hex[:8]
    await s.execute(text("INSERT INTO sources (id,slug,name,source_type) VALUES (:i,:s,:s,'rss')"),
                    {"i": str(sid), "s": f"fixture-{tag}"})
    await s.execute(
        text("INSERT INTO raw_items (id,source_id,external_id,title,raw,relevance) "
             "VALUES (:i,:s,:e,'fixture','{}'::jsonb,'relevant')"),
        {"i": str(rid), "s": str(sid), "e": f"ext-{tag}"})
    await s.execute(
        text("INSERT INTO articles (id,raw_item_id,clean_text,retrieval_tier,word_count) "
             "VALUES (:i,:r,'body','rss',1)"), {"i": str(aid), "r": str(rid)})
    await s.execute(
        text("INSERT INTO event_memberships (id,event_id,article_id,match_type,is_survivor) "
             "VALUES (:i,:e,:a,'seed',true)"),
        {"i": str(uuid.uuid4()), "e": str(event_id), "a": str(aid)})
    for ent in entity_ids:
        await s.execute(
            text("INSERT INTO article_entities (id,article_id,entity_id,role) "
                 "VALUES (:i,:a,:en,'subject')"),
            {"i": str(uuid.uuid4()), "a": str(aid), "en": str(ent)})
    return sid, rid, aid


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
            await _attach_article(s, eid, [e[0] for e in ents])

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
            await _purge_events(s, [eid])
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
                                {"i": str(fe), "t": f"filler {tag} {fe}"})
                for ent_id, *_ in (m1, m2):
                    await s.execute(text("INSERT INTO event_entities (id,event_id,entity_id,role) VALUES (:i,:e,:en,'subject')"),
                                    {"i": str(uuid.uuid4()), "e": str(fe), "en": str(ent_id)})
            await s.execute(text("INSERT INTO events (id,title,sector,last_updated_at,embedding) "
                                 "VALUES (:i,:t,'politics',now(),CAST(:v AS vector))"),
                            {"i": str(target), "t": f"metro shut {tag}", "v": _vec(V)})
            for ent_id, *_ in (m1, m2, specific):
                await s.execute(text("INSERT INTO event_entities (id,event_id,entity_id,role) VALUES (:i,:e,:en,'subject')"),
                                {"i": str(uuid.uuid4()), "e": str(target), "en": str(ent_id)})
            await _attach_article(s, target, [e for e, *_ in (m1, m2, specific)])

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
            await _purge_events(s, all_ev)
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
                {"i": str(eid), "t": f"16 metro stations shut {tag}", "v": _vec(V)},
            )
            await s.execute(
                text("INSERT INTO entities (id, slug, name, entity_type) VALUES (:i,:s,:n,:et)"),
                {"i": str(actor[0]), "s": actor[1], "n": actor[1], "et": actor[2]},
            )
            await s.execute(
                text("INSERT INTO event_entities (id, event_id, entity_id, role) VALUES (:i,:e,:en,'subject')"),
                {"i": str(uuid.uuid4()), "e": str(eid), "en": str(actor[0])},
            )
            await _attach_article(s, eid, [actor[0]])

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
            await _purge_events(s, [eid])
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})


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
        await _purge_events(s, eids)
        await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"), {"e": [str(x) for x in eids]})


@pytest.mark.parametrize("title", [KANNADA, TAMIL], ids=["kannada", "tamil"])
async def test_collapsed_script_never_merges_on_distance_alone(title):
    """An IDENTICAL embedding is still not enough. This is the 120-article path."""
    if not await _db_reachable():
        pytest.skip("no database")
    eid, tag = uuid.uuid4(), uuid.uuid4().hex[:6]
    try:
        async with session_scope() as s:
            await _seed_event(s, eid, f"an unrelated story {tag}")
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
            await _seed_event(s, eid, f"an unrelated story {tag}")
            ents.append(await _seed_actor(s, eid, f"solo-actor-{tag}"))
            await _attach_article(s, eid, ents)
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
            await _seed_event(s, eid, f"the same story in English {tag}")
            ents.append(await _seed_actor(s, eid, f"actor-one-{tag}"))
            ents.append(await _seed_actor(s, eid, f"actor-two-{tag}"))
            await _attach_article(s, eid, ents)
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


async def test_a_pile_of_half_magnets_is_not_a_match():
    """sum(1/df) can clear MIN_IDF from several middling actors none of which is
    actually specific — three actors at df 15 sum to 0.20, past the 0.15 floor.
    That is how two unrelated blobs that both name a few national figures reach
    each other. At least ONE shared actor has to be specific on its own."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    mids = [(uuid.uuid4(), f"half-magnet-{n}-{tag}") for n in range(3)]
    fillers = [uuid.uuid4() for _ in range(14)]
    target = uuid.uuid4()
    all_ev = [str(x) for x in fillers] + [str(target)]
    try:
        async with session_scope() as s:
            for eid, slug in mids:
                await s.execute(
                    text("INSERT INTO entities (id,slug,name,entity_type) VALUES (:i,:s,:n,'person')"),
                    {"i": str(eid), "s": slug, "n": slug},
                )
            # 14 fillers + the target carry all three → df 15 each → 1/df = 0.0667,
            # sum 0.20 (clears MIN_IDF 0.15), max 0.0667 (fails MIN_TOP_IDF 0.1).
            for fe in fillers:
                await s.execute(
                    text("INSERT INTO events (id,title,sector,last_updated_at) "
                         "VALUES (:i,:t,'politics',now())"),
                    {"i": str(fe), "t": f"filler {tag} {fe}"},
                )
                for eid, _ in mids:
                    await s.execute(
                        text("INSERT INTO event_entities (id,event_id,entity_id,role) "
                             "VALUES (:i,:e,:en,'subject')"),
                        {"i": str(uuid.uuid4()), "e": str(fe), "en": str(eid)},
                    )
            await _seed_event(s, target, f"an unrelated english story {tag}")
            for eid, _ in mids:
                await s.execute(
                    text("INSERT INTO event_entities (id,event_id,entity_id,role) "
                         "VALUES (:i,:e,:en,'subject')"),
                    {"i": str(uuid.uuid4()), "e": str(target), "en": str(eid)},
                )
            await _attach_article(s, target, [e for e, _ in mids])

        async with session_scope() as s:
            miss = await find_event(
                s, cve_ids=[], url=None, title=f"a different english story {tag}", published_at=None,
                embedding=V_MODERATE, entity_slugs=[slug for _, slug in mids],
            )
        assert miss is None, "merged on three half-magnets and no specific actor"
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_entities WHERE event_id = ANY(:e)"), {"e": all_ev})
            await s.execute(text("DELETE FROM entities WHERE id = ANY(:i)"),
                            {"i": [str(e) for e, _ in mids]})
            await _purge_events(s, all_ev)
            await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"), {"e": all_ev})


async def test_a_broad_cast_overlap_merges_without_a_rare_actor():
    """The counterpart to the half-magnet test, and a regression from production.

    An article sharing EIGHT actors with its event — Amit Shah, Rahul Gandhi, the
    party, the presiding judge — was refused because its most specific shared
    actor sat at df 12, just past the df<=10 that MIN_TOP_IDF implies. Eight
    shared actors is not a coincidence; demanding a rare one on top is a second
    tax on the same evidence. Four mid-df actors (df 15 -> max 1/df = 0.067,
    below MIN_TOP_IDF) must merge on breadth alone, while three still do not.
    """
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    shared = [(uuid.uuid4(), f"broad-{n}-{tag}") for n in range(4)]
    fillers = [uuid.uuid4() for _ in range(14)]
    target = uuid.uuid4()
    all_ev = [str(x) for x in fillers] + [str(target)]
    try:
        async with session_scope() as s:
            for eid, slug in shared:
                await s.execute(
                    text("INSERT INTO entities (id,slug,name,entity_type) VALUES (:i,:s,:n,'person')"),
                    {"i": str(eid), "s": slug, "n": slug})
            for fe in fillers:
                await s.execute(
                    text("INSERT INTO events (id,title,sector,last_updated_at) "
                         "VALUES (:i,:t,'politics',now())"), {"i": str(fe), "t": f"filler {tag} {fe}"})
                for eid, _ in shared:
                    await s.execute(
                        text("INSERT INTO event_entities (id,event_id,entity_id,role) "
                             "VALUES (:i,:e,:en,'subject')"),
                        {"i": str(uuid.uuid4()), "e": str(fe), "en": str(eid)})
            await _seed_event(s, target, f"the same story in English {tag}")
            for eid, _ in shared:
                await s.execute(
                    text("INSERT INTO event_entities (id,event_id,entity_id,role) "
                         "VALUES (:i,:e,:en,'subject')"),
                    {"i": str(uuid.uuid4()), "e": str(target), "en": str(eid)})
            await _attach_article(s, target, [e for e, _ in shared])

        # four mid-df actors, none individually specific -> merges on breadth
        async with session_scope() as s:
            hit = await find_event(
                s, cve_ids=[], url=None, title=f"a related english story {tag}", published_at=None,
                embedding=V_MODERATE, entity_slugs=[sl for _, sl in shared])
        assert hit is not None and hit.match_type == "entity_overlap"

        # three of the same actors -> below the breadth bar, and still no rare
        # actor, so it must NOT merge (this is the half-magnet guard intact)
        async with session_scope() as s:
            miss = await find_event(
                s, cve_ids=[], url=None, title=f"an unrelated english story {tag}", published_at=None,
                embedding=V_MODERATE, entity_slugs=[sl for _, sl in shared[:3]])
        assert miss is None
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_entities WHERE event_id = ANY(:e)"), {"e": all_ev})
            await s.execute(text("DELETE FROM entities WHERE id = ANY(:i)"),
                            {"i": [str(e) for e, _ in shared]})
            await _purge_events(s, all_ev)
            await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"), {"e": all_ev})


async def test_an_actor_inherited_from_one_absorbed_article_does_not_widen_the_gate():
    """The feedback loop, closed.

    event_entities is cumulative: an actor arrives when an article is absorbed and
    stays forever. So an event that once swallowed one article about a national
    figure became matchable by every future article naming that figure, and each
    bad merge widened the opening for the next. One production event reached 978
    actors this way, at which point the gate is simply open.

    Here a big event holds ten articles about one subject and ONE stray article
    that named two other actors. Under the old rule those two counted for the
    event and an unrelated article sharing them merged straight in. Now an actor
    must be named by at least two of the event's OWN articles to speak for it.
    """
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    core = [(uuid.uuid4(), f"core-{n}-{tag}") for n in range(2)]
    stray = [(uuid.uuid4(), f"stray-{n}-{tag}") for n in range(2)]
    eid = uuid.uuid4()
    try:
        async with session_scope() as s:
            await _seed_event(s, eid, f"a big event {tag}")
            for ent, slug in core + stray:
                await s.execute(
                    text("INSERT INTO entities (id,slug,name,entity_type) VALUES (:i,:s,:n,'person')"),
                    {"i": str(ent), "s": slug, "n": slug})
                # cumulative event-level link: exactly what used to be consulted
                await s.execute(
                    text("INSERT INTO event_entities (id,event_id,entity_id,role) "
                         "VALUES (:i,:e,:en,'subject')"),
                    {"i": str(uuid.uuid4()), "e": str(eid), "en": str(ent)})
            # ten articles carry the core actors...
            for _ in range(10):
                await _attach_article(s, eid, [e for e, _ in core])
            # ...and exactly ONE stray article named the other two.
            await _attach_article(s, eid, [e for e, _ in stray])

        # An unrelated article sharing only the two STRAY actors must not merge:
        # they speak for one of eleven articles, not for the event.
        async with session_scope() as s:
            miss = await find_event(
                s, cve_ids=[], url=None, title=f"a wholly different story {tag}", published_at=None,
                embedding=V_MODERATE, entity_slugs=[sl for _, sl in stray])
        assert miss is None, "an actor from one absorbed article still widened the gate"

        # The core actors, named by ten of eleven, still match.
        async with session_scope() as s:
            hit = await find_event(
                s, cve_ids=[], url=None, title=f"more on the same thing {tag}", published_at=None,
                embedding=V_MODERATE, entity_slugs=[sl for _, sl in core])
        assert hit is not None and hit.match_type == "entity_overlap"
    finally:
        async with session_scope() as s:
            await _purge_events(s, [eid])
            await s.execute(text("DELETE FROM entities WHERE id = ANY(:i)"),
                            {"i": [str(e) for e, _ in core + stray]})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})
