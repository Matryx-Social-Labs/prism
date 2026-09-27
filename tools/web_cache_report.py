"""Where the web stands on cost and speed. Read-only.

Vercel function calls and memory per UTC day (the bill), how many requests the
CDN answered from cache, and first/warm response times for the pages and API
calls readers and crawlers make, with the region that served them. Written for
the caching plan of 2026-09-27: run it before a change and at each gate after,
and compare the saved lines.

  uv run python -m tools.web_cache_report                       # last 8 days + timings
  uv run python -m tools.web_cache_report --save .context/review/cache-report.jsonl

Baseline, 2026-09-27: 162-177k function calls a day at the crawler peak,
0.16 GB-h of memory per 1,000 calls, functions in iad1 (Washington) calling an
API in asia-southeast1 (Singapore); the feed API 1.0-1.6 s on every call.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import statistics
import time
import urllib.request
from pathlib import Path

WEB = "https://www.readprism.news"
API = "https://api.readprism.news"
REPEATS = 3
_CLI_AUTH = Path.home() / "Library/Application Support/com.vercel.cli/auth.json"


def _token() -> str:
    return os.environ.get("VERCEL_TOKEN") or json.loads(_CLI_AUTH.read_text())["token"]


def _team() -> str:
    if os.environ.get("VERCEL_ORG_ID"):
        return os.environ["VERCEL_ORG_ID"]
    root = Path(__file__).resolve().parents[1]
    for p in (root / "web/.vercel/project.json", root / ".vercel/project.json"):
        if p.exists():
            return json.loads(p.read_text())["orgId"]
    raise SystemExit("no Vercel team: set VERCEL_ORG_ID or run `vercel link` in web/")


def usage(days: int) -> list[dict]:
    """One row per UTC day: function calls, memory GB-h, and CDN hits/misses."""
    now = dt.datetime.now(dt.UTC)
    since = (now - dt.timedelta(days=days)).strftime("%Y-%m-%dT00:00:00.000Z")
    url = (f"https://api.vercel.com/v2/usage?teamId={_team()}&type=requests"
           f"&from={since}&to={now.strftime('%Y-%m-%dT%H:%M:%S.000Z')}")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {_token()}"})
    rows = json.load(urllib.request.urlopen(req, timeout=30))["data"]
    out = []
    for r in rows:
        calls = r["function_invocation_successful_count"] + r["function_invocation_error_count"]
        gbh = r["function_execution_successful_gb_hours"] + r["function_execution_error_gb_hours"]
        out.append({"day": r["date"][:10], "calls": calls, "gb_h": round(gbh, 2),
                     "gb_h_per_1k": round(gbh / calls * 1000, 3) if calls else None,
                     "cdn_hit": r["request_hit_count"], "cdn_miss": r["request_miss_count"]})
    return out


def _fetch(url: str) -> tuple[float, int, dict]:
    """Seconds to the response headers, the status, and the headers."""
    req = urllib.request.Request(url, headers={"User-Agent": "prism-web-cache-report/1"})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            ttfb = time.perf_counter() - t
            r.read()
            return ttfb, r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        return time.perf_counter() - t, e.code, dict(e.headers)


def _targets() -> list[tuple[str, str]]:
    """The surfaces worth timing, with today's newest record and story in them."""
    feed = json.load(urllib.request.urlopen(f"{API}/api/v1/feed?limit=1", timeout=60))["items"]
    trending = json.load(urllib.request.urlopen(f"{API}/api/v1/trending?limit=1", timeout=60))["stories"]
    rid = feed[0]["id"] if feed else None
    slug = trending[0].get("slug") if trending else None
    pages = ["/", "/feed", "/trending", "/about", "/entity/india", "/subject/politics"]
    pages += [f"/story/{rid}"] if rid else []
    pages += [f"/trending/{slug}"] if slug else []
    calls = ["/api/v1/feed?sort=latest&limit=60", "/api/v1/trending?limit=24", "/api/v1/digest/markets"]
    calls += [f"/api/v1/events/{rid}"] if rid else []
    return [("web", WEB + p) for p in pages] + [("api", API + c) for c in calls]


def timings() -> list[dict]:
    out = []
    for kind, url in _targets():
        runs = [_fetch(url) for _ in range(REPEATS)]
        first, status, headers = runs[0]
        vid = headers.get("x-vercel-id") or headers.get("X-Vercel-Id") or ""
        out.append({
            "kind": kind, "url": url.split(".news", 1)[1], "status": status,
            "first_s": round(first, 3), "warm_s": round(statistics.median(r[0] for r in runs[1:]), 3),
            "cache": runs[-1][2].get("x-vercel-cache") or runs[-1][2].get("X-Vercel-Cache"),
            # "bom1::sin1::id": the edge that took the request, then the function region.
            "regions": "::".join(vid.split("::")[:-1]) or None,
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--days", type=int, default=8)
    ap.add_argument("--save", type=Path, help="append this run as one JSON line")
    args = ap.parse_args()

    days = usage(args.days)
    print(f"{'day':<11}{'calls':>9}{'GB-h':>8}{'GB-h/1k':>9}{'cdn hit':>9}{'cdn miss':>10}")
    for d in days:
        print(f"{d['day']:<11}{d['calls']:>9}{d['gb_h']:>8}{str(d['gb_h_per_1k']):>9}{d['cdn_hit']:>9}{d['cdn_miss']:>10}")
    rows = timings()
    print(f"\n{'':<4}{'url':<58}{'status':>7}{'first':>8}{'warm':>8}  cache  regions")
    for r in rows:
        print(f"{r['kind']:<4}{r['url'][:58]:<58}{r['status']:>7}{r['first_s']:>8}{r['warm_s']:>8}  "
              f"{(r['cache'] or '-'):<6} {r['regions'] or '-'}")
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        with args.save.open("a") as f:
            f.write(json.dumps({"at": dt.datetime.now(dt.UTC).isoformat(), "days": days, "timings": rows}) + "\n")
        print(f"\nsaved to {args.save}")


if __name__ == "__main__":
    main()
