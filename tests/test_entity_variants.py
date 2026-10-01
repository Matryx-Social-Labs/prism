"""One name, one entity: another spelling of a name in a record's cast is folded on Jev's word.

The Flydubai pilot reached production as fifteen entities (smit-machchhar,
smit-machhar, smith-machar, ...), one per transliteration. The contract under
test: a clash is asked only with evidence and never when one article names both;
"same" folds the variant into the spelling with the most mentions, journalled;
"different" is remembered and never asked again; a Jev failure folds nothing and
never fails the attach; an undone fold stays undone. Jev is mocked.
"""

import datetime as dt
import re
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import correlation.variants as variants
from common.config import get_settings
from common.db import session_scope
from common.decisions import Decisions, NoulAnswer
from common.text import slugify
from correlation import consumer, entity_fold
from tools import entity_variants

pytestmark = pytest.mark.asyncio(loop_scope="session")

LONG_AGO = dt.datetime.now(dt.UTC) - dt.timedelta(days=60)


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _conn():
    import asyncpg

    return await asyncpg.connect(re.sub(r"^postgresql\+asyncpg://", "postgresql://", get_settings().database_url))


class Scene:
    """Records built from member articles' names, all deleted afterwards. Every
    slug carries the scene's tag, so other sessions' entities never clash."""

    def __init__(self):
        self.tag = uuid.uuid4().hex[:8]
        self.entities: dict[str, uuid.UUID] = {}
        self.events: list[uuid.UUID] = []
        self.articles: list[uuid.UUID] = []
        self.sources: list[uuid.UUID] = []

    def slug(self, name: str) -> str:
        return f"{slugify(name)}-{self.tag}"

    async def record(self, *members: list[str], title: str = "Indian pilot saves 180 passengers") -> tuple:
        """One record; each argument is one member article's names, the first founding it."""
        eid, sid = uuid.uuid4(), uuid.uuid4()
        self.events.append(eid)
        self.sources.append(sid)
        arts = []
        async with session_scope() as s:
            await s.execute(text("INSERT INTO events (id, title, summary, sector, first_seen_at, last_updated_at) "
                                 "VALUES (:i, :t, 's', 'civic', :w, :w)"), {"i": eid, "t": title, "w": LONG_AGO})
            await s.execute(text("INSERT INTO sources (id, slug, name, source_type) VALUES (:i, :s, :s, 'rss')"),
                            {"i": sid, "s": f"fixture-{sid.hex[:8]}"})
            for k, names in enumerate(members):
                rid, aid = uuid.uuid4(), uuid.uuid4()
                await s.execute(text("INSERT INTO raw_items (id, source_id, external_id, title, raw, relevance) "
                                     "VALUES (:i, :s, :e, 'fixture', '{}'::jsonb, 'relevant')"),
                                {"i": rid, "s": sid, "e": f"ext-{rid.hex[:12]}"})
                await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                                     "VALUES (:i, :r, 'body', 'direct', 1)"), {"i": aid, "r": rid})
                await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
                                     "VALUES (:i, :e, :a, :m, :f)"),
                                {"i": uuid.uuid4(), "e": eid, "a": aid, "m": "new_event" if k == 0 else "title_time",
                                 "f": k == 0})
                for name in names:
                    ent = await self._entity(s, name)
                    await s.execute(text("INSERT INTO article_entities (id, article_id, entity_id, role) "
                                         "VALUES (:i, :a, :n, 'subject')"), {"i": uuid.uuid4(), "a": aid, "n": ent})
                    await s.execute(text("INSERT INTO event_entities (id, event_id, entity_id, role) "
                                         "VALUES (:i, :e, :n, 'subject') ON CONFLICT DO NOTHING"),
                                    {"i": uuid.uuid4(), "e": eid, "n": ent})
                arts.append(aid)
        self.articles += arts
        return eid, arts

    async def _entity(self, s, name: str) -> uuid.UUID:
        if name not in self.entities:
            self.entities[name] = uuid.uuid4()
            await s.execute(text("INSERT INTO entities (id, slug, name, entity_type) VALUES (:i, :s, :n, 'person')"),
                            {"i": self.entities[name], "s": self.slug(name), "n": name})
        return self.entities[name]

    async def cleanup(self):
        ents, evs = list(self.entities.values()), self.events
        async with session_scope() as s:
            await s.execute(text("DELETE FROM entity_variant_verdicts WHERE variant_id = ANY(:n) OR survivor_id = ANY(:n)"),
                            {"n": ents})
            await s.execute(text("DELETE FROM event_entities WHERE event_id = ANY(:e) OR entity_id = ANY(:n)"),
                            {"e": evs, "n": ents})
            await s.execute(text("DELETE FROM event_links WHERE from_event_id = ANY(:e) OR to_event_id = ANY(:e)"),
                            {"e": evs})
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = ANY(:e)"), {"e": evs})
            await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"), {"e": evs})
            await s.execute(text("DELETE FROM enrichments WHERE article_id = ANY(:a)"), {"a": self.articles})
            await s.execute(text("DELETE FROM articles WHERE id = ANY(:a)"), {"a": self.articles})
            await s.execute(text("DELETE FROM raw_items WHERE source_id = ANY(:s)"), {"s": self.sources})
            await s.execute(text("DELETE FROM sources WHERE id = ANY(:s)"), {"s": self.sources})
            await s.execute(text("UPDATE entities SET merged_into = NULL WHERE id = ANY(:n)"), {"n": ents})
            await s.execute(text("DELETE FROM entities WHERE id = ANY(:n)"), {"n": ents})


