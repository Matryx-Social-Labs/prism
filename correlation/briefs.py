"""Lens briefs — the same event, written through each profession's eyes.

Hybrid generation (cost discipline):
- Pipeline time (correlation): general + the event's primary lens, one LLM
  call per news event; regenerated when membership changes.
- On demand (API): any other lens on first request, cached into the event
  projection — this is what lets a cyber professional pull the cyber read
  of a war story, or a trader pull the market read of a breach.
- CVE-record-only events: composed template briefs, zero LLM cost.
"""

import json
import uuid

from sqlalchemy import text as sql_text

from common.config import get_settings
from common.db import session_scope
from common.lenses import LENSES
from common.llm import structured_chat
from common.logging import get_logger
from common.observability import fetch_prompt
from correlation.schemas import LensBriefs

logger = get_logger(__name__)

SECTOR_PRIMARY_LENS = {
    "cybersecurity": "cyber",
    "finance": "markets",
    "business": "markets",
}


def primary_lens_for(sector: str | None) -> str:
    return SECTOR_PRIMARY_LENS.get(sector or "", "reader")


def template_briefs(projection: dict, summary: str | None) -> dict[str, dict]:
    """Deterministic briefs for authoritative CVE records — no LLM."""
    cyber = projection.get("cyber") or {}
    cvss = cyber.get("cvss") or {}
    exploitation = cyber.get("exploitation") or {}
    remediation = cyber.get("remediation") or {}
    affected = cyber.get("affected") or []
    cves = cyber.get("cve_ids") or []

    products = ", ".join(
        " ".join(filter(None, [a.get("vendor"), a.get("product")])) for a in affected[:3]
    )
    severity = (
        f"CVSS {cvss['score']:.1f} ({cvss.get('severity', 'unrated')})"
        if cvss.get("score") is not None
        else "not yet scored"
    )
    exploited = bool(exploitation.get("kev_listed") or exploitation.get("known_exploited"))

    general = (
        f"A security vulnerability ({', '.join(cves[:2]) or 'unidentified'}) affecting "
        f"{products or 'multiple products'} has been "
        f"{'confirmed as actively exploited by attackers' if exploited else 'publicly disclosed'}. "
        f"Severity is rated {severity}. "
        f"{'Organizations using the affected software are being urged to act immediately. ' if exploited else ''}"
        f"{('Recommended action: ' + remediation['action']) if remediation.get('action') else 'Vendor guidance should be followed as it becomes available.'}"
    )

    checks = ", ".join(
        f"{m.get('framework')} {m.get('control')}" for m in (cyber.get("control_mapping") or [])[:3]
    )
    cyber_brief = (
        f"{', '.join(cves[:2]) or 'This vulnerability'} in {products or 'the affected products'} is "
        f"{'in CISA KEV — active exploitation confirmed; treat as an emergency patch' if exploited else 'disclosed but not yet known-exploited; prioritize by exposure'}. "
        f"Severity {severity}. "
        f"Inventory exposure to the affected versions, then "
        f"{remediation.get('action') or 'apply vendor mitigations'}. "
        f"{('Relevant controls: ' + checks + '.') if checks else ''}"
    )

    general_points = [
        p for p in [
            "Check whether your organization uses the affected software" if products else None,
            "Expect a patch or maintenance window from your IT team" if exploited else None,
        ] if p
    ]
    cyber_points = [
        p for p in [
            f"Inventory exposure to: {products}" if products else "Inventory exposure to the affected versions",
            remediation.get("action"),
            "Treat as emergency patch — KEV-listed, exploitation confirmed" if exploited else "Prioritize by internet exposure",
            f"Map to controls: {checks}" if checks else None,
        ] if p
    ]
    return {
        "reader": {"text": general.strip(), "points": general_points},
        "cyber": {"text": cyber_brief.strip(), "points": cyber_points},
    }


