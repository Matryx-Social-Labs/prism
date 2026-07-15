"""CISA Known Exploited Vulnerabilities collector (free, authoritative).

Watermark: the max dateAdded seen; re-runs only emit newly added entries
(persist is idempotent on cveID anyway).
"""

from datetime import datetime

import httpx

from common.logging import get_logger
from common.schemas import RawItemEnvelope
from ingestion.base import get_watermark, persist_envelopes, set_watermark

logger = get_logger(__name__)

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
SLUG = "cisa_kev"


async def collect() -> int:
    watermark = await get_watermark(SLUG)
    last_added = watermark.get("last_date_added", "")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(KEV_URL)
        response.raise_for_status()
        catalog = response.json()

    envelopes: list[RawItemEnvelope] = []
    max_added = last_added
    for vuln in catalog.get("vulnerabilities", []):
        date_added = vuln.get("dateAdded", "")
        if last_added and date_added <= last_added:
            continue
        max_added = max(max_added, date_added)
        body = "\n\n".join(
            part
            for part in (
                vuln.get("shortDescription"),
                f"Required action: {vuln.get('requiredAction')}" if vuln.get("requiredAction") else None,
                f"Known ransomware campaign use: {vuln.get('knownRansomwareCampaignUse')}"
                if vuln.get("knownRansomwareCampaignUse")
                else None,
            )
            if part
        )
        envelopes.append(
            RawItemEnvelope(
                source_slug=SLUG,
                source_type="cve_feed",
                external_id=vuln["cveID"],
                url=f"https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext={vuln['cveID']}",
                title=f"{vuln['cveID']}: {vuln.get('vulnerabilityName', 'Known exploited vulnerability')}",
                body=body or None,
                language="en",
                published_at=_parse_date(date_added),
                raw=vuln,
            )
        )

    inserted = await persist_envelopes(envelopes)
    if max_added:
        await set_watermark(SLUG, {"last_date_added": max_added})
    logger.info("collector_run", collector="cisa_kev", new=inserted, candidates=len(envelopes))
    return inserted


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
