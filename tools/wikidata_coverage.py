"""How much of our entity vocabulary actually exists in Wikidata? Read-only.

    uv run python -m tools.wikidata_coverage

The QID plan assumes Wikidata knows our entities. For Modi and the BJP that is
obviously true; for a district collector, a ward councillor or a small regional
party it may not be, and India's news is full of those. If most rows fall to the
`local` fallback namespace then QIDs buy far less than the design assumes, and
the honest scope shrinks to "fold the 39 known split slugs" rather than a linking
subsystem.

Measured BEFORE building the linker, deliberately: it is the difference between a
week of work and an afternoon.

Two samples, because they answer different questions:
  - TOP by document frequency: the entities that actually drive clustering, where
    a wrong or missing link costs the most.
  - UNIFORM random: what the long tail looks like, which is what decides whether
    the fallback path is an edge case or the main path.
  - RANDOM among df >= 2: the number that actually decides the design. An entity
    appearing in ONE event can never form a shared-actor edge, so it is
    clustering-inert and its coverage is irrelevant.

RESULT, 2026-08-28 (n=100 per sample):

    TOP by document frequency        97% found
    RANDOM among df >= 2             72% found     <- the decision number
    UNIFORM random (incl. df 1)      34% found

So the entities that matter are well covered and the tail is not, which is the
good shape: every miss in the uniform sample was df 1 — "G. Ravikumar",
"Veeranagouda Patil Bayyapur" — exactly the local figures predicted, and exactly
the ones that cannot affect clustering.

72% IS A LOWER BOUND. This probe uses a single exact-string English
wbsearchentities call, and that misses variants it should catch:

    "Pakistan Muslim League-Nawaz"  -> NO HIT
    "Pakistan Muslim League (N)"    -> Q799577

Same party. So the real ceiling is higher, and the failure is precisely the one
the linker exists to fix. It also settles a design question: candidate generation
must run against a LOCAL ALIAS INDEX built from Wikidata labels+aliases, not
against live exact search, because exact search cannot see the alias that would
have matched.

CONCLUSION: QID linking is viable and worth its scope. The `local` fallback
namespace is for the df-1 tail, where it costs nothing.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import urllib.parse
import urllib.request

API = "https://www.wikidata.org/w/api.php"
UA = "Prism/1.0 (+https://www.readprism.news) entity-coverage-probe"


def _search(name: str, lang: str = "en") -> dict | None:
    """First wbsearchentities hit for `name`, or None."""
    q = urllib.parse.urlencode({
        "action": "wbsearchentities", "search": name, "language": lang,
        "uselang": lang, "type": "item", "limit": 1, "format": "json",
    })
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310 - fixed https host
            hits = json.load(r).get("search") or []
    except Exception:
        return None
    return hits[0] if hits else None


async def run(n: int) -> None:
    import asyncpg

    from tools.scratch import _prod_url

    c = await asyncpg.connect(_prod_url(), timeout=120)
    try:
        await c.execute("SET default_transaction_read_only = on")
        top = await c.fetch(
            """SELECT ent.name, count(DISTINCT ee.event_id) AS df
               FROM entities ent JOIN event_entities ee ON ee.entity_id = ent.id
               WHERE ent.entity_type IN ('person','organization','company')
               GROUP BY ent.name ORDER BY df DESC LIMIT $1""", n)
        rand = await c.fetch(
            """SELECT ent.name, count(DISTINCT ee.event_id) AS df
               FROM entities ent JOIN event_entities ee ON ee.entity_id = ent.id
               WHERE ent.entity_type IN ('person','organization','company')
               GROUP BY ent.name ORDER BY random() LIMIT $1""", n)
        # The number that actually decides the design. An entity in ONE event can
        # never form a shared-actor edge, so its Wikidata coverage is irrelevant to
        # clustering — it is inert. Restricting to df >= 2 asks the real question:
        # of the entities that CAN link two events, how many can we canonicalise?
        linking = await c.fetch(
            """SELECT ent.name, count(DISTINCT ee.event_id) AS df
               FROM entities ent JOIN event_entities ee ON ee.entity_id = ent.id
               WHERE ent.entity_type IN ('person','organization','company')
               GROUP BY ent.name HAVING count(DISTINCT ee.event_id) >= 2
               ORDER BY random() LIMIT $1""", n)
        share = await c.fetchval(
            """SELECT round(100.0 * count(*) FILTER (WHERE df >= 2) / count(*), 1) FROM (
                 SELECT count(DISTINCT ee.event_id) AS df
                 FROM entities ent JOIN event_entities ee ON ee.entity_id = ent.id
                 WHERE ent.entity_type IN ('person','organization','company')
                 GROUP BY ent.name) x""")
        print(f"  entities that can form an edge (df >= 2): {share}% of the vocabulary")
    finally:
        await c.close()

    for label, rows in (("TOP by document frequency", top), ("UNIFORM random", rand),
                        ("RANDOM among df >= 2 (can actually link)", linking)):
        hits = misses = 0
        examples: list[str] = []
        for r in rows:
            hit = await asyncio.to_thread(_search, r["name"])
            if hit:
                hits += 1
            else:
                misses += 1
                if len(examples) < 6:
                    examples.append(f'{r["name"]} (df {r["df"]})')
        total = hits + misses
        print(f"\n=== {label} — {total} entities ===")
        print(f"  found in Wikidata : {hits:4}  ({hits / total:.1%})")
        print(f"  NOT found         : {misses:4}  ({misses / total:.1%})")
        if examples:
            print("  misses:")
            for e in examples:
                print(f"    - {e}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=120, help="entities per sample")
    a = ap.parse_args()
    asyncio.run(run(a.n))


if __name__ == "__main__":
    main()
