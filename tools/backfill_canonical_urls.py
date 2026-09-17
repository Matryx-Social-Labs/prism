"""Backfill ``raw_items.url_canonical`` without changing source URLs.

Default is a read-only count and a few before/after examples.  ``--apply`` writes
only rows whose canonical key is missing; reruns are safe.  If the canonicalizer
version changes, add an explicit ``--rewrite`` mode rather than silently changing
keys produced by an earlier release.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import text

from common.db import get_session_factory
from common.urls import CANONICAL_URL_VERSION, canonicalize_url


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()

    async with get_session_factory()() as session:
        rows = (await session.execute(text(
            "SELECT id, url FROM raw_items "
            "WHERE url IS NOT NULL AND url_canonical IS NULL ORDER BY id"
        ))).mappings().all()

    changed = [(row["id"], row["url"], canonicalize_url(row["url"])) for row in rows]
    changed = [(rid, old, new) for rid, old, new in changed if new]
    decorated = sum(old != new for _, old, new in changed)
    print(
        f"canonical URL v{CANONICAL_URL_VERSION}: {len(changed)} rows missing a key; "
        f"{decorated} normalise to a different string"
    )
    for _, old, new in [x for x in changed if x[1] != x[2]][:10]:
        print(f"  {old}\n    -> {new}")
    if not args.apply:
        print("dry run — pass --apply after the migration is deployed")
        return 0

    factory = get_session_factory()
    written = 0
    for start in range(0, len(changed), args.batch_size):
        batch = changed[start:start + args.batch_size]
        async with factory() as session:
            await session.execute(
                text("UPDATE raw_items SET url_canonical = :canonical, "
                     "url_canonical_version = :version WHERE id = :id"),
                [{"id": rid, "canonical": canonical, "version": CANONICAL_URL_VERSION}
                 for rid, _, canonical in batch],
            )
            await session.commit()
        written += len(batch)
        print(f"  written {written}/{len(changed)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
