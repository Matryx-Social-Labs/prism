"""Per-lens feed ranking.

score = lens-weighted recency decay + lens-specific boosts + corroboration.
Recency decays from the event's occurred_at (real-world time), not ingest
time. Becomes the per-user `user_event_scores` model when real profiles land.
"""

from datetime import UTC, datetime

from common.lenses import Lens

_MAGNITUDE = {"minor": 0.3, "moderate": 0.6, "major": 1.0}


def score_event(
    *,
    lens: Lens,
    reference_time: datetime,
    projection: dict | None,
) -> float:
    now = datetime.now(UTC)
    ref = reference_time if reference_time.tzinfo else reference_time.replace(tzinfo=UTC)
    age_hours = max((now - ref).total_seconds() / 3600, 0.0)
    recency = max(0.0, 1.0 - age_hours / 168)  # linear decay over 7 days

    projection = projection or {}
    weights = lens.ranking
    score = recency * weights.recency

    cyber = projection.get("cyber") or {}
    if weights.severity:
        cvss = (cyber.get("cvss") or {}).get("score") or 0.0
        score += (cvss / 10.0) * weights.severity
    if weights.exploited and (cyber.get("exploitation") or {}).get("kev_listed"):
        score += weights.exploited

    finance = projection.get("finance") or {}
    if weights.price_impact and finance.get("price_impact"):
        pi = finance["price_impact"]
        magnitude = _MAGNITUDE.get(pi.get("magnitude") or "", 0.3)
        confidence = pi.get("confidence") or 0.5
        score += magnitude * confidence * weights.price_impact

    source_count = projection.get("source_count", 1)
    score += min(source_count - 1, 4) * weights.corroboration

    return round(score, 4)
