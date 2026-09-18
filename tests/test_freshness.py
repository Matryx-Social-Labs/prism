"""Freshness telemetry must show real stage clocks without risking liveness."""

from datetime import UTC, datetime

import pytest

from common.freshness import WINDOW_HOURS, pipeline_freshness

pytestmark = pytest.mark.asyncio


class FakeMappings:
    def __init__(self, row):
        self.row = row

    def one(self):
        return self.row


class FakeResult:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return FakeMappings(self.row)


class FakeSession:
    def __init__(self, row):
        self.row = row
        self.params = None

    async def execute(self, statement, params):
        self.params = params
        if isinstance(self.row, Exception):
            raise self.row
        return FakeResult(self.row)


async def test_reports_each_pipeline_clock_and_backlog_age():
    now = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    row = {
        "observed_count": 100,
        "latest_observed_at": now,
        "publish_observe_samples": 90,
        "publish_observe_p50_s": 45.1236,
        "publish_observe_p95_s": 300,
        "classified_count": 80,
        "classification_pending": 20,
        "classify_samples": 75,
        "classify_p50_s": 5,
        "classify_p95_s": 30,
        "oldest_classification_pending_s": 600,
        "enrichment_eligible": 60,
        "enriched_count": 50,
        "enrichment_pending": 10,
        "enrich_samples": 45,
        "enrich_p50_s": 25,
        "enrich_p95_s": 120,
        "oldest_enrichment_pending_s": 240,
        "correlated_count": 48,
        "correlation_pending": 2,
        "latest_event_at": now,
        "correlate_samples": 48,
        "correlate_p50_s": 2,
        "correlate_p95_s": 9,
        "oldest_correlation_pending_s": 18,
        "observed_event_samples": 48,
        "observed_event_p50_s": 35,
        "observed_event_p95_s": 150,
        "story_visible_count": 47,
        "story_pending": 1,
        "story_samples": 47,
        "latest_story_visible_at": now,
        "story_p50_s": 30,
        "story_p95_s": 800,
        "oldest_story_pending_s": 900,
        "observed_story_samples": 47,
        "observed_story_p50_s": 65,
        "observed_story_p95_s": 920,
        "published_event_p50_s": 90,
        "published_event_p95_s": 450,
        "published_event_samples": 44,
        "published_story_samples": 43,
        "published_story_p50_s": 130,
        "published_story_p95_s": 1100,
    }
    session = FakeSession(row)

    out = await pipeline_freshness(session)

    assert session.params == {"window_hours": WINDOW_HOURS}
    assert out["observation"]["latest_at"] == "2026-09-17T12:00:00+00:00"
    assert out["observation"]["publish_to_observe"] == {
        "samples": 90,
        "p50_s": 45.124,
        "p95_s": 300.0,
    }
    assert out["classification"]["pending"] == 20
    assert out["classification"]["oldest_pending_s"] == 600.0
    assert out["classification"]["latency"]["samples"] == 75
    assert out["enrichment"]["completed"] == 50
    assert out["correlation"]["pending"] == 2
    assert out["story_visibility"]["pending"] == 1
    assert out["story_visibility"]["latency"]["p95_s"] == 800.0
    assert out["end_to_end"]["observe_to_event"]["p95_s"] == 150.0
    assert out["end_to_end"]["publish_to_event"]["samples"] == 44
    assert out["end_to_end"]["publish_to_story"]["samples"] == 43


async def test_accepts_a_bounded_clean_cohort_window():
    session = FakeSession({})

    out = await pipeline_freshness(session, window_hours=6)

    assert session.params == {"window_hours": 6}
    assert out["window_hours"] == 6


async def test_clamps_internal_window_callers_to_one_week():
    session = FakeSession({})

    low = await pipeline_freshness(session, window_hours=0)
    assert session.params == {"window_hours": 1}
    assert low["window_hours"] == 1

    high = await pipeline_freshness(session, window_hours=10_000)
    assert session.params == {"window_hours": 168}
    assert high["window_hours"] == 168


async def test_database_failure_is_unknown_not_a_health_failure():
    out = await pipeline_freshness(FakeSession(RuntimeError("old schema")))
    assert out == {"ok": None, "window_hours": WINDOW_HOURS, "error": "unavailable"}
