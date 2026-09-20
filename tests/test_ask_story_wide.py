"""Plus reads the whole story; free reads the event.

Two developments of one story, one report each. A free reader's question on
development A retrieves A's report only; a Plus reader's retrieves both. An
event with no story membership reads as itself under both plans.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text

import agent.rag as rag
from common.config import get_settings
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest_asyncio.fixture(loop_scope="session")
async def story():
    if not await _db():
        pytest.skip("no local database")
    dim = get_settings().prism_embed_dim
    vec = "[" + ",".join(["0.01"] * dim) + "]"
    ev_a, ev_b, ev_lone, run, old_run = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    arts = {ev: uuid.uuid4() for ev in (ev_a, ev_b, ev_lone)}
    raws = {ev: uuid.uuid4() for ev in (ev_a, ev_b, ev_lone)}
    async with session_scope() as s:
        src = (await s.execute(text("SELECT id FROM sources ORDER BY created_at LIMIT 1"))).scalar()
        if src is None:
            src = uuid.uuid4()
            await s.execute(text("INSERT INTO sources (id, slug, name, source_type, publisher, country, language) VALUES (:i, 'storywide-test', 'Story Wide', 'rss', 'sw', 'IN', 'en')"), {"i": str(src)})
        for ev in (ev_a, ev_b, ev_lone):
            await s.execute(text("INSERT INTO events (id, title, summary, last_updated_at) VALUES (:e, :t, 's', now())"), {"e": str(ev), "t": f"storywide {ev}"})
            await s.execute(text("INSERT INTO raw_items (id, source_id, external_id, url, title, published_at, language, raw, relevance) VALUES (:r, :s, :x, :u, 't', now(), 'en', '{}', 'relevant')"), {"r": str(raws[ev]), "s": str(src), "x": f"sw-{ev}", "u": f"https://example.org/sw/{ev}"})
            await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) VALUES (:a, :r, 'x', 'feed', 1)"), {"a": str(arts[ev]), "r": str(raws[ev])})
            await s.execute(text("INSERT INTO article_chunks (id, article_id, chunk_index, text, embedding) VALUES (gen_random_uuid(), :a, 0, :t, CAST(:v AS vector))"), {"a": str(arts[ev]), "t": f"report of {ev}", "v": vec})
            await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) VALUES (gen_random_uuid(), :e, :a, 'new_event', true)"), {"e": str(ev), "a": str(arts[ev])})
        prior = (await s.execute(text("SELECT id FROM partition_runs WHERE status='current'"))).scalar()
        await s.execute(text("UPDATE partition_runs SET status='superseded' WHERE status='current'"))
        await s.execute(text("INSERT INTO partition_runs (id, status, created_at) VALUES (:r, 'current', now())"), {"r": str(run)})
        for ev in (ev_a, ev_b):
            await s.execute(text("INSERT INTO event_story (run_id, event_id, story_label, off_spine) VALUES (:r, :e, 7, false)"), {"r": str(run), "e": str(ev)})
        # A superseded run once put A with the lone event: only the CURRENT run's story counts.
        await s.execute(text("INSERT INTO partition_runs (id, status, created_at) VALUES (:r, 'superseded', now())"), {"r": str(old_run)})
        for ev in (ev_a, ev_lone):
            await s.execute(text("INSERT INTO event_story (run_id, event_id, story_label, off_spine) VALUES (:r, :e, 3, false)"), {"r": str(old_run), "e": str(ev)})
    try:
        yield ev_a, ev_b, ev_lone, arts
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_story WHERE run_id IN (:r, :o)"), {"r": str(run), "o": str(old_run)})
            await s.execute(text("DELETE FROM partition_runs WHERE id IN (:r, :o)"), {"r": str(run), "o": str(old_run)})
            ids = [str(a) for a in arts.values()]
            await s.execute(text("DELETE FROM event_memberships WHERE article_id = ANY(CAST(:a AS uuid[]))"), {"a": ids})
            await s.execute(text("DELETE FROM article_chunks WHERE article_id = ANY(CAST(:a AS uuid[]))"), {"a": ids})
            await s.execute(text("DELETE FROM articles WHERE id = ANY(CAST(:a AS uuid[]))"), {"a": ids})
            await s.execute(text("DELETE FROM raw_items WHERE id = ANY(CAST(:r AS uuid[]))"), {"r": [str(r) for r in raws.values()]})
            await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"), {"e": [str(ev_a), str(ev_b), str(ev_lone)]})
            if prior:
                await s.execute(text("UPDATE partition_runs SET status='current' WHERE id = :p"), {"p": str(prior)})


@pytest.fixture(autouse=True)
def _flat_query(monkeypatch):
    dim = get_settings().prism_embed_dim

    async def _q(_text):
        return [0.01] * dim

    monkeypatch.setattr(rag, "embed_query", _q)


async def test_free_reads_the_event_and_plus_reads_the_story(story):
    ev_a, ev_b, _, arts = story
    free, _, _ = await rag.retrieve_grounding(ev_a, "q")
    plus, _, _ = await rag.retrieve_grounding(ev_a, "q", story_wide=True)
    assert {c.article_id for c in free} == {arts[ev_a]}
    assert {c.article_id for c in plus} == {arts[ev_a], arts[ev_b]}, "the current run's story, not a superseded one's"


async def test_an_event_outside_any_story_reads_as_itself_for_plus(story):
    _, _, ev_lone, arts = story
    plus, _, _ = await rag.retrieve_grounding(ev_lone, "q", story_wide=True)
    assert {c.article_id for c in plus} == {arts[ev_lone]}


async def test_the_plan_decides_the_scope(monkeypatch):
    seen: list = []

    async def _spy(_e, _q, *, story_wide=False):
        seen.append(story_wide)
        return [], {}, ""

    async def _allow(_q):
        return type("G", (), {"allowed": True})()

    async def _noop(*_a):
        return None

    monkeypatch.setattr(rag, "retrieve_grounding", _spy)
    monkeypatch.setattr(rag, "guard_question", _allow)
    monkeypatch.setattr(rag, "_persist_turn", _noop)
    for plan in ("free", "plus"):
        _ = [e async for e in rag.answer_stream(event_id=uuid.uuid4(), session_id=uuid.uuid4(), question="q", plan=plan)]
    assert seen == [False, True]