@pytest_asyncio.fixture(loop_scope="session")
async def scene():
    if not await _db_reachable():
        pytest.skip("no database")
    sc = Scene()
    yield sc
    await sc.cleanup()


@pytest.fixture
def jev(monkeypatch):
    """Answers every pair with `jev.answer` (an Exception is raised); records the states asked."""

    class Fake:
        answer: float | Exception = 0.0
        asked: list[dict] = []

    fake = Fake()
    fake.asked = []

    async def fake_decide(state, questions, **_):
        fake.asked.append(state)
        if isinstance(fake.answer, Exception):
            raise fake.answer
        return Decisions(answers={k: NoulAnswer(noul=fake.answer) for k in questions}, model="typesafe/jev-test")

    monkeypatch.setattr(variants, "decide", fake_decide)
    monkeypatch.setattr(get_settings(), "prism_entity_variants", "live")
    monkeypatch.setattr(get_settings(), "prism_entity_variant_min", 0.7)
    return fake


async def _scalar(sql: str, **params):
    async with session_scope() as s:
        return (await s.execute(text(sql), params)).scalar()


# ── the key ──────────────────────────────────────────────────────────────────


async def test_transliterations_share_a_key_and_short_or_one_word_names_do_not():
    assert variants.same_name("smit-machchhar", "smith-machar")
    assert variants.same_name("trinamool-congress", "trinamul-congress")
    assert variants.same_name("fly-dubai", "flydubai"), "a respaced name is the same name"
    assert not variants.same_name("trinamool", "trinamul"), "one word is too little to key on"
    assert not variants.same_name("ab-cd", "abb-cdd"), "under five consonants is too little"
    assert not variants.same_name("smit-machchhar", "smit-machchhar")


# ── the ingest half ──────────────────────────────────────────────────────────


async def test_a_spelling_jev_calls_the_same_folds_into_the_one_with_more_mentions(scene, jev):
    jev.answer = 0.82
    event, (_, _, incoming) = await scene.record(["Smit Machchhar"], ["Smit Machchhar"], ["Smith Machar"])
    survivor, variant = scene.entities["Smit Machchhar"], scene.entities["Smith Machar"]

    assert await variants.reconcile_on_attach(event, incoming) == 1

    assert len(jev.asked) == 1
    assert await _scalar("SELECT entity_id FROM article_entities WHERE article_id = :a", a=incoming) == survivor
    assert await _scalar("SELECT count(*) FROM event_entities WHERE event_id = :e", e=event) == 1
    assert await _scalar("SELECT merged_into FROM entities WHERE id = :v", v=variant) == survivor
    journal = await _scalar("SELECT journal FROM entity_variant_verdicts WHERE variant_id = :v AND survivor_id = :s",
                            v=variant, s=survivor)
    assert journal["variant"] == str(variant) and journal["entries"], "a fold must be undoable"


