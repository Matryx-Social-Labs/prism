"""One-off (2026-09-20, kept for the next time a feed is added): for each event a
whole-site language paper's stamp filed under a state while the
story involves another country: ask whether the event is LOCAL to that state (a
state government, a city, a district, a state-based body). Keep the code only then."""
import asyncio
import sys

from pydantic import BaseModel, Field
from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from common.llm import REASONING_OFF, structured_chat
from common.regions import IN_STATES

NAMES = dict(IN_STATES)
LOCAL_SECTIONS = ["thehindu_tamilnadu", "thehindu_kerala", "thehindu_karnataka", "thehindu_andhra", "thehindu_telangana", "toi_delhi", "toi_mumbai"]
Q = """
SELECT e.id, e.title, e.regions, e.projection->'lens_briefs'->>'reader' AS brief FROM events e
WHERE e.last_updated_at > now() - interval '30 days'
  AND EXISTS (SELECT 1 FROM unnest(e.regions) r WHERE r LIKE 'IN-%')
  AND EXISTS (SELECT 1 FROM unnest(e.regions) r WHERE r <> 'IN' AND r NOT LIKE 'IN-%')
  AND NOT EXISTS (
      SELECT 1 FROM event_memberships m JOIN articles a ON a.id = m.article_id JOIN raw_items ri ON ri.id = a.raw_item_id
      JOIN sources so ON so.id = ri.source_id WHERE m.event_id = e.id AND so.slug = ANY(:local))
ORDER BY e.last_updated_at DESC
"""
class Local(BaseModel):
    local: bool = Field(description="true only if the event is local to the named state: its government, a city, a district, a court, a company or body based there acting there; false for a national or foreign event the state's papers merely reported")
async def main():
    run = "--run" in sys.argv
    model = get_settings().prism_model_gate
    async with session_scope() as s:
        rows = (await s.execute(text(Q), {"local": LOCAL_SECTIONS})).all()
    keep = clear = 0
    async with session_scope() as s:
        for eid, title, regions, brief in rows:
            states = [r for r in regions if r.startswith("IN-")]
            names = ", ".join(NAMES.get(c, c) for c in states)
            try:
                out = await structured_chat(model=model, messages=[
                {"role": "system", "content": "You decide whether a news event is LOCAL to an Indian state. Reply with a JSON object {\"local\": true|false} and nothing else."},
                {"role": "user", "content": f"State: {names}\nHeadline: {title}\nRecord: {(brief or '')[:500]}"}],
                    output_model=Local, trace_name="unstamp", max_tokens=60, temperature=0, reasoning=REASONING_OFF)
            except ValueError:
                keep += 1  # undecided: leave the stamp
                continue
            if out.local:
                keep += 1
                continue
            clear += 1
            print("  clear", states, "|", title[:80])
            if run:
                await s.execute(text("UPDATE events SET regions = :r WHERE id = :id"), {"r": [x for x in regions if not x.startswith("IN-")], "id": eid})
    print(f"kept {keep} local · cleared {clear}{' (dry run)' if not run else ''}")
asyncio.run(main())
