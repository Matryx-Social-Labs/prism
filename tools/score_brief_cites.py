"""How much of the free brief is evidenced: the trust plan's Phase 2 number.

For the newest records with a reader brief, splits the brief into the lines the
page prints and asks correlation/cites.py which report each line restates and
whether every figure it states is in that report. Read-only and model-free, so
it runs against production over the proxy as safely as against the local DB.

    uv run python -m tools.score_brief_cites                 # newest 300 records
    uv run python -m tools.score_brief_cites --limit 1000 --show 10

Reports, by how a line was cited and by the record's report languages: lines
cited, lines whose figures are all in a cited report ("supported"), lines with a
figure no report contains (the zero-tolerance count), and lines cited to nothing.
This is the machine's view; the plan's gate (99.5% of reported lines evidenced)
is measured on a human-labelled sample of these same lines.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict

from sqlalchemy import text

from common.db import session_scope
from correlation.cites import cite_lines, figures

_RECORDS = text(
    """
    SELECT e.id, e.projection -> 'lens_briefs' ->> 'reader' AS brief
    FROM events e
    WHERE e.projection -> 'lens_briefs' ->> 'reader' IS NOT NULL
    ORDER BY e.last_updated_at DESC
    LIMIT :limit
    """
)
_REPORTS = text(
    """
    SELECT a.id, a.clean_text, ri.language
    FROM event_memberships em
    JOIN articles a ON a.id = em.article_id
    JOIN raw_items ri ON ri.id = a.raw_item_id
    WHERE em.event_id = :eid
    """
)


async def score(limit: int, show: int) -> dict:
    by_method: Counter = Counter()
    tally: dict[str, Counter] = defaultdict(Counter)
    unsupported: list[tuple[str, str]] = []
    async with session_scope() as s:
        records = (await s.execute(_RECORDS, {"limit": limit})).all()
        for eid, brief in records:
            rows = (await s.execute(_REPORTS, {"eid": eid})).all()
            langs = "+".join(sorted({r[2] or "?" for r in rows})) or "none"
            for line in cite_lines(brief, [(r[0], r[1]) for r in rows]):
                t = tally[langs]
                t["lines"] += 1
                by_method[line["method"]] += 1
                t["cited"] += bool(line["cites"])
                t["supported"] += line["supported"]
                if line["cites"] and figures(line["text"]) and not line["supported"]:
                    t["figure_missing"] += 1
                    unsupported.append((str(eid), line["text"]))
    total = Counter()
    for t in tally.values():
        total.update(t)
    return {"records": len(records), "total": total, "by_method": by_method, "by_langs": tally, "unsupported": unsupported[:show]}


def _pct(n: int, d: int) -> str:
    return f"{n} of {d}" if d < 30 else f"{100 * n / d:.1f}%"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=300, help="newest N records with a reader brief")
    ap.add_argument("--show", type=int, default=5, help="print N lines with a figure no report contains")
    args = ap.parse_args()
    r = asyncio.run(score(args.limit, args.show))
    t = r["total"]
    print(f"{r['records']} records, {t['lines']} lines")
    print(f"  cited to a report      {_pct(t['cited'], t['lines'])}")
    print(f"  figures all in report  {_pct(t['supported'], t['lines'])}")
    print(f"  a figure not in report {t['figure_missing']} lines (zero tolerance)")
    print("  by method: " + ", ".join(f"{k} {v}" for k, v in r["by_method"].most_common()))
    for langs, c in sorted(r["by_langs"].items(), key=lambda kv: -kv[1]["lines"]):
        print(f"  {langs:<14} lines {c['lines']:>5}  cited {_pct(c['cited'], c['lines']):>9}  supported {_pct(c['supported'], c['lines']):>9}")
    for eid, line in r["unsupported"]:
        print(f"  ! {eid}  {line}")


if __name__ == "__main__":
    main()
