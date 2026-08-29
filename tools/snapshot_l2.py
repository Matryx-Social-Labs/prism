"""Offline snapshot for the L2 story-layer rebuild: embeddings, time, and actors.

    uv run python -m tools.snapshot_l2      # pull from production, READ-ONLY

`tools/sweep_partition.py` already snapshots a graph, but not one this can use. It
stores the ENTITY edge list and no embeddings, because v1's story layer is built
from IDF-weighted shared actors — the very representation the rebuild exists to
replace (Nallapati CIKM 2004: person-name overlap made news clustering worse,
0.50 -> 0.45 F1; our own entity-only story layer plateaus at F1 0.47).

TWO DELIBERATE DIFFERENCES FROM THE v1 SNAPSHOT, both about honest measurement:

1. NO TIME WINDOW. v1 loads events from the last STORY_WINDOW_DAYS=30, baked into
   module-level SQL. The corpus has been frozen since ingestion was switched off,
   but that window keeps sliding, and it has now slid past the gold set: of the 86
   events in `tools/gold_stories`, only 48 are still inside 30 days. Scoring a
   configuration against 48 of 86 labelled events is precisely the "measured on a
   slice restricted to the evaluation set" error this repo has already made once
   and written down. So this takes every non-CVE event — 5,413 of them, all
   embedded — and the gold set is fully covered.

2. EMBEDDINGS, L2-NORMALISED. Stored unit-length so cosine similarity is a plain
   dot product and the sweep never re-normalises in an inner loop. 5,413 x 768
   float32 is ~16 MB, small enough to hold in memory for a full pairwise pass.

CVE records are excluded for the same reason v1 excludes them: they cluster by
identity, not by narrative, and 1638 of them once collapsed into 7 under fuzzy
matching. They are not what the story layer is for.

Actors are still collected. They are demoted from primary signal to secondary
confirmation, not deleted — the plan's L2 keeps entities as a confirm gate — and
`df` is here so any use of them is IDF-weighted rather than raw-count, which is
the lesson already recorded in [[prism-idf-not-df-cutoff]].
"""

from __future__ import annotations

import asyncio
import gzip
import json
import os
import re
import subprocess
from pathlib import Path

SNAPSHOT = Path(".cache/l2_snapshot.json.gz")
VECTORS = Path(".cache/l2_snapshot.npz")


def _prod_url() -> str:
    raw = os.environ.get("REPAIR_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        out = subprocess.run(
            ["railway", "variables", "--service", "Postgres", "--kv"],
            capture_output=True, text=True, timeout=120,
        ).stdout
        raw = next(
            ln.split("=", 1)[1].strip() for ln in out.splitlines() if ln.startswith("DATABASE_URL=")
        )
    return re.sub(r"^postgres(ql)?(\+asyncpg)?://", "postgresql://", raw)


async def build() -> None:
    import asyncpg
    import numpy as np

    c = await asyncpg.connect(_prod_url(), timeout=180)
    try:
        # Belt and braces: the server refuses writes even if the code is wrong.
        await c.execute("SET default_transaction_read_only = on")
        rows = await c.fetch(
            """
            SELECT e.id::text AS id, e.title, e.sector, e.regions,
                   extract(epoch FROM coalesce(e.occurred_at, e.first_seen_at)) AS ts,
                   e.embedding::text AS emb,
                   (SELECT count(*) FROM event_memberships m WHERE m.event_id = e.id) AS source_count
            FROM events e
            WHERE coalesce(e.title, '') !~ '^CVE-'
              AND e.embedding IS NOT NULL
            ORDER BY e.id
            """
        )
        # The TEXT each event's stored vector was built from — the first chunk of
        # the earliest article, matching `_first_chunk_embedding`. Carried so a
        # different encoder can be measured on identical input: comparing mpnet on
        # first-chunk text against another model on titles would measure the text,
        # not the model.
        chunks = await c.fetch(
            """
            SELECT DISTINCT ON (m.event_id) m.event_id::text AS eid, ch.text AS content
            FROM event_memberships m
            JOIN article_chunks ch ON ch.article_id = m.article_id AND ch.chunk_index = 0
            ORDER BY m.event_id, m.created_at, m.article_id
            """
        )
        # Actors follow the FOLDED entity graph: entities.merged_into is resolved
        # here, so a snapshot taken before and after a fold cannot disagree about
        # who is in an event.
        ent = await c.fetch(
            """
            SELECT ee.event_id::text AS eid, coalesce(t.slug, en.slug) AS slug
            FROM event_entities ee
            JOIN entities en ON en.id = ee.entity_id
            LEFT JOIN entities t ON t.id = en.merged_into
            WHERE en.entity_type IN ('person', 'organization')
            """
        )
    finally:
        await c.close()

    ids = [r["id"] for r in rows]
    index = {eid: i for i, eid in enumerate(ids)}
    text_by_event = {r["eid"]: (r["content"] or "") for r in chunks}
    actors: list[list[str]] = [[] for _ in ids]
    for r in ent:
        i = index.get(r["eid"])
        if i is not None:
            actors[i].append(r["slug"])
    actors = [sorted(set(a)) for a in actors]
    df: dict[str, int] = {}
    for a in actors:
        for slug in a:
            df[slug] = df.get(slug, 0) + 1

    # pgvector renders as '[a,b,...]'; parse once here rather than per sweep run.
    mat = np.asarray(
        [np.fromstring(r["emb"].strip("[]"), sep=",", dtype=np.float32) for r in rows],
        dtype=np.float32,
    )
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0          # a zero vector stays zero rather than becoming NaN
    mat /= norms

    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(SNAPSHOT, "wt") as fh:
        json.dump(
            {
                "ids": ids,
                "titles": [r["title"] for r in rows],
                "ts": [float(r["ts"]) if r["ts"] is not None else None for r in rows],
                "source_count": [int(r["source_count"] or 0) for r in rows],
                "sector": [r["sector"] for r in rows],
                "regions": [list(r["regions"] or []) for r in rows],
                "actors": actors,
                "df": df,
                "text": [text_by_event.get(e, "") for e in ids],
            },
            fh,
        )
    np.savez_compressed(VECTORS, emb=mat)

    from tools.gold_stories import STORIES

    gold = {e for v in STORIES.values() for e in v}
    covered = len(gold & set(ids))
    have_text = sum(1 for e in ids if text_by_event.get(e))
    print(f"  events   : {len(ids)}   dim {mat.shape[1]}   with source text {have_text}")
    print(f"  actors   : {sum(len(a) for a in actors)} links over {len(df)} distinct")
    print(f"  gold     : {covered}/{len(gold)} events present")
    if covered < len(gold):
        # Loudly, because a partial gold set silently inflates or deflates every
        # score computed against it and still looks like a normal result.
        print("  WARNING: gold set is NOT fully covered — scores would be on a slice")
    print(f"  wrote    : {SNAPSHOT}  {VECTORS}")


if __name__ == "__main__":
    asyncio.run(build())
