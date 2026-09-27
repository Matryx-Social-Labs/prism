"""Where an event is filed: its members decide, and the sector is the path's.

Three general news feeds (Mint /rss/news, BusinessLine's default feed, ET top
stories) were declared single-topic business feeds, so every item skipped the
gate and the classifier and was filed as business — and the event took the
sector of whichever article founded it and kept it. About half the business
events those feeds started were not business: a Punjab campus protest led the
front page under Business & Markets (audit, 2026-09-27). Separately, `sector`
and `subject_path` disagreed on 6.4% of events, so Pulse and the subject pages
filed the same record differently.
"""

import json
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from classification import consumer as classification_consumer
from classification.schemas import ClassificationResult, GateResult
from common.db import session_scope
from correlation.consumer import _rebuild_projection, placement
from ingestion.rss import SPEC_BY_SLUG


def _c(path=None, sector=None, subsector=None, confidence=None, regions=None) -> dict:
    return {"subject_path": path, "sector": sector, "subsector": subsector,
            "subject_confidence": confidence, "regions": regions or []}


# ── the rule ────────────────────────────────────────────────────────────────


def test_the_members_majority_files_the_event_not_the_founder():
    got = placement([_c("business", "business"), _c("politics.protest", "politics"),
                     _c("politics.governance", "politics")], None, None)
    assert (got["sector"], got["subject_path"]) == ("politics", "politics.protest"), \
        "the earliest member of the winning sector gives the path"


def test_a_tie_goes_to_the_earliest_member():
    got = placement([_c("business.companies"), _c("politics.courts")], None, None)
    assert (got["sector"], got["subsector"], got["subject_path"]) == ("business", "corporate", "business.companies")


def test_the_sector_is_always_the_paths():
    got = placement([_c("politics.diplomacy", "business", confidence=0.9)], None, None)
    assert (got["sector"], got["subsector"], got["subject_confidence"]) == ("politics", "diplomacy", 0.9)


def test_a_member_classified_before_the_tree_does_not_outvote_a_placed_one():
    got = placement([_c(sector="business"), _c(sector="business"), _c("civic.accidents", "other")], None, None)
    assert (got["sector"], got["subject_path"]) == ("other", "civic.accidents")


def test_an_event_placed_on_the_tree_keeps_it_when_no_member_was():
    """tools/backfill_subjects placed old events without rewriting their sector:
    that is the 6.4%. The path is primary, so the sector follows it."""
    got = placement([_c(sector="business")], "politics.diplomacy", 0.8)
    assert (got["sector"], got["subject_path"], got["subject_confidence"]) == ("politics", "politics.diplomacy", 0.8)


def test_with_no_path_anywhere_the_sector_majority_stands():
    got = placement([_c(sector="finance", subsector="banking"), _c(sector="politics"),
                     _c(sector="finance", subsector="markets")], None, None)
    assert (got["sector"], got["subsector"], got["subject_path"]) == ("finance", "banking", None)


def test_nothing_to_go_on_changes_nothing():
    assert placement([{}, {}], None, None) is None


# ── the feeds ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("slug", ["livemint", "hindu_businessline", "economictimes", "businessstandard"])
def test_general_news_feeds_are_not_declared_single_topic(slug):
    assert SPEC_BY_SLUG[slug].sector is None


@pytest.mark.parametrize(("slug", "sector"), [("espncricinfo", "sports"), ("rbi", "finance")])
def test_genuinely_single_topic_feeds_keep_their_sector(slug, sector):
    assert SPEC_BY_SLUG[slug].sector == sector


# ── against Postgres ────────────────────────────────────────────────────────


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _source(s, slug: str) -> uuid.UUID:
    await s.execute(
        text("INSERT INTO sources (id, slug, name, source_type, country) VALUES (:i, :s, :s, 'rss', 'IN') "
             "ON CONFLICT (slug) DO NOTHING"),
        {"i": str(uuid.uuid4()), "s": slug},
    )
    return (await s.execute(text("SELECT id FROM sources WHERE slug = :s"), {"s": slug})).scalar_one()


async def _member(s, event_id, source_id, classification: dict, minutes_ago: int) -> None:
    raw_id, art_id = uuid.uuid4(), uuid.uuid4()
    await s.execute(
        text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, relevance, classification, "
             "published_at) VALUES (:i, :s, :x, :u, 't', '{}'::jsonb, 'relevant', CAST(:c AS jsonb), "
             "now() - make_interval(mins => :m))"),
        {"i": str(raw_id), "s": str(source_id), "x": raw_id.hex, "u": f"http://x/{raw_id}", "m": minutes_ago,
         "c": json.dumps(classification)},
    )
    await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                         "VALUES (:i, :r, 't', 'rss', 1)"), {"i": str(art_id), "r": str(raw_id)})
    await s.execute(text("INSERT INTO enrichments (id, article_id, summary) VALUES (:i, :a, 's')"),
                    {"i": str(uuid.uuid4()), "a": str(art_id)})
    await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
                         "VALUES (:i, :e, :a, 'embedding', false)"),
                    {"i": str(uuid.uuid4()), "e": str(event_id), "a": str(art_id)})


async def test_the_projection_rebuild_refiles_the_event_by_its_members():
    if not await _db_reachable():
        pytest.skip("no database")
    eid = uuid.uuid4()
    async with session_scope() as s:
        src = await _source(s, f"t-{eid.hex[:8]}")
        await s.execute(
            text("INSERT INTO events (id, title, sector, subject_path, regions, last_updated_at) "
                 "VALUES (:i, 'Punjab university students protest', 'business', 'business', '{IN}', now())"),
            {"i": str(eid)},
        )
        await _member(s, eid, src, _c("business", "business"), minutes_ago=90)  # the founder
        await _member(s, eid, src, _c("politics.protest", "politics", "governance_policy", 0.9), minutes_ago=60)
        await _member(s, eid, src, _c("politics.protest", "politics", "governance_policy", 0.8), minutes_ago=30)

    await _rebuild_projection(eid)

    async with session_scope() as s:
        row = (await s.execute(text("SELECT sector, subsector, subject_path, subject_confidence FROM events "
                                    "WHERE id = :i"), {"i": str(eid)})).one()
    assert tuple(row) == ("politics", "governance_policy", "politics.protest", 0.9)


async def test_a_general_feed_item_goes_through_the_gate_and_the_classifier(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    asked: list[str] = []

    async def gate_and_classify(title, body, country, meta):
        asked.append(title)
        return GateResult(is_relevant=True, reason="news"), ClassificationResult(
            sector="politics", subject_path="politics.protest", regions=["IN", "IN-PB"])

    async def publish(topic, message):
        return "1-0"

    monkeypatch.setattr(classification_consumer, "_gate_and_classify", gate_and_classify)
    monkeypatch.setattr(classification_consumer.stream, "publish", publish)
    item = uuid.uuid4()
    async with session_scope() as s:
        src = await _source(s, "livemint")
        await s.execute(
            text("INSERT INTO raw_items (id, source_id, external_id, title, raw, relevance) "
                 "VALUES (:i, :s, :x, 'Punjab uni students hold protest, block highway', '{}'::jsonb, 'pending')"),
            {"i": str(item), "s": str(src), "x": item.hex},
        )

    await classification_consumer.handle_raw_item({"raw_item_id": str(item)})

    async with session_scope() as s:
        cls = (await s.execute(text("SELECT classification FROM raw_items WHERE id = :i"), {"i": str(item)})).scalar_one()
    assert asked == ["Punjab uni students hold protest, block highway"]
    assert (cls["sector"], cls["role_interests"]) == ("politics", []), "no forced business, no forced Markets read"
