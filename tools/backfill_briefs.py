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
  --sync [N]      no batch: call the chat endpoint directly for up to N events
                  (default all), newest first, 8 at a time, persisting as it goes.
                  Full price; the trial batch sat in_progress for 22h with 0/10 done.
  --rewrite-days N  rewrite the briefs of the last N days even where one exists
                  (the 2026-09-20 prompt: standalone sentences the page prints as points)
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
from common.llm import _parse_json_loose
from correlation.briefs import persist_briefs
from correlation.consumer import extracted_reader_brief

BATCHES = "https://openrouter.ai/api/beta/batches"
SYSTEM = (
    "You write for a general reader of Indian news. Given one news report, return JSON with two keys: "
    '"reader_brief" — three to five plain English sentences for a general reader, each ONE fact that stands on its '
    "own (the page prints them as separate points): no 'however', 'meanwhile' or 'this' carrying over from the "
    "sentence before, no pronoun for something named in an earlier sentence; the first says what happened, the "
    'last why it matters; only what the report states, no opinion; and "watch_points" — up to three one-line things '
    "to watch next that the report itself points to, an empty list if none. Respond with the JSON object only."
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
    """The model's JSON, tolerating a fence or trailing prose; None when it is
    not a brief."""
    try:
        data = _parse_json_loose(content)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    # glm-5.3-flash under json_object (no schema) sometimes wraps the object in a
    # single key ({"answer": {...}} or {"answer": "<json string>"}) and sometimes
    # writes the brief as a list of sentences — 7 of 40 on the first sync runs.
    # Unwrap and join; nothing else.
    if len(data) == 1 and "reader_brief" not in data:
        inner = next(iter(data.values()))
        if isinstance(inner, str):
            try:
                inner = _parse_json_loose(inner)
            except ValueError:
                return None
        if isinstance(inner, dict):
            data = inner
    if isinstance(data.get("reader_brief"), list):
        data = {**data, "reader_brief": " ".join(str(x).strip() for x in data["reader_brief"])}
    return extracted_reader_brief(data)


async def run_sync(todo, model: str, headers: dict) -> int:
    """The batch bodies, sent one by one through the live endpoint. Mandatory-
    reasoning models (glm) get the smallest effort so the 400-token ceiling is
    spent on the brief, not on thinking."""
    sem = asyncio.Semaphore(8)
    written = skipped = 0

    async def one(http, ev):
        nonlocal written, skipped
        # English is asked for again here, and the ceiling raised: a Hindi source
        # had glm answer in Devanagari and run out of tokens at 400.
        body = {"model": model, "reasoning": {"effort": "minimal"}, **request_for(ev)["body"], "max_tokens": 900}
        body["messages"][-1]["content"] += "\n\nWrite the brief in English."
        async with sem:
            try:
                r = await http.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, content=json.dumps(body))
                content = ((((r.json().get("choices") or [{}])[0]).get("message") or {}).get("content") or "") if r.status_code == 200 else ""
            except (httpx.HTTPError, ValueError):
                content = ""
        brief = parse(content)
        if not brief:
            skipped += 1
            return
        await persist_briefs(__import__("uuid").UUID(ev["id"]), {"reader": brief})
        written += 1
        if written % 200 == 0:
            print(f"  {written} written, {skipped} skipped", flush=True)

    async with httpx.AsyncClient(timeout=120) as http:
        await asyncio.gather(*[one(http, ev) for ev in todo])
    print(f"written {written}, skipped {skipped} of {len(todo)} on {model}")
    return 0


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--submit", nargs="?", const=500, type=int, default=None)
    ap.add_argument("--collect", default=None)
    ap.add_argument("--sync", nargs="?", const=0, type=int, default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--rewrite-days", type=int, default=None)
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

    limit = args.submit or args.sync or None
    select = MISSING
    if args.rewrite_days:
        select = MISSING.replace("WHERE e.projection->'lens_briefs'->>'reader' IS NULL", f"WHERE e.last_updated_at > now() - interval '{int(args.rewrite_days)} days'")
    async with get_session_factory()() as session:
        todo = (await session.execute(text(select + " ORDER BY e.last_updated_at DESC" + (f" LIMIT {int(limit)}" if limit else "")))).mappings().all()
    if args.sync is not None:
        return await run_sync(todo, model, headers)
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
