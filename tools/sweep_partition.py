"""Offline harness for story-layer experiments. Snapshot once, sweep for free.

    uv run python -m tools.sweep_partition --snapshot     # pull graph from prod (read-only)
    uv run python -m tools.sweep_partition                # sweep against the snapshot

Every story-layer change until now was judged on structural proxies or, worse, on
a measurement taken over a slice restricted to the evaluation set — which inflates
any splitting rule (see the note in correlation/partition.py). This exists so a
configuration is scored the same way every time: full graph in, gold pairs out.

It is deliberately offline. The remaining work (CPM, resolution sweeps, attachment)
is pure local computation over data already collected, so it must not need a
database, a Railway session, or a single LLM call. Snapshot lives in
.cache/graph_snapshot.json.gz and is git-ignored.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import os
import statistics
from pathlib import Path

SNAPSHOT = Path(".cache/graph_snapshot.json.gz")


async def build_snapshot(path: Path = SNAPSHOT) -> None:
    """Pull nodes+edges from production, READ-ONLY, at a floor low enough that any
    threshold in the sweep can be reached by filtering rather than re-querying."""
    import re
    import subprocess

    raw = os.environ.get("REPAIR_DATABASE_URL")
    if not raw:
        out = subprocess.run(
            ["railway", "variables", "--service", "Postgres", "--kv"],
            capture_output=True, text=True, timeout=120,
        ).stdout
        raw = next(ln.split("=", 1)[1].strip() for ln in out.splitlines() if ln.startswith("DATABASE_URL="))
    os.environ["DATABASE_URL"] = re.sub(r"^postgres(ql)?(\+asyncpg)?://", "postgresql+asyncpg://", raw)

    import correlation.partition as P
    from common.db import session_scope

    P.PARTITION_MIN_EDGE_WEIGHT = 0.01  # widest useful graph; sweep filters upward
    async with session_scope() as s:
        nodes = await P._load_nodes(s)
        edges = await P._load_edges(s)

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "nodes": [
            {"id": n.id, "title": n.title, "sector": n.sector, "regions": n.regions,
             "occurred_at": str(n.occurred_at) if n.occurred_at else None,
             "source_count": n.source_count, "actors": n.actors}
            for n in nodes.values()
        ],
        "edges": [[a, b, w] for a, b, w in edges],
    }
    with gzip.open(path, "wt") as fh:
        json.dump(payload, fh)
    print(f"snapshot: {len(payload['nodes'])} nodes, {len(payload['edges'])} edges -> {path}")


def load_snapshot(path: Path = SNAPSHOT):
    from correlation.partition import Node

    if not path.exists():
        raise SystemExit(f"no snapshot at {path} — run with --snapshot first")
    with gzip.open(path, "rt") as fh:
        payload = json.load(fh)
    nodes = {
        d["id"]: Node(id=d["id"], title=d["title"], sector=d["sector"], regions=d["regions"],
                      occurred_at=d["occurred_at"], source_count=d["source_count"], actors=d["actors"])
        for d in payload["nodes"]
    }
    edges = [(a, b, float(w)) for a, b, w in payload["edges"]]
    return nodes, edges


def score(pred: dict[str, str], keys: set[str] | None = None) -> dict:
    """Delegates to tools.score_stories.score_pairs — one scorer, so a number here
    and a number there always mean the same thing."""
    from tools.score_stories import score_pairs

    return score_pairs(pred, keys)


def shape(labels: dict[str, int]) -> dict:
    sizes: dict[int, int] = {}
    for lbl in labels.values():
        sizes[lbl] = sizes.get(lbl, 0) + 1
    multi = [n for n in sizes.values() if n > 1]
    if not multi:
        return {"max": 0, "gt25": 0, "mean": 0.0, "groups": len(sizes)}
    return {
        "max": max(multi), "gt25": sum(1 for n in multi if n > 25),
        "mean": statistics.mean(multi), "groups": len(sizes),
    }


def run_config(nodes, edges, *, floor: float, method: str, res: float, gate: bool) -> dict:
    """One configuration end to end. `method` is 'rb' (modularity, current) or 'cpm'."""
    import igraph as ig
    import leidenalg

    import correlation.partition as P

    sub = [e for e in edges if e[2] >= floor]
    idx = {eid: i for i, eid in enumerate(nodes)}
    g = ig.Graph(n=len(idx))
    g.vs["name"] = list(nodes)
    weights = []
    for a, b, w in sub:
        if a in idx and b in idx:
            g.add_edge(idx[a], idx[b])
            weights.append(w)
    cls = leidenalg.CPMVertexPartition if method == "cpm" else leidenalg.RBConfigurationVertexPartition
    part = leidenalg.find_partition(
        g, cls, weights=weights or None, resolution_parameter=res, seed=42
    )
    labels = {g.vs[v]["name"]: c for c, members in enumerate(part) for v in members}
    if gate:
        labels = P.split_on_shared_content(labels, nodes)
    return {"labels": labels, "edges": len(sub)}


def cross_validate(nodes, edges, plans) -> None:
    """Tune on half the gold stories, report on the other half. Both directions.

    Picking the best of ~50 configs on 25 hand-labelled stories will find a sharp
    optimum whether or not one exists — the 0.012/0.40 cell scored Cdet 0.6009 while
    its neighbour 0.012/0.30 scored 0.8527, which is the shape of noise, not signal.
    A config that only wins on the fold it was chosen on is an artefact, and shipping
    it would repeat #131 with better arithmetic.
    """
    from tools.gold_stories import STORIES, STORY_OF

    keys = sorted(STORIES)
    # Deterministic, balanced split: alternate by sorted name so both folds carry
    # large and singleton stories rather than one fold getting all the easy ones.
    fold_a = {k for i, k in enumerate(keys) if i % 2 == 0}
    fold_b = set(keys) - fold_a
    print(f"fold A: {len(fold_a)} stories   fold B: {len(fold_b)} stories\n")

    cache = {}
    for method, res, floor in plans:
        for gate in (False, True):
            out = run_config(nodes, edges, floor=floor, method=method, res=res, gate=gate)
            cache[(method, res, floor, gate)] = {e: str(v) for e, v in out["labels"].items() if e in STORY_OF}

    for train, test, name in ((fold_a, fold_b, "A->B"), (fold_b, fold_a, "B->A")):
        best = min(cache, key=lambda k: score(cache[k], train)["Cdet"])
        tr, te = score(cache[best], train), score(cache[best], test)
        print(f"  {name}: tuned {best[0]} res={best[1]} floor={best[2]} gate={'ON' if best[3] else 'off'}")
        print(f"     train Cdet {tr['Cdet']:.4f} F1 {tr['F1']:.4f}  ->  HELD-OUT Cdet {te['Cdet']:.4f} F1 {te['F1']:.4f}")
        live = ("rb", 1.0, 0.50, True)
        if live in cache:
            lt = score(cache[live], test)
            print(f"     live config on the same held-out fold: Cdet {lt['Cdet']:.4f} F1 {lt['F1']:.4f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true", help="refresh the local graph snapshot")
    ap.add_argument("--floors", default="0.15,0.30,0.50")
    ap.add_argument("--cpm", default="0.02,0.05,0.10,0.20,0.40")
    ap.add_argument("--rb", default="1.0")
    ap.add_argument("--cv", action="store_true", help="tune on half the gold stories, report on the other half")
    a = ap.parse_args()

    if a.snapshot:
        asyncio.run(build_snapshot())
        return

    from tools.gold_stories import STORY_OF

    nodes, edges = load_snapshot()
    print(f"snapshot: {len(nodes)} nodes, {len(edges)} edges\n")
    plans_cv = [("rb", float(r), f) for r in a.rb.split(",") for f in map(float, a.floors.split(","))]
    plans_cv += [("cpm", float(r), f) for r in a.cpm.split(",") for f in map(float, a.floors.split(","))]
    if a.cv:
        cross_validate(nodes, edges, plans_cv)
        return
    hdr = f"{'method':7} {'res':>6} {'floor':>6} {'gate':>4} {'edges':>6} {'max':>4} {'>25':>4} {'mean':>5} | {'P':>6} {'R':>6} {'F1':>6} {'Cdet':>6} {'fp':>4} {'fn':>4}"
    print(hdr)
    print("-" * len(hdr))
    rows = []
    plans = [("rb", float(r), f) for r in a.rb.split(",") for f in map(float, a.floors.split(","))]
    plans += [("cpm", float(r), f) for r in a.cpm.split(",") for f in map(float, a.floors.split(","))]
    for method, res, floor in plans:
        for gate in (False, True):
            out = run_config(nodes, edges, floor=floor, method=method, res=res, gate=gate)
            sh = shape(out["labels"])
            sc = score({e: str(v) for e, v in out["labels"].items() if e in STORY_OF})
            rows.append((sc["Cdet"], method, res, floor, gate, sh, sc, out["edges"]))
            print(f"{method:7} {res:>6.3f} {floor:>6.2f} {'ON' if gate else 'off':>4} {out['edges']:>6} "
                  f"{sh['max']:>4} {sh['gt25']:>4} {sh['mean']:>5.2f} | {sc['P']:>6.4f} {sc['R']:>6.4f} "
                  f"{sc['F1']:>6.4f} {sc['Cdet']:>6.4f} {sc['fp']:>4} {sc['fn']:>4}")
    best = min(rows, key=lambda r: r[0])
    print(f"\nbest by Cdet: {best[1]} res={best[2]} floor={best[3]} gate={'ON' if best[4] else 'off'} "
          f"-> Cdet {best[6]['Cdet']:.4f}  F1 {best[6]['F1']:.4f}  max {best[5]['max']}")


if __name__ == "__main__":
    main()
