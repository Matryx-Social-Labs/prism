"""tools/backfill_classification: re-file what the old rules published.

The plan is read from the rows as stored and must predict what the projection
rebuild will write; the write path re-classifies with the model's answer even
when the gate now says not-news (the record stays published), drops cyber
facts from non-cyber articles, and rebuilds without re-dating the event."""

import json
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import tools.backfill_classification as bf
from common.db import session_scope
from common.decisions import ChoiceAnswer, Decisions, NoulAnswer

FEEDS = ("livemint",)


def _row(event, slug, cls, *, sector="business", path=None, regions=("IN",), has_cyber=False, title="t"):
    return {"event_id": event, "title": title, "sector": sector, "subsector": None, "subject_path": path,
            "subject_confidence": None, "regions": list(regions), "raw_item_id": uuid.uuid4(),
            "classification": cls, "slug": slug, "enrichment_id": uuid.uuid4(), "has_cyber": has_cyber}


def test_the_plan_names_every_change_and_nothing_else():
    politics = {"sector": "politics", "subject_path": "politics.protest", "regions": ["IN"]}
    rows = [
        # Founded by a forced-business Mint item, outvoted by two political reports.
        _row("protest", "livemint", {"sector": "business", "subject_path": "business", "regions": ["IN"]},
             path="business"),
        _row("protest", "ndtv", politics, path="business"),
        _row("protest", "thehindu", politics, path="business"),
        # A burn death carrying CWE-284.
        _row("burn", "thehindu", {"sector": "other", "subject_path": "civic.accidents"}, sector="other",
             path="civic.accidents", has_cyber=True),
        # Stamped Kerala by the old feed rule; its one member said national.
        _row("strike", "thehindu_kerala", {"sector": "finance", "subject_path": "business.banking",
                                           "regions": ["IN"]}, sector="finance", path="business.banking",
             regions=("IN", "IN-KL")),
        # Placed on the tree after the fact, sector never rewritten.
        _row("summit", "ndtv", {"sector": "business"}, path="politics.diplomacy"),
        # Already right: a breach, cyber facts and all.
        _row("breach", "thehackernews", {"sector": "cybersecurity", "subject_path": "tech.security"},
             sector="cybersecurity", path="tech.security", has_cyber=True),
    ]
    p = bf.plan(rows, FEEDS)
    assert set(p["reclassify"].values()) == {"protest"}
    assert set(p["strip"].values()) == {"burn"}
    assert {e: (old, new) for e, (old, new, _) in p["moved"].items()} == {
        "protest": ("business", "politics"), "summit": ("business", "politics")}
    assert p["restated"] == {"strike"}
    assert p["events"] == 5


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


def _not_news_politics() -> Decisions:
    return Decisions(answers={
        "event": NoulAnswer(noul=0.9), "not_news": NoulAnswer(noul=0.8),  # a live blog
        "sector": ChoiceAnswer(choice="politics", confidence=0.9, probabilities={}),
        "subsector": ChoiceAnswer(choice="politics/governance_policy", confidence=0.9, probabilities={}),
        "subject": ChoiceAnswer(choice="politics", confidence=0.9, probabilities={}),
        "sub_politics": ChoiceAnswer(choice="protest", confidence=0.9, probabilities={}),
        "indian_state": ChoiceAnswer(choice="IN-PB", confidence=0.9, probabilities={}),
        "country": ChoiceAnswer(choice="IN", confidence=1, probabilities={}),
        "language": ChoiceAnswer(choice="en", confidence=1, probabilities={}),
        "cyber": NoulAnswer(noul=0.0), "markets": NoulAnswer(noul=0.1), "fast_lane": NoulAnswer(noul=0.0),
    })


async def test_the_write_path_refiles_strips_and_rebuilds_without_redating(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")

    async def fake_decide(*_a, **_k):
        return _not_news_politics()

    monkeypatch.setattr(bf, "decide", fake_decide)
    eid, raw, art, enr = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    slug = f"t-{eid.hex[:8]}"
    async with session_scope() as s:
        src = (await s.execute(text("INSERT INTO sources (id, slug, name, source_type, country) "
                                    "VALUES (gen_random_uuid(), :s, :s, 'rss', 'IN') RETURNING id"),
                               {"s": slug})).scalar_one()
        await s.execute(text("INSERT INTO events (id, title, sector, subject_path, regions, last_updated_at) "
                             "VALUES (:e, 'Punjab students block highway', 'business', 'business', '{IN}', "
                             "now() - interval '3 hours')"), {"e": str(eid)})
        await s.execute(text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, relevance, "
                             "classification) VALUES (:r, :s, :x, :u, 'Punjab students block highway', '{}'::jsonb, "
                             "'relevant', CAST(:c AS jsonb))"),
                        {"r": str(raw), "s": str(src), "x": raw.hex, "u": f"http://x/{raw}",
                         "c": json.dumps({"sector": "business", "subject_path": "business", "regions": ["IN"],
                                          "role_interests": ["markets"]})})
        await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                             "VALUES (:a, :r, 't', 'rss', 1)"), {"a": str(art), "r": str(raw)})
        await s.execute(text("INSERT INTO enrichments (id, article_id, summary, lens_fields) VALUES "
                             "(:n, :a, 's', CAST(:l AS jsonb))"),
                        {"n": str(enr), "a": str(art), "l": json.dumps({"cyber": {"weakness": ["CWE-284"]}})})
        await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
                             "VALUES (gen_random_uuid(), :e, :a, 'new_event', true)"), {"e": str(eid), "a": str(art)})
    try:
        rows = [r for r in await bf._read(7, read_only=True) if r["event_id"] == eid]
        assert rows, "the window read must see the event"
        new, rejected, _, failed = await bf._reclassify(list(bf.plan(rows, (slug,))["reclassify"]))
        after = bf.plan([r for r in await bf._read(7, read_only=False) if r["event_id"] == eid], (slug,))
        await bf._strip_cyber(list(after["strip"]))
        await bf._rebuild({eid})
        async with session_scope() as s:
            ev = (await s.execute(text(
                "SELECT sector, subject_path, regions, projection->'cyber' AS cyber, "
                "projection->'role_interests' AS roles, now() - last_updated_at > interval '1 hour' AS old "
                "FROM events WHERE id = :e"), {"e": str(eid)})).mappings().one()
            lens = (await s.execute(text("SELECT lens_fields FROM enrichments WHERE id = :n"),
                                    {"n": str(enr)})).scalar_one()
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": str(eid)})
            await s.execute(text("DELETE FROM enrichments WHERE id = :n"), {"n": str(enr)})
            await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": str(art)})
            await s.execute(text("DELETE FROM raw_items WHERE id = :r"), {"r": str(raw)})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})
            await s.execute(text("DELETE FROM sources WHERE slug = :s"), {"s": slug})
    assert failed == 0 and len(new) == 1
    assert len(rejected) == 1, "a live blog the gate now rejects is listed, not unpublished"
    assert (ev["sector"], ev["subject_path"], ev["regions"]) == ("politics", "politics.protest", ["IN", "IN-PB"])
    assert ev["cyber"] is None and lens is None, "a campus protest carries no cyber facts"
    assert ev["roles"] == [], "the forced Markets read is gone"
    assert ev["old"], "a backfill must not re-date the record"
