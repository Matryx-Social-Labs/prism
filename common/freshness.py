"""Truthful stage-latency telemetry for the news pipeline.

These numbers describe observations from the last 24 hours, while oldest
pending ages cover all unfinished work. The helper is best-effort because it is
called by ``/healthz``: observability may be unavailable, but must never make
the API unavailable.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.logging import get_logger

logger = get_logger(__name__)

WINDOW_HOURS = 24
MIN_WINDOW_HOURS = 1
MAX_WINDOW_HOURS = 168

# One bounded pass over the recent raw-item window. DISTINCT ON protects the
# timings from historical duplicate article rows while choosing the first time
# each item reached the next stage.
_FRESHNESS_SQL = text(
    """
    WITH recent_raw AS (
        SELECT id, published_at, observed_at, classified_at, relevance
        FROM raw_items
        WHERE observed_at >= now() - make_interval(hours => :window_hours)
    ),
    first_article AS (
        SELECT DISTINCT ON (a.raw_item_id)
               a.raw_item_id, a.id AS article_id, a.fetched_at
        FROM articles a
        JOIN recent_raw r ON r.id = a.raw_item_id
        ORDER BY a.raw_item_id, a.fetched_at, a.id
    ),
    first_membership AS (
        SELECT DISTINCT ON (m.article_id)
               m.article_id, m.event_id, m.created_at AS event_at
        FROM event_memberships m
        JOIN first_article a ON a.article_id = m.article_id
        ORDER BY m.article_id, m.created_at, m.id
    ),
    journeys AS (
        SELECT r.*, a.article_id, a.fetched_at, m.event_id, m.event_at,
               e.story_visible_at
        FROM recent_raw r
        LEFT JOIN first_article a ON a.raw_item_id = r.id
        LEFT JOIN first_membership m ON m.article_id = a.article_id
        LEFT JOIN events e ON e.id = m.event_id
    )
    SELECT
        count(*)::int AS observed_count,
        max(observed_at) AS latest_observed_at,

        count(*) FILTER (
            WHERE published_at IS NOT NULL
              AND published_at >= observed_at - interval '7 days'
              AND published_at <= observed_at + interval '5 minutes'
        )::int AS publish_observe_samples,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY greatest(0, extract(epoch FROM (observed_at - published_at)))
        ) FILTER (
            WHERE published_at IS NOT NULL
              AND published_at >= observed_at - interval '7 days'
              AND published_at <= observed_at + interval '5 minutes'
        ) AS publish_observe_p50_s,
        percentile_cont(0.95) WITHIN GROUP (
            ORDER BY greatest(0, extract(epoch FROM (observed_at - published_at)))
        ) FILTER (
            WHERE published_at IS NOT NULL
              AND published_at >= observed_at - interval '7 days'
              AND published_at <= observed_at + interval '5 minutes'
        ) AS publish_observe_p95_s,

        count(*) FILTER (WHERE classified_at IS NOT NULL)::int AS classified_count,
        count(*) FILTER (WHERE relevance = 'pending')::int AS classification_pending,
        count(*) FILTER (WHERE classified_at >= observed_at)::int AS classify_samples,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY extract(epoch FROM (classified_at - observed_at))
        ) FILTER (WHERE classified_at >= observed_at) AS classify_p50_s,
        percentile_cont(0.95) WITHIN GROUP (
            ORDER BY extract(epoch FROM (classified_at - observed_at))
        ) FILTER (WHERE classified_at >= observed_at) AS classify_p95_s,

        count(*) FILTER (WHERE relevance = 'relevant')::int AS enrichment_eligible,
        count(*) FILTER (WHERE relevance = 'relevant' AND article_id IS NOT NULL)::int
            AS enriched_count,
        count(*) FILTER (WHERE relevance = 'relevant' AND article_id IS NULL)::int
            AS enrichment_pending,
        count(*) FILTER (WHERE fetched_at >= classified_at)::int AS enrich_samples,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY extract(epoch FROM (fetched_at - classified_at))
        ) FILTER (WHERE fetched_at >= classified_at) AS enrich_p50_s,
        percentile_cont(0.95) WITHIN GROUP (
            ORDER BY extract(epoch FROM (fetched_at - classified_at))
        ) FILTER (WHERE fetched_at >= classified_at) AS enrich_p95_s,

        count(*) FILTER (WHERE article_id IS NOT NULL AND event_at IS NOT NULL)::int
            AS correlated_count,
        count(*) FILTER (WHERE article_id IS NOT NULL AND event_at IS NULL)::int
            AS correlation_pending,
        max(event_at) AS latest_event_at,
        count(*) FILTER (WHERE event_at >= fetched_at)::int AS correlate_samples,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY extract(epoch FROM (event_at - fetched_at))
        ) FILTER (WHERE event_at >= fetched_at) AS correlate_p50_s,
        percentile_cont(0.95) WITHIN GROUP (
            ORDER BY extract(epoch FROM (event_at - fetched_at))
        ) FILTER (WHERE event_at >= fetched_at) AS correlate_p95_s,
        count(*) FILTER (WHERE event_at >= observed_at)::int AS observed_event_samples,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY extract(epoch FROM (event_at - observed_at))
        ) FILTER (WHERE event_at >= observed_at) AS observed_event_p50_s,
        percentile_cont(0.95) WITHIN GROUP (
            ORDER BY extract(epoch FROM (event_at - observed_at))
        ) FILTER (WHERE event_at >= observed_at) AS observed_event_p95_s,

        count(*) FILTER (WHERE event_at IS NOT NULL AND story_visible_at IS NOT NULL)::int
            AS story_visible_count,
        count(*) FILTER (WHERE event_at IS NOT NULL AND story_visible_at IS NULL)::int
            AS story_pending,
        count(*) FILTER (WHERE story_visible_at IS NOT NULL)::int AS story_samples,
        max(story_visible_at) AS latest_story_visible_at,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY extract(epoch FROM (greatest(story_visible_at, event_at) - event_at))
        ) FILTER (WHERE story_visible_at IS NOT NULL) AS story_p50_s,
        percentile_cont(0.95) WITHIN GROUP (
            ORDER BY extract(epoch FROM (greatest(story_visible_at, event_at) - event_at))
        ) FILTER (WHERE story_visible_at IS NOT NULL) AS story_p95_s,
        extract(epoch FROM (
            now() - min(event_at) FILTER (
                WHERE event_at IS NOT NULL AND story_visible_at IS NULL
            )
        )) AS oldest_story_pending_s,
        count(*) FILTER (
            WHERE story_visible_at IS NOT NULL AND event_at >= observed_at
        )::int AS observed_story_samples,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY extract(epoch FROM (greatest(story_visible_at, event_at) - observed_at))
        ) FILTER (
            WHERE story_visible_at IS NOT NULL AND event_at >= observed_at
        ) AS observed_story_p50_s,
        percentile_cont(0.95) WITHIN GROUP (
            ORDER BY extract(epoch FROM (greatest(story_visible_at, event_at) - observed_at))
        ) FILTER (
            WHERE story_visible_at IS NOT NULL AND event_at >= observed_at
        ) AS observed_story_p95_s,
        count(*) FILTER (
            WHERE event_at >= published_at
              AND published_at >= observed_at - interval '7 days'
              AND published_at <= observed_at + interval '5 minutes'
        )::int AS published_event_samples,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY extract(epoch FROM (event_at - published_at))
        ) FILTER (
            WHERE event_at >= published_at
              AND published_at >= observed_at - interval '7 days'
              AND published_at <= observed_at + interval '5 minutes'
        ) AS published_event_p50_s,
        percentile_cont(0.95) WITHIN GROUP (
            ORDER BY extract(epoch FROM (event_at - published_at))
        ) FILTER (
            WHERE event_at >= published_at
              AND published_at >= observed_at - interval '7 days'
              AND published_at <= observed_at + interval '5 minutes'
        ) AS published_event_p95_s,
        count(*) FILTER (
            WHERE story_visible_at IS NOT NULL
              AND event_at >= published_at
              AND published_at >= observed_at - interval '7 days'
              AND published_at <= observed_at + interval '5 minutes'
        )::int AS published_story_samples,
        percentile_cont(0.5) WITHIN GROUP (
            ORDER BY extract(epoch FROM (greatest(story_visible_at, event_at) - published_at))
        ) FILTER (
            WHERE story_visible_at IS NOT NULL
              AND event_at >= published_at
              AND published_at >= observed_at - interval '7 days'
              AND published_at <= observed_at + interval '5 minutes'
        ) AS published_story_p50_s,
        percentile_cont(0.95) WITHIN GROUP (
            ORDER BY extract(epoch FROM (greatest(story_visible_at, event_at) - published_at))
        ) FILTER (
            WHERE story_visible_at IS NOT NULL
              AND event_at >= published_at
              AND published_at >= observed_at - interval '7 days'
              AND published_at <= observed_at + interval '5 minutes'
        ) AS published_story_p95_s,

        (SELECT extract(epoch FROM (now() - min(observed_at)))
         FROM raw_items WHERE relevance = 'pending') AS oldest_classification_pending_s,
        (SELECT extract(epoch FROM (now() - min(r.classified_at)))
         FROM raw_items r
         WHERE r.relevance = 'relevant' AND r.classified_at IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM articles a WHERE a.raw_item_id = r.id))
            AS oldest_enrichment_pending_s,
        (SELECT extract(epoch FROM (now() - min(a.fetched_at)))
         FROM articles a
         WHERE NOT EXISTS (
             SELECT 1 FROM event_memberships m WHERE m.article_id = a.id
         )) AS oldest_correlation_pending_s
    FROM journeys
    """
)


def _int(row: Any, key: str) -> int:
    return int(row.get(key) or 0)


def _float(row: Any, key: str) -> float | None:
    value = row.get(key)
    return round(float(value), 3) if value is not None else None


def _time(row: Any, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _latency(row: Any, prefix: str, samples: int) -> dict[str, int | float | None]:
    return {
        "samples": samples,
        "p50_s": _float(row, f"{prefix}_p50_s"),
        "p95_s": _float(row, f"{prefix}_p95_s"),
    }


async def pipeline_freshness(
    db: AsyncSession,
    *,
    window_hours: int = WINDOW_HOURS,
) -> dict[str, Any]:
    """Return stage counts and clocks without ever raising to ``/healthz``.

    A bounded window lets operators distinguish a recovered live path from an
    older catch-up cohort. The default remains 24 hours for existing callers.
    """
    window_hours = max(MIN_WINDOW_HOURS, min(MAX_WINDOW_HOURS, int(window_hours)))
    try:
        result = await db.execute(_FRESHNESS_SQL, {"window_hours": window_hours})
        row = result.mappings().one()
    except Exception:  # noqa: BLE001 - a telemetry query cannot break liveness
        logger.exception("pipeline_freshness_unavailable")
        return {"ok": None, "window_hours": window_hours, "error": "unavailable"}

    published_samples = _int(row, "publish_observe_samples")
    enriched = _int(row, "enriched_count")
    return {
        "ok": True,
        "window_hours": window_hours,
        "observation": {
            "count": _int(row, "observed_count"),
            "latest_at": _time(row, "latest_observed_at"),
            "publish_to_observe": _latency(row, "publish_observe", published_samples),
        },
        "classification": {
            "completed": _int(row, "classified_count"),
            "pending": _int(row, "classification_pending"),
            "oldest_pending_s": _float(row, "oldest_classification_pending_s"),
            "latency": _latency(row, "classify", _int(row, "classify_samples")),
        },
        "enrichment": {
            "eligible": _int(row, "enrichment_eligible"),
            "completed": enriched,
            "pending": _int(row, "enrichment_pending"),
            "oldest_pending_s": _float(row, "oldest_enrichment_pending_s"),
            "latency": _latency(row, "enrich", _int(row, "enrich_samples")),
        },
        "correlation": {
            "eligible": enriched,
            "completed": _int(row, "correlated_count"),
            "pending": _int(row, "correlation_pending"),
            "oldest_pending_s": _float(row, "oldest_correlation_pending_s"),
            "latest_at": _time(row, "latest_event_at"),
            "latency": _latency(row, "correlate", _int(row, "correlate_samples")),
        },
        "story_visibility": {
            "eligible": _int(row, "correlated_count"),
            "completed": _int(row, "story_visible_count"),
            "pending": _int(row, "story_pending"),
            "oldest_pending_s": _float(row, "oldest_story_pending_s"),
            "latest_at": _time(row, "latest_story_visible_at"),
            "latency": _latency(row, "story", _int(row, "story_samples")),
        },
        "end_to_end": {
            "observe_to_event": _latency(
                row, "observed_event", _int(row, "observed_event_samples")
            ),
            "publish_to_event": _latency(
                row, "published_event", _int(row, "published_event_samples")
            ),
            "observe_to_story": _latency(
                row, "observed_story", _int(row, "observed_story_samples")
            ),
            "publish_to_story": _latency(
                row, "published_story", _int(row, "published_story_samples")
            ),
        },
    }