async def test_a_spelling_jev_calls_different_stays_and_is_never_asked_again(scene, jev):
    jev.answer = 0.3
    event, (_, incoming) = await scene.record(["Sahil Goyal"], ["Sahil Gill"])

    assert await variants.reconcile_on_attach(event, incoming) == 0
    assert await variants.reconcile_on_attach(event, incoming) == 0

    assert len(jev.asked) == 1, "a pair already answered was asked again"
    assert await _scalar("SELECT merged_into FROM entities WHERE id = :v", v=scene.entities["Sahil Gill"]) is None
    assert await _scalar("SELECT noul FROM entity_variant_verdicts WHERE variant_id = ANY(:n)",
                         n=list(scene.entities.values())) == 0.3


async def test_no_answer_from_jev_folds_nothing_records_nothing_and_does_not_raise(scene, jev):
    jev.answer = TimeoutError("jev slow")
    event, (_, incoming) = await scene.record(["Smit Machchhar"], ["Smith Machar"])

    assert await variants.reconcile_on_attach(event, incoming) == 0

    assert await _scalar("SELECT merged_into FROM entities WHERE id = :v", v=scene.entities["Smith Machar"]) is None
    assert await _scalar("SELECT count(*) FROM entity_variant_verdicts WHERE variant_id = ANY(:n)",
                         n=list(scene.entities.values())) == 0, "a failure must stay unanswered, to be asked again"


async def test_two_spellings_one_article_names_together_are_two_entities_and_never_asked(scene, jev):
    """30 days of production: 6 of the 7 such pairs were different people or units
    (Rehan/Rehana Shaikh, Eastern/Southern Railway)."""
    jev.answer = 0.99
    event, (_, incoming) = await scene.record(["Rehan Shaikh", "Rehana Shaikh"], ["Rehan Shaikh"])

    assert await variants.reconcile_on_attach(event, incoming) == 0
    assert jev.asked == []


async def test_shadow_records_the_answer_and_folds_nothing(scene, jev, monkeypatch):
    monkeypatch.setattr(get_settings(), "prism_entity_variants", "shadow")
    jev.answer = 0.9
    event, (_, _, incoming) = await scene.record(["Smit Machchhar"], ["Smit Machchhar"], ["Smith Machar"])

    assert await variants.reconcile_on_attach(event, incoming) == 0

    assert await _scalar("SELECT merged_into FROM entities WHERE id = :v", v=scene.entities["Smith Machar"]) is None
    assert await _scalar("SELECT noul FROM entity_variant_verdicts WHERE variant_id = :v",
                         v=scene.entities["Smith Machar"]) == 0.9


async def test_an_undone_fold_is_restored_and_never_folded_again(scene, jev):
    jev.answer = 0.9
    event, (_, _, incoming) = await scene.record(["Smit Machchhar"], ["Smit Machchhar"], ["Smith Machar"])
    survivor, variant = scene.entities["Smit Machchhar"], scene.entities["Smith Machar"]
    assert await variants.reconcile_on_attach(event, incoming) == 1

    c = await _conn()
    try:
        await entity_variants.unfold(c, scene.slug("Smith Machar"), write=True)
    finally:
        await c.close()

    assert await _scalar("SELECT entity_id FROM article_entities WHERE article_id = :a", a=incoming) == variant
    assert await _scalar("SELECT count(*) FROM event_entities WHERE event_id = :e AND entity_id = :v",
                         e=event, v=variant) == 1, "the event's row for the variant was deleted, and must come back"
    assert await _scalar("SELECT merged_into FROM entities WHERE id = :v", v=variant) is None

    assert await variants.reconcile_on_attach(event, incoming) == 0
    assert len(jev.asked) == 1
    assert await _scalar("SELECT merged_into FROM entities WHERE id = :v", v=variant) is None, "an undone fold came back"
    assert await _scalar("SELECT reverted_at IS NOT NULL FROM entity_variant_verdicts WHERE variant_id = :v "
                         "AND survivor_id = :s", v=variant, s=survivor)


async def test_the_consumer_asks_after_the_attach_and_never_fails_ingest_over_it(scene, monkeypatch):
    event, (_, incoming) = await scene.record(["Smit Machchhar"], ["Smith Machar"])
    enrichment = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO enrichments (id, article_id, summary, shared_fields, lens_fields, model) "
                             "VALUES (:i, :a, 's', '{}'::jsonb, '{}'::jsonb, 'test')"), {"i": enrichment, "a": incoming})
    calls = []

    async def down(event_id, article_id):
        calls.append((event_id, article_id))
        raise RuntimeError("entity_variant_verdicts missing")

    async def nothing(*_a, **_k):
        return None

    monkeypatch.setattr(consumer, "reconcile_on_attach", down)
    monkeypatch.setattr(consumer, "_rebuild_projection", nothing)
    monkeypatch.setattr(consumer, "mark_event_dirty", nothing)

    await consumer.handle_enriched_item({"article_id": str(incoming), "enrichment_id": str(enrichment)})

    assert calls == [(event, incoming)]


