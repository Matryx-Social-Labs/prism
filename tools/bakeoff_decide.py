"""Does Jev agree with the LLM gate and classifier — and in Kannada? Measured.

Replays production raw_items the LLM pair already labelled through the one
typed Jev call (classification/decide.py) and prints agreement per language
and per sector, plus the confusion pairs, plus what a confidence floor would
send back to the LLM. The sample is stratified by language because Kannada is
a third of the corpus and Jev's multilingual behaviour is undocumented.

  uv run python -m tools.bakeoff_decide --per-language 150 --floor 0.6

Reads production (read-only). Spends ~$0.00005 an item: 600 items is 3 cents.
Writes .cache/bakeoff_decide.json so the numbers can be quoted later.

The LLM's labels are a silver standard, not gold: where the two disagree, read
the confusion pairs before deciding who was wrong. The gold sets
(evals/datasets/relevance.jsonl, classification.jsonl) are the tie-breaker —
run `evals/run_all.py --backend decide` for those.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import asyncpg

from classification.decide import QUESTIONS, decided_confidence, state_for, to_results
from common.decisions import _ANSWER, Decisions, decide
from tools.snapshot_l2 import _prod_url

OUT = Path(".cache/bakeoff_decide.json")
SAMPLE_SEED = 0.23
CONCURRENCY = 8
LANGUAGES = ("en", "kn", "hi")


async def sample(per_language: int) -> list[dict]:
    c = await asyncpg.connect(_prod_url(), timeout=180)
    try:
        await c.execute("SET default_transaction_read_only = on")
        await c.execute("SELECT setseed($1)", SAMPLE_SEED)
        rows: list[dict] = []
        for lang in LANGUAGES:
            # Relevant items carry the language the classifier saw; rejected ones carry
            # none, so they are sampled by the source's language to keep the mix honest.
            rows += [dict(r) for r in await c.fetch(
                """
                (SELECT ri.id::text AS id, ri.title, ri.body, s.slug AS src, s.country AS source_country,
                        ri.relevance, ri.classification, ri.classification->>'language' AS language
                 FROM raw_items ri JOIN sources s ON s.id = ri.source_id
                 WHERE ri.relevance = 'relevant' AND s.source_type <> 'cve_feed'
                   AND ri.classification->>'language' = $1
                   AND ri.classified_at > now() - interval '14 days'
                 ORDER BY random() LIMIT $2)
                UNION ALL
                (SELECT ri.id::text, ri.title, ri.body, s.slug, s.country, ri.relevance, NULL, $1
                 FROM raw_items ri JOIN sources s ON s.id = ri.source_id
                 WHERE ri.relevance = 'rejected' AND s.source_type <> 'cve_feed'
                   AND coalesce(s.language, 'en') = $1
                   AND ri.classified_at > now() - interval '14 days'
                 ORDER BY random() LIMIT $3)
                """,
                lang, int(per_language * 0.75), per_language - int(per_language * 0.75),
            )]
        return rows
    finally:
        await c.close()


async def judge(rows: list[dict]) -> list[dict]:
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(r: dict) -> dict:
        async with sem:
            try:
                d = await decide(state_for(r["title"], r["body"]), QUESTIONS, trace_name="bakeoff-decide")
            except Exception as exc:  # noqa: BLE001 — a failed item is a row in the table, not a crash
                return {**r, "error": f"{type(exc).__name__}: {str(exc)[:120]}"}
        gate, cls = to_results(d, source_country=r["source_country"])
        return {
            **r,
            "jev_relevant": gate.is_relevant,
            "jev": cls.model_dump() if cls else None,
            "confidence": round(decided_confidence(d), 3),
            "cost": d.usage.cost,
            "raw": {k: v.model_dump() for k, v in d.answers.items()},
        }

    return await asyncio.gather(*(one(r) for r in rows))


def rescore(r: dict) -> dict:
    """The cached raw answers through today's to_results — thresholds are tuned here, not re-bought."""
    if "error" in r:
        return r
    d = Decisions(answers={k: _ANSWER.validate_python(v) for k, v in r["raw"].items()})
    gate, cls = to_results(d, source_country=r["source_country"])
    return {**r, "jev_relevant": gate.is_relevant, "jev": cls.model_dump() if cls else None,
            "confidence": round(decided_confidence(d), 3)}


