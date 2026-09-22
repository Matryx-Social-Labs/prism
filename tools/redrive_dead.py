"""Read and re-drive the dead-letter streams.

`common/stream._dead_letter` has written every permanently-failed payload to
`<topic>.dead` since the streams existed, and nothing has ever read one back
(audit H10). `/healthz` counts them, so an operator learns that items died —
and then has only XRANGE by hand to find out which, or to give them another
run after the bug is fixed.

    uv run python -m tools.redrive_dead --list                    # what is in there, by error
    uv run python -m tools.redrive_dead --list --topic raw.items  # one topic
    uv run python -m tools.redrive_dead --show 1758537600000-0    # one payload in full
    uv run python -m tools.redrive_dead --redrive --topic raw.items --limit 50
    uv run python -m tools.redrive_dead --redrive --match LlmQuotaError --yes

Re-driving republishes the ORIGINAL payload to its own topic and deletes the
dead entry only once the publish returned. Every stage handler is idempotent,
so an entry that turns out to have been processed after all is a no-op.
Read-only unless --redrive, and --redrive without --yes prints what it would
do and stops.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter

from common.logging import get_logger
from common.stream import TOPIC_GROUPS, get_redis

logger = get_logger(__name__)

DEAD_SUFFIX = ".dead"


def dead_topics() -> list[str]:
    return [f"{topic}{DEAD_SUFFIX}" for topic, _ in TOPIC_GROUPS]


def _decode(value) -> str:
    return value.decode() if isinstance(value, bytes) else str(value)


async def read_dead(topic: str, limit: int) -> list[tuple[str, dict]]:
    r = get_redis()
    entries = await r.xrange(topic, count=limit)
    return [(_decode(eid), {_decode(k): _decode(v) for k, v in fields.items()}) for eid, fields in entries]


async def list_dead(topics: list[str], limit: int) -> int:
    total = 0
    for topic in topics:
        entries = await read_dead(topic, limit)
        if not entries:
            continue
        total += len(entries)
        by_error = Counter(e.get("error", "(none)").split(":")[0] for _, e in entries)
        print(f"\n{topic}: {len(entries)}")
        for error, n in by_error.most_common():
            print(f"  {n:5d}  {error}")
        first, last = entries[0], entries[-1]
        print(f"  oldest {first[0]}  newest {last[0]}")
        print(f"  e.g. {last[1].get('error', '')[:160]}")
    if not total:
        print("nothing dead-lettered")
    return total


async def show(entry_id: str, topics: list[str]) -> int:
    for topic in topics:
        for eid, fields in await read_dead(topic, 1000):
            if eid == entry_id:
                print(f"{topic} {eid}")
                for k, v in fields.items():
                    print(f"  {k}: {v[:2000]}")
                return 0
    print(f"no dead entry {entry_id}", file=sys.stderr)
    return 1


async def redrive(topics: list[str], limit: int, match: str | None, apply: bool) -> int:
    """Republish each dead payload to its live topic, then delete the entry."""
    from common import stream

    r = get_redis()
    moved = 0
    for dead in topics:
        live = dead[: -len(DEAD_SUFFIX)]
        for eid, fields in await read_dead(dead, limit):
            if match and match not in fields.get("error", ""):
                continue
            raw = fields.get("data") or ""
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                print(f"  skip {eid}: payload is not JSON ({raw[:80]})")
                continue
            if not apply:
                print(f"  would redrive {eid} -> {live}: {raw[:120]}")
                moved += 1
                continue
            await stream.publish(live, payload)
            # Delete only after the publish returned: a crash between the two
            # replays an item, which every handler tolerates, where the reverse
            # order would lose it for good.
            await r.xdel(dead, eid)
            logger.info("redriven", topic=live, entry_id=eid)
            moved += 1
    print(f"{'redrove' if apply else 'would redrive'} {moved} entr{'y' if moved == 1 else 'ies'}")
    return moved


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", help="one live topic (raw.items, classified.items, enriched.items)")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--show", metavar="ENTRY_ID")
    ap.add_argument("--redrive", action="store_true")
    ap.add_argument("--match", help="only entries whose error contains this")
    ap.add_argument("--yes", action="store_true", help="actually republish; without it, a dry run")
    args = ap.parse_args()

    topics = [f"{args.topic}{DEAD_SUFFIX}"] if args.topic else dead_topics()
    if args.show:
        return await show(args.show, topics)
    if args.redrive:
        await redrive(topics, args.limit, args.match, apply=args.yes)
        return 0
    await list_dead(topics, args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
