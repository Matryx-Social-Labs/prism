"""Score production's clustering against the hand labels. Read-only.

    uv run python -m tools.score_clustering

Prints B-cubed, macro purity and cluster counts for the labelled slice, overall
and per predicted cluster. Run it before and after any change to
correlation/clustering.py so the change is argued against a number.

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
from collections import defaultdict

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


async def fetch_membership(c: asyncpg.Connection) -> dict[str, list[dict]]:
    """Articles of every labelled event, in the publication order the labels index."""
    rows = await c.fetch(
        """
        SELECT em.article_id::text AS aid, em.event_id::text AS eid,
               ri.title, ri.published_at
        FROM event_memberships em
        JOIN articles ar ON ar.id = em.article_id
        JOIN raw_items ri ON ri.id = ar.raw_item_id
        WHERE left(em.event_id::text, 8) = ANY($1::text[])
        ORDER BY em.event_id, ri.published_at
        """,
        list(GOLD.keys()),
    )
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by[r["eid"]].append(dict(r))
    return dict(by)


async def main() -> None:
    c = await asyncpg.connect(_db_url(), timeout=60)
    try:
        await c.execute("SET default_transaction_read_only = on")
        by = await fetch_membership(c)
    finally:
        await c.close()

    predicted: dict[str, str] = {}
    gold: dict[str, str] = {}
    drift: list[str] = []

    for eid, rows in sorted(by.items(), key=lambda kv: -len(kv[1])):
        labels = GOLD[eid[:8]]
        # The labels are positional. If the event has gained or lost members since
        # labelling, the indices no longer mean what they meant — say so loudly
        # rather than scoring a silently misaligned set.
        if len(rows) != len(labels):
            drift.append(f"{eid[:8]}: labelled {len(labels)}, now {len(rows)}")
            continue
        for i, r in enumerate(rows):
            predicted[r["aid"]] = eid
            gold[r["aid"]] = labels[i]

    print(f"gold: {labelled_article_count()} articles, {gold_event_count()} real events")
    if drift:
        print("\n!! MEMBERSHIP DRIFT — these events changed since labelling and were SKIPPED:")
        for d in drift:
            print(f"     {d}")
        print("   Re-label them before trusting the totals below.")

    s = score(predicted, gold)
    print(f"\nscored {s.items} articles")
    print(f"  B3 precision  {s.b3_precision:.4f}   <- the over-merge number")
    print(f"  B3 recall     {s.b3_recall:.4f}   <- near 1.0 by construction, see docstring")
    print(f"  B3 F1         {s.b3_f1:.4f}")
    print(f"  macro purity  {s.macro_purity:.4f}   <- cluster-weighted")
    print(f"  clusters      {s.predicted_clusters} predicted vs {s.gold_clusters} gold")

    print("\n  per predicted cluster (worst first):")
    per = []
    for eid, rows in by.items():
        labels = GOLD[eid[:8]]
        if len(rows) != len(labels):
            continue
        sub_p = {r["aid"]: eid for r in rows}
        sub_g = {r["aid"]: labels[i] for i, r in enumerate(rows)}
        per.append((score(sub_p, sub_g), eid, rows[0]["title"]))
    for ss, eid, title in sorted(per, key=lambda x: x[0].macro_purity):
        print(f"    {eid[:8]}  n={ss.items:3}  purity={ss.macro_purity:.3f}  "
              f"real events inside={ss.gold_clusters:3}  {(title or '')[:44]}")


if __name__ == "__main__":
    asyncio.run(main())
