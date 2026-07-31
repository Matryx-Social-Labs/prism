"""Score production's clustering against the hand labels. Read-only.

    uv run python -m tools.score_clustering

Prints B-cubed, macro purity and cluster counts for the labelled slice, overall
and per predicted cluster.

THIS SCORES THE ROWS IN PRODUCTION, NOT THE CURRENT MATCHER. Those are different
things and confusing them will send you off building the wrong fix:

    this tool        (production as STORED)   P=0.2908  purity=0.4842   6 clusters
    scratch --score  (today's find_event)     P=0.8017  purity=0.9223  71 clusters

Same articles, same labels. Production's rows were written before the 0.0.79-81
fixes, so what this measures is accumulated historical damage. Use it to decide
whether a REPAIR pass is worth running. To judge a change to
correlation/clustering.py, use `tools/scratch --score`, which replays the articles
through the real find_event.

READ THE NUMBERS CORRECTLY. tools/gold_labels covers only the six largest
production events, chosen because that is where fusion is worst. So:

  - B-cubed PRECISION and macro purity are meaningful: they measure how much
    unrelated material each cluster has absorbed, which is the defect.
  - B-cubed RECALL is not. Almost everything in this slice is over-merged, so
    recall starts near 1.0 by construction and can only fall. A change that
    improves precision at some cost to recall is probably good, and this set
    cannot tell you how much recall it really cost.
  - The cluster COUNT against gold is the honest headline.

Do not quote an F1 from this as "Prism's clustering accuracy". It is a
regression suite for one failure mode, not a corpus sample.
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess

import asyncpg

from correlation.cluster_metrics import score
from tools.gold_labels import GOLD, gold_event_count, labelled_article_count


def _db_url() -> str:
    raw = os.environ.get("REPAIR_DATABASE_URL")
    if not raw:
        out = subprocess.run(
            ["railway", "variables", "--service", "Postgres", "--kv"],
            capture_output=True, text=True, timeout=90,
        ).stdout
        for line in out.splitlines():
            if line.startswith("DATABASE_URL="):
                raw = line.split("=", 1)[1].strip()
                break
    if not raw:
        raise SystemExit("no database url (set REPAIR_DATABASE_URL)")
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw)


async def fetch_membership(c: asyncpg.Connection) -> dict[str, str]:
    """article_id -> the event that currently holds it, for labelled articles only.

    Keyed by article id, so it keeps working after a repair moves articles between
    events. The first version indexed labels positionally and broke the first time
    a repair ran.
    """
    rows = await c.fetch(
        "SELECT article_id::text AS aid, event_id::text AS eid "
        "FROM event_memberships WHERE article_id = ANY($1::uuid[])",
        list(GOLD),
    )
    return {r["aid"]: r["eid"] for r in rows}


async def main() -> None:
    c = await asyncpg.connect(_db_url(), timeout=60)
    try:
        await c.execute("SET default_transaction_read_only = on")
        predicted = await fetch_membership(c)
    finally:
        await c.close()

    missing = set(GOLD) - set(predicted)
    print(f"gold: {labelled_article_count()} articles, {gold_event_count()} real events")
    if missing:
        print(f"  !! {len(missing)} labelled article(s) hold no membership — excluded")

    s = score(predicted, GOLD)
    print(f"\nscored {s.items} articles")
    print(f"  B3 precision  {s.b3_precision:.4f}   <- the over-merge number")
    print(f"  B3 recall     {s.b3_recall:.4f}")
    print(f"  B3 F1         {s.b3_f1:.4f}")
    print(f"  macro purity  {s.macro_purity:.4f}   <- cluster-weighted")
    print(f"  clusters      {s.predicted_clusters} predicted vs {s.gold_clusters} gold")

    by_cluster: dict[str, list[str]] = {}
    for aid, eid in predicted.items():
        by_cluster.setdefault(eid, []).append(aid)
    print("\n  per predicted cluster holding >1 labelled article (worst purity first):")
    per = []
    for eid, aids in by_cluster.items():
        if len(aids) < 2:
            continue
        sub_p = {a: eid for a in aids}
        sub_g = {a: GOLD[a] for a in aids}
        per.append((score(sub_p, sub_g), eid, len(aids)))
    for ss, eid, n in sorted(per, key=lambda x: x[0].macro_purity)[:12]:
        print(f"    {eid[:8]}  n={n:3}  purity={ss.macro_purity:.3f}  real events inside={ss.gold_clusters}")


if __name__ == "__main__":
    asyncio.run(main())
