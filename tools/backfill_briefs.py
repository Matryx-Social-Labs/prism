"""Write the Reader brief for every event that has none, through OpenRouter's
batch endpoint at half price.

The extractor writes the brief for every event born after dd35074; this pass
covers the corpus before it (6,331 single-source events on prod on 2026-09-17,
and the multi-source events whose brief a rebuild had dropped). A batch is
asynchronous with a 24-hour window and billed at 50% of the model's price,
which is the right shape for a backfill and the wrong one for the live path.

  (default)       count and estimate; write nothing, submit nothing
  --submit [N]    submit one batch of up to N events (default 500); prints the batch id
  --collect ID    fetch a finished batch and persist its briefs
  --model M       the model slug (default: the light extract model)

State is the event row itself: a collected brief lands in projection.lens_briefs,
so a re-run only ever picks up what is still missing.
"""

import argparse
import asyncio
import json
import sys

import httpx
from sqlalchemy import text

from common.config import get_settings
from common.db import get_session_factory
from correlation.briefs import persist_briefs
from correlation.consumer import extracted_reader_brief

BATCHES = "https://openrouter.ai/api/beta/batches"
SYSTEM = (
    "You write for a general reader of Indian news. Given one news report, return JSON with two keys: "
    '"reader_brief" — three or four plain English sentences on what happened and why it matters, only what the '
    "report states, no opinion, no lists; and \"watch_points\" — up to three one-line things to watch next that the "
    "report itself points to, an empty list if none. Respond with the JSON object only."
)
MISSING = (
    "SELECT e.id::text AS id, e.title, e.summary, a.clean_text "
    "FROM events e JOIN event_memberships m ON m.event_id = e.id AND m.is_survivor "
    "JOIN articles a ON a.id = m.article_id "
    "WHERE e.projection->'lens_briefs'->>'reader' IS NULL"
)


def request_for(ev) -> dict:
    body = (ev["clean_text"] or "")[:6000]
    return {
        "custom_id": ev["id"],
        "body": {
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Headline: {ev['title']}\nSummary: {ev['summary'] or ''}\n\nReport:\n{body}"},
            ],
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
        },
    }


def parse(content: str) -> dict | None:
    """The model's JSON, tolerating a fence; None when it is not a brief."""
    s = content.strip()
    if s.startswith("```"):
        s = s.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        return None
    return extracted_reader_brief(data) if isinstance(data, dict) else None


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--submit", nargs="?", const=500, type=int, default=None)
    ap.add_argument("--collect", default=None)
    ap.add_argument("--model", default=None)
    args = ap.parse_args()
    settings = get_settings()
    model = args.model or settings.prism_model_extract_light
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json"}

    if args.collect:
        async with httpx.AsyncClient(timeout=120) as http:
            r = await http.get(f"{BATCHES}/{args.collect}", headers=headers)
            r.raise_for_status()
            batch = r.json()
        print(f"batch {args.collect}: {batch.get('status')} · {batch.get('request_counts')} · usage {batch.get('usage')}")
        if batch.get("status") != "completed":
            return 0
        written = skipped = 0
        for res in batch.get("results", []):
            resp = res.get("response") or {}
            content = (((resp.get("body") or {}).get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            brief = parse(content) if resp.get("status_code") == 200 else None
            if not brief:
                skipped += 1
                continue
            await persist_briefs(__import__("uuid").UUID(res["custom_id"]), {"reader": brief})
            written += 1
        print(f"written {written}, skipped {skipped}")
        return 0

    async with get_session_factory()() as session:
        todo = (await session.execute(text(MISSING + " ORDER BY e.last_updated_at DESC" + (f" LIMIT {int(args.submit)}" if args.submit else "")))).mappings().all()
    print(f"{len(todo)} events without a Reader brief; ~{len(todo) * 1.6 / 1000:.2f}M input + ~{len(todo) * 0.25 / 1000:.2f}M output tokens on {model} at batch price")
    if not args.submit:
        print("dry run — pass --submit [N] to send one batch, then --collect <id> when it completes")
        return 0
    payload = {"endpoint": "/v1/chat/completions", "model": model, "requests": [request_for(ev) for ev in todo]}
    async with httpx.AsyncClient(timeout=300) as http:
        r = await http.post(BATCHES, headers=headers, content=json.dumps(payload))
        if r.status_code >= 400:
            print(f"submit failed {r.status_code}: {r.text[:400]}", file=sys.stderr)
            return 1
        b = r.json()
    print(f"submitted batch {b.get('id')} · status {b.get('status')} · {len(todo)} requests")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
