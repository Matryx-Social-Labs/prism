"""Which model writes the lens brief cheapest without losing the reader? Judged blind.

The analysis stage (event-analysis, lens briefs, Ask) runs qwen/qwen3.7-plus
($0.32 / $1.28 per M) and is ~25% of spend on ~3% of calls. Candidates:
z-ai/glm-5.3-flash ($0.09 / $0.30), deepseek/deepseek-v3.2 ($0.27 / $0.40),
qwen/qwen3.7-flash ($0.03 / $0.13). Each writes the Reader brief for the same
events from the same record, through the real generate_briefs; then the judge
model scores every brief blind on two things: groundedness against the record
(the existing judge-brief-groundedness prompt — does it invent?) and a reader
rubric (clear, complete, neutral, 0-1). Prints per-model means, seconds per
brief, and words per brief.

  uv run python -m tools.bakeoff_brief --events 12 \
      --models qwen/qwen3.7-plus z-ai/glm-5.3-flash deepseek/deepseek-v3.2 qwen/qwen3.7-flash

Spend: events x models briefs + 2 judge calls each; ~$0.60 for 12 x 4.

A professional lens is judged the same way (the rubric reads for a general
reader, so for Markets/Cyber lean on `grounded`): --lens markets samples events
that offer it. "model@think" runs the provider's default reasoning, "model@nothink"
the smallest effort, whatever generate_briefs itself asks for:

  uv run python -m tools.bakeoff_brief --lens markets --min-sources 1 --events 10 \
      --models z-ai/glm-5.3-flash@think z-ai/glm-5.3-flash@nothink
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import text

import correlation.briefs as briefs_mod
from common import spend
from common.config import get_settings
from common.db import session_scope
from common.llm import REASONING_OFF, structured_chat
from correlation.briefs import OFFERS_SQL, generate_briefs
from evals.brief_groundedness import _judge as judge_grounded
from evals.brief_groundedness import _record

OUT = Path(".cache/bakeoff_brief.json")


class ReaderRubric(BaseModel):
    clear: float = Field(ge=0, le=1, description="Plain, readable by a general Indian news reader")
    complete: float = Field(ge=0, le=1, description="Covers what happened and why it matters, using the record")
    neutral: float = Field(ge=0, le=1, description="No opinion, no loaded words, no invented certainty")


async def sample(n: int, lens: str = "reader", min_sources: int = 3) -> list[dict]:
    offers = OFFERS_SQL.get(lens, "true")
    async with session_scope() as s:
        evs = (await s.execute(text(
            "SELECT id, title, summary, sector, regions, projection FROM events "
            "WHERE COALESCE((projection->>'source_count')::int, 1) >= :m AND summary IS NOT NULL "
            f"AND {offers} "
            "AND created_at > now() - interval '3 days' ORDER BY random() LIMIT :n"), {"n": n, "m": min_sources})).mappings().all()
        out = []
        for ev in evs:
            persp = (await s.execute(text("SELECT label, stance, origin_country, summary FROM perspectives WHERE event_id = :e"), {"e": str(ev["id"])})).mappings().all()
            imps = (await s.execute(text("SELECT COALESCE(en.name, i.provenance ->> 'entity_name') AS entity, i.effect, i.direction, i.horizon FROM impacts i LEFT JOIN entities en ON en.id = i.entity_id WHERE i.event_id = :e LIMIT 12"), {"e": str(ev["id"])})).mappings().all()
            out.append({"id": str(ev["id"]), "title": ev["title"], "record": _record(dict(ev), persp, imps)})
        return out


async def rubric(record: str, brief: str) -> ReaderRubric:
    return await structured_chat(
        model=get_settings().prism_model_judge,
        messages=[
            {"role": "system", "content": "You judge a short news brief for a general Indian reader. Score each criterion from 0 to 1. Judge only the brief against the record; do not reward length."},
            {"role": "user", "content": f"RECORD:\n{record}\n\nBRIEF:\n{brief}"},
        ],
        output_model=ReaderRubric, trace_name="bakeoff-brief-rubric", max_tokens=1500, reasoning=REASONING_OFF,
    )


async def brief_spend() -> tuple[float, int, int]:
    """(cost, output tokens, calls) the ledger holds today for the lens-brief stage."""
    stages = (await spend.days(1))[0]["stages"]
    rows = [r for r in stages if r["stage"] == "lens-brief"]
    return sum(r["cost"] for r in rows), sum(r["output_tokens"] for r in rows), sum(r["calls"] for r in rows)


def summarise(model: str, n: int, rows: list[dict], spent: tuple[float, int, int]) -> dict:
    ok = [r for r in rows if not r.get("failed") and not r.get("unjudged")]

    def mean(k: str) -> float:
        return round(sum(r[k] for r in ok) / max(1, len(ok)), 2)

    secs = sorted(r["secs"] for r in rows)
    calls = max(1, spent[2])
    return {"model": model, "events": n, "failed": sum(1 for r in rows if r.get("failed")),
            "grounded": mean("grounded"), "clear": mean("clear"), "complete": mean("complete"), "neutral": mean("neutral"),
            "words": mean("words"), "secs": round(sum(secs) / max(1, len(secs)), 1),
            "max_secs": round(secs[-1], 1) if secs else 0.0,
            "out_tok": round(spent[1] / calls), "usd": round(spent[0] / calls, 5), "rows": rows}


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--events", type=int, default=12)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--lens", default="reader")
    ap.add_argument("--min-sources", type=int, default=3)
    a = ap.parse_args()
    items = await sample(a.events, a.lens, a.min_sources)
    print(f"  {len(items)} events offering {a.lens} with >= {a.min_sources} sources from the last 3 days")
    settings = get_settings()
    incumbent = settings.prism_model_correlate
    real_structured_chat = briefs_mod.structured_chat
    results = []
    try:
        for spec in a.models:
            # "model@nothink" / "model@think" force the reasoning either way, so
            # the cost of thinking aloud on prose is measured, not assumed.
            model, _, variant = spec.partition("@")
            settings.prism_model_correlate = model  # generate_briefs reads it at call time
            if variant in ("nothink", "think"):
                # Default reasoning gets the 3,000-token ceiling it ran under
                # until 2026-09-27; at 2,000 it thinks itself out of room.
                forced = {"reasoning": REASONING_OFF} if variant == "nothink" else {"reasoning": None, "max_tokens": 3000}

                async def chat(_forced=forced, **kw):
                    return await real_structured_chat(**{**kw, **_forced})

                briefs_mod.structured_chat = chat
            else:
                briefs_mod.structured_chat = real_structured_chat
            print(f"  {spec} …", flush=True)
            rows = []
            before = await brief_spend()
            for it in items:
                t0 = time.monotonic()
                try:
                    out = await generate_briefs(uuid.UUID(it["id"]), [a.lens])
                except Exception as e:  # noqa: BLE001
                    print(f"    ! {it['id'][:8]}: {str(e)[:90]}", file=sys.stderr)
                    rows.append({"id": it["id"], "failed": True, "secs": time.monotonic() - t0})
                    continue
                secs = time.monotonic() - t0
                brief = (out.get(a.lens) or {}).get("text") or ""
                if not brief:
                    rows.append({"id": it["id"], "failed": True, "secs": secs})
                    continue
                settings.prism_model_correlate = incumbent  # the judge is not the candidate
                try:
                    g = await judge_grounded({"record": it["record"], "brief": brief})
                    r = await rubric(it["record"], brief)
                    rows.append({"id": it["id"], "secs": secs, "words": len(brief.split()), "grounded": g.grounded,
                                 "clear": r.clear, "complete": r.complete, "neutral": r.neutral, "brief": brief})
                except Exception as e:  # noqa: BLE001
                    print(f"    ! judge {it['id'][:8]}: {str(e)[:90]}", file=sys.stderr)
                    rows.append({"id": it["id"], "secs": secs, "words": len(brief.split()), "unjudged": True, "brief": brief})
                finally:
                    settings.prism_model_correlate = model
            after = await brief_spend()
            results.append(summarise(spec, len(items), rows, tuple(x - y for x, y in zip(after, before, strict=True))))
    finally:
        settings.prism_model_correlate = incumbent
        briefs_mod.structured_chat = real_structured_chat
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(results, indent=1))
    keys = ["failed", "grounded", "clear", "complete", "neutral", "words", "secs", "max_secs", "out_tok", "usd"]
    print(f"\n  {'model':30} " + " ".join(f"{k:>9}" for k in keys))
    for r in results:
        print(f"  {r['model']:30} " + " ".join(f"{str(r[k]):>9}" for k in keys))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
