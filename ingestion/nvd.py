"""NVD CVE API 2.0 collector (free; optional API key raises the rate limit).

Watermark: lastModified cursor. First run backfills a short recent window
so the prototype has data without pulling the whole corpus.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx

from common.config import get_settings
from common.schemas import RawItemEnvelope
from ingestion.base import get_watermark, persist_envelopes, set_watermark

logger = logging.getLogger(__name__)

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
SLUG = "nvd"
FIRST_RUN_WINDOW_DAYS = 3
PAGE_SIZE = 200


async def collect() -> int:
    settings = get_settings()
    watermark = await get_watermark(SLUG)
    now = datetime.now(UTC)
    start = (
        datetime.fromisoformat(watermark["last_modified"])
        if watermark.get("last_modified")
        else now - timedelta(days=FIRST_RUN_WINDOW_DAYS)
    )
    # NVD requires the date range to be <= 120 days; ours is always small.
    params = {
        "lastModStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
        "lastModEndDate": now.strftime("%Y-%m-%dT%H:%M:%S.000%z"),
        "resultsPerPage": PAGE_SIZE,
        "startIndex": 0,
    }
    headers = {"apiKey": settings.nvd_api_key} if settings.nvd_api_key else {}
    # Public rate limit: 5 req/30s without a key, 50 req/30s with one.
    delay = 1.0 if settings.nvd_api_key else 6.5

    inserted_total = 0
    max_modified = watermark.get("last_modified", "")
    async with httpx.AsyncClient(timeout=60) as client:
        while True:
            response = await client.get(NVD_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            envelopes: list[RawItemEnvelope] = []
            for wrapper in data.get("vulnerabilities", []):
                cve = wrapper.get("cve", {})
                cve_id = cve.get("id")
                if not cve_id:
                    continue
                description = next(
                    (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"),
                    None,
                )
                modified = cve.get("lastModified", "")
                if modified > max_modified:
                    max_modified = modified
                envelopes.append(
                    RawItemEnvelope(
                        source_slug=SLUG,
                        source_type="cve_feed",
                        external_id=cve_id,
                        url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                        title=f"{cve_id}: {(description or 'CVE record')[:160]}",
                        body=description,
                        language="en",
                        published_at=_parse_dt(cve.get("published")),
                        raw=cve,
                    )
                )

            inserted_total += await persist_envelopes(envelopes)

            total = data.get("totalResults", 0)
            next_index = params["startIndex"] + PAGE_SIZE
            if next_index >= total:
                break
            params["startIndex"] = next_index
            await asyncio.sleep(delay)

    if max_modified:
        await set_watermark(SLUG, {"last_modified": max_modified})
    logger.info("nvd: %d new items", inserted_total)
    return inserted_total


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
