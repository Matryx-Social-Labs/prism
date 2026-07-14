"""Prototype ranking for the default cyber_grc profile.

score = recency decay + CVSS severity + KEV boost + source-count boost.
Becomes the per-user `user_event_scores` model when real profiles land.
"""

from datetime import UTC, datetime


def score_event(
    *,
    last_updated_at: datetime,
    cvss_score: float | None,
    kev_listed: bool,
    source_count: int,
) -> float:
    now = datetime.now(UTC)
    updated = last_updated_at if last_updated_at.tzinfo else last_updated_at.replace(tzinfo=UTC)
    age_hours = max((now - updated).total_seconds() / 3600, 0.0)
    recency = max(0.0, 1.0 - age_hours / 168)  # linear decay over 7 days

    severity = (cvss_score or 0.0) / 10.0
    kev = 0.5 if kev_listed else 0.0
    corroboration = min(source_count - 1, 4) * 0.05

    return round(recency * 1.0 + severity * 0.8 + kev + corroboration, 4)
