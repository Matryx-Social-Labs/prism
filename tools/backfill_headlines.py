"""Write Prism's headline for every event that still carries an outlet's words.

Founder decision 1(b), 2026-09-17: the canonical title is a Prism-written
headline from the reports, labelled as ours. New events get one from the
extractor (`SharedExtraction.headline`); this pass covers the corpus that
existed before, because ingestion is frozen and nothing else will.

  (default)  count what would be written and estimate the spend; touches nothing
  --apply    write `events.title` + `events.headline_by = 'prism'`
  --limit N  stop after N events (try 20 first and read them)

The outlet's own headline is not lost: it stays on the survivor's raw item and
prints under Sources. The model sees the extractor's summary and up to four
outlet headlines and returns one English headline of at most twelve words;
anything longer, empty, or quoting is rejected and the event is left as it is.
Spend is an LLM call per event on the light extract model; this is the
founder's decision to make, which is why the default is a dry run.
"""

import argparse
import asyncio
import re
import sys

from pydantic import BaseModel, Field
from sqlalchemy import text

from common.config import get_settings
from common.db import get_session_factory
from common.llm import structured_chat

MAX_WORDS = 12
# One event's prompt is ~350 input tokens and the answer ~25; the estimate uses
# those, and the rate is the light extract model's published input price.
TOKENS_IN, TOKENS_OUT = 350, 25


class Headline(BaseModel):
    headline: str = Field(description=f"At most {MAX_WORDS} words, English, present tense, neutral, no quotation marks")


def acceptable(h: str) -> bool:
    h = h.strip()
    return 0 < len(h.split()) <= MAX_WORDS and not re.search(r'["“”]', h) and not h.endswith(".")


async def write_one(session, ev, sources: list[str]) -> str | None:
    messages = [
        {"role": "system", "content": "You write neutral news headlines in English for an Indian news reader. Use only what the reports state. No opinion, no quotation marks, no trailing full stop, at most twelve words."},
        {"role": "user", "content": "Summary: " + (ev["summary"] or "") + "\n\nOutlet headlines:\n" + "\n".join(f"- {s}" for s in sources) + "\n\nWrite the headline."},
    ]
    out = await structured_chat(model=get_settings().prism_model_extract_light, messages=messages, output_model=Headline, trace_name="backfill-headline", max_tokens=80)
    return out.headline.strip() if acceptable(out.headline) else None


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    async with get_session_factory()() as session:
        todo = (await session.execute(text(
            "SELECT e.id, e.title, e.summary FROM events e WHERE e.headline_by IS NULL "
            "AND EXISTS (SELECT 1 FROM event_memberships m WHERE m.event_id = e.id) ORDER BY e.last_updated_at DESC"
            + (f" LIMIT {int(args.limit)}" if args.limit else "")
        ))).mappings().all()
        print(f"{len(todo)} events carry an outlet's headline; ~{len(todo) * TOKENS_IN / 1e6:.2f}M input + ~{len(todo) * TOKENS_OUT / 1e6:.3f}M output tokens on {get_settings().prism_model_extract_light}")
        if not args.apply:
            print("dry run — pass --apply to write (try --limit 20 first)")
            return 0
        written = skipped = 0
        # Eight in flight: sequential, seven thousand events is hours; the
        # light model tolerates this comfortably. Each event commits alone, so
        # a crash leaves nothing half-written and a rerun resumes.
        sem = asyncio.Semaphore(args.concurrency)

        async def one(ev) -> None:
            nonlocal written, skipped
            async with sem, get_session_factory()() as s:
                heads = (await s.execute(text(
                    "SELECT ri.title FROM event_memberships m JOIN articles a ON a.id = m.article_id JOIN raw_items ri ON ri.id = a.raw_item_id "
                    "WHERE m.event_id = :eid ORDER BY m.is_survivor DESC, ri.published_at ASC NULLS LAST LIMIT 4"
                ), {"eid": ev["id"]})).scalars().all()
                try:
                    h = await write_one(s, ev, [t for t in heads if t] or [ev["title"]])
                except Exception as e:  # one bad call must not end the pass
                    print(f"  ! {ev['id']}: {e}", file=sys.stderr)
                    h = None
                if not h:
                    skipped += 1
                    return
                await s.execute(text("UPDATE events SET title = :t, headline_by = 'prism' WHERE id = :eid"), {"t": h, "eid": ev["id"]})
                await s.commit()
                written += 1
                print(f"  {ev['id']}  {h}", flush=True)

        await asyncio.gather(*(one(ev) for ev in todo))
        print(f"written {written}, skipped {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
