"""Lens briefs — the same event, written through each profession's eyes.

Written before anyone taps, so a tap reads a brief rather than waiting on one:
- Pipeline time (correlation): every lens the story offers, in the one
  analysis call per news event; regenerated when membership changes.
- Sweep (worker): the lenses recent stories offer and still lack, single-
  source stories above all (sweep_lens_briefs).
- On demand (API): anything still missing on first request, cached into the
  event projection — this is what lets a cyber professional pull the cyber
  read of a war story, or a trader pull the market read of a breach.
- CVE-record-only events: composed template briefs, zero LLM cost.
"""

import json
import uuid

from sqlalchemy import text as sql_text

from common.config import get_settings
from common.db import session_scope
from common.lenses import LENSES
from common.llm import REASONING_OFF, structured_chat
from common.logging import get_logger
from common.observability import fetch_prompt
from common.text import is_model_commentary
from correlation.cites import cite_lines
from correlation.schemas import LensBriefs

logger = get_logger(__name__)

# The brief is written at the smallest reasoning effort. Bake-off 2026-09-27
# (tools/bakeoff_brief, pinned to Together, 10 live briefs a lens, judged blind):
#   Markets  minimal 4.9 s (max 6.8)  $0.00021  grounded 0.84 | default 26.2 s (max 43.3)  $0.00099  grounded 0.91
#   Cyber    minimal 7.1 s (max 20.8) $0.00027  grounded 0.78 | default 22.8 s (max 35.3)  $0.00097  grounded 0.55
# No steady grounding cost either way (the judge swings more than the
# setting), ~15% fewer words, a quarter of the price and a fifth of the wait.
# Room for two lenses' prose and points, not for a model thinking aloud.
BRIEF_MAX_TOKENS = 2000


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
    settings = get_settings()
    result = await structured_chat(
        model=settings.prism_model_correlate,
        messages=messages,
        output_model=LensBriefs,
        trace_name="lens-brief",
        # A tap used to wait on the default: glm thought for 2,758 of its 3,000
        # tokens and took 25 s (audit, 2026-09-27). See BRIEF_MAX_TOKENS.
        max_tokens=BRIEF_MAX_TOKENS,
        reasoning=REASONING_OFF,
        providers=[p.strip() for p in settings.prism_brief_providers.split(",") if p.strip()] or None,
        metadata={"stage": "lens-brief", "event_id": str(event_id), "lenses": lenses},
        langfuse_prompt=prompt if prompt.version else None,
    )
    # A read that describes its input ("…in the provided text") is dropped here,
    # not only at the store: the API serves this return value before persisting.
    generated = {
        slug: read
        for slug, read in result.model_dump().items()
        if slug in lenses and read and read.get("text") and not is_model_commentary(read["text"])
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
    # Model commentary about the input is never stored, from any writer (the
    # extractor's Reader brief, the analysis pass, the API, the backfill).
    briefs = {
        slug: read for slug, read in briefs.items()
        if not is_model_commentary(read.get("text") if isinstance(read, dict) else read)
    }
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
        # Which report each line of the free brief came from, and whether its
        # figures are in it (correlation/cites.py). Shadow: stored, not shown.
        if texts.get("reader"):
            reports = (
                await session.execute(
                    sql_text(
                        "SELECT a.id, a.clean_text FROM event_memberships em "
                        "JOIN articles a ON a.id = em.article_id WHERE em.event_id = :eid"
                    ),
                    {"eid": str(event_id)},
                )
            ).all()
            await session.execute(
                sql_text(
                    "UPDATE events SET projection = jsonb_set(COALESCE(projection, '{}'::jsonb), '{lens_cites}', "
                    "COALESCE(projection -> 'lens_cites', '{}'::jsonb) || CAST(:cites AS jsonb), true) WHERE id = :eid"
                ),
                {"eid": str(event_id), "cites": json.dumps({"reader": cite_lines(texts["reader"], [(r[0], r[1]) for r in reports])})},
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


# available_lenses' evidence clauses as SQL over `events`, for the sweep below
# (and tools/bakeoff_brief) to find the events that offer a professional lens
# without reading every projection in the window. Keep the two in step; the
# sweep re-checks each row with available_lenses itself.
OFFERS_SQL: dict[str, str] = {
    "cyber": "(jsonb_typeof(projection->'cyber') = 'object' OR projection->'role_interests' ? 'cyber' "
             "OR sector = 'cybersecurity')",
    "markets": "(jsonb_typeof(projection->'finance') = 'object' OR projection->'role_interests' ? 'markets' "
               "OR sector IN ('finance', 'business'))",
}
SWEEP_HOURS = 48
SWEEP_LIMIT = 50
SWEEP_RETRY_S = 6 * 3600  # a lens the model wrote nothing for is tried again after this


async def sweep_lens_briefs(*, hours: int = SWEEP_HOURS, limit: int = SWEEP_LIMIT) -> int:
    """Write the professional lenses recent stories offer and do not have yet.

    The analysis pass writes every lens a story of two or more reports offers;
    a single-source story never reaches it (correlation/consumer.py
    MIN_SOURCES_FOR_ANALYSIS), and a lens a story comes to offer between tiers
    waits for the next one. Either way the first reader to tap it waited on the
    model: 92% of Markets taps in 48 h (audit, 2026-09-27). Newest first, a
    bounded batch per pass, nothing under the budget floor. Returns briefs written.
    """
    from common import budget
    from common.stream import get_redis

    if budget.below_floor(await budget.current()):
        return 0
    lacking = " OR ".join(
        f"({offers} AND NOT COALESCE(projection->'lens_briefs', '{{}}'::jsonb) ? '{slug}')"
        for slug, offers in OFFERS_SQL.items()
    )
    async with session_scope() as session:
        rows = (
            await session.execute(
                sql_text(
                    f"SELECT id, sector, projection FROM events "
                    f"WHERE last_updated_at > now() - make_interval(hours => :h) AND ({lacking}) "
                    f"ORDER BY last_updated_at DESC LIMIT :n"
                ),
                {"h": hours, "n": limit},
            )
        ).mappings().all()
    redis = get_redis()
    written = 0
    for row in rows:
        have = (row["projection"] or {}).get("lens_briefs") or {}
        missing = [
            slug for slug in available_lenses(row["projection"], row["sector"])
            if slug != "reader" and slug not in have
            # Once per SWEEP_RETRY_S: a story the model writes nothing for must
            # not hold a place in every batch.
            and await redis.set(f"prism:lens-sweep:{row['id']}:{slug}", 1, nx=True, ex=SWEEP_RETRY_S)
        ]
        if not missing:
            continue
        try:
            briefs = await generate_briefs(row["id"], missing)
            await persist_briefs(row["id"], briefs)
            written += len(briefs)
        except Exception:
            logger.warning("lens_brief_sweep_failed", event_id=str(row["id"]), lenses=missing, exc_info=True)
    logger.info("lens_brief_sweep", candidates=len(rows), written=written)
    return written
