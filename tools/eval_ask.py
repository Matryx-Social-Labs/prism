"""Ask groundedness — the gate for the redesign (PLAN-LAUNCH.md §2, ≥ 0.95).

Samples live events with several reports, asks each two questions — one any
reader asks, one an analyst asks — through the real `answer_stream` (the same
retrieval, prompt, model tiering and structured tail as production), then has
the judge score every answer against the very excerpts the agent was shown.
Table rows are judged with the prose: an invented figure in a table is still
an invented figure.

Read-only against whatever DATABASE_URL points at: `_persist_turn` is stubbed,
so no agent session or message is written. One answer + one judge call per
question; 50 questions cost well under a dollar on the free tier.

Usage:  uv run python tools/eval_ask.py [--events 25] [--plan free|plus] [--out /tmp/eval-ask.jsonl]
Needs OPENROUTER_API_KEY, LLM_PROVIDER=openrouter and a real PRISM_MODEL_JUDGE
in the environment (the laptop .env points the judge at a local Ollama model).
"""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy import text

import agent.rag as rag
from common.config import get_settings
from common.db import session_scope
from common.llm import structured_chat
from common.observability import fetch_prompt

EVERYONE = [
    "What happened, in short?",
    "Why does this matter?",
    "What changed most recently?",
    "Who is involved and what did they say?",
]
ANALYST = [
    "Which outlets reported this, and what did only one of them report?",
    "What numbers are given, and do any of the reports disagree on them?",
    "Give me a timeline of what changed, with dates.",
    "Give me every direct quote in the reports, with who said it.",
]
GATE = 0.95


class Verdict(BaseModel):
    grounded: float = Field(ge=0.0, le=1.0)
    citation_quality: float = Field(ge=0.0, le=1.0)
    correct_refusal: bool | None = None
    reasoning: str = ""


async def _events(n: int) -> list[tuple[uuid.UUID, str]]:
    async with session_scope() as s:
        rows = (
            await s.execute(
                text(
                    """
                    SELECT e.id, e.title
                    FROM events e
                    WHERE e.last_updated_at > now() - interval '7 days'
                      AND (SELECT count(*) FROM event_memberships m WHERE m.event_id = e.id) >= 3
                    ORDER BY random()
                    LIMIT :n
                    """
                ),
                {"n": n},
            )
        ).all()
    return [(r[0], r[1]) for r in rows]


async def _ask(event_id: uuid.UUID, question: str, plan: str) -> tuple[str, str, dict | None]:
    """The answer as the reader gets it, plus the excerpts the model was shown."""
    chunks, _, _ = await rag.retrieve_grounding(event_id, question, story_wide=plan == "plus")
    sources = "\n\n".join(f"[{c.number}] ({c.source_name}) {c.text}" for c in chunks)
    prose, structure = "", None
    async for ev in rag.answer_stream(event_id=event_id, session_id=uuid.uuid4(), question=question, plan=plan):
        if ev["type"] == "token":
            prose += ev["text"]
        elif ev["type"] == "structure":
            structure = ev
        elif ev["type"] == "error":
            prose += f" [error: {ev['message']}]"
    return prose, sources, structure


def _judged_text(prose: str, structure: dict | None) -> str:
    if not structure:
        return prose
    lines = [prose]
    for r in structure.get("rows") or []:
        lines.append(f"Table row: {r['a']} — {r['b']} {r['n']}".strip())
    if structure.get("gaps"):
        lines.append(f"Not in the reports: {structure['gaps']}")
    return "\n".join(lines)


async def _judge(sources: str, question: str, answer: str) -> Verdict:
    prompt = fetch_prompt("judge-groundedness")
    messages = prompt.compile(sources=sources, question=question, answer=answer)
    return await structured_chat(
        model=get_settings().prism_model_judge,
        messages=messages,
        output_model=Verdict,
        trace_name="judge-groundedness",
        temperature=0,
    )


async def main(n_events: int, plan: str, out: Path) -> int:
    async def _no_write(*_a, **_k):
        return None

    rag._persist_turn = _no_write  # read-only: nothing lands in agent_sessions/messages
    events = await _events(n_events)
    if not events:
        print("no events with 3+ reports in the last 7 days", file=sys.stderr)
        return 2
    rows: list[dict] = []
    for i, (eid, title) in enumerate(events):
        for q in (EVERYONE[i % len(EVERYONE)], ANALYST[i % len(ANALYST)]):
            prose, sources, structure = await _ask(eid, q, plan)
            v = await _judge(sources, q, _judged_text(prose, structure))
            row = {
                "event_id": str(eid), "title": title, "question": q, "plan": plan,
                "answer": prose, "structure": structure,
                "grounded": v.grounded, "citation_quality": v.citation_quality,
                "correct_refusal": v.correct_refusal, "reasoning": v.reasoning,
            }
            rows.append(row)
            flag = "" if v.grounded >= 0.9 else "  <-- LOW"
            print(f"{v.grounded:.2f} cit {v.citation_quality:.2f}  {title[:48]:<48} | {q[:52]}{flag}")
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    g = sum(r["grounded"] for r in rows) / len(rows)
    c = sum(r["citation_quality"] for r in rows) / len(rows)
    tables = sum(1 for r in rows if r["structure"] and r["structure"].get("rows"))
    gaps = sum(1 for r in rows if r["structure"] and r["structure"].get("gaps"))
    wrong_refusals = sum(1 for r in rows if r["correct_refusal"] is False)
    print(f"\n{len(rows)} questions on {len(events)} events, plan={plan}")
    print(f"grounded mean {g:.3f}  citation_quality mean {c:.3f}  gate {GATE} -> {'PASS' if g >= GATE else 'FAIL'}")
    print(f"tables {tables}  'not in the reports' lines {gaps}  wrong refusals {wrong_refusals}  below 0.9: {sum(1 for r in rows if r['grounded'] < 0.9)}")
    print(f"rows -> {out}")
    return 0 if g >= GATE else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=25)
    ap.add_argument("--plan", choices=("free", "plus"), default="free")
    ap.add_argument("--out", type=Path, default=Path("/tmp/eval-ask.jsonl"))
    a = ap.parse_args()
    sys.exit(asyncio.run(main(a.events, a.plan, a.out)))