def report(rows: list[dict], floor: float) -> dict:
    by_lang: dict[str, Counter] = defaultdict(Counter)
    by_sector: dict[str, Counter] = defaultdict(Counter)
    confusions: Counter = Counter()
    gate_confusions: Counter = Counter()
    fallback = Counter()
    cost = 0.0
    for r in rows:
        if "error" in r:
            by_lang[r["language"]]["error"] += 1
            continue
        cost += r["cost"]
        lang = r["language"]
        llm_rel = r["relevance"] == "relevant"
        c = by_lang[lang]
        c["n"] += 1
        c["gate_agree"] += r["jev_relevant"] == llm_rel
        if r["confidence"] < floor:
            fallback[lang] += 1
        if r["jev_relevant"] != llm_rel:
            gate_confusions[(f"llm={r['relevance']}", f"jev={'relevant' if r['jev_relevant'] else 'rejected'}", lang)] += 1
        llm = r["classification"] if isinstance(r["classification"], dict) else (json.loads(r["classification"]) if r["classification"] else None)
        jev = r["jev"]
        if not (llm and jev):
            continue
        c["classified"] += 1
        same = llm["sector"] == jev["sector"]
        c["sector_agree"] += same
        by_sector[llm["sector"]]["n"] += 1
        by_sector[llm["sector"]]["agree"] += same
        if not same:
            confusions[(llm["sector"], jev["sector"], lang)] += 1
        c["subsector_agree"] += llm.get("subsector") == jev.get("subsector")
        c["state_agree"] += {x for x in llm.get("regions", []) if "-" in x} == {x for x in jev["regions"] if "-" in x}
        c["route_agree"] += llm.get("route") == jev["route"]
        c["lenses_agree"] += sorted(llm.get("role_interests", [])) == sorted(jev["role_interests"])
        c["language_agree"] += llm.get("language") == jev["language"]

    def pct(c: Counter, k: str, d: str) -> str:
        return f"{100 * c[k] / c[d]:5.1f}%" if c[d] else "    -"

    print(f"\n{'lang':5} {'n':>4} {'gate':>6} {'sector':>7} {'subsec':>7} {'state':>6} {'route':>6} {'lenses':>7} {'lang':>6} {'<floor':>7} {'err':>4}")
    for lang, c in sorted(by_lang.items()):
        print(f"{lang:5} {c['n']:4d} {pct(c, 'gate_agree', 'n')} {pct(c, 'sector_agree', 'classified'):>7} "
              f"{pct(c, 'subsector_agree', 'classified'):>7} {pct(c, 'state_agree', 'classified'):>6} "
              f"{pct(c, 'route_agree', 'classified'):>6} {pct(c, 'lenses_agree', 'classified'):>7} "
              f"{pct(c, 'language_agree', 'classified'):>6} {fallback[lang]:7d} {c['error']:4d}")
    print("\nsector (LLM's label)   n   agree")
    for sector, c in sorted(by_sector.items(), key=lambda kv: -kv[1]["n"]):
        print(f"  {sector:20} {c['n']:4d} {pct(c, 'agree', 'n')}")
    print("\ngate disagreements (llm, jev, lang):")
    for k, n in gate_confusions.most_common(10):
        print(f"  {n:4d}  {k}")
    print("\nsector confusions (llm -> jev, lang):")
    for k, n in confusions.most_common(15):
        print(f"  {n:4d}  {k[0]} -> {k[1]}  [{k[2]}]")
    print(f"\ncost ${cost:.4f} for {sum(c['n'] for c in by_lang.values())} items; floor {floor} would send "
          f"{sum(fallback.values())} back to the LLM")
    return {"by_language": {k: dict(v) for k, v in by_lang.items()},
            "by_sector": {k: dict(v) for k, v in by_sector.items()},
            "sector_confusions": [(k, n) for k, n in confusions.most_common()],
            "gate_confusions": [(k, n) for k, n in gate_confusions.most_common()],
            "fallback_under_floor": dict(fallback), "floor": floor, "cost_usd": cost}


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-language", type=int, default=150)
    ap.add_argument("--floor", type=float, default=0.8, help="confidence floor to simulate")
    ap.add_argument("--from-cache", action="store_true",
                    help="re-score the last run's raw answers with the current thresholds; no API spend")
    args = ap.parse_args()
    if args.from_cache:
        judged = [rescore(r) for r in json.loads(OUT.read_text())["rows"]]
    else:
        rows = await sample(args.per_language)
        print(f"sampled {len(rows)} items", file=sys.stderr)
        judged = await judge(rows)
    summary = report(judged, args.floor)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "rows": judged}, indent=1, default=str))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
