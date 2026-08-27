"""The offline fixture corpus stays loadable and stays fresh.

A fresh clone used to serve an empty feed until you enabled ingestion and paid
for LLM calls, which made the first hour cost money and every "did that help?"
question unanswerable offline.
"""

import gzip
import json
from datetime import datetime
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "corpus.json.gz"


@pytest.fixture(scope="module")
def corpus():
    with gzip.open(FIXTURE, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def test_the_fixture_exists_and_covers_every_table_the_loader_writes():
    from tools.load_fixtures import TABLES

    with gzip.open(FIXTURE, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    for table, _cols in TABLES:
        assert data.get(table), f"fixture has no rows for {table}, which the loader writes"


def test_it_covers_both_gold_sets(corpus):
    """gold_stories names EVENTS; gold_labels names ARTICLES in a different, larger
    set of events. Exporting only the story events left 156 of 171 labelled
    articles with no membership and score_clustering silently scored 15 of them."""
    from tools.gold_labels import GOLD
    from tools.gold_stories import STORY_OF

    event_ids = {e["id"] for e in corpus["events"]}
    article_ids = {a["id"] for a in corpus["articles"]}
    assert set(STORY_OF).issubset(event_ids), "gold_stories events missing from the fixture"
    assert set(GOLD).issubset(article_ids), "gold_labels articles missing from the fixture"


def test_events_carry_embeddings(corpus):
    """The partition gates edges on cosine distance. With NULL embeddings that
    gate passes every pair, so a local partition would not resemble production."""
    with_vec = [e for e in corpus["events"] if e.get("embedding")]
    assert len(with_vec) > len(corpus["events"]) * 0.9


def test_the_corpus_is_time_shifted_on_load_so_it_cannot_rot():
    """partition.py only sees events newer than `now() - 30 days`. Without a shift
    the fixture silently shrinks as real time passes — 32 of 86 gold events had
    already aged out on the first attempt — and the drift reads as a code
    regression rather than a stale fixture."""
    from tools.load_fixtures import _time_shift

    with gzip.open(FIXTURE, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    shift = _time_shift(data)
    newest = max(datetime.fromisoformat(e["last_updated_at"]) for e in data["events"])
    assert (newest + shift).timestamp() > (datetime.now().timestamp() - 60 * 60 * 24 * 2), (
        "after shifting, the newest event should be within ~2 days of now"
    )


def test_the_loader_refuses_a_non_local_database(monkeypatch):
    """It WRITES. This repo reaches production over the Railway proxy for admin
    queries, so a leftover exported DATABASE_URL is a live path to writing
    fixture rows into real data."""
    from common.config import get_settings

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@prod.example.com:5432/prism")
    get_settings.cache_clear()
    from tools.load_fixtures import _refuse_non_local

    with pytest.raises(SystemExit):
        _refuse_non_local()
    get_settings.cache_clear()