# ── the fold ─────────────────────────────────────────────────────────────────


async def test_a_fold_points_names_already_folded_into_the_variant_at_the_survivor(scene):
    """clustering follows merged_into one hop; a chain would hide the survivor."""
    await scene.record(["Smit Machchhar"], ["Smit Machchhar"], ["Smith Machar"], ["Smit Machar"])
    s, v, older = (scene.entities[n] for n in ("Smit Machchhar", "Smith Machar", "Smit Machar"))
    c = await _conn()
    try:
        await c.execute("UPDATE entities SET merged_into = $1 WHERE id = $2", v, older)
        async with c.transaction():
            entries = await entity_fold.journal(c, v, s)
            await entity_fold.fold_into(c, v, s)
        assert await c.fetchval("SELECT merged_into FROM entities WHERE id = $1", older) == s
        async with c.transaction():
            await entity_fold.restore(c, entries)
        assert await c.fetchval("SELECT merged_into FROM entities WHERE id = $1", older) == v
        assert await c.fetchval("SELECT merged_into FROM entities WHERE id = $1", v) is None
    finally:
        await c.close()


# ── the backlog tool ─────────────────────────────────────────────────────────


async def test_the_backlog_asks_only_pairs_with_evidence_against_the_survivor(scene):
    """A verified follow-up link is evidence; a shared skeleton alone is not
    (sahil-goyal/sahil-gill never meet in production)."""
    first, _ = await scene.record(["Abhijeet Dipke"], ["Abhijeet Dipke"], title="Dipke detained in Assam")
    later, _ = await scene.record(["Abhijit Deepke"], title="Dipke released")
    await scene.record(["Abhijeet Deepak"], title="Unrelated")
    async with session_scope() as s:
        await s.execute(text("INSERT INTO event_links (id, from_event_id, to_event_id, relation, confidence, method) "
                             "VALUES (:i, :f, :t, 'leads_to', 0.9, 'verified')"),
                        {"i": uuid.uuid4(), "f": first, "t": later})
    c = await _conn()
    try:
        rows = await c.fetch("SELECT en.id, en.slug, en.name, en.entity_type, count(*)::int AS mentions "
                             "FROM entities en JOIN article_entities ae ON ae.entity_id = en.id "
                             "WHERE en.id = ANY($1::uuid[]) GROUP BY en.id", list(scene.entities.values()))
        names = [variants.Name(r["id"], r["slug"], r["name"], r["entity_type"], r["mentions"]) for r in rows]
        groups = entity_variants.groups(names)
        ev = await entity_variants.evidence(c, groups)
    finally:
        await c.close()

    assert len(groups) == 1 and groups[0][0].id == scene.entities["Abhijeet Dipke"], "the survivor leads"
    survivor = scene.entities["Abhijeet Dipke"]
    assert ev[frozenset((scene.entities["Abhijit Deepke"], survivor))] == (
        "verified_link", "Dipke released", "Dipke detained in Assam")
    assert frozenset((scene.entities["Abhijeet Deepak"], survivor)) not in ev


async def test_the_dry_run_csv_names_every_decision(tmp_path):
    s = variants.Name(uuid.uuid4(), "smit-machchhar", "Smit Machchhar", "person", 88)
    v = [variants.Name(uuid.uuid4(), slug, slug, "person", 1) for slug in ("a-b", "c-d", "e-f", "g-h")]
    key = [frozenset((n.id, s.id)) for n in v]
    ev = {k: ("record", "t", "t") for k in key[:3]}
    counts = entity_variants.write_csv(str(tmp_path / "x.csv"), [[s, *v]], ev, {key[2]}, {},
                                       {key[0]: (0.8, "m"), key[1]: (0.4, "m")}, 0.7)
    assert counts == {"fold": 1, "keep": 1, "named_together": 1, "no_evidence": 1}
