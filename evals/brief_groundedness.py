"""Brief groundedness eval — do the lens briefs invent facts?

Samples real briefs from the DB and judges each against the SAME structured
record the brief was generated from (title, summary, perspectives, impacts,
lens fields). A longer brief has more room to hallucinate, so this guards the
brief-depth work: it flags briefs whose claims aren't supported by the record.

Usage:  python evals/brief_groundedness.py [N]     (default N=20)
Reads DATABASE_URL from the environment (.env for local, or a prod URL).
Budget: one judge LLM call per sampled brief.
"""

import asyncio
import json
import sys

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from common.llm import structured_chat
from common.observability import fetch_prompt

FLAG_BELOW = 0.7


class BriefGroundednessVerdict(BaseModel):
    # Ollama Cloud doesn't enforce json_schema field names, so the judge drifts
    # to score/grounded_score/groundedness_score — accept them all.
    model_config = ConfigDict(populate_by_name=True)
    grounded: float = Field(
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("grounded", "grounded_score", "groundedness_score", "score"),
    )
    unsupported_claims: list[str] = Field(default_factory=list)
    reasoning: str = ""


def _record(ev: dict, perspectives: list, impacts: list) -> str:
    projection = ev["projection"] or {}
    lens_fields = {k: v for k, v in projection.items() if k in ("cyber", "finance") and v}
    persp = "\n".join(
        f"- [{p['origin_country'] or '?'}] {p['label']} ({p['stance'] or 'n/a'}): {p['summary'] or ''}"
        for p in perspectives
    ) or "(none)"
    imps = "\n".join(
        f"- {i['entity'] or 'unknown'}: {i['effect']} ({i['direction'] or '?'}, {i['horizon'] or '?'})"
        for i in impacts
    ) or "(none)"
    return (
        f"Title: {ev['title']}\n"
        f"Summary: {ev['summary'] or '(none)'}\n"
        f"Sector: {ev['sector'] or 'unspecified'} | Regions: {', '.join(ev['regions'] or []) or 'unspecified'}\n"
        f"Perspectives:\n{persp}\n"
        f"Impacts:\n{imps}\n"
        f"Lens fields: {json.dumps(lens_fields, default=str)[:2500] or '(none)'}"
    )


async def _sample(n: int) -> list[dict]:
    async with session_scope() as s:
        events = (
            await s.execute(
                text(
                    """
                    SELECT id, title, summary, sector, regions, projection
                    FROM events
                    WHERE projection->'lens_briefs'->>'general' IS NOT NULL
                      AND summary IS NOT NULL
                      AND length(projection->'lens_briefs'->>'general') > 400
                    ORDER BY random() LIMIT :n
                    """
                ),
                {"n": n},
            )
        ).mappings().all()
        out = []
        for ev in events:
            perspectives = (
                await s.execute(
                    text("SELECT label, stance, origin_country, summary FROM perspectives WHERE event_id = :e"),
                    {"e": str(ev["id"])},
                )
            ).mappings().all()
            impacts = (
                await s.execute(
                    text(
                        """
                        SELECT COALESCE(en.name, i.provenance ->> 'entity_name') AS entity,
                               i.effect, i.direction, i.horizon
                        FROM impacts i LEFT JOIN entities en ON en.id = i.entity_id
                        WHERE i.event_id = :e LIMIT 12
                        """
                    ),
                    {"e": str(ev["id"])},
                )
            ).mappings().all()
            out.append(
                {
                    "id": str(ev["id"]),
                    "title": ev["title"],
                    "brief": ev["projection"]["lens_briefs"]["general"],
                    "record": _record(ev, perspectives, impacts),
                }
            )
        return out


async def _judge(item: dict) -> BriefGroundednessVerdict:
    prompt = fetch_prompt("judge-brief-groundedness")
    messages = prompt.compile(record=item["record"], brief=item["brief"])
    return await structured_chat(
        model=get_settings().prism_model_judge,
        messages=messages,
        output_model=BriefGroundednessVerdict,
        trace_name="judge-brief-groundedness",
    )


async def main(n: int) -> None:
    items = await _sample(n)
    if not items:
        print("no briefs to judge (none over 400 chars) — nothing to eval")
        return
    # Small concurrency to keep it quick without hammering the LLM.
    sem = asyncio.Semaphore(4)

    async def run(it):
        async with sem:
            try:
                return it, await _judge(it)
            except Exception as exc:  # noqa: BLE001 — one bad judge shouldn't kill the run
                print(f"  judge failed for {it['id'][:8]}: {exc}")
                return it, None

    results = [r for r in await asyncio.gather(*(run(it) for it in items)) if r[1] is not None]
    if not results:
        print("all judge calls failed")
        return

    scores = [v.grounded for _, v in results]
    mean = sum(scores) / len(scores)
    flagged = sorted((r for r in results if r[1].grounded < FLAG_BELOW), key=lambda r: r[1].grounded)
    print(f"\nbrief groundedness — n={len(results)}")
    print(f"  mean grounded : {mean:.3f}")
    print(f"  min / max     : {min(scores):.2f} / {max(scores):.2f}")
    print(f"  flagged (<{FLAG_BELOW}): {len(flagged)}")
    for it, v in flagged:
        print(f"\n  ⚠ {v.grounded:.2f}  {it['title'][:70]}")
        for c in v.unsupported_claims[:4]:
            print(f"      – {c}")
        if v.reasoning:
            print(f"      ({v.reasoning})")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    asyncio.run(main(n))