async def generate_briefs(event_id: uuid.UUID, lenses: list[str]) -> dict[str, dict]:
    """LLM-generate briefs for the requested lenses; caller persists."""
    async with session_scope() as session:
        event = (
            await session.execute(
                sql_text(
                    "SELECT title, summary, sector, regions, projection FROM events WHERE id = :eid"
                ),
                {"eid": str(event_id)},
            )
        ).mappings().first()
        if event is None:
            return {}
        perspectives = (
            await session.execute(
                sql_text(
                    "SELECT label, stance, origin_country, summary FROM perspectives WHERE event_id = :eid"
                ),
                {"eid": str(event_id)},
            )
        ).mappings().all()
        impacts = (
            await session.execute(
                sql_text(
                    """
                    SELECT COALESCE(en.name, i.provenance ->> 'entity_name') AS entity,
                           i.effect, i.direction, i.horizon
                    FROM impacts i LEFT JOIN entities en ON en.id = i.entity_id
                    WHERE i.event_id = :eid LIMIT 12
                    """
                ),
                {"eid": str(event_id)},
            )
        ).mappings().all()

    projection = event["projection"] or {}
    lens_fields = {
        k: v for k, v in projection.items() if k in ("cyber", "finance") and v
    }
    prompt = fetch_prompt("lens-brief")
    messages = prompt.compile(
        lenses=", ".join(lenses),
        title=event["title"],
        summary=event["summary"] or "(no summary)",
        regions=", ".join(event["regions"] or []) or "unspecified",
        sector=event["sector"] or "unspecified",
        perspectives="\n".join(
            f"- [{p['origin_country'] or '?'}] {p['label']} ({p['stance'] or 'n/a'}): {p['summary'] or ''}"
            for p in perspectives
        )
        or "(none yet)",
        impacts="\n".join(
            f"- {i['entity'] or 'unknown'}: {i['effect']} ({i['direction'] or '?'}, {i['horizon'] or '?'})"
            for i in impacts
        )
        or "(none yet)",
        lens_fields=json.dumps(lens_fields, default=str)[:2500] or "(none)",
    )
    result = await structured_chat(
        model=get_settings().prism_model_correlate,
        messages=messages,
        output_model=LensBriefs,
        trace_name="lens-brief",
        max_tokens=1500,
        metadata={"stage": "lens-brief", "event_id": str(event_id), "lenses": lenses},
        langfuse_prompt=prompt if prompt.version else None,
    )
    generated = {
        slug: read
        for slug, read in result.model_dump().items()
        if slug in lenses and read and read.get("text")
    }
    logger.info("lens_briefs_generated", event_id=str(event_id), lenses=list(generated))
    return generated


async def persist_briefs(event_id: uuid.UUID, briefs: dict[str, dict | str]) -> None:
    """Merge briefs into the event projection (jsonb, concurrency-safe).

    Texts land in projection.lens_briefs (strings — served/consumed
    everywhere), action points in projection.lens_points.
    """
    if not briefs:
        return
    texts = {
        slug: (read["text"] if isinstance(read, dict) else str(read))
        for slug, read in briefs.items()
        if (read.get("text") if isinstance(read, dict) else read)
    }
    points = {
        slug: read["points"]
        for slug, read in briefs.items()
        if isinstance(read, dict) and read.get("points")
    }
    if not texts:
        return
    async with session_scope() as session:
        await session.execute(
            sql_text(
                """
                UPDATE events
                SET projection = jsonb_set(
                    jsonb_set(
                        COALESCE(projection, '{}'::jsonb),
                        '{lens_briefs}',
                        COALESCE(projection -> 'lens_briefs', '{}'::jsonb) || CAST(:briefs AS jsonb),
                        true
                    ),
                    '{lens_points}',
                    COALESCE(projection -> 'lens_points', '{}'::jsonb) || CAST(:points AS jsonb),
                    true
                )
                WHERE id = :eid
                """
            ),
            {"eid": str(event_id), "briefs": json.dumps(texts), "points": json.dumps(points)},
        )


def available_lenses(projection: dict | None, sector: str | None = None) -> list[str]:
    """Lenses with a genuine distinct read for THIS event, general always.

    A lens is offered only when the event evidences it: extracted lens
    fields, a classifier role-interest hit, a matching sector, or an
    already-cached brief. Clients render exactly these tabs — a cricket
    match no longer offers a cyber read.
    """
    projection = projection or {}
    briefs = projection.get("lens_briefs") or {}
    roles = set(projection.get("role_interests") or [])
    applicable = {
        "reader": True,
        "cyber": bool(projection.get("cyber"))
        or "cyber" in roles
        or sector == "cybersecurity",
        "markets": bool(projection.get("finance"))
        or "markets" in roles
        or sector in ("finance", "business"),
    }
    return [
        slug
        for slug, lens in LENSES.items()
        if not lens.upcoming and (applicable.get(slug, False) or slug in briefs)
    ]
